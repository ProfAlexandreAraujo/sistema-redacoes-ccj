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
- Conflitos entre emendas que afetam o mesmo dispositivo
- Referências cruzadas que ficam desatualizadas
- Emendas aditivas sem alvo definido ("acrescente-se onde couber") que exigem decisão de posicionamento

O sistema detecta e resolve esses problemas automaticamente.

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
| **4 · Harmonizar** | Clique em "Harmonizar". A IA aplica as emendas aprovadas, renumera e detecta problemas |
| **5 · Redação Final** | Revise o texto gerado, veja os avisos e exporte em .docx ou .txt |

---

## Regras seguidas (Regimento Interno — Resolução 1.673/2025)

### Art. 250, §1º — Correções permitidas
O sistema **aponta** erros de linguagem, ortografia e técnica legislativa, mas **não os corrige automaticamente**.  
Cabe ao relator decidir se aplica a correção e comunicar via ofício com ampla justificativa.

### Art. 250, §2º — Erros críticos
Se detectar incoerência, contradição evidente ou absurdo manifesto entre emendas aprovadas, o sistema classifica como **Erro Crítico** e recomenda a reabertura da discussão, conforme o RI.

### Teor das emendas
O sistema **jamais altera** o conteúdo substantivo de uma emenda aprovada.  
A única modificação automática permitida é a atualização de referências cruzadas internas (ex: renumeração de artigos).

### Emendas sem alvo definido ("acrescente-se onde couber")
Quando uma **emenda aditiva** não especifica o dispositivo de destino, o sistema posiciona automaticamente a unidade normativa (artigo, parágrafo, inciso, alínea ou item) no local mais coerente tematicamente, registra a decisão no log e gera um aviso com o tipo de unidade inserida e o local exato.

Quando uma **emenda modificativa ou substitutiva** chega sem alvo identificável, o sistema **não aplica** a modificação — gerar um aviso de revisão manual obrigatória e registra no log que a emenda não foi aplicada, evitando que o modelo invente qual dispositivo deveria ser alterado.

---

## Estrutura de arquivos

```
sistema_redacoes/
├── app.py              # Interface Streamlit
├── harmonizer.py       # Motor de harmonização (IA)
├── utils.py            # Leitura de docx, exportação, save/load
├── iniciar.bat         # Atalho para iniciar
├── requirements.txt    # Dependências Python
├── README.md           # Este arquivo
└── sessoes_salvas/     # Sessões salvas automaticamente (JSON)
```

---

## Dicas para a sessão de amanhã

1. **Antes da sessão**: carregue o projeto e todas as emendas. A IA irá pré-processar e identificar cada uma.
2. **Durante a votação**: use a aba **3 · Votação** — é a mais rápida. Apenas clique ✅ ou ❌ para cada emenda.
3. **Após cada bloco de votação**: salve a sessão (botão na barra lateral).
4. **Ao final**: vá para a aba 4, clique em Harmonizar e revise os resultados na aba 5.

---

## Suporte técnico

Em caso de erros, o log do terminal mostrará detalhes. Problemas comuns:
- `API key inválida` → Verifique a chave em https://console.anthropic.com
- `Erro de conexão` → Verifique a internet
- `Emenda sem texto` → Adicione o texto na aba 2
