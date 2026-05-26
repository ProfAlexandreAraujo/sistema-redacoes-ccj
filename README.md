# Sistema de Redações — CCJ CMRJ

**Comissão de Constituição, Justiça e Redação**  
Câmara Municipal do Rio de Janeiro

---

## O que este sistema faz

Auxilia o assessor jurídico da CCJ a elaborar a **Redação Final** (art. 250 RI) e a **Redação do Vencido** de projetos aprovados com emendas, com foco especial em projetos complexos com grande número de emendas.

### Problema resolvido

Quando dezenas ou centenas de emendas são aprovadas em votação plenária, surgem problemas como:
- Emendas supressivas que alteram a numeração dos artigos seguintes
- Outras emendas que ainda referenciam os números antigos
- **Conflitos entre emendas que afetam o mesmo dispositivo** (o risco mais grave)
- Emendas aditivas sem alvo definido ("acrescente-se onde couber") que exigem decisão de posicionamento
- Emendas modificativas sem alvo identificável que não podem ser aplicadas sem decisão do relator
- Referências cruzadas que ficam desatualizadas

O sistema detecta e resolve esses problemas automaticamente, com alerta claro quando a decisão deve ser do relator.

---

## Como usar

### 1. Iniciar o sistema

Dê duplo clique em `iniciar.bat`  
**ou** execute no terminal:
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes
python -m streamlit run app.py
```

Acesse em: **http://localhost:8501**

### 2. Configurar a chave API

Na barra lateral, insira sua chave da API Anthropic.  
Ela pode ser obtida em: https://console.anthropic.com

### 3. Fluxo de trabalho

| Aba | Função |
|-----|--------|
| **1 · Projeto** | Cole ou faça upload do texto do projeto original |
| **2 · Emendas** | Cole/faça upload de todas as emendas. A IA identifica automaticamente tipo, alvo e texto de cada uma |
| **3 · Votação** | Durante a sessão plenária, marque cada emenda como Aprovada / Rejeitada / Prejudicada |
| **4 · Harmonizar** | Clique em "Harmonizar". A IA aplica as emendas aprovadas, renumera, detecta conflitos e problemas |
| **5 · Redação Final** | Revise o texto gerado, veja os avisos e exporte em .docx ou .txt |

---

## Regras seguidas (Regimento Interno — Resolução 1.673/2025)

### Art. 250, §1º — Correções permitidas
O sistema **corrige automaticamente** erros de linguagem, ortografia e pontuação que não alterem o significado jurídico, registrando cada correção no LOG e em AVISOS.  
Cabe ao relator decidir se mantém as correções e comunicar via ofício com ampla justificativa.

### Art. 250, §2º — Erros críticos e absurdos manifestos
Se detectar incoerência, contradição evidente ou absurdo manifesto entre emendas aprovadas, o sistema classifica como **Erro Crítico** e recomenda a reabertura da discussão, conforme o RI.  
O documento é exportado como **Rascunho de Trabalho** por padrão até o relator confirmar ciência explicitamente.

### Teor das emendas
O sistema **jamais altera** o conteúdo substantivo de uma emenda aprovada.  
A única modificação automática permitida é a atualização de referências cruzadas internas (ex: renumeração de artigos).

### Emendas conflitantes (duas emendas aprovadas sobre o mesmo dispositivo)
Quando duas emendas aprovadas afetam o mesmo dispositivo, o sistema:
1. **Detecta** o conflito em varredura prévia antes de aplicar qualquer emenda
2. **Aplica** a emenda de menor número como cautela formal (votada primeiro)
3. **Marca** o dispositivo com aviso inline no texto
4. **Registra** como Erro Crítico (§2º) — dispara o fluxo de rascunho de trabalho
5. **Sugere** uma proposta de harmonização orientativa — mas a decisão é exclusiva do relator

### Emendas sem alvo definido ("acrescente-se onde couber")
Quando uma **emenda aditiva** não especifica o dispositivo de destino, o sistema posiciona automaticamente a unidade normativa (artigo, parágrafo, inciso, alínea ou item) no local mais coerente tematicamente, registra a decisão no log e gera um aviso com o tipo de unidade inserida e o local exato.

Quando uma **emenda modificativa ou substitutiva** chega sem alvo identificável, o sistema **não aplica** a modificação e classifica como **Erro Crítico (§2º RI)** — o documento é exportado como Rascunho de Trabalho por padrão, exigindo confirmação explícita antes de virar Redação Final. Isso evita que o modelo invente qual dispositivo deveria ser alterado e garante que uma emenda aprovada não seja silenciosamente ignorada.

---

## Arquitetura de proteções

| Proteção | Onde | O que faz |
|---|---|---|
| Preservação verbatim (A1) | Prompt | Emenda aprovada nunca é alterada em conteúdo |
| Referências cruzadas (A2) | Prompt | Única alteração automática de conteúdo permitida |
| Preservação de anexos (A3) | Prompt | Conteúdo de anexos nunca alterado sem emenda expressa |
| A4.1 — aditiva sem alvo | Prompt | Posicionamento temático com AVISO + LOG obrigatórios |
| A4.2 — modificativa sem alvo | Prompt | Não aplica; gera ERRO CRÍTICO (§2º) + LOG |
| Renumeração (B1–B5) | Prompt | LC 95/98 + LC 48/2000 |
| E1 — correções linguísticas | Prompt | Concordância, caixa, pontuação — registradas no LOG |
| E1.5 — sem mérito em AVISOS | Prompt | Mérito vai para NOTAS_TECNICAS |
| E2 — conflito entre emendas | Prompt | Varredura prévia; cautela por menor número; ERROS_CRITICOS + SUGESTOES_NORMATIVAS |
| Detecção estrutural absurdos | Python | Circular, inoperante — independe do modelo |
| Escalada de §1º para §2º | Python | Padrões semânticos nos avisos |
| Validação XML | Python | Par completo de 8 tags ou ValueError |
| Rascunho de trabalho | Python + App | §2º → DOCX sai como rascunho até relator confirmar |
| `_invalidar_resultado()` | App | Qualquer mudança limpa resultado anterior |
| Skip set completo | Python | Strings "Nenhum/a..." filtradas corretamente |

---

## Estrutura de arquivos

```
sistema_redacoes/
├── app.py                        # Interface Streamlit
├── harmonizer.py                 # Motor de harmonização (IA) + regras A1–A4, B, C, D, E
├── utils.py                      # Leitura de docx/txt/pdf, exportação, save/load
├── auditoria.py                  # Diagnóstico rápido do ambiente (dependências, API, módulos)
├── verificar.py                  # Suite de testes estruturais (91/92 sem API)
├── teste_real.py                 # Teste com PLC 92/2025 real (sem custo de API)
├── PROMPT_AUDITORIA_EXTERNA.md   # Prompt para auditoria por LLM externa
├── iniciar.bat                   # Atalho para iniciar localmente
├── requirements.txt              # Dependências Python
├── README.md                     # Este arquivo
└── sessoes_salvas/               # Sessões salvas automaticamente (JSON)
```

---

## Dicas para a sessão plenária

1. **Antes da sessão**: carregue o projeto e todas as emendas. A IA irá pré-processar e identificar cada uma.
2. **Durante a votação**: use a aba **3 · Votação** — é a mais rápida. Apenas clique ✅ ou ❌ para cada emenda.
3. **Após cada bloco de votação**: salve a sessão (botão na barra lateral).
4. **Ao final**: vá para a aba 4, clique em Harmonizar e revise os resultados na aba 5.
5. **Se houver conflito de emendas**: o sistema vai exibir um alerta 🚨 e uma sugestão orientativa 💡 — mas a decisão de qual prevalece é do relator.

---

## Suporte técnico

Em caso de erros, o log do terminal mostrará detalhes. Problemas comuns:
- `API key inválida` → Verifique a chave em https://console.anthropic.com
- `Erro de conexão` → Verifique a internet
- `Emenda sem texto` → Adicione o texto na aba 2
- `Resposta truncada` → Reduza o número de emendas por lote ou tente novamente
