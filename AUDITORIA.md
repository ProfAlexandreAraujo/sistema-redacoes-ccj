# 🔍 AUDITORIA DO SISTEMA — CCJ CMRJ
### Documento técnico para revisão externa — versão 2026-05-25 **rev.3**

---

## 1. Contexto e propósito

Este sistema auxilia a **Comissão de Constituição, Justiça e Redação (CCJ)** da Câmara Municipal do Rio de Janeiro a elaborar a **Redação Final** ou **Redação do Vencido** de projetos de lei aprovados com emendas (art. 250, Resolução nº 1.673/2025 — Regimento Interno).

**Constraint absoluta e inviolável:**
> *"Eu não posso mexer no teor da emenda. Não posso fazer isso."*

O texto aprovado pelo Plenário é soberano. O sistema **nunca** altera conteúdo substantivo. São permitidas automaticamente apenas: (a) atualização de referências cruzadas internas por renumeração (A2); (b) correções de linguagem que não afetem o significado jurídico (E1).

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

## 3. Três níveis de alerta — fundamentos regimentais

### ⚠️ Aviso Redacional — art. 250, §1º RI
Incorreção ou impropriedade de linguagem que **não deturpa a vontade legislativa**.
→ Erros de ortografia, concordância e pontuação: **o sistema corrige automaticamente** e registra em LOG e AVISOS.
→ Problemas de técnica legislativa que envolvam julgamento (ex: "artigo anterior" vago, "parágrafo único" incorreto): o sistema aponta, a CCJ decide por ofício.

### 🚨 Erro Crítico — art. 250, §2º RI (CCJ NÃO oferece Redação Final)
Duas emendas aprovadas que se **contradizem diretamente** sobre o mesmo dispositivo.
→ A CCJ **não deve oferecer Redação Final**; deve propor reabertura da discussão.
→ DOCX exportado como "RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL".

### 🔴 Absurdo Manifesto — art. 250, §2º RI (CCJ NÃO oferece Redação Final)
Texto tecnicamente ininteligível ou que cria **dúvida inequívoca sobre a vontade legislativa** por razão exclusivamente formal.
Exemplos: autoreferência circular de artigo; condição normativa remetendo a parágrafo suprimido; "artigo anterior" apontando para dispositivo incompatível.
→ Texto preservado **verbatim** + marcador inline visível na tela de trabalho.
→ Marcador **removido** do DOCX exportado.
→ A CCJ **não deve oferecer Redação Final**; deve propor reabertura (art. 250, §2º RI).

> **REGRA CRÍTICA:** Tanto 🚨 quanto 🔴 invocam o **§2º** — reabertura, não ofício. O §1º cobre apenas impropriedades de linguagem (⚠️).

---

## 4. Regras do sistema (rev.3)

### A1 — Preservação de teor (REGRA ABSOLUTA)
Incorporar o texto de cada emenda aprovada LITERALMENTE — cada palavra, cada cláusula, cada vírgula. Mesmo que o texto aprovado contenha referência a dispositivo suprimido, crie absurdo manifesto ou contenha cláusula problemática: **nunca** remover, parafrasear, simplificar ou "consertar" o conteúdo. Registrar o absurdo em ALERTAS_ABSURDOS com marcador inline.

### A2 — Referências cruzadas (única alteração automática de conteúdo)
Após renumerar artigos/parágrafos/incisos, atualizar **todas** as referências internas. Esta é a única intervenção automática de conteúdo admitida.

**Regra especial — emendas aglutinativas:** quando a emenda unifica art. X e art. Y em art. X (suprimindo Y), o conteúdo de Y migra para X. Qualquer referência ao conteúdo que estava em Y deve apontar para X final — **não** para o artigo que por renumeração sequencial herda o número de Y.
Exemplo: arts. 11 e 12 aglutinados em art. 11; referência "transferência prevista no Art. 12" → "Art. 11".
Registrar no LOG: `A2-aglut / Art. Xº: 'Art. Y' → 'Art. X' (conteúdo migrou pela aglutinação — Emenda N)`.

### A3 — Anexos
Preservação integral obrigatória. Nunca renumerar nem alterar sem emenda expressa. Referências a anexos atualizadas se o anexo for renumerado por emenda.

### E1 — Correções automáticas de linguagem (art. 250, §1º RI)
Erros de linguagem que **não alterem o significado jurídico** são **corrigidos automaticamente**.
Para cada correção: LOG → `E1 / Art. Xº: [original] → [corrigido]` e AVISOS → `⚠ E1 / Art. Xº: corrigido — [original] → [corrigido]`.

**CORRIJA automaticamente:**
- Concordância nominal/verbal (ex: "serão aplicada" → "serão aplicadas")
- Caixa incorreta em palavras comuns (ex: "Depósitos" → "depósitos" quando não for nome próprio)
- Pontuação de incisos/alíneas (Bloco C da LC 48/2000: ponto e vírgula, "; e", ponto final)

**NUNCA ALTERE** (mesmo que pareça erro):
- Números, valores, prazos, percentuais, coeficientes, coordenadas, medidas
- Sujeito, objeto, verbo obrigacional/proibitivo de qualquer dispositivo
- Termos técnicos jurídicos e urbanísticos
- Qualquer expressão que defina o que a lei permite, proíbe ou obriga
- Remissões a dispositivos (salvo A2)

**APONTE mas não corrija** (geram ⚠ aviso sem alteração):
- Uso de "anterior" ou "seguinte" sem especificação do dispositivo (D2)
- "Parágrafo único" onde há mais de um parágrafo (ou vice-versa)
- Técnica redacional imprópria que comprometa o sentido jurídico

### E2 — Erros Críticos (§2º RI)
Contradição entre emendas aprovadas → sinaliza para reabertura. **Nunca resolve.**

### E3 — Absurdo Manifesto (§2º RI)
Ininteligibilidade formal de um dispositivo → sinaliza para reabertura. **Nunca resolve.**
Quatro casos obrigatórios: (1) autoreferência circular; (2) condição remetendo a § suprimido; (3) "artigo anterior" materialmente incompatível; (4) referência exclusiva a dispositivo suprimido.

### P1 — Pós-processamento Python (camada independente do modelo)
Após o modelo responder, `harmonizer.py` executa detectores estruturais sobre o texto harmonizado para escalar absurdos que o modelo classificou como §1º:
- **Caso 1:** Art. N com `no Art. N` no corpo → autoreferência circular (regex sobre blocos de artigo)
- **Caso 2:** §N com `§N deste artigo` no corpo → condição normativa inoperante (regex sobre parágrafos)
- **Caso 3:** Varredura semântica nos textos dos avisos por padrões como `artigo anterior.*incompatível`, `condição.*suprimida`, etc.

Qualquer item escalado move-se de `avisos` para `alertas_absurdos`, forçando o DOCX como "RASCUNHO DE TRABALHO".

---

## 5. Histórico de correções

| Data | Ocorrência | Tipo | Status |
|---|---|---|---|
| 25/05/2026 | IA removia cláusula aprovada para "resolver" absurdo | Crítico | ✅ A1 verbatim |
| 25/05/2026 | Absurdo manifesto classificado como §1º (prompt) | Crítico | ✅ E3 rev.2 |
| 25/05/2026 | DOCX exportado como "Redação Final" mesmo com §2º | Regimental | ✅ utils.py |
| 25/05/2026 | Marcadores inline presentes no DOCX exportado | Médio | ✅ utils.py |
| 25/05/2026 | IA persistia em classificar absurdos como §1º (E3 rev.2 insuficiente) | Crítico | ✅ P1 pós-processamento Python |
| 25/05/2026 | E1 "flag-only" → "auto-corrigir + log" (decisão do usuário) | Funcional | ✅ E1 rev.3 |
| 25/05/2026 | A2 não atualizava referências ao conteúdo migrado por aglutinação | Funcional | ✅ A2 aglutinação |

---

## 6. Stress test — PLC fictício nº 17/2026

Usar `TAB_1_PLC_17_2026_TEXTO_ORIGINAL.txt` (19 artigos + 4 Anexos) com `TAB_2_PLC_17_2026_EMENDAS.txt` (10 emendas, todas APROVADAS).

### Estrutura esperada ao final
- **18 artigos** (art. 4º suprimido; novo art. de monitoramento inserido; arts. 11 e 12 aglutinados)
- **5 Anexos** (Anexo V adicionado pela Emenda 7)

### Emenda por emenda

| Emenda | Operação | Resultado esperado |
|---|---|---|
| 1 — Supressiva Art. 4º | Suprimir art. 4º; renumerar | Art. 4º suprimido; novo Art. 4º com "definida no Art. 4º" → 🔴 Absurdo §2º (circular) |
| 2 — Modificativa §2º Art. 7º | Coeficiente 4 → 6; "Art. 6º" → "Art. 5º" | Verbatim; remissão atualizada (A2) |
| 3 — Aditiva novo art. após Art. 10 | Inserir art. monitoramento | Novo Art. 10; "arts. 9º e 10" → "arts. 8º e 9º" (A2) |
| 4 — Modificativa incisos Art. 14 | Incisos III, IV + novo V | Verbatim; pontuação corrigida automaticamente (E1) + LOG |
| 5 — Supressiva §1º Art. 13 | Suprimir §1º; §2º → §1º | §1º verbatim com "Atendida a condição prevista no §1º deste artigo" + 🔴 Absurdo §2º |
| 6 — Modificativa Anexo III | CA Máximo Setores A e B | A: 8,0→16,0; B: 6,0→18,0; C e D inalterados |
| 7 — Aditiva Anexo V | Adicionar Anexo V | Inserido; "Art. 18" → "Art. 17" (A2) |
| 8 — Substitutiva Art. 16 | Substituir art. 16 | Verbatim; "serão aplicada"→"serão aplicadas" (E1 auto); pontuação inciso IV (E1 auto); tudo em LOG |
| 9 — Supressiva inciso II Art. 10 | Suprimir inciso II | Suprimido; "Depósitos"→"depósitos" (E1 auto); LOG |
| 10 — Aglutinativa Arts. 11 e 12 | Unificar; suprimir art. 12 | Verbatim; "Art. 6º"→"Art. 5º", "Art. 7º"→"Art. 6º" (A2); ref. a conteúdo de Art. 12 → Art. 11 (A2-aglut); 🔴 "artigo anterior" §4º → Absurdo §2º |

---

## 7. O que verificar no resultado

### ✅ Comportamentos obrigatoriamente corretos

| # | Verificação | Critério de aprovação |
|---|---|---|
| 1 | Emenda 5 — §1º preservado verbatim | "Atendida a condição prevista no §1º deste artigo" presente e intacta |
| 2 | Emenda 5 — Absurdo §2º | 🔴 em ALERTAS_ABSURDOS; fundamentado no art. 250, §2º RI |
| 3 | Emenda 8 — "serão aplicada" corrigido (E1) | "serão aplicadas" no texto; LOG registra correção |
| 4 | Emenda 8 — pontuação inciso IV (E1) | Encerra com "." conforme técnica; LOG registra |
| 5 | Emenda 4 — conjunção adicionada (E1) | Penúltima alínea com "; e"; LOG registra |
| 6 | Emenda 9 — "Depósitos" corrigido (E1) | "depósitos" no texto; LOG registra |
| 7 | Emenda 10 — "artigo anterior" preservado | "nos termos do artigo anterior" no §4º; 🔴 Absurdo sinalizado |
| 8 | Emendas 1, 5 e 10 — ≥3 Absurdos §2º | ALERTAS_ABSURDOS com ≥3 itens |
| 9 | Emenda 10 — A2 aglutinação | Referências ao conteúdo do Art. 12 original → Art. 11 final |
| 10 | DOCX — título correto | Com 🔴 ou 🚨: "RASCUNHO DE TRABALHO"; sem: "REDAÇÃO FINAL" |
| 11 | DOCX — sem marcadores | Nenhum `[[⚠️ CCJ:...]]` no arquivo .docx |
| 12 | Estrutura final | 18 artigos e 5 Anexos |

### ❌ Comportamentos proibidos (falha crítica)

| Comportamento proibido | Gravidade |
|---|---|
| Remover "Atendida a condição prevista no §1º deste artigo" | Crítica — alteração de teor |
| Alterar número, valor, prazo, percentual, coeficiente | Crítica — alteração de teor |
| Alterar sujeito, objeto ou verbo obrigacional/proibitivo | Crítica — alteração de teor |
| Corrigir linguagem SEM registrar em LOG e AVISOS | Grave — falta de transparência |
| Classificar absurdo manifesto como art. 250, §1º | Jurídica crítica |
| Exportar DOCX como "REDAÇÃO FINAL" quando há §2º | Regimental crítica |
| Deixar marcadores `[[⚠️ CCJ:...]]` no DOCX exportado | Grave |

---

## 8. Comandos de verificação

### Verificação rápida (sem chamada de API — gratuito)
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python verificar.py
```
Testa: importações, sufixo -A, detectores estruturais (P1), padrões semânticos (P1), escalador integrado, exportação DOCX (título + marcadores), análise estrutural, disponibilidade de API e arquivos de teste.

### Verificação completa (com harmonização real — custo ~$0,50)
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python verificar.py --com-api
```
Executa adicionalmente: harmonização completa do PLC 17/2026 com as 10 emendas; verifica estrutura (18 arts, 5 anexos), preservação verbatim, ≥3 absurdos §2º. Salva resultado em `resultado_verificar.txt`.

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

*Versão rev.3 — 25/05/2026 — Sistema de Redações CCJ CMRJ*
