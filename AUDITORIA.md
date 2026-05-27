# 🔍 AUDITORIA DO SISTEMA — CCJ CMRJ
### Documento técnico para revisão externa — versão 2026-05-26 **rev.23**

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

### 🚨 Erro Crítico — art. 250, §2º RI
Duas emendas aprovadas que se **contradizem diretamente** sobre o mesmo dispositivo.
→ A providência regimental indicada é a **reabertura da discussão**.
→ O sistema exporta o DOCX como **"RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL"** por padrão.
→ O relator pode confirmar ciência e exportar como Redação Final (com ALERTA CRÍTICO no cabeçalho e registro no log).

### 🔴 Absurdo Manifesto — art. 250, §2º RI
Texto tecnicamente ininteligível ou que cria **dúvida inequívoca sobre a vontade legislativa** por razão exclusivamente formal.
Exemplos: autoreferência circular de artigo; condição normativa remetendo a parágrafo suprimido; "artigo anterior" apontando para dispositivo incompatível.
→ Texto preservado **verbatim** + marcador inline visível na tela de trabalho.
→ Marcador **removido** do DOCX exportado.
→ A providência regimental indicada é a **reabertura da discussão** (art. 250, §2º RI).
→ DOCX e relatório TXT orientam expressamente a **reabertura** com fundamento no §2º — nunca correção por ofício do §1º.

> **REGRA CRÍTICA:** Tanto 🚨 quanto 🔴 invocam o **§2º** — reabertura, não ofício. O §1º cobre apenas impropriedades de linguagem (⚠️).

### Sistema de dois modos para exportação com §2º
O sistema distingue dois cenários ao exportar com alertas de §2º:

| Modo | Condição | Título do DOCX | Sufixo -A | Cabeçalho |
|---|---|---|---|---|
| **RASCUNHO** (padrão) | §2º presente, sem confirmação | "RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL" | Não | Aviso em vermelho: "existem alertas de §2º" |
| **REDAÇÃO FINAL** | §2º presente, relator confirmou ciência | "REDAÇÃO FINAL" | Sim | "ALERTA CRÍTICO PENDENTE — ART. 250, §2º RI" + log de OVERRIDE-HUMANO |

A confirmação é feita na aba 5 da interface (checkbox explícito). O log do DOCX registra o OVERRIDE-HUMANO com data.

---

## 4. Regras do sistema (rev.4)

### A1 — Preservação de teor (REGRA ABSOLUTA)
Incorporar o texto de cada emenda aprovada LITERALMENTE — cada palavra, cada cláusula, cada vírgula. Mesmo que o texto aprovado contenha referência a dispositivo suprimido, crie absurdo manifesto ou contenha cláusula problemática: **nunca** remover, parafrasear, simplificar ou "consertar" o conteúdo. Registrar o absurdo em ALERTAS_ABSURDOS com marcador inline.

As correções exclusivamente linguísticas autorizadas em E1 não violam A1 — são a única exceção expressa e devem ser obrigatoriamente registradas em LOG e AVISOS.

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
- Pontuação de incisos/alíneas (Bloco C da LC 48/2000: ponto e vírgula, ponto final) — **exceto** o conectivo "; e"

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
- Ausência do conectivo "; e" antes do penúltimo inciso (LC 48/2000 apenas — não exigido pela LC 95/1998 federal; prática legislativa municipal o ignora com frequência)

**NUNCA inclua em AVISOS:**
- Observações sobre mérito, política urbanística ou consistência de parâmetros (CA, gabaritos, valores numéricos aprovados pelo Plenário) — esses são assuntos de mérito, fora da competência da CCJ na Redação Final.

### E2 — Erros Críticos (§2º RI)
Contradição entre emendas aprovadas → a providência regimental indicada é a reabertura da discussão. **Nunca resolve.**

### E3 — Absurdo Manifesto (§2º RI)
Ininteligibilidade formal de um dispositivo → a providência regimental indicada é a reabertura da discussão. **Nunca resolve.**
Quatro casos obrigatórios: (1) autoreferência circular; (2) condição remetendo a § suprimido; (3) "artigo anterior" materialmente incompatível; (4) referência exclusiva a dispositivo suprimido.

### P1 — Pós-processamento Python (camada independente do modelo)
Após o modelo responder, `harmonizer.py` executa detectores estruturais sobre o texto harmonizado para escalar absurdos que o modelo classificou como §1º:
- **Caso 1:** Art. N com referência preposicionada ao próprio Art. N no corpo → autoreferência circular (regex sobre blocos de artigo)
- **Caso 2:** §N com `§N deste artigo` no corpo → condição normativa inoperante (regex sobre parágrafos)
- **Caso 3:** Varredura semântica nos textos dos avisos por padrões como `artigo anterior.*incompatível`, `condição.*suprimida`, etc.

Qualquer item escalado move-se de `avisos` para `alertas_absurdos`, ativando o modo RASCUNHO por padrão na exportação.

**Riscos conhecidos e monitorados (não bloqueadores):**
- O detector do Caso 1 exige preposição antes do número (`no Art. N`, `do Art. N` etc.) para reduzir falsos positivos, mas autorreferências intencionais raramente existem — monitorar no PLC real.
- A deduplicação de alertas usa intersecção de dispositivos (Art. N, §N); dois absurdos distintos no mesmo artigo podem ser fundidos se o modelo não os gerar separadamente. O modelo é o caminho principal; o pós-processador é camada de segurança.

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
| 25/05/2026 | "; e" auto-corrigido (LC 48/2000 apenas, não LC 95/1998 — prática ignora) | Funcional | ✅ E1 aviso-only |
| 25/05/2026 | IA incluía análises de mérito/CA urbanístico em AVISOS §1º | Crítico | ✅ bloqueio prompt |
| 25/05/2026 | DOCX e TXT descreviam absurdo manifesto com providência do §1º (ofício) em vez do §2º (reabertura) | Jurídico crítico | ✅ utils.py rev.4 |
| 25/05/2026 | Seção de avisos no DOCX afirmava "preservados exatamente como aprovados" mesmo quando havia correções E1 | Rastreabilidade | ✅ utils.py rev.4 |
| 25/05/2026 | A1 não explicitava a exceção E1 — tensão aparente entre preservação literal e auto-correção | Documentação | ✅ AUDITORIA.md rev.4 |
| 25/05/2026 | `texto_bruto` de emenda supressiva ficava vazio (recebia `novo_texto` que é null) | Rastreabilidade | ✅ harmonizer.py rev.4 |
| 25/05/2026 | `offset += len(todas_emendas)` acumulava lotes anteriores — numeração errada em múltiplos lotes | Funcional (lotes extensos) | ✅ harmonizer.py rev.4 |
| 25/05/2026 | Bloqueio de exportação do DOCX com §2º era perigoso — reabertura é politicamente inviável; sistema deve permitir o relator decidir com ciência dos alertas | Regimental/Usabilidade | ✅ sistema dois modos (utils.py + app.py rev.6) |
| 25/05/2026 | Linguagem "CCJ NÃO deve oferecer Redação Final" em E2/E3/P1 era excessivamente absoluta | Jurídico | ✅ harmonizer.py rev.6 — "providência regimental indicada é a reabertura" |
| 25/05/2026 | .txt contornava lógica de rascunho: exportava `redacao_final_*.txt` sem cabeçalho de alerta, mesmo com §2º sem confirmação | UX-regimental média/alta | ✅ app.py rev.7 — .txt respeita _eh_rascunho_aba5; inclui cabeçalho de alerta; slug `rascunho_trabalho_*.txt` |
| 25/05/2026 | Checkbox `confirmar_sec_2_aba5` persistia no session_state entre harmonizações — nova execução herdava confirmação anterior | Regimental | ✅ app.py rev.7 — `pop('confirmar_sec_2_aba5')` em todos os pontos de nova harmonização/invalidação |
| 25/05/2026 | `texto_redacao_final` também persistia — possível carry-over de texto antigo na área editável | Rastreabilidade | ✅ app.py rev.7 — `pop('texto_redacao_final')` nos mesmos pontos |
| 25/05/2026 | Rótulo dos botões não indicava o modo real (RASCUNHO vs REDAÇÃO FINAL com alerta) | UX | ✅ app.py rev.7 — rótulos dinâmicos em .txt e .docx |
| 25/05/2026 | Resultado antigo sobrevivia a mudanças em emendas/votação | Rastreabilidade/Consistência | ✅ app.py rev.8 — `_invalidar_resultado()` em 13+ pontos |
| 25/05/2026 | `extrair("TEXTO_HARMONIZADO", texto_original)` — resposta sem tags retornava silenciosamente o original | Falha silenciosa crítica | ✅ harmonizer.py rev.8 |
| 25/05/2026 | Guarda rev.8 verificava só tag de abertura — resposta truncada passava na guarda | Falha silenciosa crítica | ✅ harmonizer.py rev.9 |
| 25/05/2026 | Rev.9 exigia par completo só para TEXTO_HARMONIZADO; demais 5 tags ainda checavam só abertura | Falha silenciosa generalizada | ✅ harmonizer.py rev.10 |
| 25/05/2026 | `parsear_emendas_com_ia`: `continue` silencioso descartava lote sem JSON | Falha silenciosa | ✅ harmonizer.py rev.11 |
| 26/05/2026 | Regra E2 genérica — sem varredura prévia, sem cautela, sem sugestão | Funcional/Regimental | ✅ harmonizer.py rev.12 |
| 26/05/2026 | TXT exportado sem limpeza de marcadores `[[⚠️ CCJ:...]]` | Qualidade do produto | ✅ app.py rev.10 |
| 26/05/2026 | Sistema não suportava subemendas | Funcional — lacuna legislativa | ✅ harmonizer.py rev.13 |
| 26/05/2026 | Conflito de subemendas roteado para `avisos` §1º em vez de `erros_criticos` §2º | Regimental crítico | ✅ harmonizer.py rev.14 |
| 26/05/2026 | P1 auto-referência, P2 pai inexistente, P3 cadeia — 3 edge cases de subemendas | Regimental crítico | ✅ harmonizer.py rev.15 |
| 26/05/2026 | **[B1]** `analisar_estrutura()`: artigos sem ponto após "Art" (ex: `Art 14.`) não eram contados — PLC 55/2025 detectava 20 artigos, correto é 21 | Bug funcional (teste real na Câmara) | ✅ utils.py rev.16 — período após "Art" tornado opcional: `r'^Art\.?\s*\d+'` |
| 26/05/2026 | **[B2]** `ler_pdf()`: stop markers truncavam no **primeiro marcador da lista** (`TRAMITAÇÃO DO PROJETO`, pos=24805) em vez de no **mais cedo** (`JUSTIFICATIVA`, pos=17241) — texto extraído incluía `Art. 169` e `Art. 5°` da seção de Legislação Citada, inflando a contagem para 23 artigos | Bug funcional (teste real na Câmara) | ✅ utils.py rev.16 — truncamento no mínimo entre todos os marcadores encontrados com pos > 500 |
| 26/05/2026 | **[B3]** `ler_pdf()`: regex URL `r'https?://www\.camara\.rio/\S+'` não capturava sufixo de paginação " X/15" após espaço — rodapé residual nos PDFs do site da CMRJ | Cosmético (texto limpo para IA) | ✅ utils.py rev.16 — regex alterado para `r'https?://www\.camara\.rio/[^\n]+'` |
| 26/05/2026 | **[B4]** `exportar_redacao_final_docx()`: formatação não seguia o modelo oficial CMRJ — fonte 12pt (correto: 10pt), artigos em negrito (correto: sem negrito), sem EMENTA/AUTOR/fecho/assinaturas, cabeçalho com estilos Heading incorretos, sem margens A4 | Produto (formatação horrorosa relatada em uso real) | ✅ utils.py rev.16 — função completamente reescrita; vide seção 11.1 |
| 26/05/2026 | **[B5]** `from docx.oxml.ns import qn` e `from docx.oxml import OxmlElement` no topo de `utils.py` causavam `ImportError` no Streamlit Cloud ao carregar o módulo | Deploy crítico (app fora do ar) | ✅ utils.py rev.16.1 — imports movidos para lazy dentro de `_remover_bordas_tabela()`; ✅ **CONFIRMADO rev.17**: download DOCX no Cloud funciona corretamente |
| 26/05/2026 | **[B7]** `exportar_redacao_final_docx()`: ementa gerada em tabela sem bordas (resíduo de B4) em vez de parágrafo simples; corpo e assinaturas com fonte `'Times New Roman'` 10pt em vez de `Arial` 11pt (padrão CMRJ) | Produto (formatação inconsistente com modelos de referência) | ✅ utils.py rev.18 — ementa movida para `_para()` simples; todas as fontes unificadas para `Arial` 11pt via constantes `_FONT`/`_FSIZE` |
| 26/05/2026 | **[B6]** `parsear_emendas_com_ia()`: fallback bruto com `offset + len(todas_emendas) + 1` somava o offset duas vezes em múltiplos lotes — ex: lotes [E1,E2] ok + [fallback] produzia [1,2,5,6] em vez de [1,2,3,4] | Bug funcional silencioso (numeração errada afeta votação e subemenda_de) | ✅ harmonizer.py rev.17 — fallback usa `offset + idx_fb + 1` onde `idx_fb` é relativo ao lote atual |

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
| 4 — Modificativa incisos Art. 14 | Incisos III, IV + novo V | Verbatim; pontuação (`;` e `.`) corrigida automaticamente (E1) + LOG; ausência de "; e" → ⚠ aviso apenas |
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
| 5 | Emenda 4 — conjunção "; e" ausente | ⚠ aviso gerado (não auto-corrigido) |
| 6 | Emenda 9 — "Depósitos" corrigido (E1) | "depósitos" no texto; LOG registra |
| 7 | Emenda 10 — "artigo anterior" preservado | "nos termos do artigo anterior" no §4º; 🔴 Absurdo sinalizado |
| 8 | Emendas 1, 5 e 10 — ≥3 Absurdos §2º | ALERTAS_ABSURDOS com ≥3 itens |
| 9 | Emenda 10 — A2 aglutinação | Referências ao conteúdo do Art. 12 original → Art. 11 final |
| 10 | DOCX — modo RASCUNHO (padrão com §2º) | Sem confirmação → "RASCUNHO DE TRABALHO"; sufixo -A ausente |
| 10b | DOCX — modo REDAÇÃO FINAL (com confirmação) | Com confirmação → "REDAÇÃO FINAL"; "ALERTA CRÍTICO PENDENTE" no cabeçalho; "OVERRIDE-HUMANO" no log |
| 11 | DOCX — sem marcadores | Nenhum `[[⚠️ CCJ:...]]` no arquivo .docx |
| 12 | Estrutura final | 18 artigos e 5 Anexos |
| 13 | DOCX — texto de absurdo cita §2º e reabertura | Seção de absurdos menciona "§2º" e "reabertura" — nunca "ofício" ou "§1º" |
| 14 | DOCX — seção de avisos não afirma preservação total | Texto da seção não contém "preservados exatamente como aprovados" |
| **15** | **DOCX rev.18 — formato oficial CMRJ** | **Título CENTER BOLD UNDERLINE; fonte Arial 11pt (B7); ementa como parágrafo simples (não tabela); A CÂMARA MUNICIPAL negrito; DECRETA: alinhado à direita; artigos SEM negrito; fecho com data em português; assinaturas dos 3 vereadores** |

### ❌ Comportamentos proibidos (falha crítica)

| Comportamento proibido | Gravidade |
|---|---|
| Remover "Atendida a condição prevista no §1º deste artigo" | Crítica — alteração de teor |
| Alterar número, valor, prazo, percentual, coeficiente | Crítica — alteração de teor |
| Alterar sujeito, objeto ou verbo obrigacional/proibitivo | Crítica — alteração de teor |
| Corrigir linguagem SEM registrar em LOG e AVISOS | Grave — falta de transparência |
| Classificar absurdo manifesto como art. 250, §1º | Jurídica crítica |
| Exportar DOCX como "REDAÇÃO FINAL" quando há §2º **sem confirmação do relator** | Regimental crítica |
| Deixar marcadores `[[⚠️ CCJ:...]]` no DOCX exportado | Grave |
| Texto do DOCX orientar correção de absurdo por ofício do §1º | Jurídica crítica |
| Incluir análise de mérito urbanístico (CA, gabaritos) em AVISOS | Grave — fora da competência |

---

## 8. Comandos de verificação

### Verificação rápida (sem chamada de API — gratuito)
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python verificar.py
```
Testa (128/129 verificações locais — rev.23; 2 checks de stress test requerem arquivos TAB no caminho local — 126/127 em CI sem esses arquivos): importações, sufixo -A, detectores estruturais P1 (casos 1 e 2), padrões semânticos P1 (caso 3), escalador integrado, exportação DOCX em dois modos, fundamentação §2º, seção de avisos, TXT modo rascunho, parsing de emendas e offset, **análise estrutural incluindo Art sem ponto (B1)**, disponibilidade de API e arquivos de teste, validação XML, `_invalidar_resultado()`, A4, E2, subemendas (P1/P2/P3).

### Verificação completa (com harmonização real — custo ~$0,50)
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python verificar.py --com-api
```
Executa adicionalmente: harmonização completa do PLC 17/2026 com as 10 emendas.

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

## 11. Extratos de código para verificação (rev.19)

Esta seção contém os trechos mais críticos do código atual para facilitar a auditoria. O código completo está em https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj

---

### 11.1 `utils.py` — exportação DOCX no formato oficial CMRJ — rev.19

A função foi **completamente reescrita** para seguir os 4 modelos reais da CMRJ
(`730-A_2026 -- REDAÇÃO FINAL.docx`, `279-A-2025 - REDAÇÃO DO VENCIDO.docx`,
`279-A-2025`, `REDAÇÃO FINAL PL 1456-A 2025.docx`) inspecionados via python-docx.

**Assinatura atualizada (novos parâmetros `ementa` e `autor`):**
```python
def exportar_redacao_final_docx(
    texto: str,
    nome_projeto: str,
    avisos: list[str],
    erros: list[str],
    alertas_absurdos: list[str] = None,
    mapa: dict = None,
    log: list[str] = None,
    tipo_redacao: str = "Redação Final",
    prosseguir_com_alerta_sec_2: bool = False,
    ementa: str = "",   # ← NOVO rev.16: extraído de extrair_ementa_autor()
    autor: str = "",    # ← NOVO rev.16
) -> bytes:
```

**Evolução histórica da formatação DOCX (B4 rev.16 → B7 rev.18):**

| Elemento | Antes rev.15 | Depois rev.16 B4 | **Estado atual rev.18 B7** |
|---|---|---|---|
| Fonte | Times New Roman **12pt** | Times New Roman **10pt** | **Arial 11pt** |
| Página | Sem definição | A4 (21,0×29,7cm), margens **2,5cm** todos os lados | inalterado |
| Cabeçalho | Heading 1 "CÂMARA MUNICIPAL" + Heading 2 "CCJ" | **Removido** | inalterado |
| Título | Bold 14pt, sem sublinhado | **Bold + Underline** 10pt CENTER | Arial 11pt (size_pt explícito removido) |
| Artigos | **Bold** (incorreto) | **Sem negrito** (conforme modelos) | inalterado |
| `A CÂMARA MUNICIPAL...` | Sem destaque | **Bold JUSTIFY** | inalterado |
| `DECRETA:` / `D E C R E T A:` | Sem destaque | **Bold RIGHT** (detectado por regex) | inalterado |
| Ementa | **Ausente** | EMENTA: bold + tabela sem bordas | **parágrafo simples** (sem tabela) |
| Autor(es) | **Ausente** | Bold JUSTIFY | inalterado |
| "Elaborada em DD/MM" | No corpo | **Removido** do corpo | inalterado |
| Fecho | **Ausente** | "Sala da Comissão, DD de mês de YYYY." CENTER sp6 | inalterado |
| Assinaturas | **Ausentes** | Átila Nunes (presidente) + tabela 2×2 sem bordas | inalterado |

**Trecho chave — configuração de página e ementa:**
```python
# Configuração da página: A4, margens 2,5 cm
sec = doc.sections[0]
sec.page_width    = Cm(21.0)
sec.page_height   = Cm(29.7)
sec.top_margin    = Cm(2.5)
sec.bottom_margin = Cm(2.5)
sec.left_margin   = Cm(2.5)
sec.right_margin  = Cm(2.5)

# Estilo padrão B4: Times New Roman 10 pt — posteriormente atualizado em B7
# (B7 rev.18: Arial 11pt via constantes _FONT/_FSIZE; vide seção B7 abaixo)
normal = doc.styles['Normal']
normal.font.name  = 'Times New Roman'   # B4; B7 muda para 'Arial'
normal.font.size  = Pt(10)              # B4; B7 muda para Pt(11)

# Ementa B4: tabela sem bordas — posteriormente substituído em B7
# (B7 rev.18: ementa como parágrafo simples _para(), sem tabela)
if ementa:
    tbl_em = doc.add_table(rows=1, cols=1)
    _remover_bordas_tabela(tbl_em)
    cell_em = tbl_em.cell(0, 0)
    p_em    = cell_em.paragraphs[0]
    p_em.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_em = p_em.add_run(ementa)
    r_em.font.size = Pt(10)

# Fecho com data em português
MESES_PT = {1:'janeiro', 2:'fevereiro', 3:'março', 4:'abril',
            5:'maio', 6:'junho', 7:'julho', 8:'agosto',
            9:'setembro', 10:'outubro', 11:'novembro', 12:'dezembro'}
hoje    = datetime.date.today()
data_pt = f"{hoje.day} de {MESES_PT[hoje.month]} de {hoje.year}"
_footer_para(f"Sala da Comissão, {data_pt}.")
_footer_para("Vereador Átila Nunes")
_footer_para("Presidente")

# Tabela 2×2 sem bordas para Dr. Gilberto | Inaldo Silva
tbl_sig = doc.add_table(rows=2, cols=2)
_remover_bordas_tabela(tbl_sig)
for row_i, col_i, text in [
    (0, 0, "Vereador Dr. Gilberto"), (0, 1, "Vereador Inaldo Silva"),
    (1, 0, "Vice-presidente"),        (1, 1, "Vogal"),
]:
    cell = tbl_sig.cell(row_i, col_i)
    p    = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
```

**Extração automática de ementa e autor do projeto original:**
```python
def extrair_ementa_autor(texto: str) -> tuple[str, str]:
    """Extrai ementa e linha de autor do texto original do projeto."""
    ementa = ""
    autor  = ""
    m_em = re.search(
        r'EMENTA:\s*\n([\s\S]*?)(?=\n\s*(?:Autor\(es\)|A\s+C[ÂA]MARA|$))',
        texto, re.IGNORECASE
    )
    if m_em:
        ementa = ' '.join(m_em.group(1).split())   # colapsa whitespace
    m_aut = re.search(r'(Autor\(es\)\s*:.*)', texto, re.IGNORECASE)
    if m_aut:
        autor = m_aut.group(1).strip()
    return ementa, autor
```

---

### 11.2 `utils.py` — correções B1, B2, B3 (rev.16)

**B1 — `analisar_estrutura()`: período após "Art" tornado opcional**
```python
# Antes (bug):
artigos = re.findall(r'^Art\.\s*\d+[ºo°]?', texto, re.MULTILINE | re.IGNORECASE)
# Depois (fix):
artigos = re.findall(r'^Art\.?\s*\d+[ºo°]?', texto, re.MULTILINE | re.IGNORECASE)
# Razão: PDFs da CMRJ às vezes omitem o ponto após "Art" — ex: "Art 14." no PLC 55/2025
```

**B2 — `ler_pdf()`: truncamento no mínimo entre todos os marcadores**
```python
# Antes (bug): parava no primeiro marcador encontrado NA LISTA (não o mais cedo no texto)
for marcador in (...):
    idx = texto_completo.find(marcador)
    if idx > 500:
        texto_completo = texto_completo[:idx]
        break  # ← bug: 'TRAMITAÇÃO' (pos 24805) era acionado antes de 'JUSTIFICATIVA' (pos 17241)

# Depois (fix): mínimo entre todos
stop_pos = len(texto_completo)
for marcador in _stop_marcadores:
    idx = texto_completo.find(marcador)
    if idx > 500:
        stop_pos = min(stop_pos, idx)
texto_completo = texto_completo[:stop_pos]
```

**B3 — `ler_pdf()`: regex URL captura sufixo de paginação**
```python
# Antes (bug): \S+ parava no espaço antes de "8/15"
r'https?://www\.camara\.rio/\S+\s*\n?'
# Depois (fix): captura toda a linha
r'https?://www\.camara\.rio/[^\n]+'
```

**B5 — `utils.py`: imports de API interna do python-docx no topo do módulo (hotfix rev.16.1)**
```python
# Antes (bug): `from docx.oxml.ns import qn` e `from docx.oxml import OxmlElement`
# estavam no TOPO do arquivo — executados no momento do `import utils`.
# No Streamlit Cloud (Linux + versão distinta do python-docx) a importação
# falhava com ImportError, derrubando o app inteiro na inicialização.
# O erro só foi detectado após o deploy; localmente não se reproduzia.

# Depois (fix): imports movidos para dentro de _remover_bordas_tabela()
def _remover_bordas_tabela(tabela) -> None:
    from docx.oxml.ns import qn as _qn           # ← lazy: só no download DOCX
    from docx.oxml import OxmlElement as _OxmlElement
    ...
# Lição: APIs internas de pacotes terceiros nunca devem ser importadas
# no nível de módulo em código que roda em ambientes distintos (local ≠ Cloud).
```

**✅ STATUS FECHADO — B5 (confirmado rev.17):** o fix lazy impede o crash no carregamento do módulo e foi confirmado em produção — o download de DOCX no Streamlit Cloud funciona corretamente. Nota adicional (rev.18): a tabela sem bordas na ementa foi substituída por `_para()` simples, eliminando uma das duas chamadas a `_remover_bordas_tabela()` e reduzindo ainda mais a superfície de uso de oxml.

---

**B6 — `harmonizer.py`: fallback de parsing somava offset duas vezes em múltiplos lotes (rev.17)**
```python
# Cenário que dispara o bug:
#   Lote 1: JSON ok → emendas [E1, E2]; offset atualizado para 2
#   Lote 2: fallback bruto com 2 partes
#
# Antes (bug):
num = offset + len(todas_emendas) + 1
# offset=2, len(todas_emendas)=2 → num=5   (E3 esperado)
# offset=2, len(todas_emendas)=3 → num=6   (E4 esperado)
# Resultado: [1, 2, 5, 6] — buracos afetam votação e subemenda_de
#
# Depois (fix): idx_fb relativo ao lote atual
idx_fb = 0
for parte in partes:
    if parte.strip():
        num = offset + idx_fb + 1    # offset=2, idx_fb=0 → 3; idx_fb=1 → 4
        todas_emendas.append(...)
        idx_fb += 1
# Resultado: [1, 2, 3, 4] ✓
```

---

### 11.3 `app.py` — aba 5: confirmação do relator + invalidação de estado — rev.8

```python
def _invalidar_resultado() -> None:
    """Limpa resultado harmonizado e todo estado derivado da aba 5."""
    st.session_state.resultado_harm = None
    st.session_state.pop('confirmar_sec_2_aba5', None)
    st.session_state.pop('texto_redacao_final', None)

# Chamada na aba 5 (exportação) — passa ementa e autor:
_ementa_doc, _autor_doc = extrair_ementa_autor(st.session_state.get('texto_original', ''))
docx_bytes = exportar_redacao_final_docx(
    texto=texto_editavel, nome_projeto=nome_projeto,
    avisos=res.avisos, erros=res.erros_criticos,
    alertas_absurdos=getattr(res, 'alertas_absurdos', []),
    mapa=res.mapa_renumeracao, log=res.log_alteracoes,
    tipo_redacao=_tipo_rdz_aba5,
    prosseguir_com_alerta_sec_2=_prosseguir_sec_2,
    ementa=_ementa_doc,   # ← NEW rev.16
    autor=_autor_doc,     # ← NEW rev.16
)
```

---

### 11.4 `harmonizer.py` — validação XML obrigatória — rev.12

```python
_TODAS_TAGS      = [
    "TEXTO_HARMONIZADO", "MAPA_RENUMERACAO",
    "AVISOS", "ERROS_CRITICOS", "ALERTAS_ABSURDOS",
    "NOTAS_TECNICAS", "SUGESTOES_NORMATIVAS", "LOG_ALTERACOES",
]
_TAGS_NAO_VAZIAS = {"TEXTO_HARMONIZADO", "LOG_ALTERACOES"}

for _tag in _TODAS_TAGS:
    _m = re.search(rf'<{_tag}>(.*?)</{_tag}>', resp_text, re.DOTALL)
    if not _m:
        _sem_par.append(_tag)
    elif _tag in _TAGS_NAO_VAZIAS and not _m.group(1).strip():
        _conteudo_vazio.append(_tag)

if _sem_par:
    raise ValueError(f"Resposta truncada — par completo ausente: {', '.join(_sem_par)}.")
```

---

### 11.5 `harmonizer.py` — pós-processador P1 (camada Python independente do modelo)

```python
# Caso 1 — Autoreferência circular
refs_art = re.findall(
    r'\b(?:n[oa]s?|d[oa]s?|ao?|conform[ae]?|observad[oa])\s+[Aa]rt\.?\s*(\d+)', corpo
)
if any(r == num_art for r in refs_art):
    alertas.append(f"🔴 Art. {num_art}: autoreferência circular — reabertura (§2º RI)")

# Caso 2 — Condição normativa inoperante
if ref_m.group(1) == par_num:
    alertas.append(f"🔴 §{par_num}º: condição normativa inoperante — reabertura (§2º RI)")

# Caso 3 — Padrões semânticos nos textos dos avisos
_PADROES_ABSURDO_AVISO = re.compile(
    r'referência circular|autoref|artigo anterior.*incompatível'
    r'|condição.*suprimid|§.*não existe mais|§.*foi suprimid'
    r'|artigo anterior.*monitoramento|artigo anterior.*versa\b',
    re.IGNORECASE | re.DOTALL
)
```

---

### 11.6 Resultado dos testes automatizados (verificar.py — 128/129)

```
[1]  IMPORTAÇÕES               ✅ 3/3
[2]  SUFIXO -A                 ✅ 4/4
[3]  P1 CASO 1                 ✅ 2/2
[4]  P1 CASO 2                 ✅ 1/1
[5]  P1 PADRÕES SEMÂNTICOS     ✅ 5/5
[6]  P1 INTEGRAÇÃO             ✅ 3/3
[7]  EXPORTAÇÃO DOCX
  ✅  §2º sem confirmação → RASCUNHO (título, sem sufixo-A, aviso, cor vermelha)
  ✅  §2º com confirmação → REDAÇÃO FINAL (sufixo-A, ALERTA CRÍTICO, OVERRIDE-HUMANO)
  ✅  Sem §2º → REDAÇÃO FINAL normal (título sublinhado)
  ✅  Absurdo cita §2º e reabertura (não §1º/ofício)
  ✅  Seção avisos não diz 'preservados exatamente'
  ✅  TXT rascunho: cabeçalho, reabertura, slug correto    (total: 18 verificações)
[7g] FORMATAÇÃO B7 (rev.18/rev.19/rev.20)               ✅ 7/7
  ✅  Normal.font.name == 'Arial'
  ✅  Normal.font.size == 11pt
  ✅  Apenas 1 tabela no DOCX (assinaturas; ementa não é tabela)
  ✅  Ementa aparece como parágrafo simples
  ✅  Corpo do texto: run.font.name == 'Arial'
  ✅  Heading 2 style: font.name == 'Arial'
  ✅  Heading 2 style: font.size == 11pt
[7e] PARSING                   ✅ 6/6
[8]  ANÁLISE ESTRUTURAL        ✅ 4/4  (inclui 'Art sem ponto B1' — rev.16)
[9]  API KEY                   ❌ 0/1  (esperado — chave ausente localmente)
[10] ARQUIVOS STRESS TEST      ✅ 2/2  (condicional — skipped se arquivos ausentes)
[11] VALIDAÇÃO XML GENERALIZADA ✅ 16/16
[12] HELPER _invalidar_resultado() ✅ 5/5
[13] REGRA A4                  ✅ 11/11
[14] REGRA E2                  ✅ 12/12
[15] SUBEMENDAS (rev.15)       ✅ 23/23
  (inclui P1, P2, P3 confirmados)
[B6] FALLBACK MULTI-LOTE (rev.17) ✅ 2/2
  ✅  Sequência [1,2,3,4] (não [1,2,5,6])
  ✅  Offset após fallback = 4

RESULTADO: 128/129 (único fail = API key ausente — esperado; +3 testes 7h regex marcador rev.23)
```

---

### 11.7 Riscos residuais conhecidos e aceitos

| Risco | Probabilidade | Status | Mitigação |
|---|---|---|---|
| Detector P1 Caso 1 pode ter falso positivo em autorreferência intencional | Muito baixa | Monitorado | P1 é camada de segurança; falso positivo gera alerta, não cancelamento |
| Deduplicação pode fundir dois absurdos no mesmo artigo | Baixa | Monitorado | Modelo é caminho principal; duplicatas protegem, não suprimem |
| Modelo pode classificar absurdo manifesto como ⚠ Aviso | Baixa | Monitorado | P1 escalona independentemente |
| Relator pode confirmar ciência sem ler os alertas | Possível | **Residual** | Interface exige warning→checkbox→2º st.error→log rastreável |
| IA não preenche erros_criticos e P1 não escalona → sai como REDAÇÃO FINAL normal | Baixa (dupla camada) | **Residual** | E2+E3 forçam modelo; P1 cobre estruturais; falha dupla não detectável sem API |
| `extrair_ementa_autor()` pode retornar vazio se PDF não seguir o padrão CMRJ | Baixa | **Residual — aceitável** | Campo ementa fica em branco no DOCX; usuário preenche manualmente no Word |
| `Art\.?` pode capturar "Art " sem número (ex: "Artigo") | Muito baixa | Monitorado | Regex exige `\d+` logo após — "Artigo" falha na sequência "igo" ≠ dígito |
| Stop markers de `ler_pdf()` dependem de strings fixas — PDF com formatação diferente pode passar despercebido | Baixa | Monitorado | Usuário vê o texto extraído na aba 1 e pode editar antes de harmonizar |
| **Paridade local ↔ Cloud** — código que passa localmente pode falhar no deploy por divergência de versão de pacote ou path de API interna | **Média** | **GAP confirmado em produção (B5)** | **Usar apenas API pública de pacotes terceiros no topo do módulo; APIs internas como imports lazy dentro das funções que as usam** |
| Nenhum teste automatizado verifica "módulo carrega limpo em ambiente Linux/Cloud" | Média | **Gap aberto** | A ser investigado: verificar.py poderia incluir `import utils; import app` como smoke test de carregamento |
| **B5 — download DOCX no Cloud com `qn`/`OxmlElement`** — import lazy evita crash na inicialização, e uso de oxml no download também confirmado funcional | Baixa | **✅ Confirmado rev.17 + rev.18** | Confirmado em produção; uso de oxml reduzido (ementa virou `_para()` simples em rev.18) |
| **B6 — fallback de parsing multi-lote** — `offset + len(todas_emendas) + 1` causava buracos na numeração quando lotes anteriores já tinham emendas | **Alta** | **✅ Corrigido rev.17** | Fix: `offset + idx_fb + 1`; 2 novos testes em verificar.py (118/119) |

---

### 11.8 Arquivos de referência CMRJ (modelos e PDF de teste)

Os seguintes arquivos são rastreados no repositório como referência de formatação e testes:

| Arquivo | Tipo | Observação |
|---|---|---|
| `730-A_2026 -- REDAÇÃO FINAL.docx` | Modelo Redação Final | Nome indica 2026 (ano da sessão); conteúdo diz PL nº 730-A/2025 (ano do projeto). **Normal** — projeto protocolado em 2025, Redação Final elaborada em 2026 |
| `273-2025 - REDAÇÃO DO VENCIDO.docx` | Modelo Redação do Vencido | |
| `279-A-2025 - REDAÇÃO DO VENCIDO.docx` | Modelo Redação do Vencido (com sufixo -A) | |
| `REDAÇÃO FINAL PL 1456-A  2025.docx` | Modelo Redação Final (alternativo) | |
| `PLC 55 2025.pdf` | PDF de teste real | Projeto usado no primeiro teste em produção (26/05/2026); contém `Art 14.` sem ponto (bug B1) e stop markers desalinhados (bug B2) |

> **Inconsistência aparente documentada:** o arquivo `730-A_2026` tem 2026 no nome mas 2025 no número do projeto. Isso é correto — projetos da CMRJ são numerados pelo ano de protocolamento; o sufixo do arquivo indica o ano em que a Redação Final foi produzida. Não é um erro.

---

*Versão rev.23 — 26/05/2026 — Sistema de Redações CCJ CMRJ*
