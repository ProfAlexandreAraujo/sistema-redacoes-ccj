"""
harmonizer.py — Motor de harmonização legislativa
Sistema de Redações — CCJ CMRJ
"""

import re
import json
import copy
import anthropic
from collections import defaultdict
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
    subemenda_de: Optional[int] = None  # Nº da emenda-pai se for subemenda

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
            numero      = d['numero'],
            texto_bruto = d['texto_bruto'],
            tipo        = tipo_map.get(d.get('tipo') or ''),
            alvo        = d.get('alvo'),
            novo_texto  = d.get('novo_texto'),
            autor       = d.get('autor'),
            status      = status_map.get(d.get('status') or 'Pendente', StatusEmenda.PENDENTE),
            parseada    = d.get('parseada', False),
            notas_parse = d.get('notas_parse'),
            subemenda_de = d.get('subemenda_de'),
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
    sugestoes_normativas: list[str] = field(default_factory=list)  # 💡 orientativas — não vão pro DOCX


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
# PRÉ-PROCESSAMENTO: SUBEMENDAS
# ─────────────────────────────────────────────────────────────────────────────

def _resolver_subemendas(
    todas_emendas: list["Emenda"],
    aprovadas: list["Emenda"],
) -> tuple[list["Emenda"], list[str], list[str], list[str]]:
    """
    Pré-processa subemendas antes da harmonização.

    Uma subemenda é uma emenda que substitui o texto de outra emenda (emenda-pai)
    antes de votá-la. Se a subemenda foi aprovada, prevalece seu texto; se rejeitada,
    a emenda-pai mantém o texto original.

    Regras:
    - SubEmenda aprovada + Emenda-pai aprovada  → texto da emenda-pai substituído
      pelo texto da subemenda; subemenda retirada do bloco enviado à IA.
    - SubEmenda aprovada + Emenda-pai NÃO aprovada → inoperante; registra aviso (§1º).
    - SubEmenda rejeitada/prejudicada → emenda-pai mantém texto original; registra log.
    - Duas subemendas aprovadas para a mesma emenda-pai → CONFLITO → erro crítico (§2º).
    - Auto-referência (subemenda_de == numero) → erro crítico (§2º); emenda excluída.
    - Emenda-pai inexistente na lista → erro crítico (§2º); deliberação sem efeito.
    - Subemenda encadeada (pai é também subemenda) → erro crítico (§2º); não aplicada.

    Parâmetros:
    - todas_emendas: lista completa (para verificar status da emenda-pai)
    - aprovadas: emendas com status APROVADA (base da harmonização)

    Retorna (lista_processada, log_entries, avisos_simples, erros_criticos).
    Erros críticos (§2º) disparam o fluxo de rascunho de trabalho no app.
    """
    # Mapa de todas as emendas por número (para buscar status do pai)
    todas_por_num: dict[int, "Emenda"] = {e.numero: e for e in todas_emendas}

    # Cópia rasa das aprovadas para não mutar o session_state
    aprovadas_copia: list["Emenda"] = [copy.copy(e) for e in aprovadas]
    por_num_apr: dict[int, int] = {e.numero: i for i, e in enumerate(aprovadas_copia)}

    log: list[str] = []
    avisos: list[str] = []          # §1º — avisos informativos
    erros_criticos: list[str] = []  # §2º — conflitos que bloqueiam publicação
    excluir: set[int] = set()       # índices de subemendas a retirar da lista final

    # Conjunto de números de emendas que são subemendas (têm subemenda_de != None).
    # Usado para detectar encadeamentos (subemenda de subemenda).
    nums_que_sao_subemendas: set[int] = {
        e.numero for e in todas_emendas if e.subemenda_de is not None
    }

    # ── Mapear subemendas APROVADAS por emenda-pai ───────────────────────────
    # Detecta auto-referência (P1) e encadeamento (P3) antes de mapear.
    subs_apr_por_pai: dict[int, list[int]] = defaultdict(list)
    for i, e in enumerate(aprovadas_copia):
        if e.subemenda_de is None:
            continue

        # P1 — Auto-referência: subemenda aponta para si mesma → ERRO CRÍTICO §2º
        if e.subemenda_de == e.numero:
            erros_criticos.append(
                f"🚨 AUTO-REFERÊNCIA DE SUBEMENDA — Emenda {e.numero}: "
                f"campo subemenda_de aponta para si mesma (subemenda_de={e.numero}). "
                "Emenda não aplicada. Corrija o vínculo e reharmonize "
                "(art. 250, §2º RI)."
            )
            log.append(
                f"Emenda {e.numero}: auto-referência detectada (subemenda_de == numero) "
                "— não aplicada (§2º)."
            )
            excluir.add(i)
            continue

        # P3 — Subemenda encadeada: o pai é ele próprio uma subemenda → ERRO CRÍTICO §2º
        if e.subemenda_de in nums_que_sao_subemendas:
            pai_obj = todas_por_num.get(e.subemenda_de)
            avo_num = pai_obj.subemenda_de if pai_obj else "?"
            erros_criticos.append(
                f"🚨 SUBEMENDA ENCADEADA — SubEmenda {e.numero} referencia SubEmenda "
                f"{e.subemenda_de} (que é subemenda de Emenda {avo_num}). "
                "Cadeias de subemendas não são suportadas automaticamente — decisão do "
                "relator obrigatória antes da harmonização (art. 250, §2º RI)."
            )
            log.append(
                f"SubEmenda {e.numero}: subemenda encadeada "
                f"(subemenda_de={e.subemenda_de}, que também é subemenda) "
                "— não aplicada (§2º)."
            )
            excluir.add(i)
            continue

        subs_apr_por_pai[e.subemenda_de].append(i)

    # ── Processar cada grupo de subemendas por emenda-pai ────────────────────
    for pai_num, sub_idxs in subs_apr_por_pai.items():
        pai_em_todas = todas_por_num.get(pai_num)
        pai_apr_idx  = por_num_apr.get(pai_num)

        # P2 — Emenda-pai não existe na lista → ERRO CRÍTICO §2º (não §1º)
        # Uma subemenda aprovada que não pode ser aplicada é uma deliberação do
        # Plenário sem efeito — situação equivalente a A4.2 (emenda sem alvo).
        if pai_em_todas is None:
            for si in sub_idxs:
                s = aprovadas_copia[si]
                erros_criticos.append(
                    f"🚨 SUBEMENDA SEM PAI — SubEmenda {s.numero}: referencia Emenda "
                    f"{pai_num} que não consta na lista de emendas. SubEmenda aprovada "
                    "não foi aplicada — deliberação do Plenário sem efeito. "
                    "Corrija o vínculo e reharmonize (art. 250, §2º RI)."
                )
                log.append(
                    f"SubEmenda {s.numero}: Emenda {pai_num} inexistente — "
                    "não aplicada (§2º)."
                )
                excluir.add(si)
            continue

        # Conflito: mais de uma subemenda aprovada para o mesmo pai → ERRO CRÍTICO §2º
        if len(sub_idxs) > 1:
            nums = [aprovadas_copia[si].numero for si in sub_idxs]
            erros_criticos.append(
                f"🚨 CONFLITO DE SUBEMENDAS — Emenda {pai_num}: "
                f"SubEmendas {nums} foram todas aprovadas — somente uma deveria prevalecer. "
                "Decisão do relator obrigatória antes da harmonização (art. 250, §2º RI). "
                "Nenhuma substituição automática foi realizada."
            )
            log.append(
                f"SubEmendas {nums} → Emenda {pai_num}: CONFLITO — nenhuma substituição "
                "aplicada. Decisão do relator obrigatória (art. 250, §2º RI)."
            )
            excluir.update(sub_idxs)
            continue

        # Caso normal: uma única subemenda aprovada
        si  = sub_idxs[0]
        sub = aprovadas_copia[si]
        excluir.add(si)

        if pai_apr_idx is not None:
            # Pai também aprovado → substituição efetiva
            novo_txt = sub.novo_texto or sub.texto_bruto
            aprovadas_copia[pai_apr_idx].novo_texto  = novo_txt
            aprovadas_copia[pai_apr_idx].notas_parse = (
                f"Texto substituído pela SubEmenda {sub.numero} (aprovada). "
                "O texto aplicado é o da subemenda, não o original da emenda."
            )
            log.append(
                f"SubEmenda {sub.numero} → Emenda {pai_num}: texto substituído pelo Plenário. "
                f"Prevalece o texto da SubEmenda {sub.numero}."
            )
        else:
            # Subemenda aprovada mas emenda-pai não aprovada → inoperante (§1º)
            status_pai = pai_em_todas.status.value
            avisos.append(
                f"⚠ SubEmenda {sub.numero} aprovada, mas Emenda {pai_num} não foi aprovada "
                f"({status_pai}) — subemenda é inoperante "
                "(não há emenda-pai ativa para substituir)."
            )
            log.append(
                f"SubEmenda {sub.numero}: inoperante — Emenda {pai_num} "
                f"não aprovada ({status_pai})."
            )

    # Registra no log subemendas rejeitadas/prejudicadas que afetam emendas aprovadas
    for e in todas_emendas:
        if e.subemenda_de is not None and e.status != StatusEmenda.APROVADA:
            if por_num_apr.get(e.subemenda_de) is not None:
                log.append(
                    f"SubEmenda {e.numero} {e.status.value.lower()} → "
                    f"Emenda {e.subemenda_de} mantém texto original."
                )

    lista_final = [e for i, e in enumerate(aprovadas_copia) if i not in excluir]
    return lista_final, log, avisos, erros_criticos


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


def _resumo_para_ia(texto: str, max_chars: int = 600) -> str:
    """
    Extrai o conteúdo substantivo da emenda para classificação pela IA.
    Pula o bloco de autores/comissões (boilerplate) que impede a classificação.
    O bloco termina tipicamente com "FINANCEIRA." seguido do conteúdo real.
    """
    primeira_linha = texto.split('\n')[0].strip()

    # Estratégia 1: bloco de autores termina com "FINANCEIRA." (padrão mais comum)
    m = re.search(r'FINANCEIRA\.\s*\n', texto, re.IGNORECASE)
    if m:
        conteudo = texto[m.end():].strip()[:max_chars].replace('\n', ' ')
        return f"{primeira_linha} | {conteudo}"

    # Estratégia 2: primeira linha em minúsculas ou verbo legislativo típico
    for linha in texto.split('\n')[1:]:
        l = linha.strip()
        if not l:
            continue
        if re.match(
            r'^(?:Fica|Ficam|O\s|Os\s|A\s|As\s|Art\.|§|"Art\.|Inclua|Redija|'
            r'Modifica|Suprima|Acrescenta|Adiciona|Altera|Revoga|EMENTA|Texto\s+da)',
            l, re.IGNORECASE
        ):
            pos = texto.find(l)
            conteudo = texto[pos:pos + max_chars].replace('\n', ' ')
            return f"{primeira_linha} | {conteudo}"

    # Fallback: remove bloco Autor(es) e retorna o que restar
    sem_autores = re.sub(r'Autor\(es\)\s*:.*', '', texto,
                         flags=re.IGNORECASE | re.DOTALL).strip()
    return sem_autores[:max_chars].replace('\n', ' ')


def parsear_emendas_com_ia(texto_emendas: str, api_key: str) -> list[Emenda]:
    """
    Usa Claude para classificar tipo, alvo e autor de cada emenda.

    Estratégia em dois passos:
    1. Segmentação determinística por regex — extrai numero e subemenda_de do cabeçalho.
    2. IA em lotes (max 25 peças) — retorna APENAS metadados; não reproduz texto_bruto.
       Isso evita overflow de tokens para projetos com emendas muito longas.
    """
    client   = anthropic.Anthropic(api_key=api_key)
    tipo_map = {t.value: t for t in TipoEmenda}

    # ── Passo 1: segmentar deterministicamente ───────────────────────────────
    partes_raw = re.split(r'\n(?=(?:SUB)?EMENDA\s)', texto_emendas, flags=re.IGNORECASE)

    pecas: list[dict] = []
    for idx_fb, parte in enumerate(partes_raw):
        parte_s = parte.strip()
        if not parte_s:
            continue

        cab    = parte_s.split('\n')[0]
        sub_de = None
        num_m  = None

        if re.match(r'^\s*SUBEMENDA\b', parte_s, re.IGNORECASE):
            partes_cab = re.split(r'\s+[AÀà]\s+EMENDA\b', cab, maxsplit=1, flags=re.IGNORECASE)
            proprio    = partes_cab[0]
            pai_txt    = partes_cab[1] if len(partes_cab) > 1 else ''
            num_m      = re.search(r'N[ºo°]?\s*(\d+)', proprio, re.IGNORECASE)
            pai_m      = re.search(r'N[ºo°]?\s*(\d+)', pai_txt,  re.IGNORECASE)
            if pai_m:
                sub_de = int(pai_m.group(1))
        else:
            num_m = re.search(r'EMENDA\s+N[ºo°]?\s*(\d+)', cab, re.IGNORECASE)

        pecas.append({
            'numero_cab':   int(num_m.group(1)) if num_m else None,
            'sub_de':       sub_de,
            'texto':        parte_s,
        })

    if not pecas:
        return []

    # Número sequencial para peças sem número no cabeçalho
    _max_num = max((p['numero_cab'] for p in pecas if p['numero_cab']), default=0)
    _seq     = _max_num
    for p in pecas:
        if p['numero_cab'] is None:
            _seq += 1
            p['numero_final'] = _seq
        else:
            p['numero_final'] = p['numero_cab']

    # ── Passo 2: classificar com IA em lotes de 25 peças ─────────────────────
    # Envia só as primeiras 400 chars de cada peça — suficiente para classificar.
    # A IA devolve APENAS metadados (tipo, alvo, autor, notas) sem reproduzir texto.
    LOTE = 25
    todas: list[Emenda] = []

    for inicio in range(0, len(pecas), LOTE):
        lote = pecas[inicio:inicio + LOTE]

        linhas_resumo = []
        for p in lote:
            resumo = _resumo_para_ia(p['texto'], max_chars=600)
            linhas_resumo.append(f"No {p['numero_final']}: {resumo}")

        prompt = f"""Você é especialista em técnica legislativa municipal brasileira.

Classifique as emendas abaixo. Retorne APENAS os metadados — NÃO reproduza o texto.

Para cada emenda identifique:
- numero: o número indicado no início (ex: "No 17" → 17)
- tipo: "Modificativa" | "Supressiva" | "Aditiva" | "Substitutiva" | "Aglutinativa" | "Outro"
- alvo: dispositivo afetado (ex: "Art. 5o", "paragrafo 1o do Art. 7o", "inciso VII do Art. 4o", "Anexo III") ou null
- autor: nome do vereador/vereadora principal (apenas o primeiro, sem comissões) ou null
- notas: observação importante (ex: "alvo ambiguo", "emenda incompleta") ou null

Responda SOMENTE com JSON valido:
{{"emendas": [
  {{"numero": 17, "tipo": "Aditiva", "alvo": "Art. 4o", "autor": "Maira do MST", "notas": null}}
]}}

EMENDAS PARA CLASSIFICAR:
{chr(10).join(linhas_resumo)}"""

        meta_por_num: dict[int, dict] = {}
        try:
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=6000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                resp_text = stream.get_final_text()

            m = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if m:
                data = json.loads(m.group())
                for item in data.get('emendas', []):
                    n = item.get('numero')
                    if n is not None:
                        meta_por_num[int(n)] = item
        except Exception:
            pass  # fallback: meta_por_num vazio → emendas entram como brutas

        for p in lote:
            num      = p['numero_final']
            meta     = meta_por_num.get(num, {})
            tipo_str = meta.get('tipo') or ''
            _parseada = bool(meta)   # qualquer resposta da IA = parsing realizado

            if not meta:
                _notas = "Parsing automático falhou — revisar manualmente"
                if p['numero_cab'] is None:
                    _notas += " (numero nao reconhecido no cabecalho)"
            else:
                _notas = meta.get('notas') or None

            todas.append(Emenda(
                numero       = num,
                texto_bruto  = p['texto'],
                tipo         = tipo_map.get(tipo_str, TipoEmenda.OUTRO),
                alvo         = meta.get('alvo'),
                novo_texto   = None,   # harmonizer usa texto_bruto como fallback
                autor        = meta.get('autor'),
                parseada     = _parseada,
                notas_parse  = _notas,
                subemenda_de = p['sub_de'],
            ))

    todas.sort(key=lambda e: e.numero)
    return todas


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

    # Pré-processa subemendas: substitui textos e retira subemendas da lista enviada à IA
    emendas_para_ia, log_subemendas, avisos_subemendas, erros_criticos_sub = _resolver_subemendas(emendas, aprovadas)

    if not emendas_para_ia:
        return ResultadoHarmonizacao(
            texto_harmonizado=texto_original,
            log_alteracoes=["Nenhuma emenda restante após resolução de subemendas. Texto original mantido."]
                           + log_subemendas,
            avisos=avisos_subemendas,
            erros_criticos=erros_criticos_sub,
        )

    # Monta o sumário das emendas aprovadas (já com textos de subemendas substituídos)
    linhas_emendas = []
    for e in emendas_para_ia:
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

A3.1 — CONTEÚDO GRÁFICO, TABULAR E GEORREFERENCIADO (tratamento obrigatório)
    Quando uma emenda cria ou altera Anexo cujo conteúdo é essencialmente gráfico ou tabular
    (mapas, plantas, quadros de parâmetros, tabelas de fatores, coordenadas UTM, delimitações
    georreferenciadas, figuras) e esse conteúdo NÃO foi fornecido no texto da emenda
    (ex.: a emenda nomeia o Anexo sem trazer seu corpo; menciona "conforme tabela" sem fornecer
    a tabela; fornece apenas o título "ANEXO X — [nome]" sem o conteúdo):

    a) Incorpore normalmente o texto normativo da emenda (artigos, incisos, parágrafos, caput).
    b) No local do conteúdo ausente, insira exatamente:
       [INSERIR CONTEÚDO — Emenda Nº N / ANEXO X — (título)]
    c) Gere APENAS um AVISO (§1º) — NÃO erro crítico, NÃO absurdo manifesto:
       "⚠ Emenda N / Anexo X: conteúdo gráfico/tabular não fornecido no texto da emenda —
        inserir o arquivo antes da publicação."
    d) NUNCA gere ERROS_CRITICOS nem ALERTAS_ABSURDOS por ausência de conteúdo gráfico,
       tabular ou georreferenciado. Mapas, tabelas e coordenadas não existem em formato
       texto puro — sua ausência no input é esperada e não configura ininteligibilidade
       jurídica nem falha normativa da CCJ.

    Aplica-se a: Quadros de Parâmetros Urbanísticos, Tabelas de Fator de Ajuste Locacional,
    Tabelas de Potencial Construtivo, Mapas de Subsetores, Anexos de Bens Imóveis, Plantas,
    e qualquer Anexo cujo conteúdo essencial seja visual ou tabular extenso.

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
    b) OBRIGATÓRIO — registrar em ERROS_CRITICOS (não em AVISOS):
       "🚨 Emenda N (modificativa/substitutiva): alvo não identificável — emenda NÃO aplicada.
        A Redação Final está materialmente incompleta. Revisão e decisão do relator obrigatórias
        antes da publicação (art. 250, §2º RI)."
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

E2. CONFLITOS ENTRE EMENDAS APROVADAS — DETECÇÃO OBRIGATÓRIA E SUGESTÃO NORMATIVA

    ⚡ ANTES DE APLICAR QUALQUER EMENDA — VARREDURA PRÉVIA OBRIGATÓRIA:
    Examine a lista completa de emendas aprovadas e identifique TODOS os pares em que:
    (a) Duas ou mais emendas modificam, substituem ou suprimem o MESMO dispositivo
        (mesmo artigo, mesmo parágrafo, mesmo inciso ou mesma alínea)
    (b) Uma emenda supressiva e uma emenda modificativa afetam o MESMO dispositivo
    (c) Duas emendas fixam valores, prazos ou condições incompatíveis para a MESMA obrigação
    (d) Uma emenda que, ao ser aplicada, torna outro dispositivo aprovado de cumprimento impossível

    ⚠ ATENÇÃO — DUAS EMENDAS MODIFICANDO O MESMO DISPOSITIVO É O CASO MAIS PERIGOSO:
    Não tente adivinhar qual deve "prevalecer" — ambas foram aprovadas pelo Plenário soberano.
    Qualquer escolha não autorizada configuraria usurpação da competência plenária.

    PROCEDIMENTO OBRIGATÓRIO PARA CADA CONFLITO IDENTIFICADO:

    PASSO 1 — No TEXTO_HARMONIZADO:
    Aplique a emenda de MENOR NÚMERO (cautela formal — menor número = votada primeiro).
    Imediatamente após o dispositivo conflitante, insira o marcador:
    [[⚠️ CCJ: CONFLITO DE EMENDAS — decisão do relator obrigatória]]

    PASSO 2 — Em ERROS_CRITICOS, registre:
    "🚨 CONFLITO / Emendas [N] e [M] — [dispositivo afetado]:
    • Emenda [N] ([tipo]): [descreva o texto ou ação da Emenda N]
    • Emenda [M] ([tipo]): [descreva o texto ou ação da Emenda M]
    Conflito: [descrição precisa — em que aspecto exato se contradizem]
    No texto: mantida Emenda [N] (menor número) como cautela — marcado para revisão.
    A providência regimental indicada é a reabertura da discussão (art. 250, §2º RI)."

    PASSO 3 — Em SUGESTOES_NORMATIVAS, registre:
    "💡 Sugestão / Emendas [N] e [M] — [dispositivo afetado]:
    [Proposta de redação que tente reconciliar as duas emendas. Se irreconciliáveis, apresente
    as alternativas claramente:
    Alternativa A (Emenda [N] — [tipo]): [texto ou consequência]
    Alternativa B (Emenda [M] — [tipo]): [texto ou consequência]
    Fundamentação da sugestão preferencial (se existir): [razão técnico-legislativa objetiva]]
    ⚠ Sugestão estritamente orientativa — decisão final exclusiva do relator (art. 250, §2º RI)."

    SITUAÇÕES QUE NUNCA DEVEM PASSAR DESPERCEBIDAS:
    — Emenda X modifica Art. Y com redação α; Emenda Z modifica o MESMO Art. Y com redação β
    — Emenda P suprime Art. Q; Emenda R modifica o MESMO Art. Q
    — Emenda S estabelece prazo N dias; Emenda T estabelece prazo M dias para a MESMA obrigação
    — Resultado que gera absurdo jurídico manifesto insanável sem alterar teor (→ ver E3)

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

    SITUAÇÕES QUE NÃO CONFIGURAM ABSURDO MANIFESTO — classificar como ⚠ AVISO, nunca 🔴:
    — Instrução de renumeração de dispositivos de lei externa (ex: "renumerando os demais
      parágrafos do art. X da LC Y") — questão de técnica legislativa sobre eficácia em lei
      externa; o dispositivo desta lei é inteligível; gere aviso de verificação, não 🔴.
    — Erro tipográfico de numeração no texto votado (ex: inciso com dupla indicação "VII - V –")
      quando o inciso é identificável pelo contexto e posição — gere ⚠ AVISO descrevendo o
      problema tipográfico; 🔴 só se o dispositivo ficar completamente ininteligível.
    — Referência a número de lei externa que pode ter sido alterada — incerteza factual, não
      absurdo; gere ⚠ AVISO recomendando verificação.
    — Cláusula de redação incomum, sub-ótima ou passiva sem sujeito explícito, quando ainda
      é possível extrair o comando normativo — imperfeição redacional, não absurdo.

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

<SUGESTOES_NORMATIVAS>
[Sugestões orientativas de harmonização — geradas SOMENTE quando há conflito entre emendas aprovadas (E2).]
[NÃO são decisões da CCJ. NÃO constam no documento exportado. A decisão final é exclusiva do relator.]
[Formato: "💡 Sugestão / Emendas N e M — [dispositivo]: [proposta de texto ou alternativas]"]
[        "⚠ Sugestão estritamente orientativa — decisão final exclusiva do relator (art. 250, §2º RI)."]
[Escreva "Nenhuma sugestão." se não houver conflito.]
</SUGESTOES_NORMATIVAS>

<LOG_ALTERACOES>
[Um registro por linha: "Emenda N (Tipo): ação exata realizada no texto"]
</LOG_ALTERACOES>"""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=64000,   # teto máximo do modelo (claude-sonnet-4-6)
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        resp_text = stream.get_final_text()

    def extrair(tag: str, default: str = "") -> str:
        m = re.search(rf'<{tag}>(.*?)</{tag}>', resp_text, re.DOTALL)
        return m.group(1).strip() if m else default

    # ── Validação: TEXTO_HARMONIZADO é obrigatório; demais tags são opcionais ─
    # Para projetos muito extensos (76+ emendas com capítulos inteiros reescritos),
    # o output da IA pode ser truncado após gerar o texto principal.
    # Estratégia: falhar apenas se o texto harmonizado estiver ausente/vazio;
    # para as demais tags, usar defaults e emitir aviso de resposta parcial.
    _m_texto = re.search(
        r'<TEXTO_HARMONIZADO>(.*?)</TEXTO_HARMONIZADO>', resp_text, re.DOTALL
    )
    if not _m_texto or not _m_texto.group(1).strip():
        raise ValueError(
            "Texto harmonizado ausente ou vazio — resposta da IA inválida. "
            "Tente novamente."
        )

    _TAGS_META = [
        "MAPA_RENUMERACAO", "AVISOS", "ERROS_CRITICOS", "ALERTAS_ABSURDOS",
        "NOTAS_TECNICAS", "SUGESTOES_NORMATIVAS", "LOG_ALTERACOES",
    ]
    _tags_truncadas = [
        t for t in _TAGS_META
        if not re.search(rf'<{t}>(.*?)</{t}>', resp_text, re.DOTALL)
    ]

    texto_harm = re.search(
        r'<TEXTO_HARMONIZADO>(.*?)</TEXTO_HARMONIZADO>', resp_text, re.DOTALL
    ).group(1).strip()   # par validado acima — .group(1) seguro
    mapa_raw      = extrair("MAPA_RENUMERACAO", "")
    avisos_raw    = extrair("AVISOS", "")
    erros_raw     = extrair("ERROS_CRITICOS", "")
    alertas_raw   = extrair("ALERTAS_ABSURDOS", "")
    notas_raw     = extrair("NOTAS_TECNICAS", "")
    sugest_raw    = extrair("SUGESTOES_NORMATIVAS", "")
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
        skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.", "Sem renumeração necessária.", "Nenhuma nota técnica.", "Nenhuma sugestão."}
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
    sugest_list  = parse_linhas(sugest_raw,  modo='paragrafo')
    log_list     = parse_linhas(log_raw,     modo='linha')

    # Se houve truncamento nas seções de metadados, registra aviso proeminente
    if _tags_truncadas:
        _aviso_truncamento = (
            "⚠ ATENÇÃO — RESPOSTA PARCIAL: o projeto é extenso demais para gerar "
            f"todos os metadados em uma única chamada. Seções ausentes: "
            f"{', '.join(_tags_truncadas)}. "
            "O TEXTO HARMONIZADO está completo. "
            "Revise manualmente os dispositivos alterados antes de exportar como Redação Final."
        )
        avisos_list.insert(0, _aviso_truncamento)
        log_list.insert(0,
            f"RESPOSTA-PARCIAL: seções truncadas = {', '.join(_tags_truncadas)}"
        )

    # Pós-processamento: eleva absurdos manifestos classificados erroneamente como §1º avisos
    avisos_list, alertas_list = _escalar_avisos_para_absurdos(
        avisos_list, texto_harm, alertas_list
    )

    # Injeta log, avisos e erros críticos de subemendas no início (pré-processamento visível)
    if log_subemendas:
        log_list = log_subemendas + log_list
    if avisos_subemendas:
        avisos_list = avisos_subemendas + avisos_list
    if erros_criticos_sub:
        # Conflito de subemendas → §2º → ativa fluxo de rascunho de trabalho
        erros_list = erros_criticos_sub + erros_list

    return ResultadoHarmonizacao(
        texto_harmonizado    = texto_harm,
        avisos               = avisos_list,
        erros_criticos       = erros_list,
        alertas_absurdos     = alertas_list,
        mapa_renumeracao     = mapa,
        log_alteracoes       = log_list,
        notas_tecnicas       = notas_list,
        sugestoes_normativas = sugest_list,
    )
