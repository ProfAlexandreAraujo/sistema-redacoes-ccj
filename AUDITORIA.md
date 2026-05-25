# 🔍 AUDITORIA DO SISTEMA — CCJ CMRJ
### Documento técnico para revisão externa — versão 2026-05-25 rev.2

---

## 1. Contexto e propósito

Este sistema auxilia a **Comissão de Constituição, Justiça e Redação (CCJ)** da Câmara Municipal do Rio de Janeiro a elaborar a **Redação Final** ou **Redação do Vencido** de projetos de lei aprovados com emendas (art. 250, Resolução nº 1.673/2025 — Regimento Interno).

**Constraint absoluta e inviolável:**
> *"Eu não posso mexer no teor da emenda. Não posso fazer isso."*
O texto aprovado pelo Plenário é soberano. O sistema **nunca** altera conteúdo substantivo. A única modificação automática permitida é a atualização de referências cruzadas internas decorrente de renumeração.

---

## 2. Normas legislativas que o sistema deve respeitar

| Norma | O que rege |
|---|---|
| **LC 95/1998 (federal)** | Técnica de elaboração de normas: estrutura, artigos, renumeração |
| **Decreto 12.002/2024** | Regulamenta LC 95/1998 com regras detalhadas de redação |
| **LC Municipal 48/2000 RJ** | Técnica legislativa específica da CMRJ (pontuação, incisos, alíneas) |
| **LC Municipal 51/2001 RJ** | Complementa LC 48/2000 |
| **Res. 1.673/2025 (RI), art. 250** | Competência da CCJ, níveis de intervenção, quando reabrir discussão |

---

## 3. Três níveis de alerta — fundamentos regimentais corretos

### ⚠️ Aviso Redacional — art. 250, §1º RI
Incorreção ou impropriedade de linguagem que **não deturpa a vontade legislativa**.
→ O sistema aponta o problema. O texto é preservado exatamente como aprovado.
→ A CCJ pode corrigir por ofício com ampla justificativa.
→ **O sistema nunca corrige automaticamente — apenas aponta.**

### 🚨 Erro Crítico — art. 250, §2º RI (CCJ NÃO oferece Redação Final)
Duas emendas aprovadas que se **contradizem diretamente** sobre o mesmo dispositivo, ou uma torna a outra de cumprimento impossível.
→ A CCJ **não deve oferecer Redação Final**; deve propor reabertura da discussão.
→ Exportação do DOCX recebe título "RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL".

### 🔴 Absurdo Manifesto — art. 250, §2º RI (CCJ NÃO oferece Redação Final)
Texto tecnicamente ininteligível ou que cria **dúvida inequívoca sobre a vontade legislativa** por razão exclusivamente formal (não por conflito entre emendas).
Exemplos: dispositivo que remete a artigo integralmente suprimido; "artigo anterior" que passou a apontar para dispositivo incompatível; condição normativa que referencia parágrafo inexistente.
→ O texto é preservado **verbatim** + marcador inline visível na tela de trabalho.
→ O marcador é **removido** do DOCX exportado (não integra a lei).
→ A CCJ **não deve oferecer Redação Final**; deve propor reabertura (art. 250, §2º RI).

> **REGRA CRÍTICA:** Tanto 🚨 Erro Crítico quanto 🔴 Absurdo Manifesto invocam o **§2º** — CCJ propõe reabertura, não ofício. O §1º cobre apenas impropriedades de linguagem (⚠️ Aviso).

---

## 4. Regras do prompt de IA (estado atual — rev.3) + pós-processamento Python

### A1 — Preservação verbatim (REGRA ABSOLUTA)
Ao incorporar o texto de emenda aprovada, copiar LITERALMENTE — cada palavra, cada cláusula, cada vírgula. Mesmo que o texto aprovado contenha referência a dispositivo suprimido, crie absurdo manifesto ou contenha cláusula problemática, **nunca** remover, parafrasear ou simplificar. Copiar o absurdo e registrar em ALERTAS_ABSURDOS.

### A2 — Referências cruzadas (única alteração automática permitida)
Após renumerar artigos, atualizar todas as referências internas. Esta é a única intervenção automática de conteúdo admitida.

### A3 — Anexos
Preservação integral obrigatória. Nunca renumerar nem alterar sem emenda expressa.

### A2 — Referências cruzadas (única alteração automática de conteúdo)
Atualiza numeração de artigos/parágrafos/incisos após renumeração. **Regra especial de aglutinação**: quando emenda aglutina arts. X e Y em X (suprimindo Y), qualquer referência ao conteúdo de Y deve apontar para X final — não para o artigo que herda o número de Y por renumeração sequencial.

### E1 — Correções automáticas de linguagem (rev.3)
O sistema corrige automaticamente erros de ortografia, concordância e pontuação que **não alterem o significado jurídico**, registrando cada correção em LOG e AVISOS. A preocupação central é o teor (o que a lei manda, proíbe, permite) — não erros de português. Números, valores, prazos, verbos obrigacionais: jamais alterados.

### E2 — Erros Críticos (§2º RI)
Contradição entre emendas aprovadas → sinaliza para reabertura. Nunca resolve.

### E3 — Absurdo Manifesto (§2º RI)
Ininteligibilidade formal de um dispositivo → sinaliza para reabertura. Nunca resolve.

### P1 — Pós-processamento Python (camada de segurança independente do modelo)
Após o modelo responder, `harmonizer.py` executa dois detectores estruturais sobre o **texto harmonizado** para escalar absurdos que o modelo teimou em classificar como §1º:

- **Caso 1 — Autoreferência circular**: Art. N cujo corpo referencia `no Art. N` (mesmo número). Detectado por regex sobre os blocos de artigo.
- **Caso 2 — Condição normativa inoperante**: §N cujo corpo contém `§N deste artigo` (parágrafo que remete a si mesmo). Detectado por regex sobre parágrafos numerados.
- **Caso 3 — Semântica de avisos**: varredura nos textos dos avisos por palavras-chave que indicam absurdo não detectado estruturalmente (ex: "artigo anterior.*incompatível", "condição.*suprimida", "§.*foi suprimido").

Qualquer item escalado é movido de `avisos` para `alertas_absurdos`, o que força o DOCX a ser gerado como "RASCUNHO DE TRABALHO".

---

## 5. Histórico de correções aplicadas

| Data | Bug | Tipo | Status |
|---|---|---|---|
| 25/05/2026 | AI removia cláusula aprovada para "resolver" absurdo | Crítico | ✅ Corrigido (A1 verbatim) |
| 25/05/2026 | Correções sem log explícito | Médio | ✅ Corrigido (E1 flag-only) |
| 25/05/2026 | Absurdo manifesto classificado como §1º em vez de §2º (prompt) | Crítico | ✅ Corrigido (E3 rev.2) |
| 25/05/2026 | DOCX exportado como "Redação Final" mesmo com §2º | Regimental | ✅ Corrigido (utils.py) |
| 25/05/2026 | Marcadores inline presentes no DOCX exportado | Médio | ✅ Corrigido (utils.py) |
| 25/05/2026 | Correções automáticas de gramática/pontuação | Regimental | ✅ Corrigido (E1 flag-only) |
| 25/05/2026 | IA persiste em classificar absurdos como §1º mesmo com E3 rev.2 | Crítico | ✅ Corrigido (harmonizer.py — pós-processamento Python) |
| 25/05/2026 | E1 "flag-only" revertido para "auto-corrigir + log" (decisão do usuário) | Funcional | ✅ Aplicado (E1 rev.3) |
| 25/05/2026 | A2 não atualizava referências ao conteúdo migrado por aglutinação | Funcional | ✅ Corrigido (A2 aglutinação — harmonizer.py) |

---

## 6. Cenário de stress test — PLC fictício nº 17/2026

Use o **texto original** (`TAB_1_PLC_17_2026_TEXTO_ORIGINAL.txt`, 19 artigos + 4 Anexos) com as **10 emendas** (`TAB_2_PLC_17_2026_EMENDAS.txt`). Todas devem ser marcadas como **APROVADAS**.

### Estrutura esperada ao final
- **18 artigos** (art. 4º original suprimido; novo art. de monitoramento inserido; arts. 11 e 12 aglutinados)
- **5 Anexos** (Anexo V adicionado pela Emenda 7)

### Emenda por emenda — resultado esperado

| Emenda | Operação | Resultado esperado |
|---|---|---|
| 1 — Supressiva Art. 4º | Suprimir art. 4º; renumerar subsequentes | Art. 4º suprimido; art. 5º → art. 4º; ⚠ circularidade em "definida no Art. 4º" → 🔴 Absurdo (§2º) |
| 2 — Modificativa §2º Art. 7º | Alterar coeficiente de 4 para 6; atualizar "Art. 6º" → "Art. 5º" | Texto incorporado verbatim; remissão atualizada |
| 3 — Aditiva novo art. após Art. 10 | Inserir art. de monitoramento; renumerar | Novo art. 10; remissões arts. 9º e 10 atualizadas para arts. 8º e 9º |
| 4 — Modificativa incisos Art. 14 | Alterar incisos III e IV; adicionar inciso V | Texto incorporado; pontuação corrigida automaticamente (E1) e registrada em LOG |
| 5 — Supressiva §1º Art. 13 | Suprimir §1º; §2º → §1º | §1º resultante preservado **verbatim** com "Atendida a condição prevista no §1º deste artigo" intacto + 🔴 Absurdo (§2º) |
| 6 — Modificativa Anexo III | Alterar CA Máximo Setores A e B | Setor A: 8,0 → 16,0; Setor B: 6,0 → 18,0; Setores C e D inalterados |
| 7 — Aditiva Anexo V | Adicionar Anexo V ao final | Anexo V inserido; referência Art. 18 → Art. 17 atualizada |
| 8 — Substitutiva Art. 16 | Substituir art. 16 integralmente | "serão aplicada" → "serão aplicadas" (E1 auto); pontuação inciso IV corrigida (E1 auto); tudo registrado |
| 9 — Supressiva inciso II Art. 10 | Suprimir inciso II; inciso III → inciso II | Inciso suprimido; "Depósitos" → "depósitos" (E1 auto); pontuação corrigida (E1 auto); registrado |
| 10 — Aglutinativa Arts. 11 e 12 | Aglutinar em art. único; suprimir art. 12; renumerar | Texto verbatim; "Art. 6º"→"Art. 5º", "Art. 7º"→"Art. 6º" atualizados; referências ao conteúdo de Art. 12 original → Art. 11 (A2-aglut); 🔴 "artigo anterior" §4º → Absurdo (§2º) |

---

## 7. O que verificar no resultado

### ✅ Comportamentos obrigatoriamente corretos

| # | Verificação | Critério de aprovação |
|---|---|---|
| 1 | Emenda 5 — §1º preservado verbatim | Frase "Atendida a condição prevista no §1º deste artigo" **presente e intacta** no texto final |
| 2 | Emenda 5 — Absurdo classificado como §2º | Alerta 🔴 presente; fundamentado no art. 250, §2º RI |
| 3 | Emenda 8 — "serão aplicada" corrigido (E1 auto) | Texto final traz "serão aplicadas"; LOG registra correção automática |
| 4 | Emenda 8 — pontuação corrigida (E1 auto) | Inciso IV encerra com "." conforme técnica; LOG registra correção |
| 5 | Emenda 4 — conjunção adicionada (E1 auto) | "b) requalificação..." com "; e" adicionado; LOG registra |
| 6 | Emenda 9 — "Depósitos" corrigido (E1 auto) | "depósitos" (minúscula) no texto final; LOG registra |
| 7 | Emenda 10 — "artigo anterior" preservado | Frase "nos termos do artigo anterior" presente no §4º; 🔴 Absurdo sinalizado |
| 8 | Emendas 1, 5 e 10 — Absurdos como §2º | Pelo menos 3 absurdos manifestos classificados como §2º (reabertura) |
| 9 | Emenda 10 — A2 aglutinação: ref. a conteúdo de Art. 12 → Art. 11 | Qualquer artigo que referencie o conteúdo da outorga/transferência aponta para Art. 11 final |
| 10 | DOCX exportado — sem "Redação Final" | Quando há 🔴 ou 🚨: exporta como "RASCUNHO DE TRABALHO" |
| 11 | DOCX exportado — sem marcadores inline | Nenhum `[[⚠️ CCJ:...]]` no arquivo .docx |
| 12 | Estrutura final | 18 artigos e 5 Anexos |

### ❌ Comportamentos proibidos (falha crítica se ocorrer)

| Comportamento proibido | Classificação |
|---|---|
| Remoção de "Atendida a condição prevista no §1º deste artigo" | Falha crítica — alteração de teor |
| Alteração de número, valor, prazo, percentual, coeficiente | Falha crítica — alteração de teor |
| Alteração de sujeito, objeto ou verbo obrigacional/proibitivo | Falha crítica — alteração de teor |
| Correção de linguagem SEM registrar em LOG e AVISOS | Falha — falta de transparência |
| Absurdo manifesto classificado como art. 250, §1º | Falha jurídica crítica |
| DOCX exportado como "REDAÇÃO FINAL" quando há §2º | Falha regimental crítica |
| Marcadores `[[⚠️ CCJ:...]]` no DOCX exportado | Falha — conteúdo não deliberado pelo Plenário |

---

## 8. Comando de diagnóstico no terminal

```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python teste_real.py
```

Executa: carrega PLC real (49.431 chars), analisa estrutura, verifica API, testa parsing e harmonização, salva `resultado_teste_real.txt`.

---

## 9. URLs e acesso

| Ambiente | URL |
|---|---|
| **Streamlit Cloud** *(principal)* | https://ccj-redacoes.streamlit.app |
| **GitHub** *(código-fonte)* | https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj |

---

## 10. Parâmetros técnicos da IA

| Parâmetro | Valor | Motivo |
|---|---|---|
| Modelo | `claude-sonnet-4-6` | Equilíbrio custo/performance para textos jurídicos longos |
| max_tokens (harmonização) | 60.000 | Suporta PLCs grandes + 180 emendas (teto: 64k) |
| max_tokens (parsing) | 20.000 | Suficiente para 180 emendas em JSON |
| Modo de chamada | Streaming obrigatório | Evita timeout em operações longas |
| Custo estimado (100 emendas + PLC 50k chars) | ~$0,40–$0,60 | Sonnet: $3/M input, $15/M output |

---

*Versão rev.2 — 25/05/2026 — Sistema de Redações CCJ CMRJ*
