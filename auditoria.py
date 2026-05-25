"""
auditoria.py — Diagnóstico completo do Sistema de Redações CCJ CMRJ
Execute: python auditoria.py
"""

import sys
import os
import importlib
import json
from datetime import datetime

OK = "✅"
ERRO = "❌"
AVISO = "⚠️"

resultados = []

def check(label, ok, detalhe=""):
    simbolo = OK if ok else ERRO
    msg = f"  {simbolo}  {label}"
    if detalhe:
        msg += f"\n       → {detalhe}"
    print(msg)
    resultados.append((label, ok, detalhe))
    return ok

print()
print("=" * 60)
print("  AUDITORIA — Sistema de Redações CCJ CMRJ")
print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
print("=" * 60)

# ── 1. Python ──────────────────────────────────────────────
print("\n[1] Versão do Python")
v = sys.version_info
check(
    f"Python {v.major}.{v.minor}.{v.micro}",
    v.major == 3 and v.minor >= 10,
    "Requer Python 3.10+" if not (v.major == 3 and v.minor >= 10) else "OK"
)

# ── 2. Dependências ────────────────────────────────────────
print("\n[2] Dependências instaladas")
deps = {
    "streamlit": "1.35.0",
    "anthropic": "0.20.0",
    "docx": None,       # python-docx importa como 'docx'
}
for mod, min_ver in deps.items():
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", "?")
        check(f"{mod} (v{ver})", True)
    except ImportError:
        check(mod, False, "Não instalado — rode: pip install -r requirements.txt")

# ── 3. Arquivos do sistema ─────────────────────────────────
print("\n[3] Arquivos essenciais")
base = os.path.dirname(os.path.abspath(__file__))
arquivos = ["app.py", "harmonizer.py", "utils.py", "requirements.txt"]
for arq in arquivos:
    caminho = os.path.join(base, arq)
    existe = os.path.isfile(caminho)
    tamanho = f"{os.path.getsize(caminho):,} bytes" if existe else ""
    check(arq, existe, tamanho)

# ── 4. Chave API ───────────────────────────────────────────
print("\n[4] Chave API Anthropic")
chave = os.environ.get("ANTHROPIC_API_KEY", "")
secrets_path = os.path.join(base, ".streamlit", "secrets.toml")
secrets_existe = os.path.isfile(secrets_path)

if chave:
    check("ANTHROPIC_API_KEY (variável de ambiente)", True, chave[:20] + "…")
elif secrets_existe:
    check("secrets.toml encontrado", True, secrets_path)
    # tentar ler
    try:
        with open(secrets_path, encoding="utf-8") as f:
            conteudo = f.read()
        tem_chave = "ANTHROPIC_API_KEY" in conteudo
        check("ANTHROPIC_API_KEY no secrets.toml", tem_chave,
              "Chave presente" if tem_chave else "Chave ausente no arquivo")
    except Exception as e:
        check("Leitura do secrets.toml", False, str(e))
else:
    check("Chave API configurada", False,
          "Nem env var nem secrets.toml encontrados — no Streamlit Cloud está OK")

# ── 5. Teste de conexão com a API ──────────────────────────
print("\n[5] Conexão com a API Anthropic")
chave_efetiva = chave
if not chave_efetiva and secrets_existe:
    try:
        with open(secrets_path, encoding="utf-8") as f:
            for linha in f:
                if "ANTHROPIC_API_KEY" in linha:
                    chave_efetiva = linha.split("=", 1)[1].strip().strip('"\'')
                    break
    except Exception:
        pass

if chave_efetiva and len(chave_efetiva) > 20:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=chave_efetiva)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": "Responda só: OK"}]
        )
        resposta = msg.content[0].text.strip()
        check("API Anthropic respondeu", True, f'Resposta: "{resposta}"')
    except Exception as e:
        check("API Anthropic respondeu", False, str(e))
else:
    print(f"  {AVISO}  Chave não disponível localmente — teste de API ignorado")
    print("       → No Streamlit Cloud a chave está configurada nos Secrets")

# ── 6. Importação dos módulos do sistema ───────────────────
print("\n[6] Módulos do sistema")
sys.path.insert(0, base)
try:
    import harmonizer
    check("harmonizer.py importado", True)
    # Verificar classes principais
    tem_emenda = hasattr(harmonizer, "Emenda")
    tem_parsear = hasattr(harmonizer, "parsear_emendas_com_ia")
    tem_harmonizar = hasattr(harmonizer, "harmonizar_texto")
    check("Classe Emenda", tem_emenda)
    check("Função parsear_emendas_com_ia", tem_parsear)
    check("Função harmonizar_texto", tem_harmonizar)
except Exception as e:
    check("harmonizer.py importado", False, str(e))

try:
    import utils
    check("utils.py importado", True)
    tem_ler_docx = hasattr(utils, "ler_docx")
    tem_estrutura = hasattr(utils, "analisar_estrutura")
    tem_sessao = hasattr(utils, "salvar_sessao")
    check("Função ler_docx", tem_ler_docx)
    check("Função analisar_estrutura", tem_estrutura)
    check("Função salvar_sessao", tem_sessao)
except Exception as e:
    check("utils.py importado", False, str(e))

# ── 7. Teste de parsing de emenda fictícia ─────────────────
print("\n[7] Teste de estrutura — emenda fictícia")
try:
    from harmonizer import Emenda, TipoEmenda, StatusEmenda
    e = Emenda(
        numero=1,
        texto_bruto="Emenda nº 1 — Modifica o Art. 5º para: Art. 5º. Novo texto aprovado.",
        tipo=TipoEmenda.MODIFICATIVA,
        status=StatusEmenda.APROVADA,
        alvo="Art. 5º",
        novo_texto="Art. 5º. Novo texto aprovado.",
        autor="Vereador Teste",
        parseada=True,
    )
    d = e.to_dict()
    e2 = Emenda.from_dict(d)
    check("Criação de Emenda", True)
    check("Serialização to_dict / from_dict", e2.numero == 1 and e2.autor == "Vereador Teste")
    check("Status aprovada", e.status == StatusEmenda.APROVADA)
    check("Campo 'alvo' correto", e.alvo == "Art. 5º")
    check("Campo 'novo_texto' correto", e.novo_texto == "Art. 5º. Novo texto aprovado.")
except Exception as ex:
    check("Teste de Emenda fictícia", False, str(ex))

# ── 8. Teste analisar_estrutura ────────────────────────────
print("\n[8] Teste de análise de estrutura legislativa (LC 95/1998)")
try:
    from utils import analisar_estrutura
    # Texto com formato correto conforme LC 95/98 e Decreto 12.002/2024
    # Artigos no início da linha, incisos com algarismo romano + travessão,
    # alíneas com letra minúscula + ) com indentação
    texto_teste = (
        "Art. 1º Este é o artigo primeiro.\n"
        "§ 1º Este é o parágrafo primeiro.\n"
        "§ 2º Este é o parágrafo segundo.\n"
        "I — primeiro inciso;\n"
        "II — segundo inciso;\n"
        "   a) primeira alínea;\n"
        "   b) segunda alínea.\n"
        "Art. 2º Este é o artigo segundo, que faz referência ao Art. 1º.\n"
        "Parágrafo único. Parágrafo único do artigo segundo.\n"
        "Art. 3º Este artigo menciona o Art. 2º e o Art. 1º internamente.\n"
        "I — inciso do terceiro artigo;\n"
        "II — outro inciso;\n"
        "III — terceiro inciso.\n"
        "ANEXO I\n"
        "Tabela de dados.\n"
    )
    resultado = analisar_estrutura(texto_teste)
    a = resultado.get('artigos', 0)
    p = resultado.get('paragrafos', 0)
    i = resultado.get('incisos', 0)
    al = resultado.get('alineas', 0)
    ax = resultado.get('anexos', 0)
    # Texto tem: 3 artigos, 3 parágrafos (§1, §2, Parágrafo único),
    #            5 incisos, 2 alíneas, 1 anexo
    # Referências internas (Art. 1º, Art. 2º dentro do texto) NÃO devem ser contadas
    check(f"Artigos: {a} (esperado 3 — referências internas ignoradas)", a == 3,
          "Bug: regex conta referências dentro do texto como artigos" if a != 3 else "OK")
    check(f"Parágrafos: {p} (esperado 3)", p == 3,
          "Bug: parágrafo não detectado ou referência interna contada" if p != 3 else "OK")
    check(f"Incisos: {i} (esperado 5)", i == 5,
          "Bug: incisos não detectados (checar regex romano + travessão)" if i != 5 else "OK")
    check(f"Alíneas: {al} (esperado 2)", al == 2,
          "Bug: alíneas não detectadas (checar indentação + letra + parêntese)" if al != 2 else "OK")
    check(f"Anexos: {ax} (esperado 1)", ax == 1,
          "Bug: ANEXO não detectado" if ax != 1 else "OK")
except Exception as ex:
    check("analisar_estrutura", False, str(ex))

# ── Resumo final ───────────────────────────────────────────
print()
print("=" * 60)
total = len(resultados)
passou = sum(1 for _, ok, _ in resultados if ok)
falhou = total - passou

if falhou == 0:
    print(f"  {OK}  TUDO OK — {passou}/{total} verificações passaram")
    print()
    print("  Sistema pronto para uso.")
    print("  Acesse: https://ccj-redacoes.streamlit.app")
else:
    print(f"  {AVISO}  {passou}/{total} verificações OK — {falhou} problema(s) encontrado(s)")
    print()
    print("  Itens com falha:")
    for label, ok, detalhe in resultados:
        if not ok:
            print(f"    {ERRO} {label}: {detalhe}")
print("=" * 60)
print()
