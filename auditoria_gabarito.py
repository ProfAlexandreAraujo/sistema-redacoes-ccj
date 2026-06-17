"""
auditoria_gabarito.py — Comparador de Gabarito
Sistema de Redações — CCJ CMRJ

Confronta a saída da harmonização (ResultadoHarmonizacao + texto) com um GABARITO
oficial (a Redação Final efetivamente publicada e o checklist técnico derivado dela),
medindo a CONVERGÊNCIA do aplicativo com o resultado oficial.

Projetado para ser puro (sem Streamlit) — pode ser chamado da interface ou de testes.

Cada gabarito é um par de arquivos em ./gabaritos/:
  - <slug>_gabarito.json          → checklist técnico (expectativas auditáveis)
  - <slug>_redacao_oficial.txt    → texto integral da redação final publicada

O JSON é a fonte de verdade dos testes; o .txt é usado para a cobertura
dispositivo-a-dispositivo.
"""

from __future__ import annotations

import re
import json
import unicodedata
from pathlib import Path
from dataclasses import dataclass, field

GABARITOS_DIR = Path(__file__).parent / "gabaritos"

# Status possíveis de cada item de auditoria
OK      = "ok"        # convergente com o oficial
ATENCAO = "atencao"   # divergência leve / verificar
FALHA   = "falha"     # divergência relevante com o resultado oficial
INFO    = "info"      # informativo (não pontua)


# ─────────────────────────────────────────────────────────────────────────────
# ESTRUTURAS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ItemAuditoria:
    status: str          # OK | ATENCAO | FALHA | INFO
    grupo: str           # categoria (ex: "Estrutura", "Alertas")
    titulo: str
    detalhe: str = ""
    sugestao: str = ""

    @property
    def icone(self) -> str:
        return {OK: "✅", ATENCAO: "⚠️", FALHA: "❌", INFO: "ℹ️"}.get(self.status, "•")


@dataclass
class RelatorioAuditoria:
    projeto: str
    fonte: str
    itens: list[ItemAuditoria] = field(default_factory=list)

    def add(self, status, grupo, titulo, detalhe="", sugestao=""):
        self.itens.append(ItemAuditoria(status, grupo, titulo, detalhe, sugestao))

    # Contagens
    @property
    def n_ok(self):      return sum(1 for i in self.itens if i.status == OK)
    @property
    def n_atencao(self): return sum(1 for i in self.itens if i.status == ATENCAO)
    @property
    def n_falha(self):   return sum(1 for i in self.itens if i.status == FALHA)

    @property
    def score(self) -> int:
        """Convergência 0–100: OK conta cheio, ATENÇÃO conta meio, FALHA zero."""
        pontuaveis = [i for i in self.itens if i.status in (OK, ATENCAO, FALHA)]
        if not pontuaveis:
            return 0
        pontos = sum(1.0 if i.status == OK else 0.5 if i.status == ATENCAO else 0.0
                     for i in pontuaveis)
        return round(pontos / len(pontuaveis) * 100)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE NORMALIZAÇÃO E BUSCA
# ─────────────────────────────────────────────────────────────────────────────

def _sem_acento(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def _norm(s: str) -> str:
    """minúsculas, sem acento, espaços colapsados."""
    return re.sub(r'\s+', ' ', _sem_acento(s).lower()).strip()


def _menciona_emenda(texto: str, num: int | str) -> bool:
    """True se `texto` referencia a Emenda/Subemenda de número `num`
    (em qualquer forma usual), sem confundir 6 com 60/66."""
    n = str(num)
    pats = [
        rf'(?:emendas?|subemendas?)\s*n?[ºo°]?\s*0*{n}(?!\d)',
        rf'\bE{n}(?!\d)\b',
        rf'\bS\d+\s*/\s*E{n}(?!\d)\b',
    ]
    low = _sem_acento(texto).lower()
    for p in pats:
        if re.search(p, low, re.IGNORECASE):
            return True
    return False


def _numeros_em_lista_de_emendas(texto: str) -> set[int]:
    """Extrai todos os números citados como emendas, inclusive em listas
    'Emendas 6, 84 e 41'."""
    nums: set[int] = set()
    low = _sem_acento(texto)
    # 'E66', 'E6'
    for m in re.finditer(r'\bE(\d{1,3})(?!\d)', low):
        nums.add(int(m.group(1)))
    # 'Emenda(s) N, M e P' — captura a sequência após a palavra-chave
    for m in re.finditer(r'(?:emendas?|subemendas?)\s*n?[ºo°]?\s*([\d,\s eE]+)',
                         low, re.IGNORECASE):
        for x in re.findall(r'\d{1,3}', m.group(1)):
            nums.add(int(x))
    return nums


def _numeros_de_emenda_nao_sub(texto: str) -> set[int]:
    """Números citados como EMENDA (não subemenda). Usado no controle de peças
    rejeitadas, que são emendas — 'Subemenda 9' nunca deve casar com 'Emenda 9'."""
    nums: set[int] = set()
    low = _sem_acento(texto).lower()
    # 'E66', 'E9' — forma abreviada de emenda (subemendas usam 'S')
    for m in re.finditer(r'\bE(\d{1,3})(?!\d)', low):
        nums.add(int(m.group(1)))
    # 'Emenda(s) N, M e P' — exclui 'subemenda' via lookbehind
    for m in re.finditer(r'(?<!sub)emendas?\s*n?[ºo°]?\s*([\d,\s e]+)', low):
        for x in re.findall(r'\d{1,3}', m.group(1)):
            nums.add(int(x))
    return nums


def _blob(*listas) -> str:
    out = []
    for l in listas:
        if not l:
            continue
        if isinstance(l, dict):
            out.extend(f"{k} {v}" for k, v in l.items())
        else:
            out.extend(str(x) for x in l)
    return '\n'.join(out)


def _artigos_no_texto(texto: str) -> list[int]:
    """Sequência de números de artigo (cabeçalhos 'Art. N') na ordem de aparição."""
    return [int(m.group(1)) for m in re.finditer(r'(?m)^\s*Art\.\s*(\d+)', texto)]


# ─────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DE GABARITOS
# ─────────────────────────────────────────────────────────────────────────────

def listar_gabaritos() -> list[Path]:
    if not GABARITOS_DIR.exists():
        return []
    return sorted(GABARITOS_DIR.glob("*_gabarito.json"))


def detectar_gabarito(nome_projeto: str) -> Path | None:
    """Escolhe o gabarito cujo `nome_match` melhor casa com o nome do projeto."""
    alvo = _norm(nome_projeto or "")
    melhor, melhor_score = None, 0
    for p in listar_gabaritos():
        try:
            dados = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        score = sum(1 for tok in dados.get('nome_match', []) if _norm(tok) in alvo)
        if score > melhor_score:
            melhor, melhor_score = p, score
    return melhor


def carregar_gabarito(path: Path) -> dict:
    dados = json.loads(Path(path).read_text(encoding='utf-8'))
    # Carrega o texto oficial associado, se houver
    txt_nome = dados.get('texto_oficial')
    dados['_texto_oficial_conteudo'] = ""
    if txt_nome:
        txt_path = Path(path).parent / txt_nome
        if txt_path.exists():
            dados['_texto_oficial_conteudo'] = txt_path.read_text(encoding='utf-8')
    return dados


# ─────────────────────────────────────────────────────────────────────────────
# CHECKS INDIVIDUAIS
# ─────────────────────────────────────────────────────────────────────────────

def _check_entrada(emendas, gab, rel):
    exp = gab.get('entrada_esperada', {})
    if not emendas:
        return
    from harmonizer import StatusEmenda
    aprov = [e for e in emendas if getattr(e, 'status', None) == StatusEmenda.APROVADA]
    subs = [e for e in aprov if getattr(e, 'subemenda_de', None)]
    pais = [e for e in aprov if not getattr(e, 'subemenda_de', None)]
    esp_e = exp.get('emendas_aprovadas')
    esp_s = exp.get('subemendas_aprovadas')
    det = (f"Carregadas {len(pais)} emendas-pai aprovadas e {len(subs)} subemendas "
           f"(esperado: {esp_e} emendas + {esp_s} subemendas = {exp.get('total_pecas')}).")
    if esp_e is not None and (len(pais) == esp_e and len(subs) == esp_s):
        rel.add(OK, "Entrada", "Conjunto aprovado confere com o oficial", det)
    else:
        rel.add(ATENCAO, "Entrada", "Conjunto aprovado diverge do esperado", det,
                sugestao=exp.get('observacao', ''))


def _check_subemendas(resultado, gab, rel):
    log = _blob(getattr(resultado, 'log_alteracoes', []))
    faltando = []
    for s in gab.get('subemendas', []):
        sub, pai = s['sub'], s['emenda_pai']
        # procura "SubEmenda <sub>" e "Emenda <pai>" próximos no log de substituição
        achou = bool(re.search(
            rf'subemenda\s*n?[ºo°]?\s*{sub}\b.*?emenda\s*n?[ºo°]?\s*{pai}\b',
            _sem_acento(log), re.IGNORECASE | re.DOTALL)) or (
            _menciona_emenda(log, pai) and re.search(
                rf'subemenda\s*n?[ºo°]?\s*{sub}\b', _sem_acento(log), re.IGNORECASE))
        if not achou:
            faltando.append(f"S{sub}→E{pai}")
    total = len(gab.get('subemendas', []))
    if not faltando:
        rel.add(OK, "Subemendas",
                f"As {total} substituições de subemenda foram aplicadas",
                "S1→E105, S2→E122, S3→E126, S4→E128, S5→E99, S6→E102, S7→E96, "
                "S8→E136, S9→E101 — todas registradas no log.")
    else:
        rel.add(FALHA, "Subemendas",
                f"{len(faltando)} substituição(ões) de subemenda não localizada(s) no log",
                "Não confirmadas: " + ", ".join(faltando),
                "A subemenda aprovada deve substituir o texto da emenda-pai antes da montagem.")


def _check_estrutura(texto, gab, rel):
    arts = _artigos_no_texto(texto)
    est = gab.get('estrutura_final', {})
    alvo = est.get('total_artigos')
    if not arts:
        rel.add(ATENCAO, "Estrutura", "Nenhum artigo detectado no texto harmonizado",
                "Verifique se o texto foi gerado corretamente.")
        return
    ultimo = max(arts)
    # contiguidade
    seq = sorted(set(arts))
    faltam = [n for n in range(1, ultimo + 1) if n not in seq]
    duplic = sorted({n for n in arts if arts.count(n) > 1})
    det = f"Texto vai até Art. {ultimo} (oficial termina em Art. {alvo})."
    if duplic:
        det += f" Números repetidos: {duplic}."
    if faltam:
        det += f" Números ausentes na sequência: {faltam[:10]}{'…' if len(faltam) > 10 else ''}."
    if alvo and ultimo == alvo and not duplic and not faltam:
        rel.add(OK, "Estrutura",
                f"Numeração final converge: {ultimo} artigos contíguos", det)
    elif alvo and abs(ultimo - alvo) <= 2 and not duplic:
        rel.add(ATENCAO, "Estrutura",
                f"Numeração final próxima do oficial ({ultimo} vs {alvo})", det,
                "Diferença de poucos artigos — conferir agrupamento de anexos / artigos externos.")
    else:
        rel.add(FALHA, "Estrutura",
                f"Numeração final diverge do oficial ({ultimo} vs {alvo})", det,
                "Estabeleça a arquitetura de capítulos/seções ANTES de numerar artigos (ver Tabela 7 do diagnóstico).")


def _check_alertas_criticos(texto, resultado, gab, rel):
    sec2 = _blob(getattr(resultado, 'erros_criticos', []),
                 getattr(resultado, 'alertas_absurdos', []),
                 getattr(resultado, 'avisos', []))
    for ac in gab.get('alertas_criticos_esperados', []):
        padrao = ac.get('padrao', '')
        no_texto = bool(padrao) and padrao.lower() in texto.lower()
        sinalizado = bool(padrao) and padrao.lower() in sec2.lower()
        peca = ac.get('peca', '')
        # também aceita sinalização por menção à peça + termo de ininteligibilidade
        if not sinalizado and peca:
            sinalizado = bool(re.search(r'ininteligibilidade|absurdo|sem sentido', _sem_acento(sec2), re.I)) and \
                         _menciona_emenda(sec2, re.sub(r'\D', '', peca.split('/')[-1]) or '0')
        if no_texto and sinalizado:
            rel.add(OK, "Alerta crítico",
                    f"'{padrao}' ({peca}) preservado e sinalizado",
                    ac.get('decisao_oficial', ''))
        elif no_texto and not sinalizado:
            rel.add(FALHA, "Alerta crítico",
                    f"'{padrao}' ({peca}) está no texto mas NÃO foi sinalizado",
                    "O token sem sentido normativo foi incorporado sem alerta.",
                    "Deve gerar ALERTA DE ABSURDO / ERRO CRÍTICO (art. 250 §2º) e ser preservado verbatim no rascunho.")
        else:
            rel.add(INFO, "Alerta crítico",
                    f"'{padrao}' ({peca}) não está no texto harmonizado",
                    ac.get('decisao_oficial', '') +
                    "  → Confirme qual input foi carregado: a versão .docx das emendas contém o termo; "
                    "a publicação oficial o removeu por decisão do relator.")


def _check_avisos_formais(resultado, gab, rel):
    avisos_blob = _blob(getattr(resultado, 'avisos', []),
                        getattr(resultado, 'erros_criticos', []),
                        getattr(resultado, 'alertas_absurdos', []))
    faltando, presentes = [], []
    for af in gab.get('avisos_formais_esperados', []):
        toks = af.get('match', [])
        ok = all((t.isdigit() and _menciona_emenda(avisos_blob, t)) or
                 (not t.isdigit() and _norm(t) in _norm(avisos_blob))
                 for t in toks) if toks else False
        (presentes if ok else faltando).append(af)
    if not faltando:
        rel.add(OK, "Avisos formais",
                f"Todos os {len(presentes)} avisos formais esperados foram emitidos",
                "; ".join(a['peca'] for a in presentes))
    else:
        rel.add(ATENCAO, "Avisos formais",
                f"{len(faltando)} aviso(s) formal(is) esperado(s) ausente(s)",
                "\n".join(f"• {a['peca']}: {a['assunto']}" for a in faltando),
                "São pendências de técnica legislativa (§1º) que o diagnóstico oficial aponta.")


def _check_alertas_proibidos(resultado, gab, rel):
    ap = gab.get('alertas_proibidos', {})
    rejeitadas = ap.get('pecas_rejeitadas_ou_retiradas', [])
    sec2 = _blob(getattr(resultado, 'erros_criticos', []),
                 getattr(resultado, 'alertas_absurdos', []))
    nums_rej = {int(re.sub(r'\D', '', r)) for r in rejeitadas if re.sub(r'\D', '', r)}
    nums_citados = _numeros_de_emenda_nao_sub(sec2)
    indevidos = sorted(nums_rej & nums_citados)
    # confirma contexto de conflito
    indevidos = [n for n in indevidos
                 if re.search(r'conflito|conflit', _sem_acento(sec2), re.I)]
    if not indevidos:
        rel.add(OK, "Alertas proibidos",
                "Nenhum alerta contra peças rejeitadas/retiradas",
                "Peças rejeitadas (E6, E84, E41, E29, E77, E9, E34, E95, E79, E143) "
                "corretamente ausentes dos conflitos.")
    else:
        rel.add(FALHA, "Alertas proibidos",
                f"Conflito citando peça(s) rejeitada(s): {indevidos}",
                ap.get('motivo', ''),
                "Remova esses alertas — as peças não integram o conjunto aprovado.")


def _check_nao_escalar(resultado, gab, rel):
    sec2_itens = list(getattr(resultado, 'erros_criticos', [])) + \
                 list(getattr(resultado, 'alertas_absurdos', []))
    achados = []
    for regra in gab.get('nao_escalar_2', []):
        # Padrões e texto comparados sem acento (evita descasamento por diacríticos)
        pats = [re.compile(_sem_acento(p), re.IGNORECASE | re.DOTALL)
                for p in regra.get('padroes', [])]
        for item in sec2_itens:
            alvo = _sem_acento(item)
            if any(p.search(alvo) for p in pats):
                achados.append((regra, item))
    if not achados:
        rel.add(OK, "Classificação §1º/§2º",
                "Nenhuma superescalada §2º indevida detectada",
                "Anexos sem conteúdo, renumeração de lei externa e dupla numeração "
                "não estão indevidamente como erro crítico / absurdo.")
    else:
        # agrupa por regra
        por_regra = {}
        for regra, item in achados:
            por_regra.setdefault(regra['id'], (regra, []))[1].append(item[:160])
        for rid, (regra, itens) in por_regra.items():
            rel.add(FALHA, "Classificação §1º/§2º",
                    f"{len(itens)} item(ns) escalado(s) a §2º que deveriam ser {regra['classe_correta']}",
                    "\n".join(f"• {t}…" for t in itens[:6]),
                    regra.get('fundamento', ''))


def _check_harmonizacoes(resultado, gab, rel):
    log = _blob(getattr(resultado, 'log_alteracoes', []),
               getattr(resultado, 'mapa_renumeracao', {}),
               getattr(resultado, 'notas_tecnicas', []),
               getattr(resultado, 'avisos', []))
    incompletas = []
    for h in gab.get('harmonizacoes_obrigatorias', []):
        toks = h.get('match', [])
        achou = sum(1 for t in toks if _menciona_emenda(log, t))
        if achou < max(1, len(toks) // 2):
            incompletas.append((h['nucleo'], achou, len(toks)))
    total = len(gab.get('harmonizacoes_obrigatorias', []))
    if not incompletas:
        rel.add(OK, "Harmonizações",
                f"Os {total} núcleos estruturais obrigatórios aparecem no log",
                "Art. 3º, Art. 4º, Operação Interligada, Art. 28, pacote de anexos, "
                "alterações externas + ementa.")
    else:
        rel.add(ATENCAO, "Harmonizações",
                f"{len(incompletas)} núcleo(s) com cobertura parcial no log",
                "\n".join(f"• {n}: {a}/{t} peças citadas" for n, a, t in incompletas),
                "Confirme que nenhum comando aprovado foi omitido na montagem.")


def _check_conflitos_harmonizaveis(resultado, gab, rel):
    erros = list(getattr(resultado, 'erros_criticos', []))
    for c in gab.get('conflitos_que_sao_harmonizacao', []):
        pecas = c.get('pecas', [])
        for item in erros:
            if all(_menciona_emenda(item, p) for p in pecas) and \
               re.search(r'conflito', _sem_acento(item), re.I):
                rel.add(ATENCAO, "Conflito × harmonização",
                        f"Conflito Emendas {' e '.join(pecas)} — o oficial resolveu por montagem",
                        item[:240] + ("…" if len(item) > 240 else ""),
                        c.get('resolucao', ''))
                break


def _check_cobertura_texto(texto, gab, rel):
    oficial = gab.get('_texto_oficial_conteudo', '')
    if not oficial or not texto:
        return
    # Fingerprint de cada artigo oficial: primeiras palavras significativas do caput
    alvo = _norm(texto)
    arts = re.split(r'(?m)^\s*(?=Art\.\s*\d+)', oficial)
    achados = 0
    total = 0
    faltando = []
    for bloco in arts:
        m = re.match(r'Art\.\s*(\d+)', bloco.strip())
        if not m:
            continue
        total += 1
        corpo = _norm(re.sub(r'^Art\.\s*\d+[ºo°]?', '', bloco.strip())[:200])
        palavras = [w for w in corpo.split() if len(w) > 4][:6]
        if len(palavras) < 3:
            achados += 1  # artigo curto demais para impressão digital — não penaliza
            continue
        frag = ' '.join(palavras[:4])
        if frag and frag in alvo:
            achados += 1
        else:
            faltando.append(m.group(1))
    if total:
        pct = round(achados / total * 100)
        det = f"{achados} de {total} dispositivos da publicação oficial localizados na saída do app ({pct}%)."
        if faltando:
            det += f" Não localizados (por impressão digital do caput): Art. {', '.join(faltando[:15])}."
        status = OK if pct >= 85 else ATENCAO if pct >= 60 else FALHA
        rel.add(status, "Cobertura textual",
                f"Cobertura dispositivo-a-dispositivo: {pct}%", det,
                "Divergências podem refletir reescrita por emenda — confira os artigos listados contra o Diário."
                if faltando else "")


# ─────────────────────────────────────────────────────────────────────────────
# API PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def auditar(resultado, texto_harmonizado: str, emendas, gabarito: dict) -> RelatorioAuditoria:
    """Executa todos os checks e retorna o relatório de convergência."""
    rel = RelatorioAuditoria(
        projeto=gabarito.get('projeto', 'Projeto'),
        fonte=gabarito.get('fonte', ''),
    )
    texto = texto_harmonizado or getattr(resultado, 'texto_harmonizado', '') or ''

    _check_entrada(emendas, gabarito, rel)
    _check_subemendas(resultado, gabarito, rel)
    _check_estrutura(texto, gabarito, rel)
    _check_alertas_criticos(texto, resultado, gabarito, rel)
    _check_avisos_formais(resultado, gabarito, rel)
    _check_alertas_proibidos(resultado, gabarito, rel)
    _check_nao_escalar(resultado, gabarito, rel)
    _check_conflitos_harmonizaveis(resultado, gabarito, rel)
    _check_harmonizacoes(resultado, gabarito, rel)
    _check_cobertura_texto(texto, gabarito, rel)

    return rel
