# -*- coding: utf-8 -*-
"""
Suíte de verificação da calibração — Sistema de Redações CCJ.
Roda sem API (verifica tudo que não depende da chamada ao modelo).

Uso:  python tests/verificar_calibracao.py
"""
import sys, io, os, re
from pathlib import Path
APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

falhas = []
def check(nome, cond, detalhe=""):
    status = "PASS" if cond else "FALHA"
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe and not cond else ""))
    if not cond:
        falhas.append(nome)

print("=" * 64)
print("VERIFICAÇÃO DA CALIBRAÇÃO — Sistema de Redações CCJ")
print("=" * 64)

# ── 1. Imports / compilação ──────────────────────────────────────────────────
import harmonizer as H
import auditoria_gabarito as ag
check("1. Módulos importam (harmonizer, auditoria_gabarito)", True)

# ── 2. Desescalada §2º→§1º: casos que DEVEM ser rebaixados ────────────────────
deve_rebaixar = [
    "🚨 Emenda 106 (aditiva) — Anexo V: a emenda não fornece o conteúdo do Anexo V (Bens imóveis). A Redação Final está materialmente incompleta neste Anexo.",
    "🚨 Emenda 127 (aditiva) — Anexos VI e VII: a emenda não fornece o conteúdo dos Anexos. Estes Anexos são referenciados em artigos operativos (arts. 15, 18, 19).",
    "🔴 Emenda 149 / Art. 62: revogação do § 1º do Art. 437 da LC 270/2024, renumerando os demais parágrafos.",
    "🔴 Emenda 66 / Art. 3º inc. VII: o texto contém a dupla indicação 'VI - V –' (dois números ordinais).",
]
a, e, av, log = H._desescalar_falsos_sec2([deve_rebaixar[2], deve_rebaixar[3]],
                                          [deve_rebaixar[0], deve_rebaixar[1]], [], [])
check("2a. Anexos sem conteúdo rebaixados a §1º (0 erros restantes)", len(e) == 0, f"{len(e)} restaram")
check("2b. Renumeração externa + dupla numeração rebaixadas (0 absurdos)", len(a) == 0, f"{len(a)} restaram")
check("2c. Itens movidos para AVISOS (§1º)", len(av) == 4, f"{len(av)} avisos")

# ── 3. GUARDA: §2º GENUÍNO nunca pode ser rebaixado ──────────────────────────
genuino_sec2_absurdos = [
    "🔴 Art. 4º: o dispositivo referencia o próprio Art. 4º (autoreferência circular) — absurdo manifesto.",
    "🔴 §2º: a condição prevista no §1º deste artigo foi suprimida (condição normativa inoperante).",
    "🔴 Emenda 105: token 'TRADUZIK' sem sentido normativo entre os incisos II e III (ininteligibilidade).",
]
genuino_sec2_erros = [
    "🚨 CONFLITO / Emendas 30 e 31 — Art. 9º: duas redações que se excluem para o mesmo dispositivo.",
]
a2, e2, av2, log2 = H._desescalar_falsos_sec2(list(genuino_sec2_absurdos),
                                              list(genuino_sec2_erros), [], [])
check("3a. Absurdos §2º genuínos PRESERVADOS (autoref, inoperante, ininteligível)",
      len(a2) == 3, f"sobraram {len(a2)} de 3")
check("3b. Conflito de emendas §2º PRESERVADO", len(e2) == 1, f"sobrou {len(e2)} de 1")
check("3c. Nenhum §2º genuíno virou aviso", len(av2) == 0, f"{len(av2)} viraram aviso")

# ── 4. GUARDA tem prioridade: anexo + conflito juntos → NÃO rebaixa ───────────
misto = "🚨 CONFLITO / Emendas 5 e 6 — Anexo V cujo conteúdo a emenda não fornece, gerando contradição entre emendas."
a3, e3, av3, _ = H._desescalar_falsos_sec2([], [misto], [], [])
check("4. Item com marca de conflito NÃO é rebaixado mesmo citando anexo ausente",
      len(e3) == 1 and len(av3) == 0)

# ── 5. Comparador detecta divergências na saída CRUA real (se pontos.txt existir) ─
PONTOS = Path(r"C:\Users\Admin\Downloads\_calib_plc92\pontos.txt")
gab = ag.carregar_gabarito(APP / "gabaritos" / "PLC92_2025_gabarito.json")
if PONTOS.exists():
    linhas = io.open(PONTOS, encoding='utf-8').read().split('\n')
    class R:
        alertas_absurdos = [l for l in linhas if l.startswith('🔴 🔴')]
        erros_criticos   = [l for l in linhas if l.startswith('🚨 🚨')]
        avisos           = [l for l in linhas if l.startswith('⚠️ ⚠')]
        notas_tecnicas   = []
        log_alteracoes   = [l[2:].strip() for l in linhas if l.startswith('• ')]
        mapa_renumeracao = {}
        texto_harmonizado = ""
    txt_cru = '\n'.join(f"Art. {n}º X." for n in (list(range(1,43))+[43,43]+list(range(44,66))))
    rel_cru = ag.auditar(R, txt_cru, [], gab)
    check("5a. Comparador roda na saída crua", rel_cru.score is not None, "")
    check("5b. Saída crua acusa divergência (score < 60)", rel_cru.score < 60,
          f"score={rel_cru.score}")
    # aplica calibração determinística + estrutura limpa = projeção calibrada
    a4, e4, av4, lg4 = H._desescalar_falsos_sec2(list(R.alertas_absurdos),
                                                 list(R.erros_criticos), list(R.avisos), [])
    R.alertas_absurdos, R.erros_criticos, R.avisos = a4, e4, av4
    R.log_alteracoes = R.log_alteracoes + lg4
    txt_ok = '\n'.join(f"Art. {n}º X." for n in range(1, 64))
    rel_ok = ag.auditar(R, txt_ok, [], gab)
    check("5c. Após calibração o score sobe (>= 70)", rel_ok.score >= 70, f"score={rel_ok.score}")
    print(f"      → convergência: crua {rel_cru.score}/100  →  calibrada {rel_ok.score}/100")
else:
    print("[skip] 5. pontos.txt não encontrado — teste de saída real pulado")

# ── 6. Integridade do gabarito oficial ───────────────────────────────────────
oficial = gab.get('_texto_oficial_conteudo', '')
arts = re.findall(r'(?m)^Art\.\s*(\d+)', oficial)
seq = [int(x) for x in arts]
check("6a. Gabarito carrega texto oficial", len(oficial) > 50000)
check("6b. Gabarito tem 63 artigos contíguos terminando em 63",
      seq == list(range(1, 64)), f"seq vai de {seq[0] if seq else '?'} a {seq[-1] if seq else '?'}, n={len(seq)}")
check("6c. Gabarito não contém ruído de página",
      not any(re.fullmatch(r'(N[ºo°]\.?|\d{1,3})', l.strip()) for l in oficial.split('\n')))
check("6d. 'TRADUZIK' ausente do gabarito (removido na publicação)", 'TRADUZIK' not in oficial)

# ── 7. Checklist técnico do gabarito coerente ────────────────────────────────
check("7a. 9 subemendas mapeadas", len(gab.get('subemendas', [])) == 9)
check("7b. 6 avisos formais esperados", len(gab.get('avisos_formais_esperados', [])) == 6)
check("7c. 10 peças rejeitadas listadas",
      len(gab['alertas_proibidos']['pecas_rejeitadas_ou_retiradas']) == 10)
check("7d. 3 regras de desescalada §2º→§1º", len(gab.get('nao_escalar_2', [])) == 3)

print("=" * 64)
if falhas:
    print(f"RESULTADO: {len(falhas)} FALHA(S) → {falhas}")
    sys.exit(1)
print("RESULTADO: TODOS OS TESTES PASSARAM ✓")
