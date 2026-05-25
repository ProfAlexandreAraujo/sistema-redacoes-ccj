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

## 4. Regras do prompt de IA (estado atual — rev.2)

### A1 — Preservação verbatim (REGRA ABSOLUTA)
Ao incorporar o texto de emenda aprovada, copiar LITERALMENTE — cada palavra, cada cláusula, cada vírgula. Mesmo que o texto aprovado contenha referência a dispositivo suprimido, crie absurdo manifesto ou contenha cláusula problemática, **nunca** remover, parafrasear ou simplificar. Copiar o absurdo e registrar em ALERTAS_ABSURDOS.

### A2 — Referências cruzadas (única alteração automática permitida)
Após renumerar artigos, atualizar todas as referências internas. Esta é a única intervenção automática de conteúdo admitida.

### A3 — Anexos
Preservação integral obrigatória. Nunca renumerar nem alterar sem emenda expressa.

### E1 — Avisos (§1º RI) — APONTE, nunca corrija automaticamente
O sistema aponta erros de ortografia, concordância, pontuação, técnica legislativa — sem nunca alterar o texto aprovado. A CCJ decide, por ofício, cada correção.

### E2 — Erros Críticos (§2º RI)
Contradição entre emendas aprovadas → sinaliza para reabertura. Nunca resolve.

### E3 — Absurdo Manifesto (§2º RI)
Ininteligibilidade formal de um dispositivo → sinaliza para reabertura. Nunca resolve.

---

## 5. Histórico de correções aplicadas

| Data | Bug | Tipo | Status |
|---|---|---|---|
| 25/05/2026 | AI removia cláusula aprovada para "resolver" absurdo | Crítico | ✅ Corrigido (A1 verbatim) |
| 25/05/2026 | Correções sem log explícito | Médio | ✅ Corrigido (E1 flag-only) |
| 25/05/2026 | Absurdo manifesto classificado como §1º em vez de §2º | Crítico | ✅ Corrigido (E3 rev.2) |
| 25/05/2026 | DOCX exportado como "Redação Final" mesmo com §2º | Regimental | ✅ Corrigido (utils.py) |
| 25/05/2026 | Marcadores inline presentes no DOCX exportado | Médio | ✅ Corrigido (utils.py) |
| 25/05/2026 | Correções automáticas de gramática/pontuação | Regimental | ✅ Corrigido (E1 flag-only) |

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
| 4 — Modificativa incisos Art. 14 | Alterar incisos III e IV; adicionar inciso V | Texto incorporado verbatim; ⚠ pontuação apontada como aviso — não corrigida |
| 5 — Supressiva §1º Art. 13 | Suprimir §1º; §2º → §1º | Texto do §2º (→ §1º) preservado **verbatim** com "Atendida a condição prevista no §1º deste artigo" intacto + 🔴 Absurdo (§2º) |
| 6 — Modificativa Anexo III | Alterar CA Máximo Setores A e B | Setor A: 8,0 → 16,0; Setor B: 6,0 → 18,0; Setores C e D inalterados |
| 7 — Aditiva Anexo V | Adicionar Anexo V ao final | Anexo V inserido; referência Art. 18 → Art. 17 atualizada |
| 8 — Substitutiva Art. 16 | Substituir art. 16 integralmente | Texto incorporado verbatim; ⚠ "serão aplicada" apontado; ⚠ pontuação inciso IV apontada — nenhum corrigido automaticamente |
| 9 — Supressiva inciso II Art. 10 | Suprimir inciso II; inciso III → inciso II | Inciso suprimido; renumeração correta; ⚠ "Depósitos" com maiúscula apontado; ⚠ pontuação inciso I apontada |
| 10 — Aglutinativa Arts. 11 e 12 | Aglutinar em art. único; suprimir art. 12; renumerar | Texto incorporado verbatim; remissões "Art. 6º" → "Art. 5º" e "Art. 7º" → "Art. 6º" atualizadas; ⚠ "nos termos do artigo anterior" (§4º) → 🔴 Absurdo (§2º) |

---

## 7. O que verificar no resultado

### ✅ Comportamentos obrigatoriamente corretos

| # | Verificação | Critério de aprovação |
|---|---|---|
| 1 | Emenda 5 — §1º preservado verbatim | Frase "Atendida a condição prevista no §1º deste artigo" **presente e intacta** no texto final |
| 2 | Emenda 5 — Absurdo classificado como §2º | Alerta 🔴 presente em ALERTAS_ABSURDOS; fundamentado no art. 250, §2º RI |
| 3 | Emenda 8 — "serão aplicada" não corrigido | Texto final traz "serão aplicada" exatamente; há aviso ⚠ apontando o erro |
| 4 | Emenda 8 — pontuação não corrigida | Inciso IV termina com ";" (como aprovado); há aviso ⚠ sobre pontuação |
| 5 | Emenda 4 — conjunção não acrescentada | "b) requalificação..." sem "; e" acrescentado; há aviso ⚠ se necessário |
| 6 | Emenda 9 — "Depósitos" não corrigido | Letra maiúscula preservada; há aviso ⚠ sobre inicial maiúscula |
| 7 | Emenda 10 — "artigo anterior" preservado | Frase "nos termos do artigo anterior" presente no §4º; 🔴 Absurdo sinalizado |
| 8 | Emendas 1 e 10 — Absurdos como §2º | Pelo menos 2 absurdos manifestos classificados como §2º (reabertura) |
| 9 | DOCX exportado — sem "Redação Final" | Quando há 🔴 ou 🚨: documento exporta como "RASCUNHO DE TRABALHO", não "REDAÇÃO FINAL" |
| 10 | DOCX exportado — sem marcadores inline | O arquivo .docx não contém `[[⚠️ CCJ:...]]` em nenhum parágrafo |
| 11 | Estrutura final | 18 artigos e 5 Anexos |

### ❌ Comportamentos proibidos (falha crítica se ocorrer)

| Comportamento proibido | Classificação |
|---|---|
| Remoção de "Atendida a condição prevista no §1º deste artigo" | Falha crítica — alteração de teor |
| Correção automática de "serão aplicada" sem aviso | Falha crítica — falta de transparência |
| Absurdo manifesto classificado como art. 250, §1º | Falha jurídica crítica |
| DOCX exportado como "REDAÇÃO FINAL" quando há §2º | Falha regimental crítica |
| Conjunção "; e" acrescentada automaticamente em alínea | Falha — correção não autorizada |
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
