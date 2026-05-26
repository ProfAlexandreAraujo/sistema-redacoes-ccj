# Prompt de Auditoria Externa — Sistema de Redações CCJ CMRJ
### Versão rev.14 — 26/05/2026

---

## Contexto

Você é um especialista em engenharia de software e em técnica legislativa brasileira.
Preciso que você audite um sistema de IA que foi desenvolvido para apoiar a elaboração
de Redações Finais na **Comissão de Constituição, Justiça e Redação (CCJ)** da
**Câmara Municipal do Rio de Janeiro**.

O sistema chama a API do Claude (Anthropic) para harmonizar projetos de lei com emendas
aprovadas em votação plenária, seguindo as normas da **LC 95/1998**, **Decreto 12.002/2024**,
**LC Municipal 48/2000** e o **Regimento Interno (Resolução 1.673/2025), art. 250**.

A interface é uma aplicação **Streamlit** com 5 abas:
1. Projeto original (upload/texto)
2. Emendas (parsing via IA ou manual)
3. Votação (painel rápido para uso em plenário)
4. Harmonização (chama a API; inclui painel de subemendas)
5. Redação Final (revisão, edição e exportação .docx / .txt)

---

## O que a IA faz durante a harmonização

O modelo recebe:
- O texto original do projeto de lei
- As emendas aprovadas (já pré-processadas — subemendas já resolvidas pela camada Python)

E deve produzir, em formato XML estruturado (**8 tags obrigatórias** — par completo exigido
por guarda Python; ValueError se truncado):

- `<TEXTO_HARMONIZADO>` — texto com todas as emendas aplicadas, renumeração atualizada
- `<MAPA_RENUMERACAO>` — mapa de dispositivos renumerados
- `<AVISOS>` — problemas formais/linguísticos (art. 250, §1º RI)
- `<ERROS_CRITICOS>` — contradições insanáveis (art. 250, §2º RI) — **dispara rascunho**
- `<ALERTAS_ABSURDOS>` — absurdos manifestos (art. 250, §2º RI) — **dispara rascunho**
- `<NOTAS_TECNICAS>` — informações de mérito para equipes técnicas (NÃO vão pro DOCX)
- `<SUGESTOES_NORMATIVAS>` — sugestões orientativas para conflitos E2 (NÃO vão pro DOCX)
- `<LOG_ALTERACOES>` — registro de cada operação realizada

**Fluxo §2º (rascunho de trabalho):** qualquer item em `erros_criticos` ou
`alertas_absurdos` faz o DOCX/TXT sair como **"RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL"**
por padrão. O relator confirma ciência via checkbox na aba 5 para exportar como Redação Final
(com "ALERTA CRÍTICO PENDENTE" no cabeçalho e entrada "OVERRIDE-HUMANO" no log).

---

## Pré-processamento Python (camada antes da IA)

### Subemendas — `_resolver_subemendas()` (harmonizer.py rev.14)

Antes de chamar a IA, o sistema processa subemendas (emendas que substituem o texto de
outra emenda antes de votá-la). A função retorna **4 valores**:

```python
def _resolver_subemendas(
    todas_emendas: list[Emenda],
    aprovadas: list[Emenda],
) -> tuple[list[Emenda], list[str], list[str], list[str]]:
    """
    Retorna (lista_processada, log_entries, avisos_simples, erros_criticos).
    erros_criticos (§2º) dispara o fluxo de rascunho de trabalho no app.
    """
```

**Regras processadas:**

| Caso | Entrada | Saída |
|---|---|---|
| Normal | SubEmenda aprovada + emenda-pai aprovada | `novo_texto` do pai substituído; subemenda retirada da lista enviada à IA |
| Inoperante | SubEmenda aprovada + emenda-pai NÃO aprovada | Aviso §1º registrado em `avisos_simples` |
| Rejeitada | SubEmenda rejeitada/prejudicada | Emenda-pai mantém texto; registro em `log_entries` |
| **Conflito** | **Duas subemendas aprovadas para o mesmo pai** | **`erros_criticos` (§2º)** → rascunho; nenhuma substituição automática; log registra |

**Bug corrigido em rev.14:** Antes desta versão, o caso de conflito de subemendas ia para
`avisos_simples` (§1º) em vez de `erros_criticos` (§2º), o que **não disparava** o fluxo
de rascunho de trabalho. Um conflito entre duas subemendas aprovadas é tão grave quanto um
conflito entre duas emendas aprovadas — ambos requerem a decisão do relator (art. 250, §2º RI).

**Injeção no resultado:**
```python
emendas_para_ia, log_subemendas, avisos_subemendas, erros_criticos_sub = _resolver_subemendas(...)

# ... chamada à IA ...

if log_subemendas:
    log_list = log_subemendas + log_list
if avisos_subemendas:
    avisos_list = avisos_subemendas + avisos_list
if erros_criticos_sub:
    # Conflito de subemendas → §2º → ativa fluxo de rascunho de trabalho
    erros_list = erros_criticos_sub + erros_list
```

---

## Implementações no prompt da IA (para auditoria)

### 1. Regra A4 — emendas sem alvo definido (harmonizer.py)

**Problema:** emendas que chegam sem alvo definido ("acrescente-se onde couber",
"inclua-se no local adequado" ou alvo simplesmente omisso) não tinham tratamento explícito.

**Solução — regra A4 com dois sub-casos:**

```
A4. EMENDAS SEM ALVO DEFINIDO — "acrescente-se onde couber"

    A4.1 — EMENDAS ADITIVAS SEM ALVO (texto novo autônomo)
    Quando uma emenda aditiva não especificar o dispositivo exato de destino:

    a) IDENTIFIQUE a unidade normativa que está sendo inserida:
       — Artigo novo → inserir após o artigo tematicamente mais próximo
       — Parágrafo novo → inserir no artigo correspondente, após o parágrafo mais
         relacionado ou ao final dos parágrafos do artigo
       — Inciso novo → inserir no rol correspondente, respeitando sequência lógica;
         renumerar os seguintes e ajustar pontuação (Bloco C)
       — Alínea nova → inserir dentro do inciso correspondente, respeitando enumeração;
         renumerar as seguintes e ajustar pontuação (Bloco C)
       — Item novo → inserir dentro da alínea correspondente, respeitando enumeração

    b) CRITÉRIOS DE POSICIONAMENTO (em ordem de prioridade):
       — Afinidade de matéria: insira próximo a dispositivos que tratam do mesmo tema
       — Sequência lógica: respeite a progressão normativa do capítulo ou seção
       — Nunca crie "ilhas" temáticas
       — Em caso de empate, prefira o final do capítulo temático correspondente

    c) OBRIGATÓRIO — LOG_ALTERACOES:
       "A4 / Emenda N: inserida como [tipo] em [local exato] — [motivo] (alvo não especificado)"

    d) OBRIGATÓRIO — AVISOS:
       "⚠ Emenda N / alvo não especificado: inserida como [tipo] em [local exato] ..."

    NUNCA insira silenciosamente sem AVISO e sem LOG.
    NUNCA recuse aplicar a emenda por ausência de alvo.

    A4.2 — EMENDAS MODIFICATIVAS OU SUBSTITUTIVAS SEM ALVO IDENTIFICÁVEL
    a) NÃO aplique a substituição — não invente qual dispositivo está sendo modificado.
    b) OBRIGATÓRIO — ERROS_CRITICOS (não em AVISOS):
       "🚨 Emenda N (modificativa/substitutiva): alvo não identificável — emenda NÃO aplicada.
        A Redação Final está materialmente incompleta. Revisão e decisão do relator obrigatórias
        antes da publicação (art. 250, §2º RI)."
    c) OBRIGATÓRIO — LOG_ALTERACOES:
       "A4.2 / Emenda N: NÃO aplicada — alvo não identificável"
```

**Decisão de projeto:**
- A4.1: posiciona (responsabilidade da CCJ) + rastro obrigatório (§1º)
- A4.2: não aplica + ERRO CRÍTICO (§2º) — a Redação Final fica materialmente incompleta

---

### 2. Tag NOTAS_TECNICAS — separação de mérito e forma

**Problema:** o modelo colocava análises de CA urbanístico e gabaritos em `AVISOS` (§1º) —
matéria de mérito, fora da competência da CCJ.

**Solução:**
- Nova tag `<NOTAS_TECNICAS>` no XML de saída
- Regra E1.5 no prompt proíbe expressamente mérito em AVISOS:

```
E1.5. PROIBIÇÃO ABSOLUTA — ANÁLISES DE MÉRITO NOS AVISOS:
    NUNCA inclua em AVISOS qualquer observação sobre:
    — Coeficiente de aproveitamento (CA): comparações, proporções, relações entre setores
    — Gabaritos, alturas, número de pavimentos: análises de adequação
    — Consistência dos parâmetros urbanísticos aprovados pelo Plenário
    Se perceber algo desse tipo, NÃO coloque em AVISOS.
    Registre em <NOTAS_TECNICAS> como nota informativa — sem julgamento.
```

- `NOTAS_TECNICAS` aparecem na interface como expander colapsável com disclaimer
- `NOTAS_TECNICAS` **não são passadas** para `exportar_redacao_final_docx()`

---

### 3. Correção de bug — skip set incompleto (harmonizer.py)

`"Nenhuma nota técnica."` e `"Nenhuma sugestão."` não estavam no conjunto `skip` de
`parse_linhas()`, fazendo os expanders aparecerem com "1 item" cujo conteúdo era a própria frase.

```python
# Skip set completo:
skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.",
        "Sem renumeração necessária.", "Nenhuma nota técnica.", "Nenhuma sugestão."}
```

---

### 4. Regra E2 — conflitos entre emendas aprovadas + sugestão normativa (harmonizer.py)

**Problema:** a regra E2 anterior listava situações de conflito sem instruir o modelo
a realizar varredura prévia nem oferecer sugestão de harmonização.

**Solução — E2 reformulada em três passos:**

```
E2. CONFLITOS ENTRE EMENDAS APROVADAS — DETECÇÃO OBRIGATÓRIA E SUGESTÃO NORMATIVA

    ⚡ ANTES DE APLICAR QUALQUER EMENDA — VARREDURA PRÉVIA OBRIGATÓRIA:
    (a) Duas ou mais emendas afetam o MESMO dispositivo
    (b) Uma emenda supressiva e uma modificativa sobre o MESMO dispositivo
    (c) Duas emendas com valores, prazos ou condições incompatíveis para a MESMA obrigação
    (d) Uma emenda que torna outro dispositivo aprovado de cumprimento impossível

    PASSO 1 — No TEXTO_HARMONIZADO: aplica emenda de MENOR NÚMERO (cautela formal)
    e insere: [[⚠️ CCJ: CONFLITO DE EMENDAS — decisão do relator obrigatória]]

    PASSO 2 — Em ERROS_CRITICOS:
    "🚨 CONFLITO / Emendas [N] e [M] — [dispositivo]:
    • Emenda N ([tipo]): [ação]
    • Emenda M ([tipo]): [ação]
    Conflito: [descrição precisa]
    No texto: mantida Emenda [N] (menor número) como cautela.
    A providência regimental indicada é a reabertura da discussão (art. 250, §2º RI)."

    PASSO 3 — Em SUGESTOES_NORMATIVAS:
    "💡 Sugestão / Emendas [N] e [M] — [dispositivo]:
    [Proposta de reconciliação ou alternativas A/B se irreconciliáveis]
    ⚠ Sugestão estritamente orientativa — decisão final exclusiva do relator."
```

**Nova tag XML:** `<SUGESTOES_NORMATIVAS>` — 8ª tag obrigatória na resposta.
- Aparece na interface como expander amarelo expandido (visível imediatamente)
- **NÃO exportada** para o DOCX/TXT
- Marcador `[[⚠️ CCJ: CONFLITO DE EMENDAS...]]` removido automaticamente dos dois produtos exportados

**Fluxo completo:** E2 → `ERROS_CRITICOS` → §2º → DOCX como rascunho por padrão

---

### 5. Subemendas — campo `subemenda_de` + `_resolver_subemendas()` (harmonizer.py rev.13/14 + app.py)

**Problema:** O sistema não suportava subemendas — o texto de emendas que haviam sido
alteradas por subemendas aprovadas era aplicado na versão original, ignorando a decisão do Plenário.

**Implementação:**

- Campo `subemenda_de: Optional[int]` adicionado ao dataclass `Emenda`.
- Função `_resolver_subemendas()` executa **antes** da chamada à IA (detalhada acima).
- `parsear_emendas_com_ia` atualizado: reconhece texto como subemenda e extrai `subemenda_de`.
- Interface (app.py):
  - **Aba 2:** badge `↳ SubEm.E{N}` no cabeçalho do card; campo `subemenda_de` editável.
  - **Aba 3:** indicador `↳E{N}` na linha de votação.
  - **Aba 4:** painel expandido com status de cada subemenda antes de harmonizar.
  - **Formulário manual:** campo para informar `subemenda_de`.

**Bug crítico corrigido em rev.14 (durante autoauditoria):**
O conflito de subemendas era roteado para `avisos` (§1º) em vez de `erros_criticos` (§2º),
o que impedia o acionamento do fluxo de rascunho de trabalho. Corrigido: retorno passou de
3 para 4 valores; conflito vai exclusivamente para `erros_criticos_sub`.

---

### 6. verificar.py — estado atual (rev.11)

- **Seção 11:** valida 8 tags XML (inclui `NOTAS_TECNICAS` e `SUGESTOES_NORMATIVAS`)
- **Seção 13:** 11 testes estruturais (sem API) para A4.1 e A4.2
- **Seção 14:** 12 testes estruturais (sem API) para E2 + SUGESTOES_NORMATIVAS
- **Seção 15:** 14 testes estruturais (sem API) para subemendas, incluindo:
  - Caso normal: substituição, remoção da lista, log
  - Caso inoperante: aviso §1º, não vai à IA
  - Caso rejeitada: texto pai preservado
  - **Conflito → `erros_criticos` §2º gerado** (not `avisos` §1º) — 2 testes opostos
  - parsear reconhece `subemenda_de`; app.py exibe painel
- **Resultado: 106/107** (1 falha esperada: chave API não configurada localmente)

---

## Arquitetura de proteções (estado atual — rev.14)

| Proteção | Onde | O que faz |
|---|---|---|
| Preservação verbatim (A1) | Prompt | Emenda aprovada nunca é alterada em conteúdo |
| Referências cruzadas (A2) | Prompt | Única alteração automática de conteúdo permitida |
| Preservação de anexos (A3) | Prompt | Conteúdo de anexos nunca alterado sem emenda expressa |
| A4.1 — aditiva sem alvo | Prompt | Posicionamento temático com AVISO + LOG obrigatórios |
| A4.2 — modificativa sem alvo | Prompt | Não aplica; gera ERRO CRÍTICO (§2º) + LOG de emenda não aplicada |
| Renumeração (B1–B5) | Prompt | LC 95/98 + LC 48/2000 |
| E1 — correções linguísticas | Prompt | Concordância, caixa, pontuação — registradas no LOG |
| E1.5 — sem mérito em AVISOS | Prompt | Mérito vai para NOTAS_TECNICAS |
| E2 — conflito entre emendas | Prompt | Varredura prévia; cautela por menor número; ERROS_CRITICOS + SUGESTOES_NORMATIVAS |
| Subemendas — caso normal | Python (pré-IA) | Substitui texto da emenda-pai; subemenda retirada da lista |
| Subemendas — conflito | Python (pré-IA) | **ERROS_CRITICOS §2º** → rascunho; nenhuma substituição automática |
| Subemendas — inoperante | Python (pré-IA) | Aviso §1º; subemenda não vai à IA |
| Detecção estrutural absurdos | Python | Circular, inoperante — independe do modelo |
| Escalada de §1º para §2º | Python | Padrões semânticos nos avisos |
| Validação XML | Python | Par completo de 8 tags ou ValueError |
| Rascunho de trabalho | Python + App | §2º → DOCX sai como rascunho até relator confirmar |
| `_invalidar_resultado()` | App | Qualquer mudança limpa resultado anterior |
| Skip set completo | Python | Strings "Nenhum/a..." filtradas corretamente |
| Limpeza de marcadores inline | Python + App | `[[⚠️ CCJ:...]]` removido de DOCX e TXT antes da exportação |

---

## Perguntas para sua auditoria

1. **O bug de subemendas corrigido em rev.14 é suficientemente coberto?**
   - O retorno de 4 valores em `_resolver_subemendas()` é a abordagem correta?
   - Há outros edge cases de subemendas não cobertos? (ex: subemenda de subemenda? auto-referência?)
   - A lógica de "menor número como cautela" do E2 deveria se aplicar também ao conflito
     de subemendas (ou mantém a abordagem atual de não aplicar nenhuma)?

2. **A regra E2 reformulada é suficientemente robusta?**
   - A política de "aplicar emenda de menor número como cautela" é a abordagem correta?
   - Há risco de o modelo não realizar a varredura prévia e detectar o conflito apenas
     depois de aplicar as emendas?
   - As sugestões normativas podem criar viés para que o relator as adote sem análise crítica?

3. **A regra A4 está bem formulada?**
   - A distinção A4.1 (aditiva: posiciona) vs A4.2 (modificativa: não aplica) é a abordagem correta?
   - Os critérios de posicionamento para unidades menores (parágrafo, inciso, alínea, item)
     são suficientes?

4. **A separação AVISOS / NOTAS_TECNICAS / SUGESTOES_NORMATIVAS é robusta?**
   - A regra E1.5 é suficiente para o modelo não "vazar" mérito nos AVISOS?
   - Há risco de sugestões normativas aparecerem em ERROS_CRITICOS em vez de SUGESTOES_NORMATIVAS?

5. **Há algo que deveria ter sido implementado e não foi?**
   - Considerando o fluxo completo (upload → parsing → subemendas → votação → harmonização
     → exportação), há algum ponto cego evidente?

6. **O prompt tem riscos de regressão com E2 + A4 + E1.5 + subemendas?**
   - Há conflito potencial com A1 (preservação verbatim) ou com as regras do Bloco B
     (renumeração)?

7. **Sugestões livres** — o que você mudaria ou acrescentaria?

---

## Nota sobre o contexto de uso

- O relator é também o assessor que opera o sistema — não há separação de papéis.
- Projetos típicos: PLCs de zoneamento urbano (30–50 artigos, 10–180 emendas).
- O modelo usado é `claude-sonnet-4-6` com `max_tokens=60000`.
- A chave API fica nos Secrets do Streamlit Cloud — não há chave local em produção.
- O app está em: https://ccj-redacoes.streamlit.app
- O código-fonte está em: https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj
