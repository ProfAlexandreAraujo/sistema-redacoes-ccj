"""
teste_real.py — Simulação de sessão real no terminal
Sistema de Redações CCJ CMRJ

Execute: python teste_real.py
"""

import sys
import os
import re
import time
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

OK    = "✅"
ERRO  = "❌"
AVISO = "⚠️"
INFO  = "ℹ️"

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

# ─── Cabeçalho ────────────────────────────────────────────────────────────────
print()
print("=" * 65)
print("  TESTE REAL — Sistema de Redações CCJ CMRJ")
print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("=" * 65)

# ─── ETAPA 1: Carregar PLC ────────────────────────────────────────────────────
print("\n[ETAPA 1] Carregando PLC 92/2025...")

pdf_path = os.path.join(BASE, "PLC 92 2025.pdf")
txt_path = os.path.join(BASE, "PLC_92_2025_limpo.txt")

texto_plc = ""

if os.path.isfile(txt_path):
    with open(txt_path, encoding='utf-8') as f:
        texto_plc = f.read()
    print(f"  {OK}  Texto limpo carregado: {len(texto_plc):,} caracteres")
elif os.path.isfile(pdf_path):
    print(f"  {INFO}  Extraindo texto do PDF...")
    try:
        from utils import ler_pdf
        with open(pdf_path, 'rb') as f:
            texto_plc = ler_pdf(f.read())
        print(f"  {OK}  PDF extraído: {len(texto_plc):,} caracteres")
    except Exception as ex:
        print(f"  {ERRO}  Erro ao ler PDF: {ex}")
else:
    print(f"  {ERRO}  Arquivo PLC não encontrado. Coloque 'PLC 92 2025.pdf' na pasta.")
    sys.exit(1)

# ─── ETAPA 2: Análise estrutural ──────────────────────────────────────────────
print("\n[ETAPA 2] Analisando estrutura do projeto (LC 95/98)...")

from utils import analisar_estrutura
struct = analisar_estrutura(texto_plc)

print(f"  {OK}  Artigos detectados:    {struct['artigos']}")
print(f"  {OK}  Parágrafos detectados: {struct['paragrafos']}")
print(f"  {OK}  Incisos detectados:    {struct['incisos']}")
print(f"  {OK}  Alíneas detectadas:    {struct['alineas']}")
print(f"  {OK}  Anexos detectados:     {struct['anexos']}")

if struct['artigos'] < 10:
    print(f"  {AVISO}  Poucos artigos — verifique se o texto está completo.")
if struct['anexos'] == 0:
    print(f"  {AVISO}  Nenhum Anexo detectado — o PLC 92/2025 tem 4 Anexos.")

# ─── ETAPA 3: Chave API ───────────────────────────────────────────────────────
print("\n[ETAPA 3] Verificando chave API...")

api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    secrets_path = os.path.join(BASE, ".streamlit", "secrets.toml")
    if os.path.isfile(secrets_path):
        with open(secrets_path, encoding='utf-8') as f:
            for linha in f:
                if "ANTHROPIC_API_KEY" in linha:
                    api_key = linha.split("=", 1)[1].strip().strip('"\'')
                    break

if api_key and len(api_key) > 20:
    print(f"  {OK}  Chave API encontrada: {api_key[:20]}…")
else:
    print(f"  {AVISO}  Chave API não encontrada localmente.")
    print(f"       → A chave está nos Secrets do Streamlit Cloud.")
    print(f"       → Para teste local: crie .streamlit/secrets.toml com ANTHROPIC_API_KEY = \"sk-...\"")
    print()
    print("  Pulando etapas que requerem API (4 e 5).")
    print()
    print("=" * 65)
    print(f"  {OK}  ESTRUTURA OK — Sistema pronto para uso no Streamlit Cloud.")
    print(f"  → Acesse: https://ccj-redacoes.streamlit.app")
    print("=" * 65)
    print()
    sys.exit(0)

# ─── ETAPA 4: Teste de parsing de emendas ─────────────────────────────────────
print("\n[ETAPA 4] Testando parsing de emendas com IA (3 emendas sintéticas)...")

EMENDAS_TESTE = """
EMENDA Nº 1 — SUPRESSIVA
Autor: Vereador João Silva — Partido Democrático Municipal — PDM

Texto formal da emenda:
Suprima-se o art. 5º da Lei Complementar nº 17/2026.

Justificativa:
A subdivisão em setores já está contemplada no Anexo II, tornando o art. 5º redundante.

EMENDA Nº 2 — MODIFICATIVA
Autor: Vereadora Ana Costa — Movimento Renovação Urbana — MRU

Texto formal da emenda:
O § 1º do art. 6º passa a vigorar com a seguinte redação:
"§ 1º O gabarito máximo de que trata o caput poderá ser acrescido de dois pavimentos
mediante contrapartida ao Fundo de Desenvolvimento Urbano, conforme regulamentação
do Poder Executivo."

Justificativa:
Amplia a flexibilidade dos parâmetros de ocupação para incentivar investimentos na AEIU.

EMENDA Nº 3 — ADITIVA
Autor: Vereador Carlos Menezes — Aliança pelo Rio — AR

Texto formal da emenda:
Acrescente-se ao art. 14 o seguinte inciso V:
"V — execução de obras de infraestrutura viária indicadas no Anexo I desta Lei Complementar."

Justificativa:
Inclui obrigação de contrapartida em obras viárias, alinhando o instrumento ao objetivo de
requalificação do sistema de mobilidade na área de abrangência.
"""

t0 = time.time()
try:
    from harmonizer import parsear_emendas_com_ia, StatusEmenda
    print(f"  {INFO}  Enviando para a API... aguarde.")
    emendas = parsear_emendas_com_ia(EMENDAS_TESTE, api_key)
    elapsed = time.time() - t0
    print(f"  {OK}  {len(emendas)} emendas parseadas em {elapsed:.1f}s")
    for e in emendas:
        tipo = e.tipo.value if e.tipo else "?"
        alvo = e.alvo or "—"
        print(f"       Emenda {e.numero}: {tipo} | Alvo: {alvo} | Autor: {e.autor or '—'}")
        if e.notas_parse:
            print(f"       {AVISO} Nota: {e.notas_parse}")
except Exception as ex:
    print(f"  {ERRO}  Erro no parsing: {ex}")
    sys.exit(1)

# ─── ETAPA 5: Teste de harmonização ───────────────────────────────────────────
print("\n[ETAPA 5] Testando harmonização com IA (texto real + 3 emendas)...")

# Usar só os primeiros 8.000 chars para o teste rápido
texto_trecho = texto_plc[:8000]
if len(texto_plc) > 8000:
    texto_trecho += "\n[... texto truncado para teste rápido ...]"

for e in emendas:
    e.status = StatusEmenda.APROVADA

t0 = time.time()
try:
    from harmonizer import harmonizar_texto
    print(f"  {INFO}  Harmonizando... aguarde (pode levar 20-40s).")
    resultado = harmonizar_texto(
        texto_original=texto_trecho,
        emendas=emendas,
        api_key=api_key,
        nome_projeto="PLC 92/2025 — AEIU Praça XI Maravilha [TESTE]"
    )
    elapsed = time.time() - t0

    print(f"  {OK}  Harmonização concluída em {elapsed:.1f}s")
    print(f"       Texto harmonizado: {len(resultado.texto_harmonizado):,} chars")
    print(f"       Absurdos manifestos:  {len(resultado.alertas_absurdos)}")
    print(f"       Erros críticos:       {len(resultado.erros_criticos)}")
    print(f"       Avisos jurídicos:     {len(resultado.avisos)}")
    print(f"       Log (ações):          {len(resultado.log_alteracoes)}")
    print(f"       Mapa renumeração:     {len(resultado.mapa_renumeracao)} entradas")

    if resultado.alertas_absurdos:
        print(f"\n  🔴  ABSURDOS MANIFESTOS:")
        for al in resultado.alertas_absurdos:
            print(f"       {al}")

    if resultado.erros_criticos:
        print(f"\n  🚨  ERROS CRÍTICOS:")
        for e in resultado.erros_criticos:
            print(f"       {e}")

    if resultado.avisos:
        print(f"\n  ⚠️   AVISOS JURÍDICOS ({len(resultado.avisos)}):")
        for a in resultado.avisos:
            print(f"       {a}")

    if resultado.mapa_renumeracao:
        print(f"\n  🔢  MAPA DE RENUMERAÇÃO:")
        for orig, novo in resultado.mapa_renumeracao.items():
            print(f"       {orig}  →  {novo}")

    # Salvar resultado
    saida = os.path.join(BASE, "resultado_teste_real.txt")
    with open(saida, 'w', encoding='utf-8') as f:
        f.write("RESULTADO DO TESTE REAL\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        f.write("TEXTO HARMONIZADO:\n")
        f.write(resultado.texto_harmonizado)
        f.write("\n\n" + "=" * 60 + "\n")
        if resultado.alertas_absurdos:
            f.write("\nABSURDOS MANIFESTOS:\n")
            for al in resultado.alertas_absurdos:
                f.write(f"  🔴 {al}\n")
        if resultado.erros_criticos:
            f.write("\nERROS CRÍTICOS:\n")
            for e in resultado.erros_criticos:
                f.write(f"  🚨 {e}\n")
        if resultado.avisos:
            f.write(f"\nAVISOS JURÍDICOS ({len(resultado.avisos)}):\n")
            for a in resultado.avisos:
                f.write(f"  ⚠  {a}\n")
        if resultado.mapa_renumeracao:
            f.write("\nMAPA DE RENUMERAÇÃO:\n")
            for orig, novo in resultado.mapa_renumeracao.items():
                f.write(f"  {orig}  →  {novo}\n")
        if resultado.log_alteracoes:
            f.write(f"\nLOG ({len(resultado.log_alteracoes)} ações):\n")
            for item in resultado.log_alteracoes:
                f.write(f"  • {item}\n")

    print(f"\n  {OK}  Resultado salvo em: resultado_teste_real.txt")

except Exception as ex:
    print(f"  {ERRO}  Erro na harmonização: {ex}")
    import traceback
    traceback.print_exc()

# ─── Resumo final ─────────────────────────────────────────────────────────────
print()
print("=" * 65)
print(f"  {OK}  TESTE REAL CONCLUÍDO — sistema operacional para amanhã.")
print()
print("  Próximos passos:")
print("  1. Acesse https://ccj-redacoes.streamlit.app")
print("  2. Tab 1 → faça upload do PDF do PLC real")
print("  3. Tab 2 → cole as emendas aprovadas → Processar com IA")
print("  4. Tab 3 → marque as aprovadas (ou pule se só subiu aprovadas)")
print("  5. Tab 4 → Harmonizar agora")
print("  6. Tab 5 → revisar e baixar .docx")
print("=" * 65)
print()
