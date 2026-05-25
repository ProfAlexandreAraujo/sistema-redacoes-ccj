#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar.py — Verificação do Sistema de Redações CCJ CMRJ (rev.3)
Testa todos os comportamentos críticos do AUDITORIA.md sem custo de API.

Uso:
    python verificar.py              # Testes locais (gratuito)
    python verificar.py --com-api    # + harmonização completa do PLC 17/2026 (~$0,50)
"""

import sys
import os
import re
import pathlib
from io import BytesIO

sys.stdout.reconfigure(encoding="utf-8")

PASS  = "✅ PASS"
FAIL  = "❌ FAIL"
resultados: list[tuple[str, bool]] = []


def chk(nome: str, ok: bool, detalhe: str = "") -> None:
    simbolo = PASS if ok else FAIL
    print(f"  {simbolo}  {nome}")
    if detalhe and not ok:
        print(f"         ↳ {detalhe}")
    resultados.append((nome, ok))


print()
print("=" * 65)
print("  VERIFICAÇÃO DO SISTEMA — CCJ CMRJ — rev.3")
print("=" * 65)

# ────────────────────────────────────────────────────────────────────────────
# 1. IMPORTAÇÕES
# ────────────────────────────────────────────────────────────────────────────
print("\n[1] IMPORTAÇÕES")

try:
    from harmonizer import (
        _detectar_absurdos_estruturais,
        _escalar_avisos_para_absurdos,
        _PADROES_ABSURDO_AVISO,
        ResultadoHarmonizacao,
        TipoEmenda, StatusEmenda, Emenda,
    )
    chk("harmonizer.py importado", True)
except Exception as e:
    chk("harmonizer.py importado", False, str(e))
    print("\n  Falha crítica — abortando.")
    sys.exit(1)

try:
    from utils import exportar_redacao_final_docx, _aplicar_sufixo_a, analisar_estrutura
    chk("utils.py importado", True)
except Exception as e:
    chk("utils.py importado", False, str(e))

try:
    from docx import Document
    chk("python-docx disponível", True)
    _DOCX_OK = True
except Exception as e:
    chk("python-docx disponível", False, str(e))
    _DOCX_OK = False

# ────────────────────────────────────────────────────────────────────────────
# 2. SUFIXO -A
# ────────────────────────────────────────────────────────────────────────────
print("\n[2] SUFIXO -A NO NÚMERO DO PROJETO")

chk("PLC 92/2025 → PLC 92-A/2025",
    _aplicar_sufixo_a("PLC 92/2025") == "PLC 92-A/2025")
chk("PLC 17/2026 → PLC 17-A/2026",
    _aplicar_sufixo_a("PLC 17/2026") == "PLC 17-A/2026")
chk("Título completo preservado",
    "92-A/2025" in _aplicar_sufixo_a("PLC 92/2025 — AEIU Praça XI"))
chk("Sem barra: não altera",
    _aplicar_sufixo_a("PLC 92 2025") == "PLC 92 2025")

# ────────────────────────────────────────────────────────────────────────────
# 3. DETECTOR ESTRUTURAL — CASO 1 (autoreferência circular)
# ────────────────────────────────────────────────────────────────────────────
print("\n[3] P1 — DETECTOR ESTRUTURAL: Caso 1 (autoreferência circular)")

TEXTO_C1 = (
    "Art. 4º Observada a área de abrangência definida no Art. 4º desta Lei "
    "Complementar, ficam regulamentados os parâmetros urbanísticos.\n\n"
    "Art. 5º Os empreendimentos deverão atender as condições previstas no Art. 3º."
)

al_c1 = _detectar_absurdos_estruturais(TEXTO_C1)
chk("Art. 4 detectado como circular",
    any("Art. 4" in a and "circular" in a for a in al_c1))
chk("Art. 5 NÃO detectado (sem self-ref)",
    not any("Art. 5" in a for a in al_c1))

# ────────────────────────────────────────────────────────────────────────────
# 4. DETECTOR ESTRUTURAL — CASO 2 (condição normativa inoperante)
# ────────────────────────────────────────────────────────────────────────────
print("\n[4] P1 — DETECTOR ESTRUTURAL: Caso 2 (condição normativa inoperante)")

TEXTO_C2 = (
    "Art. 12. Os empreendimentos ficam sujeitos à outorga onerosa.\n\n"
    "§ 1º Atendida a condição prevista no §1º deste artigo, fica dispensada "
    "a apresentação de declaração técnica prévia.\n\n"
    "Art. 13. Outras normas gerais."
)

al_c2 = _detectar_absurdos_estruturais(TEXTO_C2)
chk("§1º detectado como condição inoperante",
    any("§1" in a and "inoperante" in a for a in al_c2))

# ────────────────────────────────────────────────────────────────────────────
# 5. PADRÕES SEMÂNTICOS — CASO 3
# ────────────────────────────────────────────────────────────────────────────
print("\n[5] P1 — PADRÕES SEMÂNTICOS NOS AVISOS: Caso 3")

CASOS_PAD = [
    (True,  "artigo anterior + monitoramento incompatível",
     "⚠ §4: nos termos do artigo anterior — trata de monitoramento, incompatível"),
    (True,  "condição §1 suprimida",
     "⚠ §1: condição prevista no §1 deste artigo foi suprimida pela Emenda 5"),
    (True,  "referência circular",
     "⚠ Art. 4: referência circular — o artigo aponta para si mesmo"),
    (False, "concordância verbal simples NÃO escalada",
     "⚠ Art. 16: concordância verbal — texto preservado como aprovado"),
    (False, "maiúscula simples NÃO escalada",
     "⚠ Art. 10: 'Depósitos' com inicial maiúscula — texto preservado"),
]
for esperado, desc, av in CASOS_PAD:
    chk(f"«{desc}»",
        bool(_PADROES_ABSURDO_AVISO.search(av)) == esperado,
        f"esperado={'escalar' if esperado else 'não escalar'}")

# ────────────────────────────────────────────────────────────────────────────
# 6. INTEGRAÇÃO DO ESCALADOR
# ────────────────────────────────────────────────────────────────────────────
print("\n[6] P1 — INTEGRAÇÃO _escalar_avisos_para_absurdos()")

AVISOS_TEST = [
    "⚠ Emenda 1 / Art. 4: referência circular — Art. 4 aponta para si mesmo",
    "⚠ Emenda 5 / §1: condição prevista no §1 deste artigo foi suprimida",
    "⚠ Emenda 10 / §4: artigo anterior trata de monitoramento, incompatível",
    "⚠ Emenda 8 / Art. 16: serão aplicada — concordância verbal",
    "⚠ Emenda 9 / Art. 10: Depósitos com maiúscula",
]
rest, alrts = _escalar_avisos_para_absurdos(AVISOS_TEST, TEXTO_C1, [])
chk("2 avisos de linguagem permanecem como avisos",
    len(rest) == 2,
    f"restantes={len(rest)}, esperado=2 — {rest}")
chk("≥3 absurdos escalados para §2º",
    len(alrts) >= 3,
    f"alertas={len(alrts)}, esperado≥3")
chk("Avisos de linguagem são os corretos (concordância / maiúscula)",
    any("serão aplicada" in r or "concordância" in r.lower() for r in rest) and
    any("Depósitos" in r or "maiúscula" in r for r in rest))

# ────────────────────────────────────────────────────────────────────────────
# 7. EXPORTAÇÃO DOCX
# ────────────────────────────────────────────────────────────────────────────
print("\n[7] EXPORTAÇÃO DOCX")

if _DOCX_OK:
    TEXTO_MARCADOR = (
        "Art. 1º Texto normal.\n"
        "Art. 2º Texto problemático. [[⚠️ CCJ: DISPOSITIVO ININTELIGÍVEL]]\n"
        "Art. 3º Conclusão."
    )

    # 7a — Com §2º → RASCUNHO, sem sufixo -A, sem marcadores
    try:
        docx_a = exportar_redacao_final_docx(
            texto=TEXTO_MARCADOR, nome_projeto="PLC 17/2026",
            avisos=[], erros=[],
            alertas_absurdos=["🔴 Art. 2: absurdo manifesto"],
        )
        doc_a  = Document(BytesIO(docx_a))
        txts_a = [p.text for p in doc_a.paragraphs]
        chk("Com §2º → título 'RASCUNHO DE TRABALHO'",
            any("RASCUNHO DE TRABALHO" in t for t in txts_a))
        chk("Com §2º → NÃO contém 'REDAÇÃO FINAL' como título",
            not any(t.strip() == "REDAÇÃO FINAL" for t in txts_a))
        chk("Com §2º → NÃO aplica sufixo -A (rascunho informal)",
            not any("17-A/2026" in t for t in txts_a))
        chk("Marcadores [[⚠️ CCJ:...]] removidos do DOCX",
            not any("[[" in t for t in txts_a))
    except Exception as e:
        chk("DOCX com §2º", False, str(e))

    # 7b — Sem §2º → REDAÇÃO FINAL com sufixo -A
    try:
        docx_b = exportar_redacao_final_docx(
            texto="Art. 1º Texto limpo sem problemas.",
            nome_projeto="PLC 17/2026",
            avisos=[], erros=[], alertas_absurdos=[],
        )
        doc_b  = Document(BytesIO(docx_b))
        txts_b = [p.text for p in doc_b.paragraphs]
        chk("Sem §2º → título 'REDAÇÃO FINAL'",
            any("REDAÇÃO FINAL" in t for t in txts_b))
        chk("Sem §2º → sufixo -A aplicado ('17-A/2026')",
            any("17-A/2026" in t for t in txts_b))
    except Exception as e:
        chk("DOCX sem §2º", False, str(e))
else:
    print("  ⏭  DOCX — python-docx não disponível, pulando")

# ────────────────────────────────────────────────────────────────────────────
# 8. ANÁLISE ESTRUTURAL
# ────────────────────────────────────────────────────────────────────────────
print("\n[8] ANÁLISE ESTRUTURAL (analisar_estrutura)")

TEXTO_EST = (
    "Art. 1º Disposições gerais.\n"
    "Art. 2º Regulamentação.\n"
    "§ 1º Primeiro parágrafo.\n"
    "§ 2º Segundo parágrafo.\n"
    "I — primeiro inciso;\n"
    "II — segundo inciso.\n"
    "  a) alínea a;\n"
    "  b) alínea b.\n"
    "ANEXO I\nANEXO II\nANEXO III"
)
est = analisar_estrutura(TEXTO_EST)
chk("2 artigos",    est["artigos"]    == 2, f"encontrado: {est['artigos']}")
chk("2 parágrafos", est["paragrafos"] == 2, f"encontrado: {est['paragrafos']}")
chk("3 anexos",     est["anexos"]     == 3, f"encontrado: {est['anexos']}")

# ────────────────────────────────────────────────────────────────────────────
# 9. CHAVE DE API
# ────────────────────────────────────────────────────────────────────────────
print("\n[9] CHAVE DE API ANTHROPIC")

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
chk("ANTHROPIC_API_KEY definida",
    bool(api_key),
    "Defina com:  $env:ANTHROPIC_API_KEY='sk-ant-...'  (PowerShell)")

# ────────────────────────────────────────────────────────────────────────────
# 10. ARQUIVOS DE STRESS TEST
# ────────────────────────────────────────────────────────────────────────────
print("\n[10] ARQUIVOS DO STRESS TEST (PLC 17/2026)")

TAB1 = pathlib.Path(r"C:\Users\Admin\Downloads\TAB_1_PLC_17_2026_TEXTO_ORIGINAL.txt")
TAB2 = pathlib.Path(r"C:\Users\Admin\Downloads\TAB_2_PLC_17_2026_EMENDAS.txt")
chk("TAB_1 (texto original) encontrado", TAB1.exists(), str(TAB1))
chk("TAB_2 (emendas) encontrado",        TAB2.exists(), str(TAB2))

# ────────────────────────────────────────────────────────────────────────────
# RESUMO
# ────────────────────────────────────────────────────────────────────────────
print()
print("=" * 65)
total  = len(resultados)
passou = sum(1 for _, ok in resultados if ok)
falhou = total - passou
print(f"  RESULTADO FINAL: {passou}/{total} verificações passaram")

if falhou:
    print(f"\n  ⚠  {falhou} falha(s) detectada(s):")
    for nome, ok in resultados:
        if not ok:
            print(f"     ❌ {nome}")
    print()
else:
    print("\n  ✅ Tudo certo — sistema pronto para uso no PLC real.")
    print()

print("=" * 65)

# ────────────────────────────────────────────────────────────────────────────
# 11. HARMONIZAÇÃO COMPLETA (--com-api)
# ────────────────────────────────────────────────────────────────────────────
if "--com-api" not in sys.argv:
    print()
    print("  Dica: rode  python verificar.py --com-api  para testar a")
    print("  harmonização completa do PLC 17/2026 (custo ~$0,50).")
    print()
    sys.exit(0 if falhou == 0 else 1)

print()
print("[11] HARMONIZAÇÃO COMPLETA (--com-api) — PLC 17/2026")

if not api_key:
    print("  ⏭  ANTHROPIC_API_KEY não definida — pulando.")
    sys.exit(0 if falhou == 0 else 1)

if not (TAB1.exists() and TAB2.exists()):
    print("  ⏭  Arquivos TAB_1/TAB_2 não encontrados — pulando.")
    sys.exit(0 if falhou == 0 else 1)

try:
    from utils import ler_txt
    from harmonizer import parsear_emendas_com_ia, harmonizar_texto

    print("  Carregando arquivos de texto...")
    texto_orig    = ler_txt(TAB1.read_bytes())
    texto_emendas = ler_txt(TAB2.read_bytes())

    print("  Parseando emendas com IA...")
    emendas = parsear_emendas_com_ia(texto_emendas, api_key)
    for e in emendas:
        e.status = StatusEmenda.APROVADA
    print(f"  {len(emendas)} emendas parseadas. Harmonizando (pode demorar ~2 min)...")

    resultado = harmonizar_texto(texto_orig, emendas, api_key, "PLC 17/2026")
    est_fin   = analisar_estrutura(resultado.texto_harmonizado)

    print()
    print("  --- Resultados da harmonização ---")
    print(f"  Artigos:  {est_fin['artigos']} (esperado: 18)")
    print(f"  Anexos:   {est_fin['anexos']}  (esperado: 5)")
    print(f"  Absurdos §2º: {len(resultado.alertas_absurdos)} (esperado: ≥3)")
    print(f"  Avisos §1º:   {len(resultado.avisos)}")
    print()

    chk("[API] 18 artigos",  est_fin["artigos"] == 18,  f"encontrado: {est_fin['artigos']}")
    chk("[API] 5 anexos",    est_fin["anexos"]  == 5,   f"encontrado: {est_fin['anexos']}")
    chk("[API] ≥3 absurdos manifestos §2º",
        len(resultado.alertas_absurdos) >= 3,
        f"alertas_absurdos={len(resultado.alertas_absurdos)}")
    # Aceita "§1º" ou "§ 1º" (com ou sem espaço — ambas são formatações válidas)
    chk("[API] Frase verbatim §1º preservada",
        bool(re.search(r'Atendida a condição prevista no §\s*1º deste artigo',
                       resultado.texto_harmonizado)))
    chk("[API] 'artigo anterior' preservado no §4º",
        "nos termos do artigo anterior" in resultado.texto_harmonizado)
    # E1 — auto-correções registradas no LOG (critérios 3 e 6 do AUDITORIA.md)
    chk("[API] E1: 'serão aplicadas' corrigido no texto (Emenda 8)",
        "serão aplicadas" in resultado.texto_harmonizado,
        "verificar se Emenda 8 foi corrigida")
    chk("[API] E1: 'depósitos' em minúscula no texto (Emenda 9)",
        bool(re.search(r'\bdepósitos\b', resultado.texto_harmonizado)),
        "verificar se Emenda 9 foi corrigida")
    chk("[API] E1: LOG registra correção de concordância",
        any("serão aplicad" in l.lower() or "E1" in l for l in resultado.log_alteracoes),
        f"log tem {len(resultado.log_alteracoes)} entradas")
    # Critério 5: "; e" → aviso apenas, NÃO auto-corrigido
    chk("[API] E1: ausência de '; e' gera aviso (não auto-corrige — LC 48/2000 apenas)",
        any("; e" in a.lower() or "conectivo" in a.lower() or "penúltim" in a.lower()
            for a in resultado.avisos),
        "esperado: aviso sobre '; e' em AVISOS §1º")
    # CA/mérito: observações sobre parâmetros urbanísticos NÃO devem aparecer em AVISOS
    chk("[API] Sem observações de mérito/CA nos AVISOS",
        not any(re.search(r'\bCA\b|\bcoeficiente de aproveitamento\b|\bganharit\b|'
                          r'setor [AB].*maior|maior.*setor|gabarito.*CA|CA.*gabarito',
                          a, re.IGNORECASE)
                for a in resultado.avisos),
        "AVISOS não devem conter análises de mérito urbanístico")
    chk("[API] Marcadores inline removidos do DOCX",
        not any("[[" in t for t in [p.text for p in Document(BytesIO(
            exportar_redacao_final_docx(
                resultado.texto_harmonizado, "PLC 17/2026",
                resultado.avisos, resultado.erros_criticos,
                resultado.alertas_absurdos,
            )
        )).paragraphs]))

    # Salva resultado completo
    saida = pathlib.Path("resultado_verificar.txt")
    with open(saida, "w", encoding="utf-8") as f:
        f.write("=== RESULTADO HARMONIZAÇÃO PLC 17/2026 — VERIFICAR.PY ===\n\n")
        f.write(f"Artigos: {est_fin['artigos']}  |  Anexos: {est_fin['anexos']}\n\n")
        f.write(f"--- ALERTAS §2º ({len(resultado.alertas_absurdos)}) ---\n")
        for a in resultado.alertas_absurdos:
            f.write(f"  {a}\n")
        f.write(f"\n--- ERROS CRÍTICOS ({len(resultado.erros_criticos)}) ---\n")
        for e in resultado.erros_criticos:
            f.write(f"  {e}\n")
        f.write(f"\n--- AVISOS §1º ({len(resultado.avisos)}) ---\n")
        for a in resultado.avisos:
            f.write(f"  {a}\n")
        f.write("\n--- LOG DE ALTERAÇÕES ---\n")
        for l in resultado.log_alteracoes:
            f.write(f"  {l}\n")
        f.write("\n--- TEXTO HARMONIZADO ---\n")
        f.write(resultado.texto_harmonizado)
    print(f"\n  Resultado completo salvo em: {saida.resolve()}")

except Exception as e:
    chk("[API] Harmonização sem erro", False, str(e))
    import traceback
    traceback.print_exc()

# Resumo final com API
print()
print("=" * 65)
total2  = len(resultados)
passou2 = sum(1 for _, ok in resultados if ok)
falhou2 = total2 - passou2
print(f"  RESULTADO FINAL (com API): {passou2}/{total2} verificações passaram")
if falhou2:
    print(f"\n  ❌ {falhou2} falha(s):")
    for nome, ok in resultados:
        if not ok:
            print(f"     • {nome}")
else:
    print("\n  ✅ Sistema completamente verificado — pronto para PLC 92/2025.")
print("=" * 65)
print()
sys.exit(0 if falhou2 == 0 else 1)
