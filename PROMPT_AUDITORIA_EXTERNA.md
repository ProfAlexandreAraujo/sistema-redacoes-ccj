# Prompt de Auditoria Externa — Sistema de Redações CCJ CMRJ

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
4. Harmonização (chama a API)
5. Redação Final (revisão, edição e exportação .docx / .txt)

---

## O que a IA faz durante a harmonização

O modelo recebe:
- O texto original do projeto de lei
- As emendas aprovadas

E deve produzir, em formato XML estruturado:
- `<TEXTO_HARMONIZADO>` — texto com todas as emendas aplicadas, renumeração atualizada
- `<MAPA_RENUMERACAO>` — mapa de dispositivos renumerados
- `<AVISOS>` — problemas formais/linguísticos (art. 250, §1º RI)
- `<ERROS_CRITICOS>` — contradições insanáveis (art. 250, §2º RI)
- `<ALERTAS_ABSURDOS>` — absurdos manifestos (art. 250, §2º RI)
- `<NOTAS_TECNICAS>` — informações de mérito para equipes técnicas (NÃO vão pro DOCX)
- `<LOG_ALTERACOES>` — registro de cada operação realizada

---

## Implementações recentes (para auditoria)

### 1. Regra A4 — emendas sem alvo definido (harmonizer.py)

**Problema identificado:** emendas que chegam sem alvo definido — expressões como
"acrescente-se onde couber", "inclua-se no local adequado" ou simplesmente sem indicação
do dispositivo de destino — não tinham tratamento explícito. O modelo poderia inserir
silenciosamente sem registrar ou, pior, recusar aplicar.

**Solução implementada:** regra A4 com dois sub-casos:

```
A4. EMENDAS SEM ALVO DEFINIDO — "acrescente-se onde couber"

    A4.1 — EMENDAS ADITIVAS SEM ALVO (texto novo autônomo)
    Quando uma emenda aditiva não especificar o dispositivo exato de destino
    (ex: "acrescente-se onde couber", "inclua-se no local adequado", "onde cabível",
    ou quando o alvo estiver simplesmente omisso):

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
       — Nunca crie "ilhas" temáticas: não insira dispositivo sobre tema X no meio de tema Y
       — Em caso de empate, prefira o final do capítulo temático correspondente

    c) OBRIGATÓRIO — registrar no LOG_ALTERACOES:
       "A4 / Emenda N: inserida como [artigo/parágrafo/inciso/alínea/item] em [local exato] — [motivo breve] (alvo não especificado na emenda)"

    d) OBRIGATÓRIO — gerar aviso em AVISOS:
       "⚠ Emenda N / alvo não especificado: inserida como [tipo] em [local exato] por coerência temática com [tema]. Posicionamento definido pela CCJ — alvo não especificado na emenda original."

    NUNCA insira silenciosamente sem AVISO e sem LOG.
    NUNCA recuse aplicar a emenda por ausência de alvo — posicionar é responsabilidade da CCJ.

    A4.2 — EMENDAS MODIFICATIVAS OU SUBSTITUTIVAS SEM ALVO IDENTIFICÁVEL
    Quando uma emenda modificativa ou substitutiva não especificar o dispositivo de destino
    e o alvo não puder ser inferido com segurança a partir do texto da emenda:

    a) NÃO aplique a substituição — não invente qual dispositivo está sendo modificado.
    b) OBRIGATÓRIO — registrar em ERROS_CRITICOS (não em AVISOS):
       "🚨 Emenda N (modificativa/substitutiva): alvo não identificável — emenda NÃO aplicada.
        A Redação Final está materialmente incompleta. Revisão e decisão do relator obrigatórias
        antes da publicação (art. 250, §2º RI)."
    c) OBRIGATÓRIO — registrar no LOG_ALTERACOES:
       "A4.2 / Emenda N: NÃO aplicada — alvo não identificável (modificativa/substitutiva sem alvo definido)"
```

**Decisão de projeto:** A4.1 e A4.2 tratam casos fundamentalmente diferentes.
- Aditivas sem alvo: o sistema posiciona — responsabilidade da CCJ, rastro obrigatório.
- Modificativas/substitutivas sem alvo: não aplica e lança **ERROS_CRITICOS** — a Redação
  Final fica materialmente incompleta, o que dispara o fluxo §2º (rascunho por padrão,
  confirmação explícita do relator para exportar como Redação Final).

---

### 2. Tag NOTAS_TECNICAS — separação de mérito e forma (harmonizer.py + app.py)

**Problema identificado:** o modelo colocava em `AVISOS` observações sobre coeficiente
de aproveitamento (CA), gabaritos e parâmetros urbanísticos — matéria de **mérito**,
fora da competência da CCJ na Redação Final.

**Solução implementada:**
- Nova tag `<NOTAS_TECNICAS>` no formato XML de saída
- Regra E1.5 no prompt proíbe expressamente mérito em AVISOS:

```
E1.5. PROIBIÇÃO ABSOLUTA — ANÁLISES DE MÉRITO NOS AVISOS:
    NUNCA inclua em AVISOS qualquer observação sobre:
    — Coeficiente de aproveitamento (CA): comparações, proporções, relações entre setores
    — Gabaritos, alturas, número de pavimentos: análises de adequação
    — Consistência dos parâmetros urbanísticos aprovados pelo Plenário
    — Qualquer julgamento sobre se os valores fazem sentido técnico ou urbanístico
    Se perceber algo desse tipo, NÃO coloque em AVISOS.
    Registre em <NOTAS_TECNICAS> como nota informativa para equipes técnicas — sem julgamento.
```

- `NOTAS_TECNICAS` aparecem na interface como expander colapsável com disclaimer
- `NOTAS_TECNICAS` **não são passadas** para `exportar_redacao_final_docx()`

---

### 3. Correção de bug — skip set incompleto (harmonizer.py)

`"Nenhuma nota técnica."` não estava no conjunto `skip` de `parse_linhas()`,
fazendo o expander aparecer com "1 nota técnica" cujo conteúdo era a própria frase.

```python
# Corrigido:
skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.",
        "Sem renumeração necessária.", "Nenhuma nota técnica."}
```

---

### 4. Regra E2 — conflitos entre emendas aprovadas + sugestão normativa (harmonizer.py)

**Problema identificado:** o sistema já tinha uma regra E2, mas ela se limitava a listar situações
de conflito sem dar instruções claras sobre como o modelo deve agir e sem oferecer sugestão
de harmonização — deixando o relator sem apoio para resolver o conflito.

**Solução implementada:** E2 reformulada em quatro passos obrigatórios:

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
- Aparece na interface como expander amarelo expandido (visível imediatamente).
- NÃO exportada para o DOCX.
- Marcador `[[⚠️ CCJ: CONFLITO DE EMENDAS...]]` removido automaticamente pelo regex existente.

**Decisão de projeto:**
- `sugestoes_normativas` é campo novo no dataclass `ResultadoHarmonizacao`.
- O sistema NÃO toma a decisão — posiciona a emenda de menor número como cautela neutra
  e fornece ao relator as informações e uma sugestão orientativa para decidir.
- O conflito dispara o fluxo §2º (rascunho de trabalho por padrão via `erros_criticos`).

---

### 5. verificar.py — estado atual (rev.9)

- **Seção 11:** valida 8 tags XML (inclui `NOTAS_TECNICAS` e `SUGESTOES_NORMATIVAS`)
- **Seção 13:** 11 testes estruturais (sem API) para A4.1 e A4.2
- **Seção 14:** 12 testes estruturais (sem API) para E2 + SUGESTOES_NORMATIVAS
- **Resultado: 91/92** (1 falha esperada: chave API não configurada localmente)

---

## Arquitetura de proteções (estado atual)

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
| Detecção estrutural absurdos | Python | Circular, inoperante — independe do modelo |
| Escalada de §1º para §2º | Python | Padrões semânticos nos avisos |
| Validação XML | Python | Par completo de 8 tags ou ValueError |
| Rascunho de trabalho | Python + App | §2º → DOCX sai como rascunho até relator confirmar |
| `_invalidar_resultado()` | App | Qualquer mudança limpa resultado anterior |
| Skip set completo | Python | Strings "Nenhum/a..." filtradas corretamente |

---

## Perguntas para sua auditoria

1. **A regra E2 reformulada é suficientemente robusta?**
   - A política de "aplicar emenda de menor número como cautela" é a abordagem correta?
   - Há risco de o modelo não realizar a varredura prévia e detectar o conflito apenas depois de aplicar as emendas?
   - As sugestões normativas podem criar viés para que o relator as adote sem análise crítica?

2. **A regra A4 refinada está bem formulada?**
   - A distinção A4.1 (aditiva: posiciona) vs A4.2 (modificativa: não aplica) é a abordagem correta?
   - Os critérios de posicionamento para unidades menores (parágrafo, inciso, alínea, item) são suficientes?
   - O LOG/AVISO com tipo de unidade e local exato é informativo o suficiente?

3. **A separação AVISOS / NOTAS_TECNICAS / SUGESTOES_NORMATIVAS é robusta?**
   - A regra E1.5 é suficiente para o modelo não "vazar" mérito nos AVISOS?
   - Há risco de sugestões normativas aparecerem em ERROS_CRITICOS em vez de SUGESTOES_NORMATIVAS?

4. **Há algo que deveria ter sido implementado e não foi?**
   - Considerando o fluxo completo (upload → parsing → votação → harmonização → exportação),
     há algum ponto cego evidente?

5. **O prompt tem riscos de regressão com E2 + A4 + E1.5?**
   - Há conflito potencial com A1 (preservação verbatim) ou com as regras do Bloco B (renumeração)?

6. **Sugestões livres** — o que você mudaria ou acrescentaria?

---

## Nota sobre o contexto de uso

- O relator é também o assessor que opera o sistema — não há separação de papéis.
- Projetos típicos: PLCs de zoneamento urbano (30–50 artigos, 10–180 emendas).
- O modelo usado é `claude-sonnet-4-6` com `max_tokens=60000`.
- A chave API fica nos Secrets do Streamlit Cloud — não há chave local em produção.
- O app está em: https://ccj-redacoes.streamlit.app
