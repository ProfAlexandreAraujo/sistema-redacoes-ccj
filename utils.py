"""
utils.py — Utilitários: leitura/escrita de docx, salvamento de sessão
Sistema de Redações — CCJ CMRJ
"""

import json
import re
import datetime
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from harmonizer import Emenda, TipoEmenda, StatusEmenda, ResultadoHarmonizacao


# ─────────────────────────────────────────────────────────────────────────────
# LEITURA DE DOCX / TXT
# ─────────────────────────────────────────────────────────────────────────────

def ler_docx(arquivo_bytes: bytes) -> str:
    """Extrai texto de um arquivo .docx preservando estrutura básica."""
    doc = Document(BytesIO(arquivo_bytes))
    paragrafos = []
    for para in doc.paragraphs:
        texto = para.text.strip()
        if texto:
            paragrafos.append(texto)
    return '\n'.join(paragrafos)


def ler_txt(arquivo_bytes: bytes) -> str:
    """Decodifica arquivo de texto."""
    for enc in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return arquivo_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return arquivo_bytes.decode('utf-8', errors='replace')


def ler_pdf(arquivo_bytes: bytes) -> str:
    """Extrai texto de arquivo PDF usando pdfplumber.
    Remove cabeçalhos e rodapés típicos de impressões web da CMRJ.
    """
    import re as _re
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber não instalado. Execute: pip install pdfplumber")

    paginas = []
    with pdfplumber.open(BytesIO(arquivo_bytes)) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ''
            # Remove cabeçalhos/rodapés de PDFs impressos do site da CMRJ
            texto = _re.sub(
                r'\d{2}/\d{2}/\d{4},?\s*\d{2}:\d{2}\s+Projeto de Lei.*?\n', '', texto
            )
            texto = _re.sub(
                r'https?://www\.camara\.rio/\S+\s*\n?', '', texto
            )
            paginas.append(texto)

    texto_completo = '\n'.join(paginas)
    # Parar antes de seções de processo/tramitação
    for marcador in ('MENSAGEM Nº', 'LEGISLAÇÃO CITADA', 'TRAMITAÇÃO DO PROJETO',
                     'Distribuição =>', 'Informações Básicas'):
        idx = texto_completo.find(marcador)
        if idx > 500:           # ignora se aparecer logo no início
            texto_completo = texto_completo[:idx]
            break

    return texto_completo.strip()


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISE ESTRUTURAL RÁPIDA
# ─────────────────────────────────────────────────────────────────────────────

def analisar_estrutura(texto: str) -> dict:
    """Retorna contagem de elementos estruturais do projeto.

    Regras baseadas na LC 95/1998, Decreto 12.002/2024 e LC Municipal 48/2000:
    - Artigos: apenas cabeçalhos (início de linha), nunca referências internas
    - Parágrafos: cabeçalhos § Nº ou "Parágrafo único" no início da linha
    - Incisos: algarismos romanos seguidos de travessão (– ou —) ou hífen (-)
    - Alíneas: letras minúsculas seguidas de ) no início da linha (com indentação)
    - Anexos: palavra ANEXO seguida de numeral romano ou arábico no início da linha
    """
    # Artigos: início de linha, seguido de número ordinal (com ou sem º/o)
    # Evita contar referências como "conforme o Art. 3º"
    artigos    = re.findall(
        r'^Art\.\s*\d+[ºo°]?',
        texto, re.MULTILINE | re.IGNORECASE
    )

    # Parágrafos: início de linha (com possível indentação)
    # Evita contar referências como "previsto no § 1º"
    paragrafos = re.findall(
        r'^\s*(?:§\s*\d+[ºo°]?|Parágrafo\s+único)',
        texto, re.MULTILINE | re.IGNORECASE
    )

    # Incisos: numerais romanos no início da linha (com ou sem indentação)
    # seguidos de travessão (–, —) ou hífen (-), conforme LC 95/98 art. 13
    # Cobre até XX para projetos extensos
    incisos    = re.findall(
        r'^\s*(?:X{0,2}(?:IX|IV|V?I{0,3}))\s*[-–—]',
        texto, re.MULTILINE
    )
    # Filtrar falsos positivos: remover matches vazios (ex: "—" sozinho)
    incisos = [m for m in incisos if re.search(r'[IVX]', m)]

    # Alíneas: letras minúsculas a-z seguidas de ) — LC 95/98 art. 13 III
    alineas    = re.findall(
        r'^\s+[a-z]\)\s',
        texto, re.MULTILINE
    )

    # Anexos: início de linha
    anexos     = re.findall(
        r'^\s*ANEXO\s+[IVX\d]+',
        texto, re.MULTILINE | re.IGNORECASE
    )

    return {
        'artigos':    len(artigos),
        'paragrafos': len(paragrafos),
        'incisos':    len(incisos),
        'alineas':    len(alineas),
        'anexos':     len(anexos),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SALVAMENTO / CARREGAMENTO DE SESSÃO
# ─────────────────────────────────────────────────────────────────────────────

SAVES_DIR = Path(__file__).parent / "sessoes_salvas"


def salvar_sessao(nome_projeto: str, texto_original: str, emendas: list[Emenda]) -> Path:
    """Salva estado da sessão em JSON."""
    SAVES_DIR.mkdir(exist_ok=True)
    slug = re.sub(r'[^\w]', '_', nome_projeto or 'projeto')[:40]
    ts   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    caminho = SAVES_DIR / f"{slug}_{ts}.json"
    dados = {
        "nome_projeto":   nome_projeto,
        "texto_original": texto_original,
        "emendas":        [e.to_dict() for e in emendas],
        "salvo_em":       ts,
    }
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return caminho


def listar_sessoes() -> list[Path]:
    """Lista arquivos de sessão salvos, mais recente primeiro."""
    if not SAVES_DIR.exists():
        return []
    return sorted(SAVES_DIR.glob("*.json"), reverse=True)


def carregar_sessao(caminho: Path) -> tuple[str, str, list[Emenda]]:
    """Carrega sessão salva. Retorna (nome_projeto, texto_original, emendas)."""
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    emendas = [Emenda.from_dict(d) for d in dados.get("emendas", [])]
    return dados.get("nome_projeto", ""), dados.get("texto_original", ""), emendas


# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAÇÃO PARA DOCX
# ─────────────────────────────────────────────────────────────────────────────

def _aplicar_sufixo_a(nome: str) -> str:
    """
    Insere o sufixo -A obrigatório no número do projeto.
    Exemplos:
        'PLC 92/2025'                      → 'PLC 92-A/2025'
        'PLC 92/2025 — AEIU Praça XI'     → 'PLC 92-A/2025 — AEIU Praça XI'
        'PLC 92 2025'  (sem barra)         → 'PLC 92 2025'  (não altera)
    """
    return re.sub(r'(\d+)\s*(/\s*\d{4})', r'\1-A\2', nome)


def exportar_redacao_final_docx(
    texto: str,
    nome_projeto: str,
    avisos: list[str],
    erros: list[str],
    alertas_absurdos: list[str] = None,
    mapa: dict = None,
    log: list[str] = None,
    tipo_redacao: str = "Redação Final",
    prosseguir_com_alerta_sec_2: bool = False,
) -> bytes:
    """
    Gera arquivo .docx formatado com o texto harmonizado.
    Inclui folha de rosto e (opcionalmente) anexo com avisos.
    """
    doc = Document()

    # Estilo padrão
    style = doc.styles['Normal']
    style.font.name  = 'Times New Roman'
    style.font.size  = Pt(12)

    # ── Cabeçalho ──
    h = doc.add_heading('CÂMARA MUNICIPAL DO RIO DE JANEIRO', level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    h2 = doc.add_heading('COMISSÃO DE CONSTITUIÇÃO, JUSTIÇA E REDAÇÃO', level=2)
    h2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Verifica presença de alertas §2º
    _alertas_norm = alertas_absurdos or []
    _erros_norm   = erros or []
    tem_sec_2     = bool(_erros_norm or _alertas_norm)

    # ── Modo de exportação ──────────────────────────────────────────────────────
    # Se há alertas §2º e o relator NÃO confirmou ciência:
    #   → documento é RASCUNHO DE TRABALHO (título explícito, sem sufixo -A)
    # Se há alertas §2º e o relator CONFIRMOU ciência (prosseguir_com_alerta_sec_2=True):
    #   → documento é REDAÇÃO FINAL com ALERTA CRÍTICO proeminente + entrada no log
    # Se não há alertas §2º: REDAÇÃO FINAL normal
    eh_rascunho = tem_sec_2 and not prosseguir_com_alerta_sec_2

    if eh_rascunho:
        titulo_doc = "RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL"
    else:
        titulo_doc = tipo_redacao.upper()

    tipo_rdz_p = doc.add_paragraph()
    tipo_rdz_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_titulo = tipo_rdz_p.add_run(titulo_doc)
    run_titulo.bold = True
    run_titulo.font.size = Pt(14)
    if eh_rascunho:
        run_titulo.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

    if eh_rascunho:
        # Aviso explicativo no modo rascunho
        p_alerta = doc.add_paragraph()
        p_alerta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_alerta = p_alerta.add_run(
            "⚠ RASCUNHO — existem alertas de §2º (absurdo manifesto ou erro crítico) "
            "que exigem avaliação antes da publicação da Redação Final. "
            "Confirme ciência na aba 5 do sistema para exportar como Redação Final."
        )
        r_alerta.bold = True
        r_alerta.italic = True
        r_alerta.font.size = Pt(10)
        r_alerta.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    elif tem_sec_2:
        # Relator confirmou ciência — documento é Redação Final com alerta proeminente
        p_alerta = doc.add_paragraph()
        p_alerta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_alerta = p_alerta.add_run(
            "⚠ ALERTA CRÍTICO PENDENTE — ART. 250, §2º RI — "
            "O relator tomou ciência dos alertas de absurdo manifesto/erro crítico "
            "e optou por prosseguir com a Redação Final. "
            "Ver Anexo de Avisos — a providência regimental indicada é a reabertura da discussão."
        )
        r_alerta.bold = True
        r_alerta.italic = True
        r_alerta.font.size = Pt(10)
        r_alerta.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

    if nome_projeto:
        # Sufixo -A apenas no documento formal (não no rascunho de trabalho)
        nome_doc = nome_projeto if eh_rascunho else _aplicar_sufixo_a(nome_projeto)
        p_proj = doc.add_paragraph()
        p_proj.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_proj.add_run(nome_doc).bold = True

    doc.add_paragraph(f"Elaborada em {datetime.date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph()

    # ── Texto harmonizado (marcadores inline de trabalho são removidos do DOCX) ──
    _marker_re  = re.compile(r'\s*\[\[⚠️ CCJ:[^\]]*\]\]', re.UNICODE)
    texto_limpo = _marker_re.sub('', texto)
    for linha in texto_limpo.split('\n'):
        p = doc.add_paragraph(linha)
        # Artigos em negrito
        if re.match(r'\s*Art\.\s*\d+', linha):
            for run in p.runs:
                run.bold = True

    # ── Folha de avisos (se houver) ──
    alertas_absurdos = alertas_absurdos or []
    mapa = mapa or {}
    log  = log  or []
    if avisos or erros or alertas_absurdos:
        doc.add_page_break()
        doc.add_heading('ANEXO — AVISOS E ALERTAS DA CCJ', level=2)
        doc.add_paragraph(
            "Os seguintes pontos foram identificados durante a harmonização e devem ser "
            "avaliados pelo relator antes da publicação da redação final."
        )
        doc.add_paragraph()

        if alertas_absurdos:
            h3 = doc.add_heading('🔴 ABSURDO MANIFESTO — REABERTURA DA DISCUSSÃO (art. 250, §2º, RI)', level=3)
            h3.runs[0].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            doc.add_paragraph(
                "Os itens abaixo configuram incoerência notória, contradição evidente ou "
                "manifesto absurdo capaz de gerar dúvida quanto à vontade legislativa. "
                "Nos termos do art. 250, §2º, do Regimento Interno, a CCJ deverá "
                "eximir-se de oferecer Redação Final e propor, em parecer, a reabertura "
                "da discussão quanto aos aspectos indicados."
            )
            for al in alertas_absurdos:
                doc.add_paragraph(f"🔴  {al}", style='List Bullet')

        if erros:
            h3 = doc.add_heading('🚨 ERROS CRÍTICOS — REABERTURA DA DISCUSSÃO', level=3)
            h3.runs[0].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            doc.add_paragraph(
                "Os itens abaixo envolvem contradição entre emendas aprovadas. "
                "A CCJ deve propor reabertura da discussão (art. 250, §2º, RI)."
            )
            for e in erros:
                doc.add_paragraph(f"🚨  {e}", style='List Bullet')

        if avisos:
            doc.add_heading('⚠️ Avisos redacionais (art. 250, §1º, RI)', level=3)
            doc.add_paragraph(
                "Os itens abaixo compreendem correções de linguagem incorporadas à minuta "
                "(registradas no log para formalização pela CCJ) ou impropriedades apontadas "
                "sem alteração do texto aprovado — em ambos os casos, observada a "
                "formalização prevista no art. 250, §1º, do Regimento Interno."
            )
            for a in avisos:
                doc.add_paragraph(f"⚠  {a}", style='List Bullet')

    if mapa:
        doc.add_paragraph()
        doc.add_heading('Mapa de Renumeração', level=3)
        for orig, novo in mapa.items():
            doc.add_paragraph(f"{orig}  →  {novo}", style='List Bullet')

    # ── Log de alterações ──
    log_final = list(log or [])
    if tem_sec_2 and prosseguir_com_alerta_sec_2:
        log_final.append(
            f"OVERRIDE-HUMANO / Art. 250, §2º RI — Relator tomou ciência dos alertas "
            f"({len(_erros_norm)} erro(s) crítico(s), {len(_alertas_norm)} absurdo(s) manifesto(s)) "
            f"e optou por prosseguir com a Redação Final em {datetime.date.today().strftime('%d/%m/%Y')}."
        )
    if log_final:
        doc.add_paragraph()
        doc.add_heading('Log de Alterações Aplicadas', level=3)
        for item in log_final:
            doc.add_paragraph(f"• {item}")

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def exportar_relatorio_problemas_txt(
    nome_projeto: str,
    avisos: list[str],
    erros: list[str],
    mapa: dict,
    alertas_absurdos: list[str] = None,
) -> str:
    """Gera relatório de problemas em texto simples."""
    linhas = [
        "=" * 60,
        "RELATÓRIO DE PROBLEMAS — SISTEMA DE REDAÇÕES CCJ CMRJ",
        "=" * 60,
        f"Projeto: {nome_projeto or 'Não informado'}",
        f"Data:    {datetime.date.today().strftime('%d/%m/%Y')}",
        "",
    ]
    alertas_absurdos = alertas_absurdos or []
    if alertas_absurdos:
        linhas += ["", "🔴 ABSURDO MANIFESTO — REABERTURA DA DISCUSSÃO (art. 250, §2º, RI):", "-" * 50]
        linhas += [f"  🔴 {al}" for al in alertas_absurdos]
    if erros:
        linhas += ["", "🚨 ERROS CRÍTICOS (podem exigir reabertura — art. 250 §2º RI):", "-" * 50]
        linhas += [f"  🚨 {e}" for e in erros]
    if avisos:
        linhas += ["", "⚠ AVISOS REDACIONAIS (art. 250 §1º RI — corrigíveis mediante ofício):", "-" * 50]
        linhas += [f"  ⚠  {a}" for a in avisos]
    if mapa:
        linhas += ["", "MAPA DE RENUMERAÇÃO:", "-" * 50]
        linhas += [f"  {orig}  →  {novo}" for orig, novo in mapa.items()]
    return '\n'.join(linhas)
