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
    alertas_absurdos: list[str] = field(default_factory=list)  # 🔴 Absurdo manifesto
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
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                resp_text = stream.get_final_text()

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

    prompt = f"""Você é o assessor jurídico da Comissão de Constituição, Justiça e Redação (CCJ) da Câmara Municipal do Rio de Janeiro, responsável pela elaboração da REDAÇÃO FINAL nos termos do art. 250 do Regimento Interno (Resolução nº 1.673/2025).

{"PROJETO: " + nome_projeto if nome_projeto else ""}

╔══════════════════════════════════════════════════════════════╗
║  NORMAS DE TÉCNICA LEGISLATIVA APLICÁVEIS                    ║
║  LC 95/1998 (federal) · Decreto 12.002/2024 · LC 48/2000 RJ ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCO A — REGRAS ABSOLUTAS (jamais podem ser violadas)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A1. PRESERVAÇÃO DO TEOR (art. 250 RI / soberania do Plenário)
    Jamais altere o conteúdo substantivo de nenhuma emenda aprovada.
    O texto aprovado pelo Plenário é soberano e deve ser incorporado exatamente como votado.
    A única modificação automática permitida é a atualização de referências cruzadas internas
    decorrente de renumeração. Qualquer outra alteração é vedada.

A2. REFERÊNCIAS CRUZADAS (única alteração automática permitida)
    Após renumerar artigos, atualize TODAS as referências internas:
    — "conforme o art. 10" → se art. 10 virou art. 8, corrija para "conforme o art. 8"
    — "nos termos do § 2º do art. 5º" → atualize ambos os números se houver mudança
    — "previsto no inciso III" → atualize se o inciso foi renumerado
    Nunca use as expressões "anterior", "seguinte" ou equivalentes vagas (LC 48/2000, art. 10, II, g).

A3. ANEXOS (preservação integral obrigatória)
    Os Anexos (mapas, quadros, tabelas, delimitações georreferenciadas) integram a lei mas
    NÃO devem ser renumerados nem alterados, salvo emenda expressa sobre eles.
    Preserve o conteúdo de cada Anexo exatamente como consta no projeto original, inclusive
    coordenadas UTM, tabelas de parâmetros e descrições de perímetros.
    Referências a Anexos nos artigos devem ser atualizadas se o Anexo for renumerado por emenda.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCO B — RENUMERAÇÃO (LC 95/1998, art. 10; LC 48/2000, art. 9)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

B1. ARTIGOS
    — Numeração ordinal até o 9º (Art. 1º, Art. 2º … Art. 9º)
    — Numeração cardinal a partir do 10 (Art. 10, Art. 11 …)
    — Emenda supressiva de artigo: os artigos seguintes são renumerados em sequência
    — Emenda aditiva de artigo: insira no local correto e renumere os seguintes

B2. PARÁGRAFOS (LC 95/1998, art. 10, III; LC 48/2000, art. 9, III)
    — Representados pelo sinal "§" seguido de numeral ordinal até o 9º, cardinal a partir do 10
    — Quando existir apenas um parágrafo: usar obrigatoriamente "Parágrafo único" por extenso
    — Se emenda supressiva eliminar parágrafo deixando apenas um: converter para "Parágrafo único"
    — Se emenda aditiva criar segundo parágrafo onde havia "Parágrafo único": converter para §1º e §2º

B3. INCISOS (LC 95/1998, art. 10, IV; LC 48/2000, art. 9, IV e VII)
    — Representados por algarismos romanos (I, II, III, IV, V …)
    — A indicação do inciso é separada do texto por travessão (—)
    — Renumerar em sequência após supressão ou adição de incisos

B4. ALÍNEAS (LC 95/1998, art. 10, IV; LC 48/2000, art. 9, IV e VII)
    — Representadas por letras minúsculas (a, b, c …)
    — A indicação da alínea é separada do texto por parêntese de fechamento: a)
    — Renumerar alfabeticamente após supressão ou adição

B5. ITENS
    — Representados por algarismos arábicos (1, 2, 3 …)
    — A indicação do item é separada do texto por ponto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCO C — PONTUAÇÃO OBRIGATÓRIA (LC 48/2000, art. 9, VI, VII, VIII, IX — LC 51/2001)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

C1. Artigos e parágrafos:
    — Texto inicia com letra MAIÚSCULA
    — Se não houver desdobramento em incisos: termina com PONTO (.)
    — Se houver desdobramento em incisos: termina com DOIS-PONTOS (:)

C2. Incisos:
    — Texto inicia com letra MINÚSCULA (salvo nome próprio)
    — Cada inciso termina com PONTO E VÍRGULA (;)
    — O penúltimo inciso termina com "; e" (se cumulativo) ou "; ou" (se disjuntivo)
    — O último inciso termina com PONTO (.)
    — Se o inciso se desdobrar em alíneas: termina com DOIS-PONTOS (:)

C3. Alíneas:
    — Texto inicia com letra MINÚSCULA (salvo nome próprio)
    — Cada alínea termina com PONTO E VÍRGULA (;)
    — A penúltima alínea termina com "; e" ou "; ou" conforme o caso
    — A última alínea termina com PONTO (.)
    — Se a alínea se desdobrar em itens: termina com DOIS-PONTOS (:)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCO D — CLAREZA E PRECISÃO (LC 95/1998, art. 11; LC 48/2000, art. 10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

D1. Uniformidade de tempo verbal: preferência pelo presente do indicativo ou futuro simples

D2. Referências a dispositivos (LC 48/2000, art. 10, II, g):
    — Usar "art." (singular) ou "arts." (plural) para artigos
    — Usar "§" (singular) ou "§§" (plural) para parágrafos numerados
    — "Parágrafo único" sempre por extenso nas referências
    — Nunca usar "anterior", "seguinte" ou equivalente vago

D3. Números e percentuais (LC 48/2000, art. 10, II, f — LC 51/2001):
    — Grafar por extenso, salvo: datas, número da lei, casos em que prejudique a compreensão
    — Valores monetários em algarismos arábicos seguidos de indicação por extenso entre parênteses

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCO E — AVISOS E ERROS CRÍTICOS (art. 250, §§ 1º e 2º, RI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

E1. AVISOS — aponte mas NÃO corrija automaticamente (art. 250, §1º RI):
    — Erros de ortografia, concordância nominal ou verbal nas emendas aprovadas
    — Violação das regras de pontuação do Bloco C nas emendas (ex: inciso terminando em ponto quando deveria ser ponto e vírgula)
    — Uso de "anterior" ou "seguinte" sem especificação do dispositivo
    — Referência a dispositivo que foi suprimido por outra emenda
    — "Parágrafo único" onde há mais de um parágrafo (ou vice-versa)
    — Técnica redacional imprópria que não comprometa o sentido jurídico
    — Inconsistência de tempo verbal entre dispositivos da mesma lei

E2. ERROS CRÍTICOS — não tente resolver, sinalize para reabertura (art. 250, §2º RI):
    — Duas emendas aprovadas que se contradizem diretamente sobre o mesmo dispositivo
    — Emenda que ao ser aplicada torna outro dispositivo aprovado de cumprimento impossível
    — Supressão e modificação simultânea do mesmo artigo por emendas distintas
    — Resultado que gera absurdo jurídico manifesto insanável sem alterar teor

E3. ALERTA DE ABSURDO MANIFESTO — intervenção obrigatória da CCJ (art. 250, §1º RI):
    — Use SOMENTE quando o texto, após a emenda, tornar-se tecnicamente ininteligível por
      razão exclusivamente formal, sem qualquer leitura possível que preserve a vontade legislativa
    — Exemplo típico: dispositivo que remete exclusivamente a artigo integralmente suprimido
      por outra emenda, tornando o próprio dispositivo vazio de qualquer sentido normativo
    — Diferente do Erro Crítico: aqui a ininteligibilidade é formal (não há conflito entre emendas,
      mas o resultado é incompreensível); a CCJ deve corrigir com ofício amplo (art. 250, §1º RI)
    — Use com extrema parcimônia — na dúvida, classifique como ⚠ AVISO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEXTO ORIGINAL DO PROJETO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{texto_original}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMENDAS APROVADAS (aplicar nesta ordem numérica):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bloco_emendas}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONDA EXATAMENTE NESTE FORMATO XML:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<TEXTO_HARMONIZADO>
[Texto completo da Redação Final com todas as emendas aplicadas, renumeração atualizada
e referências cruzadas corrigidas. Respeitar obrigatoriamente toda a pontuação do Bloco C.]
</TEXTO_HARMONIZADO>

<MAPA_RENUMERACAO>
[Uma linha por mudança de numeração. Exemplos:]
[Art. 3º → Art. 2º (supressão do Art. 2º original pela Emenda 1)]
[§ 2º do Art. 5º → Parágrafo único do Art. 4º (supressão do §1º pela Emenda 5)]
[Escreva "Sem renumeração necessária." se não houver nenhuma mudança.]
</MAPA_RENUMERACAO>

<AVISOS>
[Um aviso por linha. Formato: "⚠ Emenda N / Art. Xº: descrição detalhada do problema"]
[Base legal do aviso entre colchetes, ex: [LC 48/2000, art. 9º, VIII]]
[Escreva "Nenhum aviso." se não houver.]
</AVISOS>

<ERROS_CRITICOS>
[Um erro por parágrafo. Formato: "🚨 Emendas N e M: descrição do conflito insanável"]
[Recomendação de reabertura de discussão conforme art. 250, §2º RI]
[Escreva "Nenhum erro crítico." se não houver.]
</ERROS_CRITICOS>

<ALERTAS_ABSURDOS>
[Use SOMENTE para absurdo manifesto técnico — casos muito raros. Formato: "🔴 Emenda N / Art. Xº: descrição"]
[A CCJ deve corrigir com ofício amplamente justificado (art. 250, §1º RI).]
[Na dúvida, classifique como AVISO. Escreva "Nenhum." se não houver.]
</ALERTAS_ABSURDOS>

<LOG_ALTERACOES>
[Um registro por linha: "Emenda N (Tipo): ação exata realizada no texto"]
</LOG_ALTERACOES>"""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=28000,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        resp_text = stream.get_final_text()

    def extrair(tag: str, default: str = "") -> str:
        m = re.search(rf'<{tag}>(.*?)</{tag}>', resp_text, re.DOTALL)
        return m.group(1).strip() if m else default

    texto_harm    = extrair("TEXTO_HARMONIZADO", texto_original)
    mapa_raw      = extrair("MAPA_RENUMERACAO", "")
    avisos_raw    = extrair("AVISOS", "")
    erros_raw     = extrair("ERROS_CRITICOS", "")
    alertas_raw   = extrair("ALERTAS_ABSURDOS", "")
    log_raw       = extrair("LOG_ALTERACOES", "")

    # Mapa de renumeração
    mapa = {}
    for linha in mapa_raw.splitlines():
        if '→' in linha or '->' in linha:
            partes = linha.replace('->', '→').split('→')
            if len(partes) == 2:
                mapa[partes[0].strip()] = partes[1].strip()

    def parse_linhas(raw: str, modo: str = 'paragrafo') -> list[str]:
        """
        modo='paragrafo': agrupa linhas consecutivas em um item (sep. por linha em branco).
            → corrige avisos multi-linha contados como muitos itens.
        modo='linha': cada linha não-vazia é um item separado (para log de alterações).
        """
        skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.", "Sem renumeração necessária."}
        if modo == 'paragrafo':
            blocos = re.split(r'\n\s*\n', raw.strip())
            items = [' '.join(l.strip() for l in b.splitlines() if l.strip()) for b in blocos]
        else:
            items = [l.strip() for l in raw.splitlines() if l.strip()]
        return [i for i in items if i and i not in skip]

    return ResultadoHarmonizacao(
        texto_harmonizado = texto_harm,
        avisos            = parse_linhas(avisos_raw,  modo='paragrafo'),
        erros_criticos    = parse_linhas(erros_raw,   modo='paragrafo'),
        alertas_absurdos  = parse_linhas(alertas_raw, modo='paragrafo'),
        mapa_renumeracao  = mapa,
        log_alteracoes    = parse_linhas(log_raw,     modo='linha'),
    )
