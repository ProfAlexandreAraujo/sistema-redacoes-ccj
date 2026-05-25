# 🔍 Auditoria — Sistema de Redações CCJ CMRJ

## Como executar o diagnóstico

Abra o terminal na pasta do sistema e rode:

```
python auditoria.py
```

---

## O que o script verifica

| # | Verificação | O que testa |
|---|---|---|
| 1 | **Python** | Versão 3.10+ instalada |
| 2 | **Dependências** | streamlit, anthropic, python-docx instalados |
| 3 | **Arquivos** | app.py, harmonizer.py, utils.py, requirements.txt presentes |
| 4 | **Chave API** | secrets.toml ou variável de ambiente configurada |
| 5 | **Conexão API** | Chama a API Anthropic e verifica se responde |
| 6 | **Módulos** | Importa harmonizer.py e utils.py sem erros |
| 7 | **Emenda fictícia** | Cria, serializa e desserializa uma emenda de teste |
| 8 | **Análise estrutural** | Detecta artigos, parágrafos, incisos e anexos num texto exemplo |

---

## Fluxo de trabalho recomendado para amanhã

```
ANTES DA SESSÃO
│
├── 1. Abrir https://ccj-redacoes.streamlit.app
├── 2. Tab 1 · Projeto → carregar o texto do PLC (upload .docx ou colar)
└── 3. Tab 2 · Emendas → colar o bloco de emendas aprovadas (IA parseia)

DURANTE A SESSÃO (opcional)
│
└── Tab 3 · Votação → pode IGNORAR se subir só emendas aprovadas
                      (ou usar para marcar todas como ✅ de uma vez)

APÓS A VOTAÇÃO
│
├── Tab 4 · Harmonizar → clicar "Harmonizar Texto"
│                        (IA renumera, atualiza referências, aponta problemas)
│
└── Tab 5 · Redação Final → revisar, editar manualmente se necessário
                            → baixar .docx ou .txt formatado
```

---

## Sobre o Tab 3 — Votação

> **Você perguntou:** "Eu só vou subir as emendas aprovadas, tem problema?"

Não tem problema nenhum. Existem duas formas de usar:

**Opção A — Só aprovadas (mais simples):**
- Suba apenas as emendas que foram aprovadas
- Pule o Tab 3
- Vá direto para o Tab 4

**Opção B — Todas as emendas (com controle):**
- Suba todas as emendas (aprovadas + rejeitadas)
- No Tab 3, marque ✅ as aprovadas e ❌ as rejeitadas
- O sistema ignora automaticamente as rejeitadas na harmonização

---

## Regras críticas que o sistema respeita

| Regra | Fonte | Como o sistema aplica |
|---|---|---|
| Não altera teor das emendas | Decisão política/jurídica | IA só atualiza referências cruzadas, nunca o conteúdo |
| Pode corrigir erros de linguagem | Art. 250 §1º RI | Sistema aponta o erro com justificativa, não altera automaticamente |
| Contradição crítica | Art. 250 §2º RI | Sistema sinaliza para reabrir discussão, não resolve sozinho |
| Renumeração de artigos | Técnica legislativa | IA reconstrói numeração após supressões/adições |

---

## Estrutura dos arquivos

```
sistema_redacoes/
├── app.py              → Interface Streamlit (5 tabs + sidebar)
├── harmonizer.py       → Lógica de IA: parsing de emendas + harmonização
├── utils.py            → Leitura de arquivos, sessões, exportação
├── requirements.txt    → Dependências Python
├── auditoria.py        → Script de diagnóstico (este)
├── iniciar.bat         → Inicia Streamlit localmente
├── iniciar_completo.bat→ Inicia Streamlit + localtunnel (backup)
├── AUDITORIA.md        → Este arquivo
├── ACESSO_EQUIPE.md    → Guia para a equipe
├── README.md           → Documentação completa
└── .streamlit/
    ├── config.toml     → Tema e configurações
    └── secrets.toml.exemplo → Modelo para chave API local
```

---

## URLs

| Ambiente | URL | Quando usar |
|---|---|---|
| **Streamlit Cloud** *(recomendado)* | https://ccj-redacoes.streamlit.app | Sempre — não depende do PC |
| Localtunnel *(backup)* | https://ccj-redacoes.loca.lt | Se Cloud estiver fora |
| Local | http://localhost:8501 | Só no computador de casa |

---

## Possíveis erros e soluções

| Erro | Causa provável | Solução |
|---|---|---|
| "Informe a chave API" | secrets.toml não configurado localmente | Usar Streamlit Cloud ou criar secrets.toml |
| App em branco após gateway | localtunnel sem WebSocket | Recarregar a página |
| "This file does not exist" | Caminho errado no deploy | Verificar se é `app.py` na raiz |
| Timeout na harmonização | Projeto muito grande | Dividir em blocos menores ou aumentar timeout |
| Emendas não parseadas | Formato muito diferente do esperado | Usar entrada manual no Tab 2 |
