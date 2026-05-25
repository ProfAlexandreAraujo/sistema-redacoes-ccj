"""
harmonizer.py — Motor de harmonização legislativa
Sistema de Redações — CCJ CMRJ
"""

import re
import json
import anthropic
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class TipoEmenda(Enum):
    MODIFICATIVA  = "Modificativa"
    SUPRESSIVA    = "Supressiva"
    ADITIVA       = "Aditiva"
    SUBSTITUTIVA  = "Substitutiva"
    AGLUTINATIVA  = "Aglutinativa"
    OUTRO         = "Outro"


class StatusEmenda(Enum):
    PENDENTE     = "Pendente"
    APROVADA     = "Aprovada"
    REJEITADA    = "Rejeitada"
    PREJUDICADA  = "Prejudicada"


@dataclass
class Emenda:
    numero: int
    texto_bruto: str
    tipo: Optional[TipoEmenda] = None
    alvo: Optional[str] = None          # "Art. 5º", "Art. 5º, §2º, I", "Anexo II"
    novo_texto: Optional[str] = None    # Para modificativa/aditiva/substitutiva
    autor: Optional[str] = None
    status: StatusEmenda = StatusEmenda.PENDENTE
    parseada: bool = False
    notas_parse: Optional[str] = None   # Observações do parsing automático

    def to_dict(self) -> dict:
        d = asdict(self)
        d['tipo']   = self.tipo.value if self.tipo else None
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Emenda":
        tipo_map   = {t.value: t for t in TipoEmenda}
        status_map = {s.value: s for s in StatusEmenda}
        e = cls(
            numero     = d['numero'],
            texto_bruto = d['texto_bruto'],
            tipo       = tipo_map.get(d.get('tipo') or ''),
            alvo       = d.get('alvo'),
            novo_texto = d.get('novo_texto'),
            autor      = d.get('autor'),
            status     = status_map.get(d.get('status') or 'Pendente', StatusEmenda.PENDENTE),
            parseada   = d.get('parseada', False),
            notas_parse = d.get('notas_parse'),
        )
        return e


@dataclass
class ResultadoHarmonizacao:
    texto_harmonizado: str
    avisos: list[str] = field(default_factory=list)
    erros_criticos: list[str] = field(default_factory=list)
    mapa_renumeracao: dict = field(default_factory=dict)
    log_alteracoes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# PARSING DE EMENDAS COM IA
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(text: str, max_chars: int = 40_000) -> list[str]:
    """Divide texto longo em partes menores, respeitando separadores naturais."""
    if len(text) <= max_chars:
        return [text]

    chunks, current = [], []
    current_len = 0
    for line in text.split('\n'):
        if current_len + len(line) > max_chars and current:
            chunks.append('\n'.join(current))
            current, current_len = [], 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append('\n'.join(current))
    return chunks


def parsear_emendas_com_ia(texto_emendas: str, api_key: str) -> list[Emenda]:
    """
    Usa Claude para identificar e estruturar emendas a partir de um texto bruto.
    Divide em lotes se o texto for muito longo.
    """
    client = anthropic.Anthropic(api_key=api_key)
    chunks = _chunk_text(texto_emendas, max_chars=60_000)
    todas_emendas: list[Emenda] = []
    offset = 0

    for chunk in chunks:
        prompt = f"""Você é especialista em técnica legislativa municipal brasileira.

Analise o texto abaixo contendo emendas a um projeto de lei da Câmara Municipal do Rio de Janeiro.
Extraia CADA emenda separadamente em formato JSON.

Para cada emenda, identifique:
- numero: número da emenda (inteiro; se não houver, use sequência a partir de {offset + 1})
- tipo: "Modificativa" | "Supressiva" | "Aditiva" | "Substitutiva" | "Aglutinativa" | "Outro"
- alvo: dispositivo afetado (ex: "Art. 5º", "Art. 10, §3º", "Inciso II do Art. 7º", "Anexo I", etc.) ou null
- novo_texto: para Modificativa/Aditiva/Substitutiva, o texto novo a ser inserido; null para Supressiva
- autor: nome do vereador autor, se mencionado; null caso contrário
- notas: observações relevantes (ex: emenda está incompleta, referência ambígua, etc.) ou null

Responda SOMENTE com JSON válido no formato:
{{"emendas": [
  {{"numero": 1, "tipo": "Modificativa", "alvo": "Art. 5º", "novo_texto": "...", "autor": "Fulano", "notas": null}},
  ...
]}}

TEXTO DAS EMENDAS:
{chunk}"""

        try:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}]
            )
            resp_text = resp.content[0].text

            # Extrai JSON da resposta
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if not match:
                continue
            data = json.loads(match.group())

            for item in data.get("emendas", []):
                tipo_map = {t.value: t for t in TipoEmenda}
                e = Emenda(
                    numero      = item.get("numero", offset + len(todas_emendas) + 1),
                    texto_bruto = item.get("novo_texto") or "",
                    tipo        = tipo_map.get(item.get("tipo") or "", TipoEmenda.OUTRO),
                    alvo        = item.get("alvo"),
                    novo_texto  = item.get("novo_texto"),
                    autor       = item.get("autor"),
                    parseada    = True,
                    notas_parse = item.get("notas"),
                )
                todas_emendas.append(e)

        except (json.JSONDecodeError, KeyError, IndexError):
            # Se parsing falhar, cria emendas brutas
            partes = re.split(r'\n(?=EMENDA\s)', chunk, flags=re.IGNORECASE)
            for parte in partes:
                if parte.strip():
                    num = offset + len(todas_emendas) + 1
                    todas_emendas.append(Emenda(
                        numero=num, texto_bruto=parte.strip(), parseada=False,
                        notas_parse="Parsing automático falhou — revisar manualmente"
                    ))

        offset += len(todas_emendas)

    # Garante unicidade e ordenação por número
    todas_emendas.sort(key=lambda e: e.numero)
    return todas_emendas


# ─────────────────────────────────────────────────────────────────────────────
# HARMONIZAÇÃO COM IA
# ─────────────────────────────────────────────────────────────────────────────

def harmonizar_texto(
    texto_original: str,
    emendas: list[Emenda],
    api_key: str,
    nome_projeto: str = ""
) -> ResultadoHarmonizacao:
    """
    Aplica as emendas aprovadas ao projeto original e retorna o texto harmonizado.
    Detecta problemas de renumeração, referências cruzadas e técnica legislativa.
    """
    client = anthropic.Anthropic(api_key=api_key)
    aprovadas = [e for e in emendas if e.status == StatusEmenda.APROVADA]

    if not aprovadas:
        return ResultadoHarmonizacao(
            texto_harmonizado=texto_original,
            log_alteracoes=["Nenhuma emenda aprovada. Texto original mantido."]
        )

    # Monta o sumário das emendas aprovadas
    linhas_emendas = []
    for e in aprovadas:
        tipo_str = e.tipo.value if e.tipo else "Tipo não informado"
        alvo_str = e.alvo or "alvo não especificado"
        autor_str = f" | Autor: {e.autor}" if e.autor else ""
        linhas_emendas.append(
            f"── EMENDA Nº {e.numero} ({tipo_str}) | Alvo: {alvo_str}{autor_str}\n"
            f"{e.novo_texto or e.texto_bruto}"
        )
    bloco_emendas = "\n\n".join(linhas_emendas)

    prompt = f"""Você é o assessor jurídico da Comissão de Constituição, Justiça e Redação (CCJ) da Câmara Municipal do Rio de Janeiro, responsável pela elaboração da Redação Final nos termos do art. 250 do Regimento Interno (Resolução nº 1.673/2025).

{"PROJETO: " + nome_projeto if nome_projeto else ""}

══════════════════════════════════════════════════════
REGRAS ABSOLUTAS (não podem ser violadas):
══════════════════════════════════════════════════════

1. PRESERVAÇÃO DO TEOR: Jamais altere o conteúdo substantivo de nenhuma emenda aprovada. O texto aprovado pelo Plenário é soberano. Incorpore-o exatamente como está.

2. RENUMERAÇÃO: Após aplicar emendas supressivas ou aditivas, renumere artigos, parágrafos, incisos e alíneas em ordem sequencial. Artigos: ordinal (1º, 2º, 3º...). Parágrafos: §1º, §2º... ou "Parágrafo único" se houver apenas um. Incisos: romanos (I, II, III...). Alíneas: letras minúsculas (a, b, c...).

3. REFERÊNCIAS CRUZADAS: Atualize automaticamente toda referência interna ao texto (ex: "conforme o art. 10" → se art. 10 virou art. 9 por supressão, corrija para "conforme o art. 9"). Esta é a única alteração que você pode fazer sem autorização expressa.

4. AVISOS (não corrige, apenas aponta):
   - Erros de ortografia ou concordância no texto das emendas
   - Referências a dispositivos que foram suprimidos
   - Emendas que conflitam entre si
   - Dispositivos que ficaram sem nexo
   - Técnica legislativa ruim (ex: parágrafo único quando há mais de um parágrafo)

5. ERROS CRÍTICOS: Se houver contradição evidente entre duas emendas aprovadas que torne impossível a harmonização sem alterar o teor, aponte como ERRO CRÍTICO (não tente resolver).

══════════════════════════════════════════════════════
TEXTO ORIGINAL DO PROJETO:
══════════════════════════════════════════════════════
{texto_original}

══════════════════════════════════════════════════════
EMENDAS APROVADAS (aplicar nesta ordem):
══════════════════════════════════════════════════════
{bloco_emendas}

══════════════════════════════════════════════════════
RESPONDA EXATAMENTE NESTE FORMATO:
══════════════════════════════════════════════════════

<TEXTO_HARMONIZADO>
[Texto completo do projeto com todas as emendas aplicadas e renumeração atualizada]
</TEXTO_HARMONIZADO>

<MAPA_RENUMERACAO>
[Linha por linha: "Art. X → Art. Y" ou "§ X do Art. N → §Y do Art. M" para cada mudança de número]
[Escreva "Sem renumeração necessária." se não houver]
</MAPA_RENUMERACAO>

<AVISOS>
[Um aviso por linha. Formato: "Emenda N / Art. X: descrição do problema"]
[Escreva "Nenhum aviso." se não houver]
</AVISOS>

<ERROS_CRITICOS>
[Um erro por linha. Formato: "Emendas N e M conflitam em: descrição"]
[Escreva "Nenhum erro crítico." se não houver]
</ERROS_CRITICOS>

<LOG_ALTERACOES>
[Um registro por linha das alterações aplicadas: "Emenda N (Tipo): ação realizada"]
</LOG_ALTERACOES>"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}]
    )
    resp_text = resp.content[0].text

    def extrair(tag: str, default: str = "") -> str:
        m = re.search(rf'<{tag}>(.*?)</{tag}>', resp_text, re.DOTALL)
        return m.group(1).strip() if m else default

    texto_harm  = extrair("TEXTO_HARMONIZADO", texto_original)
    mapa_raw    = extrair("MAPA_RENUMERACAO", "")
    avisos_raw  = extrair("AVISOS", "")
    erros_raw   = extrair("ERROS_CRITICOS", "")
    log_raw     = extrair("LOG_ALTERACOES", "")

    # Mapa de renumeração
    mapa = {}
    for linha in mapa_raw.splitlines():
        if '→' in linha or '->' in linha:
            partes = linha.replace('->', '→').split('→')
            if len(partes) == 2:
                mapa[partes[0].strip()] = partes[1].strip()

    def parse_linhas(raw: str) -> list[str]:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if lines == ["Nenhum aviso."] or lines == ["Nenhum erro crítico."] or lines == ["Sem renumeração necessária."]:
            return []
        return lines

    return ResultadoHarmonizacao(
        texto_harmonizado = texto_harm,
        avisos            = parse_linhas(avisos_raw),
        erros_criticos    = parse_linhas(erros_raw),
        mapa_renumeracao  = mapa,
        log_alteracoes    = parse_linhas(log_raw),
    )
