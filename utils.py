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

def exportar_redacao_final_docx(
    texto: str,
    nome_projeto: str,
    avisos: list[str],
    erros: list[str],
    mapa: dict,
    log: list[str],
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

    tipo_rdz = doc.add_paragraph()
    tipo_rdz.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tipo_rdz.add_run('REDAÇÃO FINAL')
    run.bold = True
    run.font.size = Pt(14)

    if nome_projeto:
        p_proj = doc.add_paragraph()
        p_proj.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_proj.add_run(nome_projeto).bold = True

    doc.add_paragraph(f"Elaborada em {datetime.date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph()

    # ── Texto harmonizado ──
    for linha in texto.split('\n'):
        p = doc.add_paragraph(linha)
        # Artigos em negrito
        if re.match(r'\s*Art\.\s*\d+', linha):
            for run in p.runs:
                run.bold = True

    # ── Folha de avisos (se houver) ──
    if avisos or erros:
        doc.add_page_break()
        doc.add_heading('ANEXO — AVISOS E ALERTAS DA CCJ', level=2)
        doc.add_paragraph(
            "Os seguintes pontos foram identificados durante a harmonização e devem ser "
            "avaliados pelo relator antes da publicação da redação final."
        )
        doc.add_paragraph()

        if erros:
            doc.add_heading('ERROS CRÍTICOS', level=3).runs[0].font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            for e in erros:
                p = doc.add_paragraph(f"🔴  {e}", style='List Bullet')

        if avisos:
            doc.add_heading('Avisos', level=3)
            for a in avisos:
                doc.add_paragraph(f"⚠  {a}", style='List Bullet')

    if mapa:
        doc.add_paragraph()
        doc.add_heading('Mapa de Renumeração', level=3)
        for orig, novo in mapa.items():
            doc.add_paragraph(f"{orig}  →  {novo}", style='List Bullet')

    # ── Log de alterações ──
    if log:
        doc.add_paragraph()
        doc.add_heading('Log de Alterações Aplicadas', level=3)
        for item in log:
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
    if erros:
        linhas += ["", "ERROS CRÍTICOS (podem exigir reabertura da discussão — art. 250 §2º RI):", "-" * 50]
        linhas += [f"  🔴 {e}" for e in erros]
    if avisos:
        linhas += ["", "AVISOS (art. 250 §1º RI — corrigíveis mediante ofício justificado):", "-" * 50]
        linhas += [f"  ⚠  {a}" for a in avisos]
    if mapa:
        linhas += ["", "MAPA DE RENUMERAÇÃO:", "-" * 50]
        linhas += [f"  {orig}  →  {novo}" for orig, novo in mapa.items()]
    return '\n'.join(linhas)
