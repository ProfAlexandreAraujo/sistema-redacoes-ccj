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
    notas_tecnicas: list[str] = field(default_factory=list)   # ℹ informativo — não vai pro DOCX


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


# ─────────────────────────────────────────────────────────────────────────────
# PÓS-PROCESSAMENTO: ESCALADA PARA ABSURDO MANIFESTO (§2º RI)
# ─────────────────────────────────────────────────────────────────────────────

def _detectar_absurdos_estruturais(texto: str) -> list[str]:
    """
    Detecta absurdos manifestos diretamente no texto harmonizado, sem depender
    da classificação do modelo de IA.

    Caso 1 — Autoreferência circular:
        Art. N cujo corpo contém referência explícita ao próprio Art. N.
    Caso 2 — Condição normativa inoperante:
        §N cujo corpo contém "§N deste artigo" (parágrafo que remete a si mesmo).
    """
    alertas: list[str] = []

    # ── Caso 1: Autoreferência circular ──────────────────────────────────────
    art_matches = list(re.finditer(r'(?m)^Art\.\s*(\d+)', texto))
    for idx, m in enumerate(art_matches):
        num_art = m.group(1)
        # Corpo: do fim do cabeçalho "Art. N" até o início do próximo artigo
        corpo_ini = m.end()
        corpo_fim = art_matches[idx + 1].start() if idx + 1 < len(art_matches) else len(texto)
        corpo = texto[corpo_ini:corpo_fim]
        # Referências explícitas ao mesmo artigo: "no Art. N", "do Art. N", etc.
        refs_art = re.findall(
            r'\b(?:n[oa]s?|d[oa]s?|ao?|conform[ae]?|observad[oa])\s+[Aa]rt\.?\s*(\d+)',
            corpo
        )
        if any(r == num_art for r in refs_art):
            alertas.append(
                f"🔴 Art. {num_art}: o dispositivo referencia o próprio Art. {num_art} "
                f"(autoreferência circular) — absurdo manifesto detectado em pós-processamento "
                f"(Caso 1 — art. 250, §2º RI). A providência regimental indicada é a reabertura da discussão."
            )

    # ── Caso 2: Condição normativa inoperante ─────────────────────────────────
    # §N que contém "§N deste artigo" (parágrafo remete a si mesmo)
    for par_m in re.finditer(
        r'(?m)^\s*§\s*(\d+)[ºo°]?\s(.+?)(?=\n\s*§\s*\d|\n\s*Art\.\s*\d|\Z)',
        texto, re.DOTALL
    ):
        par_num  = par_m.group(1)
        par_body = par_m.group(2)
        for ref_m in re.finditer(
            r'§\s*(\d+)[ºo°]?\s+deste\s+artigo',
            par_body, re.IGNORECASE
        ):
            if ref_m.group(1) == par_num:
                alertas.append(
                    f"🔴 §{par_num}º: o parágrafo remete ao próprio §{par_num}º deste artigo "
                    f"(condição normativa inoperante) — absurdo manifesto detectado em pós-processamento "
                    f"(Caso 2 — art. 250, §2º RI). A providência regimental indicada é a reabertura da discussão."
                )
                break

    return alertas


# Padrões semânticos nos avisos que indicam absurdo manifesto (§2º RI)
_PADROES_ABSURDO_AVISO = re.compile(
    r'referência circular'
    r'|aponta para o próprio artigo'
    r'|autoref(?:erência)?'
    r'|artigo.*referencia.*a si mesmo'
    # Condição inoperante (§ suprimido)
    r'|condição.*suprimid'
    r'|suprimid.*condição'
    r'|§\s*\d+.*suprimid'
    r'|§.*não existe mais'
    r'|§.*foi suprimid'
    # "artigo anterior" incompatível após renumeração
    r'|artigo anterior.*incompatível'
    r'|incompatível.*artigo anterior'
    r'|artigo anterior.*trata\b'
    r'|artigo anterior.*após.*renumer'
    r'|artigo anterior.*monitoramento'
    r'|artigo anterior.*fiscaliz'
    r'|artigo anterior.*diferente'
    r'|artigo anterior.*passou a ser'
    r'|artigo anterior.*versa\b',
    re.IGNORECASE | re.DOTALL
)


def _escalar_avisos_para_absurdos(
    avisos: list[str],
    texto_harm: str,
    alertas_existentes: list[str],
) -> tuple[list[str], list[str]]:
    """
    Pós-processamento: eleva avisos (§1º) que descrevem absurdos manifestos
    para alertas_absurdos (§2º), sinalizando que a providência regimental
    indicada é a reabertura da discussão (art. 250, §2º RI).
    O DOCX será exportado como RASCUNHO DE TRABALHO a menos que o relator
    confirme ciência explicitamente na interface.

    Estratégia dupla:
    · Detecção estrutural no texto harmonizado (Casos 1 e 2 — independe do modelo)
    · Padrões semânticos nos avisos (Caso 3 e qualquer caso não coberto estruturalmente)

    Retorna (avisos_restantes, alertas_absurdos_atualizados).
    """
    def _nums(s: str) -> set[str]:
        """
        Extrai identificadores de dispositivos (Art. N ou § N) do texto,
        ignorando referências ao regimento e sufixos de reclassificação
        para evitar falsos positivos na deduplicação.
        """
        # Remove blocos entre colchetes (ex: "[Reclassificado: ...]", "(Caso 1 — ...)")
        s_clean = re.sub(r'\[.*?\]', '', s, flags=re.DOTALL)
        s_clean = re.sub(r'\(.*?\)', '', s_clean, flags=re.DOTALL)
        # Remove referências ao artigo do RI (ex: "art. 250, §2º RI")
        s_clean = re.sub(r'\bart\.?\s*250\b[^\n.;]*', '', s_clean, flags=re.IGNORECASE)
        return set(re.findall(r'(?:Art\.\s*\d+|§\s*\d+)', s_clean, re.IGNORECASE))

    def _ja_cobre(candidato: str, lista: list[str]) -> bool:
        ns = _nums(candidato)
        return bool(ns) and any(bool(ns & _nums(e)) for e in lista)

    alertas_estruturais = _detectar_absurdos_estruturais(texto_harm)
    nums_est: set[str] = set().union(*(_nums(a) for a in alertas_estruturais)) if alertas_estruturais else set()

    avisos_restantes: list[str] = []
    alertas_de_avisos: list[str] = []

    for aviso in avisos:
        nums_av = _nums(aviso)
        # Escala se: (a) keywords indicam absurdo, ou (b) dispositivo já detectado estruturalmente
        if _PADROES_ABSURDO_AVISO.search(aviso) or (nums_av & nums_est):
            texto_limpo = re.sub(r'^⚠\s*', '', aviso.strip())
            alertas_de_avisos.append(
                f"🔴 {texto_limpo}  "
                f"[Reclassificado: absurdo manifesto — art. 250, §2º RI]"
            )
        else:
            avisos_restantes.append(aviso)

    # Consolida sem duplicatas: existentes → estruturais → de avisos
    todos: list[str] = list(alertas_existentes)
    for a in alertas_estruturais:
        if not _ja_cobre(a, todos):
            todos.append(a)
    for a in alertas_de_avisos:
        if not _ja_cobre(a, todos):
            todos.append(a)

    return avisos_restantes, todos


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
- texto_bruto: texto integral original da emenda EXATAMENTE como aparece no documento, sem omissão
- autor: nome do vereador autor, se mencionado; null caso contrário
- notas: observações relevantes (ex: emenda está incompleta, referência ambígua, etc.) ou null

Responda SOMENTE com JSON válido no formato:
{{"emendas": [
  {{"numero": 1, "tipo": "Modificativa", "alvo": "Art. 5º", "novo_texto": "...", "texto_bruto": "Emenda nº 1 — ...", "autor": "Fulano", "notas": null}},
  {{"numero": 2, "tipo": "Supressiva",   "alvo": "Art. 4º", "novo_texto": null,  "texto_bruto": "Emenda nº 2 — Suprima-se o Art. 4º", "autor": null, "notas": null}},
  ...
]}}

TEXTO DAS EMENDAS:
{chunk}"""

        n_antes = len(todas_emendas)   # para corrigir offset ao final do lote

        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=20000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                resp_text = stream.get_final_text()

            # Extrai JSON da resposta
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if not match:
                raise ValueError(
                    "IA não retornou JSON válido neste lote — "
                    "emendas serão criadas como brutas para revisão manual."
                )
            data = json.loads(match.group())

            for idx_item, item in enumerate(data.get("emendas", []), start=1):
                tipo_map = {t.value: t for t in TipoEmenda}
                # texto_bruto: preferir campo explícito; fallback para novo_texto ou
                # para o texto do item como string (nunca vazio para emendas supressivas)
                texto_bruto = (
                    item.get("texto_bruto")
                    or item.get("novo_texto")
                    or f"[Emenda {item.get('numero', '?')} — {item.get('tipo', '')} | {item.get('alvo', '')}]"
                )
                numero = item.get("numero")
                if numero is None:
                    numero = offset + idx_item   # posição no lote, não acumulativo
                e = Emenda(
                    numero      = numero,
                    texto_bruto = texto_bruto,
                    tipo        = tipo_map.get(item.get("tipo") or "", TipoEmenda.OUTRO),
                    alvo        = item.get("alvo"),
                    novo_texto  = item.get("novo_texto"),
                    autor       = item.get("autor"),
                    parseada    = True,
                    notas_parse = item.get("notas"),
                )
                todas_emendas.append(e)

        except (json.JSONDecodeError, KeyError, IndexError, ValueError):
            # Se parsing falhar, cria emendas brutas
            partes = re.split(r'\n(?=EMENDA\s)', chunk, flags=re.IGNORECASE)
            for parte in partes:
                if parte.strip():
                    num = offset + len(todas_emendas) + 1
                    todas_emendas.append(Emenda(
                        numero=num, texto_bruto=parte.strip(), parseada=False,
                        notas_parse="Parsing automático falhou — revisar manualmente"
                    ))

        offset += len(todas_emendas) - n_antes   # incrementa só o lote atual

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

A1. PRESERVAÇÃO DO TEOR — REGRA ABSOLUTA INVIOLÁVEL (art. 250 RI / soberania do Plenário)
    Jamais altere o conteúdo substantivo de nenhuma emenda aprovada.
    O texto aprovado pelo Plenário é soberano e deve ser incorporado exatamente como votado.

    ⚠ REGRA CRÍTICA DE PRESERVAÇÃO VERBATIM:
    Ao incorporar o texto de emenda aprovada, copie-o LITERALMENTE — cada palavra, cada
    cláusula, cada vírgula — EXATAMENTE como consta no texto aprovado pelo Plenário.
    MESMO QUE o texto aprovado:
      · contenha referência a dispositivo suprimido por outra emenda
      · crie referência circular, condição pendente ou absurdo manifesto
      · contenha cláusula que pareça redundante, problemática ou desnecessária
    NUNCA remova, NUNCA parafraseie, NUNCA simplifique, NUNCA "conserte" nenhuma parte.
    → Se o texto aprovado cria absurdo ou ininteligibilidade, COPIE-O VERBATIM e registre
      o problema em <ALERTAS_ABSURDOS> com marcador inline no texto (ver formato abaixo).
    → A supressão de QUALQUER cláusula ou palavra do texto aprovado — mesmo que pareça
      "resolver" um problema técnico — é alteração de teor vedada pelo art. 250 RI.
    → As correções exclusivamente linguísticas previstas em E1 (concordância, caixa,
      pontuação objetiva) constituem EXCEÇÃO EXPRESSA e autorizada à preservação literal,
      devendo ser obrigatoriamente registradas em LOG e AVISOS.
    → Fora das hipóteses E1 e A2, nenhuma alteração automática é permitida.

A2. REFERÊNCIAS CRUZADAS (única alteração automática de conteúdo permitida)
    Após renumerar artigos, atualize TODAS as referências internas:
    — "conforme o art. 10" → se art. 10 virou art. 8, corrija para "conforme o art. 8"
    — "nos termos do § 2º do art. 5º" → atualize ambos os números se houver mudança
    — "previsto no inciso III" → atualize se o inciso foi renumerado
    Nunca use as expressões "anterior", "seguinte" ou equivalentes vagas (LC 48/2000, art. 10, II, g).

    ⚠ REGRA ESPECIAL — EMENDAS AGLUTINATIVAS:
    Quando a emenda unifica art. X e art. Y em art. X (suprimindo art. Y), o CONTEÚDO
    de Y migra para X. Qualquer referência ao conteúdo que estava em Y deve apontar para
    X final — NÃO para o artigo que por renumeração sequencial herda o número de Y.
    Exemplo: arts. 11 e 12 originais aglutinados em art. 11 final; outro artigo dizia
    "transferência prevista no Art. 12" → deve passar a "transferência prevista no Art. 11"
    (e não para o art. 12 final, que é o art. 13 original renumerado com outro conteúdo).
    Registre no LOG_ALTERACOES: "A2-aglut / Art. Xº: 'Art. Y' → 'Art. X' (conteúdo migrou
    pela aglutinação — Emenda N)"

A3. ANEXOS (preservação integral obrigatória)
    Os Anexos (mapas, quadros, tabelas, delimitações georreferenciadas) integram a lei mas
    NÃO devem ser renumerados nem alterados, salvo emenda expressa sobre eles.
    Preserve o conteúdo de cada Anexo exatamente como consta no projeto original, inclusive
    coordenadas UTM, tabelas de parâmetros e descrições de perímetros.
    Referências a Anexos nos artigos devem ser atualizadas se o Anexo for renumerado por emenda.

A4. EMENDAS SEM ALVO DEFINIDO — "acrescente-se onde couber"

    A4.1 — EMENDAS ADITIVAS SEM ALVO (texto novo autônomo)
    Quando uma emenda aditiva não especificar o dispositivo exato de destino
    (ex: "acrescente-se onde couber", "inclua-se no local adequado", "onde cabível",
    ou quando o alvo estiver simplesmente omisso):

    a) IDENTIFIQUE a unidade normativa que está sendo inserida:
       — Artigo novo → inserir após o artigo tematicamente mais próximo
       — Parágrafo novo → inserir no artigo correspondente, após o parágrafo mais
         relacionado ou ao final dos parágrafos do artigo
       — Inciso novo → inserir no rol correspondente, respeitando sequência lógica;
         renumerar os seguintes e ajustar pontuação (Bloco C)
       — Alínea nova → inserir dentro do inciso correspondente, respeitando enumeração;
         renumerar as seguintes e ajustar pontuação (Bloco C)
       — Item novo → inserir dentro da alínea correspondente, respeitando enumeração

    b) CRITÉRIOS DE POSICIONAMENTO (em ordem de prioridade):
       — Afinidade de matéria: insira próximo a dispositivos que tratam do mesmo tema
       — Sequência lógica: respeite a progressão normativa do capítulo ou seção
       — Nunca crie "ilhas" temáticas: não insira dispositivo sobre tema X no meio de tema Y
       — Em caso de empate, prefira o final do capítulo temático correspondente

    c) OBRIGATÓRIO — registrar no LOG_ALTERACOES:
       "A4 / Emenda N: inserida como [artigo/parágrafo/inciso/alínea/item] em [local exato] — [motivo breve] (alvo não especificado na emenda)"

    d) OBRIGATÓRIO — gerar aviso em AVISOS:
       "⚠ Emenda N / alvo não especificado: inserida como [tipo] em [local exato] por coerência temática com [tema]. Posicionamento definido pela CCJ — alvo não especificado na emenda original."

    NUNCA insira silenciosamente sem AVISO e sem LOG.
    NUNCA recuse aplicar a emenda por ausência de alvo — posicionar é responsabilidade da CCJ.

    A4.2 — EMENDAS MODIFICATIVAS OU SUBSTITUTIVAS SEM ALVO IDENTIFICÁVEL
    Quando uma emenda modificativa ou substitutiva não especificar o dispositivo de destino
    e o alvo não puder ser inferido com segurança a partir do texto da emenda:

    a) NÃO aplique a substituição — não invente qual dispositivo está sendo modificado.
    b) OBRIGATÓRIO — gerar aviso em AVISOS:
       "⚠ Emenda N (modificativa/substitutiva): alvo não identificável — emenda não aplicada.
        Revisão manual obrigatória antes da publicação."
    c) OBRIGATÓRIO — registrar no LOG_ALTERACOES:
       "A4.2 / Emenda N: NÃO aplicada — alvo não identificável (modificativa/substitutiva sem alvo definido)"

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
      ⚠ EXCETO: se o texto aprovado da emenda não trouxer "; e", apenas aponte em AVISO —
        não acrescente automaticamente (ver E1). LC 48/2000 apenas, prática municipal ignora.
    — O último inciso termina com PONTO (.)
    — Se o inciso se desdobrar em alíneas: termina com DOIS-PONTOS (:)

C3. Alíneas:
    — Texto inicia com letra MINÚSCULA (salvo nome próprio)
    — Cada alínea termina com PONTO E VÍRGULA (;)
    — A penúltima alínea termina com "; e" ou "; ou" conforme o caso
      ⚠ Mesma exceção do C2: não auto-corrija ausência de "; e"; apenas aponte em AVISO.
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

E1. CORREÇÕES AUTOMÁTICAS DE LINGUAGEM (art. 250, §1º RI):
    Erros de linguagem que NÃO alterem o significado jurídico devem ser CORRIGIDOS
    AUTOMATICAMENTE. A preocupação central é preservar o TEOR (o que a lei manda, proíbe
    ou permite) — não manter erros de português que não afetam a norma.

    CORRIJA automaticamente e registre no LOG_ALTERACOES e em AVISOS:
    — Concordância nominal e verbal (ex: "serão aplicada" → "serão aplicadas")
    — Caixa incorreta em palavras comuns (ex: "Depósitos" → "depósitos" quando não for nome
      próprio ou início de inciso)
    — Pontuação do Bloco C, EXCETO o conectivo "; e" (ex: inciso encerrando com "." → ";";
      última alínea sem "." → acrescentar ".")
    — Uniformização de tempo verbal dentro do mesmo artigo

    Para cada correção: LOG_ALTERACOES → "E1 / Art. Xº: [original] → [corrigido]"
                        AVISOS → "⚠ E1 / Art. Xº: corrigido automaticamente — [original] → [corrigido]"

    NUNCA ALTERE (independentemente de parecer erro de português):
    — Números, valores, prazos, percentuais, coeficientes, coordenadas, medidas
    — Sujeito, objeto e verbo obrigacional/proibitivo de qualquer dispositivo
    — Termos técnicos jurídicos e urbanísticos, mesmo que inusuais
    — Qualquer expressão que defina o que a lei permite, proíbe ou obriga
    — Remissões a outros dispositivos (salvo A2)

    APONTE mas não corrija (geram apenas aviso ⚠, sem alteração):
    — Uso de "anterior" ou "seguinte" sem especificação do dispositivo (D2)
    — "Parágrafo único" onde há mais de um parágrafo (ou vice-versa)
    — Referência a dispositivo suprimido que não configure absurdo manifesto (E3)
    — Técnica redacional imprópria que comprometa o sentido jurídico

E1.5. PROIBIÇÃO ABSOLUTA — ANÁLISES DE MÉRITO NOS AVISOS:
    NUNCA inclua em AVISOS qualquer observação sobre:
    — Coeficiente de aproveitamento (CA): comparações, proporções, relações entre setores
    — Gabaritos, alturas, número de pavimentos: análises de adequação
    — Consistência dos parâmetros urbanísticos aprovados pelo Plenário
    — Qualquer julgamento sobre se os valores fazem sentido técnico ou urbanístico
    Esses são assuntos de MÉRITO — soberania exclusiva do Plenário — totalmente fora da
    competência da CCJ na Redação Final. Colocá-los em AVISOS contamina o documento.
    Se perceber algo desse tipo, NÃO coloque em AVISOS.
    Registre em <NOTAS_TECNICAS> como nota informativa para equipes técnicas — sem julgamento.

    EXEMPLO PROIBIDO em AVISOS (coloque em NOTAS_TECNICAS, nunca em AVISOS):
    ❌ AVISOS: "⚠ Emenda 6 / Anexo III: CA do Setor A aumentou de 8,0 para 16,0."
    ✅ NOTAS_TECNICAS: "ℹ Emenda 6 / Anexo III: CA Setor A: 8,0 → 16,0; CA Setor B: 6,0 → 18,0."

    AUTO-TESTE antes de escrever qualquer aviso:
    Pergunte-se: "Este aviso é sobre um erro de PORTUGUÊS ou de TÉCNICA REDACIONAL FORMAL?"
    — Se sim → escreva em AVISOS.
    — Se não (se for sobre o que a lei permite, quanto vale, parâmetros, impacto) →
      coloque em NOTAS_TECNICAS (nunca em AVISOS).

E2. ERROS CRÍTICOS — não tente resolver; a providência regimental indicada é a reabertura da discussão (art. 250, §2º RI):
    — Duas emendas aprovadas que se contradizem diretamente sobre o mesmo dispositivo
    — Emenda que ao ser aplicada torna outro dispositivo aprovado de cumprimento impossível
    — Supressão e modificação simultânea do mesmo artigo por emendas distintas
    — Resultado que gera absurdo jurídico manifesto insanável sem alterar teor

E3. ALERTA DE ABSURDO MANIFESTO (art. 250, §2º RI — providência regimental indicada é a reabertura):
    QUATRO SITUAÇÕES QUE OBRIGATORIAMENTE geram 🔴 — NÃO downgrade para ⚠ AVISO:

    CASO 1 — AUTOREFERÊNCIA CIRCULAR:
    Artigo ou parágrafo cujo texto referencia o PRÓPRIO número como se fosse outro dispositivo.
    Exemplo real: Art. 4º original suprimido; Art. 5º renumerado para Art. 4º; caput do novo
    Art. 4º diz "Observada a área de abrangência definida no Art. 4º" — o artigo aponta para
    si mesmo. Isso é absurdo manifesto; classifique como 🔴.

    CASO 2 — CONDIÇÃO NORMATIVA INOPERANTE:
    Parágrafo que condiciona dispensa ou obrigação ao cumprimento de condição "prevista no §X
    deste artigo", onde o §X referenciado: (a) foi suprimido por outra emenda — o §X não existe
    mais; ou (b) É o próprio parágrafo que faz a remissão — autoreferência.
    Exemplo real: §2º original diz "Atendida a condição prevista no §1º deste artigo, fica
    dispensada..."; o §1º foi suprimido; o §2º passou a ser §1º e agora remete a si mesmo.
    Isso é absurdo manifesto; classifique como 🔴.

    CASO 3 — REMISSÃO MATERIALMENTE INCOMPATÍVEL:
    "artigo anterior", "art. X" ou "§X" que aponta para dispositivo cujo conteúdo é completamente
    incompatível com o objeto do parágrafo que faz a remissão.
    Exemplo real: §4º sobre potencial construtivo certificado diz "nos termos do artigo anterior";
    o artigo anterior, após renumeração, trata de monitoramento e fiscalização — conteúdo
    completamente incompatível. Isso é absurdo manifesto; classifique como 🔴.

    CASO 4 — REFERÊNCIA EXCLUSIVA A DISPOSITIVO SUPRIMIDO:
    Dispositivo cuja ÚNICA remissão normativa operativa aponta para artigo integralmente
    suprimido, tornando-o operativamente vazio de sentido.

    Diferença com E2: E2 = duas emendas conflitam; E3 = uma emenda, ao interagir com outra
    supressiva ou de renumeração, produz dispositivo normalmente inoperante.
    Em AMBOS (E2 e E3): a providência regimental indicada é a reabertura da discussão (§2º RI).
    Para casos fora dos quatro acima: na dúvida, classifique como ⚠ AVISO.

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
e referências cruzadas corrigidas. Respeitar obrigatoriamente toda a pontuação do Bloco C.
ATENÇÃO — Dispositivos com absurdo manifesto: preservar o texto VERBATIM e inserir
imediatamente após o dispositivo problemático o marcador:
[[⚠️ CCJ: DISPOSITIVO ININTELIGÍVEL — ver seção ABSURDOS MANIFESTOS]]
O texto do dispositivo permanece exatamente como aprovado — apenas acrescente o marcador.]
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
[⚠ AVISOS são estritamente para problemas de FORMA/LINGUAGEM.
 Parâmetros técnicos (CA, gabaritos, valores numéricos) → coloque em NOTAS_TECNICAS, não aqui.
 Escreva "Nenhum aviso." se não houver problema de forma/linguagem.]
</AVISOS>

<ERROS_CRITICOS>
[Um erro por parágrafo. Formato: "🚨 Emendas N e M: descrição do conflito insanável"]
[Recomendação de reabertura de discussão conforme art. 250, §2º RI]
[Escreva "Nenhum erro crítico." se não houver.]
</ERROS_CRITICOS>

<ALERTAS_ABSURDOS>
[Use SOMENTE para absurdo manifesto ou ininteligibilidade formal — casos muito raros.]
[Formato: "🔴 Emenda N / Art. Xº: descrição precisa do absurdo"]
[A providência regimental indicada é a reabertura da discussão (art. 250, §2º RI).]
[Na dúvida, classifique como AVISO. Escreva "Nenhum." se não houver.]
</ALERTAS_ABSURDOS>

<NOTAS_TECNICAS>
[Notas informativas para equipes técnicas — NÃO são avisos formais da CCJ e NÃO constam no documento exportado.]
[Use para registrar objetivamente alterações de parâmetros técnicos (CA, gabaritos, valores numéricos) que outros técnicos possam querer verificar.]
[Formato: "ℹ Emenda N / Dispositivo: descrição objetiva da alteração — sem julgamento de mérito"]
[Exemplo: "ℹ Emenda 6 / Anexo III: CA Setor A: 8,0 → 16,0; CA Setor B: 6,0 → 18,0 (inalterados: C e D)."]
[Escreva "Nenhuma nota técnica." se não houver.]
</NOTAS_TECNICAS>

<LOG_ALTERACOES>
[Um registro por linha: "Emenda N (Tipo): ação exata realizada no texto"]
</LOG_ALTERACOES>"""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=60000,   # teto: 64k — seguro para PLCs grandes + 180 emendas
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        resp_text = stream.get_final_text()

    def extrair(tag: str, default: str = "") -> str:
        m = re.search(rf'<{tag}>(.*?)</{tag}>', resp_text, re.DOTALL)
        return m.group(1).strip() if m else default

    # ── Validação: todas as tags esperadas devem ter par completo ───────────
    # Verificar só a tag de abertura não protege contra truncamento:
    # resposta cortada após <TAG> faria extrair() devolver "" silenciosamente.
    # TEXTO_HARMONIZADO e LOG_ALTERACOES também exigem conteúdo não vazio.
    _TODAS_TAGS      = [
        "TEXTO_HARMONIZADO", "MAPA_RENUMERACAO",
        "AVISOS", "ERROS_CRITICOS", "ALERTAS_ABSURDOS", "NOTAS_TECNICAS", "LOG_ALTERACOES",
    ]
    _TAGS_NAO_VAZIAS = {"TEXTO_HARMONIZADO", "LOG_ALTERACOES"}

    _sem_par:        list[str] = []
    _conteudo_vazio: list[str] = []

    for _tag in _TODAS_TAGS:
        _m = re.search(rf'<{_tag}>(.*?)</{_tag}>', resp_text, re.DOTALL)
        if not _m:
            _sem_par.append(_tag)
        elif _tag in _TAGS_NAO_VAZIAS and not _m.group(1).strip():
            _conteudo_vazio.append(_tag)

    if _sem_par:
        raise ValueError(
            f"Resposta da IA truncada — par completo ausente: {', '.join(_sem_par)}. "
            "Tente novamente; se o erro persistir, reduza o número de emendas por lote."
        )
    if _conteudo_vazio:
        raise ValueError(
            f"Resposta da IA inválida — conteúdo obrigatório vazio em: "
            f"{', '.join(_conteudo_vazio)}. Tente novamente."
        )

    texto_harm = re.search(
        r'<TEXTO_HARMONIZADO>(.*?)</TEXTO_HARMONIZADO>', resp_text, re.DOTALL
    ).group(1).strip()   # par validado acima — .group(1) seguro
    mapa_raw      = extrair("MAPA_RENUMERACAO", "")
    avisos_raw    = extrair("AVISOS", "")
    erros_raw     = extrair("ERROS_CRITICOS", "")
    alertas_raw   = extrair("ALERTAS_ABSURDOS", "")
    notas_raw     = extrair("NOTAS_TECNICAS", "")
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
        skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.", "Sem renumeração necessária.", "Nenhuma nota técnica."}
        if modo == 'paragrafo':
            blocos = re.split(r'\n\s*\n', raw.strip())
            items = [' '.join(l.strip() for l in b.splitlines() if l.strip()) for b in blocos]
        else:
            items = [l.strip() for l in raw.splitlines() if l.strip()]
        return [i for i in items if i and i not in skip]

    avisos_list  = parse_linhas(avisos_raw,  modo='paragrafo')
    erros_list   = parse_linhas(erros_raw,   modo='paragrafo')
    alertas_list = parse_linhas(alertas_raw, modo='paragrafo')
    notas_list   = parse_linhas(notas_raw,   modo='paragrafo')
    log_list     = parse_linhas(log_raw,     modo='linha')

    # Pós-processamento: eleva absurdos manifestos classificados erroneamente como §1º avisos
    avisos_list, alertas_list = _escalar_avisos_para_absurdos(
        avisos_list, texto_harm, alertas_list
    )

    return ResultadoHarmonizacao(
        texto_harmonizado = texto_harm,
        avisos            = avisos_list,
        erros_criticos    = erros_list,
        alertas_absurdos  = alertas_list,
        mapa_renumeracao  = mapa,
        log_alteracoes    = log_list,
        notas_tecnicas    = notas_list,
    )
