# 🔍 AUDITORIA DO SISTEMA — CCJ CMRJ
### Documento técnico para revisão externa — versão 2026-05-25 **rev.10**

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
| 25/05/2026 | Resultado antigo sobrevivia a mudanças em emendas/votação (importar texto bruto, adicionar emenda manual, editar tipo/alvo, botões de votação individual e em lote) | Rastreabilidade/Consistência | ✅ app.py rev.8 — `_invalidar_resultado()` helper aplicado em todos os 13+ pontos de mutação |
| 25/05/2026 | `extrair("TEXTO_HARMONIZADO", texto_original)` — resposta da IA sem tags retornava silenciosamente o original sem alertas | Falha silenciosa crítica | ✅ harmonizer.py rev.8 — guarda obrigatória: ValueError se `<TEXTO_HARMONIZADO>` ausente; default alterado para `""` |
| 25/05/2026 | Guarda rev.8 verificava só tag de abertura — resposta truncada (sem `</TEXTO_HARMONIZADO>`) passava na guarda mas `extrair()` devolvia `""` silenciosamente | Falha silenciosa crítica (apontada por auditor externo) | ✅ harmonizer.py rev.9 — guarda exige par completo + conteúdo não vazio; tags de alertas (`AVISOS`, `ERROS_CRITICOS`, `ALERTAS_ABSURDOS`, `LOG_ALTERACOES`) também obrigatórias |
| 25/05/2026 | Rev.9 exigia par completo apenas para `TEXTO_HARMONIZADO`; as demais 5 tags ainda checavam só a abertura — truncamento em qualquer delas (ex.: `<AVISOS>` sem `</AVISOS>`) faria `extrair()` devolver `""` silenciosamente, zerando alertas | Falha silenciosa generalizada | ✅ harmonizer.py rev.10 — guarda unificada: `_TODAS_TAGS` (6 tags) exige par completo via regex `<TAG>(.*?)</TAG>`; `_TAGS_NAO_VAZIAS` = {`TEXTO_HARMONIZADO`, `LOG_ALTERACOES`} exige conteúdo não vazio; verificar.py rev.6 — bloco [11] expandido: 14 verificações, truncamento testado tag a tag |

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
| 4 — Modificativa incisos Art. 14 | Incisos III, IV + novo V | Verbatim; pontuação (`;` e `.`) corrigida automaticamente (E1) + LOG; ausência de "; e" → ⚠ aviso apenas (LC 48/2000, não LC 95/1998) |
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
| 5 | Emenda 4 — conjunção "; e" ausente | ⚠ aviso gerado (não auto-corrigido — LC 48/2000 apenas, prática ignora) |
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
Testa (57 verificações locais): importações, sufixo -A, detectores estruturais P1 (casos 1 e 2), padrões semânticos P1 (caso 3), escalador integrado, exportação DOCX em dois modos (§2º sem confirmação → RASCUNHO; §2º com confirmação → REDAÇÃO FINAL + ALERTA CRÍTICO + log OVERRIDE-HUMANO; sem §2º → REDAÇÃO FINAL normal), fundamentação §2º nos absurdos, texto da seção de avisos, **TXT modo rascunho** (cabeçalho de alerta, slug correto, conteúdo de reabertura), parsing de emendas supressivas e offset em múltiplos lotes, análise estrutural, disponibilidade de API e arquivos de teste.

### Verificação completa (com harmonização real — custo ~$0,50)
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python verificar.py --com-api
```
Executa adicionalmente: harmonização completa do PLC 17/2026 com as 10 emendas; verifica estrutura (18 arts, 5 anexos), preservação verbatim, ≥3 absurdos §2º, E1 auto-correções no texto e LOG, aviso de "; e", ausência de mérito/CA em AVISOS. Salva resultado em `resultado_verificar.txt`.

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

---

## 11. Extratos de código para verificação (rev.10)

Esta seção contém os trechos mais críticos do código atual para facilitar a auditoria. O código completo está em https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj

---

### 11.1 `utils.py` — lógica de dois modos (`exportar_redacao_final_docx`) — rev.6

```python
def exportar_redacao_final_docx(
    texto, nome_projeto, avisos, erros,
    alertas_absurdos=None, mapa=None, log=None,
    tipo_redacao="Redação Final",
    prosseguir_com_alerta_sec_2: bool = False,
) -> bytes:
    _alertas_norm = alertas_absurdos or []
    _erros_norm   = erros or []
    tem_sec_2     = bool(_erros_norm or _alertas_norm)

    eh_rascunho = tem_sec_2 and not prosseguir_com_alerta_sec_2

    if eh_rascunho:
        titulo_doc = "RASCUNHO DE TRABALHO — NÃO É REDAÇÃO FINAL"
    else:
        titulo_doc = tipo_redacao.upper()

    if eh_rascunho:
        run_titulo.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)   # vermelho
        r_alerta.add_run("⚠ RASCUNHO — existem alertas de §2º ... Confirme ciência na aba 5.")
    elif tem_sec_2:
        r_alerta.add_run("⚠ ALERTA CRÍTICO PENDENTE — ART. 250, §2º RI — ...")

    # Sufixo -A: apenas no documento formal (não no rascunho)
    nome_doc = nome_projeto if eh_rascunho else _aplicar_sufixo_a(nome_projeto)

    # TXT também respeita o modo (cabeçalho de alerta + slug rascunho_trabalho_*.txt)
    # — feito em app.py antes de chamar esta função

    # Log do DOCX: registra o override humano com data
    log_final = list(log or [])
    if tem_sec_2 and prosseguir_com_alerta_sec_2:
        log_final.append(
            f"OVERRIDE-HUMANO / Art. 250, §2º RI — Relator tomou ciência dos alertas "
            f"({len(_erros_norm)} erro(s), {len(_alertas_norm)} absurdo(s)) "
            f"e optou por prosseguir em {datetime.date.today():%d/%m/%Y}."
        )
```

---

### 11.2 `app.py` — aba 5: confirmação do relator + invalidação de estado — rev.8

```python
# ── Helper: qualquer mutação invalida o resultado anterior ──
def _invalidar_resultado() -> None:
    """Limpa resultado harmonizado e todo estado derivado da aba 5.
    Chamado em: nova harmonização, texto alterado, emendas re-parseadas,
    importar texto bruto, adicionar emenda manual, editar tipo/alvo,
    votação individual (Aprov./Rejeit./Aprovada/Prejudicada),
    votação em lote (Todas Aprovadas/Rejeitadas/Limpar), remover todas,
    limpar status, carregar sessão.
    """
    st.session_state.resultado_harm = None
    st.session_state.pop('confirmar_sec_2_aba5', None)
    st.session_state.pop('texto_redacao_final', None)

# ── Aba 5: confirmação ──
_alertas_aba5     = getattr(res, 'alertas_absurdos', [])
_tem_sec_2        = bool(res.erros_criticos or _alertas_aba5)
_prosseguir_sec_2 = False   # default conservador

if _tem_sec_2:
    st.warning("⚠️ ... RASCUNHO DE TRABALHO por padrão ...")
    _prosseguir_sec_2 = st.checkbox(
        "✅ Confirmo ciência dos alertas críticos (§2º RI) e desejo exportar como Redação Final",
        value=False,
        key="confirmar_sec_2_aba5",   # resetado por _invalidar_resultado() em nova harm.
    )
    if _prosseguir_sec_2:
        st.error("🔴 ALERTA CRÍTICO PENDENTE inscrito no cabeçalho e no log.")

_eh_rascunho_aba5 = _tem_sec_2 and not _prosseguir_sec_2
_slug_doc = "rascunho_trabalho" if _eh_rascunho_aba5 else _slug_tipo

# TXT: cabeçalho de alerta no modo rascunho
if _eh_rascunho_aba5:
    _txt_content = (CABECALHO_RASCUNHO + texto_editavel).encode('utf-8')
else:
    _txt_content = texto_editavel.encode('utf-8')

# DOCX: passa o modo para utils.py
docx_bytes = exportar_redacao_final_docx(
    ..., prosseguir_com_alerta_sec_2=_prosseguir_sec_2,
)
```

---

### 11.3 `harmonizer.py` — validação XML obrigatória — rev.10

```python
# Guarda unificada: todas as 6 tags esperadas devem ter par completo.
# Verificar só a tag de abertura não protege contra truncamento:
# resposta cortada após <TAG> faria extrair() devolver "" silenciosamente.
# TEXTO_HARMONIZADO e LOG_ALTERACOES também exigem conteúdo não vazio.
_TODAS_TAGS      = [
    "TEXTO_HARMONIZADO", "MAPA_RENUMERACAO",
    "AVISOS", "ERROS_CRITICOS", "ALERTAS_ABSURDOS", "LOG_ALTERACOES",
]
_TAGS_NAO_VAZIAS = {"TEXTO_HARMONIZADO", "LOG_ALTERACOES"}

_sem_par:        list[str] = []
_conteudo_vazio: list[str] = []

for _tag in _TODAS_TAGS:
    _m = re.search(rf'<{_tag}>(.*?)</{_tag}>', resp_text, re.DOTALL)
    if not _m:
        _sem_par.append(_tag)
    elif _tag in _TAGS_NAO_VAZIAS and not _m.group(1).strip():
        _conteudo_vazio.append(_tag)

if _sem_par:
    raise ValueError(
        f"Resposta da IA truncada — par completo ausente: {', '.join(_sem_par)}. "
        "Tente novamente; se o erro persistir, reduza o número de emendas por lote."
    )
if _conteudo_vazio:
    raise ValueError(
        f"Resposta da IA inválida — conteúdo obrigatório vazio em: "
        f"{', '.join(_conteudo_vazio)}. Tente novamente."
    )

texto_harm = re.search(
    r'<TEXTO_HARMONIZADO>(.*?)</TEXTO_HARMONIZADO>', resp_text, re.DOTALL
).group(1).strip()   # par validado acima — .group(1) seguro
```

---

### 11.4 `harmonizer.py` — regras do prompt (E1.5, E2, E3) — trecho literal

```
E1.5. PROIBIÇÃO ABSOLUTA — ANÁLISES DE MÉRITO NOS AVISOS:
    NUNCA inclua em AVISOS qualquer observação sobre:
    — Coeficiente de aproveitamento (CA): comparações, proporções, relações entre setores
    — Gabaritos, alturas, número de pavimentos: análises de adequação
    — Consistência dos parâmetros urbanísticos aprovados pelo Plenário
    — Qualquer julgamento sobre se os valores fazem sentido técnico ou urbanístico
    Esses são assuntos de MÉRITO — soberania exclusiva do Plenário — totalmente fora da
    competência da CCJ na Redação Final. Colocá-los em AVISOS contamina o documento.
    Se perceber algo desse tipo, OMITA. Não registre. Não "avise com ressalva".

E2. ERROS CRÍTICOS — não tente resolver; a providência regimental indicada
    é a reabertura da discussão (art. 250, §2º RI):
    [contradição direta entre emendas, impossibilidade de cumprimento simultâneo, etc.]

E3. ALERTA DE ABSURDO MANIFESTO (art. 250, §2º RI — providência regimental
    indicada é a reabertura):
    [4 casos: autoreferência circular, condição inoperante, remissão incompatível,
     referência exclusiva a dispositivo suprimido]
    Em AMBOS (E2 e E3): a providência regimental indicada é a reabertura da discussão (§2º RI).
```

---

### 11.5 `harmonizer.py` — pós-processador P1 (camada Python independente do modelo)

```python
# Caso 1 — Autoreferência circular (regex estrutural sobre blocos de artigo)
refs_art = re.findall(
    r'\b(?:n[oa]s?|d[oa]s?|ao?|conform[ae]?|observad[oa])\s+[Aa]rt\.?\s*(\d+)',
    corpo
)
if any(r == num_art for r in refs_art):
    alertas.append(f"🔴 Art. {num_art}: autoreferência circular — reabertura (§2º RI)")

# Caso 2 — Condição normativa inoperante (§N remete a §N deste artigo)
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

### 11.6 Resultado dos testes automatizados (verificar.py rev.6 — 64/65)

```
[1]  IMPORTAÇÕES               ✅ 3/3
[2]  SUFIXO -A                 ✅ 4/4
[3]  P1 CASO 1                 ✅ 2/2
[4]  P1 CASO 2                 ✅ 1/1
[5]  P1 PADRÕES SEMÂNTICOS     ✅ 5/5
[6]  P1 INTEGRAÇÃO             ✅ 3/3
[7]  EXPORTAÇÃO DOCX
  ✅  §2º sem confirmação → RASCUNHO (título, sem sufixo-A, aviso)
  ✅  §2º com confirmação → REDAÇÃO FINAL (sufixo-A, ALERTA CRÍTICO, OVERRIDE-HUMANO)
  ✅  Sem §2º → REDAÇÃO FINAL normal
  ✅  Absurdo cita §2º e reabertura (não §1º/ofício)
  ✅  Seção avisos não diz 'preservados exatamente'
  ✅  TXT rascunho: cabeçalho, reabertura, slug correto    (18 verificações)
[7e] PARSING                   ✅ 4/4
[8]  ANÁLISE ESTRUTURAL        ✅ 3/3
[9]  API KEY                   ❌ 0/1  (esperado — chave ausente em ambiente local)
[10] ARQUIVOS STRESS TEST      ✅ 2/2
[11] VALIDAÇÃO XML GENERALIZADA (rev.10 — 14 verificações)
  ✅  _TODAS_TAGS cobre 6 tags (incl. MAPA_RENUMERACAO e LOG_ALTERACOES)
  ✅  Truncamento detectado por _sem_par (par abertura+fechamento)
  ✅  _TAGS_NAO_VAZIAS + _conteudo_vazio (conteúdo obrigatório não vazio)
  ✅  TEXTO_HARMONIZADO: sem par → None; truncada → None; válida → group(1)
  ✅  .group(1).strip() sem fallback silencioso
  ✅  MAPA_RENUMERACAO: truncada → None
  ✅  AVISOS: truncada → None
  ✅  ERROS_CRITICOS: truncada → None
  ✅  ALERTAS_ABSURDOS: truncada → None
  ✅  LOG_ALTERACOES: truncada → None
  ✅  LOG_ALTERACOES em _TAGS_NAO_VAZIAS (conteúdo obrigatório)
  ✅  Resposta completa válida — todos os 6 pares detectados
[12] HELPER _invalidar_resultado()
  ✅  Definido; ≥10 chamadas; v_apr; importar; adicionar manual               (5 verificações)

RESULTADO: 64/65 (único fail = API key ausente — esperado)
```

---

### 11.6 Riscos residuais conhecidos e aceitos

| Risco | Probabilidade | Status | Mitigação |
|---|---|---|---|
| Detector P1 Caso 1 pode ter falso positivo em autorreferência intencional | Muito baixa (raramente existe) | Monitorado | O P1 é camada de segurança, não bloqueio; falso positivo gera alerta, não cancelamento |
| Deduplicação pode fundir dois absurdos no mesmo artigo se modelo gerar texto similar | Baixa | Monitorado | O modelo é o caminho principal; duplicatas protegem, não suprimem |
| Modelo pode classificar absurdo manifesto como ⚠ Aviso | Baixa após E3 rev.3 + P1 | Monitorado | P1 escalona independentemente da classificação do modelo |
| Relator pode confirmar ciência sem ler os alertas (checkbox impulsivo) | Possível | **Residual** | Interface exige: warning → checkbox → 2º st.error → log OVERRIDE-HUMANO rastreável; sem fricção de senha deliberadamente (usabilidade) |
| IA não preenche erros_criticos/alertas_absurdos e P1 não escalona → sai como REDAÇÃO FINAL normal | Baixa (dupla camada) | **Residual** | E2/E3 forçam o modelo; P1 cobre casos estruturais independentemente; se ambos falham, é falha de prompt não detectável sem API |
| Resposta da IA truncada (sem `</TEXTO_HARMONIZADO>`) → passava na guarda rev.8 | Baixa | **✅ Corrigido (rev.9)** | Guarda exige par completo + conteúdo não vazio; tags de alertas obrigatórias também verificadas |
| Truncamento em qualquer das outras 5 tags (`MAPA_RENUMERACAO`, `AVISOS`, `ERROS_CRITICOS`, `ALERTAS_ABSURDOS`, `LOG_ALTERACOES`) → `extrair()` devolveria `""` silenciosamente | Baixa | **✅ Corrigido (rev.10)** | `_TODAS_TAGS` + `_sem_par`: todas as 6 tags verificam par completo; `_TAGS_NAO_VAZIAS` exige conteúdo não vazio em TEXTO_HARMONIZADO e LOG_ALTERACOES |
| Resultado harmonizado sobrevivia a mudanças pós-harmonização | Possível em sessão longa | **✅ Corrigido (rev.8)** | `_invalidar_resultado()` aplicado em todos os pontos: votação, importação, edição, remoção de emendas |

---

*Versão rev.10 — 25/05/2026 — Sistema de Redações CCJ CMRJ*
