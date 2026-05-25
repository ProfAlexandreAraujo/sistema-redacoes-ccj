# 🔍 AUDITORIA DO SISTEMA — CCJ CMRJ
### Documento técnico para revisão externa — versão atualizada 2026-05-25

---

## 1. Contexto e propósito

Este sistema auxilia a **Comissão de Constituição, Justiça e Redação (CCJ)** da Câmara Municipal do Rio de Janeiro a elaborar a **Redação Final** de projetos de lei aprovados com emendas (art. 250, Resolução nº 1.673/2025 — Regimento Interno).

**Caso real:** PLC 92/2025 (AEIU Praça XI Maravilha) — 37 artigos, 6 Anexos (mapas, tabelas de parâmetros urbanísticos, coordenadas UTM). Sessão com potencial de 80–180 emendas.

**Constraint absoluta e inviolável:**  
> *"Eu não posso mexer no teor da emenda. Não posso fazer isso."*  
O texto aprovado pelo Plenário é soberano. O sistema só pode: (a) atualizar referências cruzadas decorrentes de renumeração e (b) corrigir erros gramaticais/ortográficos objetivos, desde que registre cada correção explicitamente.

---

## 2. Normas legislativas que o sistema deve respeitar

| Norma | O que rege |
|---|---|
| **LC 95/1998 (federal)** | Técnica de elaboração de normas: estrutura, artigos, renumeração |
| **Decreto 12.002/2024** | Regulamenta LC 95/1998 com regras detalhadas de redação |
| **LC Municipal 48/2000 RJ** | Técnica legislativa específica da CMRJ (pontução, incisos, alíneas) |
| **LC Municipal 51/2001 RJ** | Complementa LC 48/2000 |
| **Res. 1.673/2025 (RI), art. 250** | Competência da CCJ, níveis de intervenção, quando reabrir discussão |

---

## 3. Três níveis de alerta do sistema

### 🔴 Absurdo Manifesto (art. 250 §1º RI — intervenção obrigatória da CCJ)
Texto tecnicamente ininteligível por razão **exclusivamente formal**.  
Exemplo: dispositivo que remete a artigo integralmente suprimido por outra emenda.  
→ O texto é preservado verbatim + marcador inline `[[⚠️ CCJ: DISPOSITIVO ININTELIGÍVEL — ver seção ABSURDOS MANIFESTOS]]` inserido no corpo do texto.

### 🚨 Erro Crítico (art. 250 §2º RI — CCJ deve propor reabertura)
Duas emendas aprovadas **contradizem-se diretamente** sobre o mesmo dispositivo, ou uma torna a outra de cumprimento impossível.  
→ O sistema sinaliza e recomenda reabertura. Não resolve sozinho.

### ⚠️ Aviso Redacional (art. 250 §1º RI — corrigível por ofício)
Problemas de pontuação, concordância, técnica legislativa — que não comprometem o sentido jurídico.  
→ Apontados para decisão do relator.

---

## 4. Regras do prompt de IA (estado atual após correções de 25/05/2026)

### Bloco A — Regras absolutas

**A1 — Preservação verbatim (REGRA CRÍTICA — reforçada na última atualização):**
```
Ao incorporar o texto de emenda aprovada, copie-o LITERALMENTE — cada palavra,
cada cláusula, cada vírgula — EXATAMENTE como consta no texto aprovado pelo Plenário.
MESMO QUE o texto aprovado:
  · contenha referência a dispositivo suprimido por outra emenda
  · crie referência circular, condição pendente ou absurdo manifesto
  · contenha cláusula que pareça redundante, problemática ou desnecessária
NUNCA remova, NUNCA parafraseie, NUNCA simplifique, NUNCA "conserte" nenhuma parte.
→ Se o texto aprovado cria absurdo, COPIE-O VERBATIM e registre em ALERTAS_ABSURDOS.
→ A supressão de QUALQUER cláusula do texto aprovado é alteração de teor vedada.
```

**A2** — Referências cruzadas: única alteração automática permitida (atualizar quando artigo muda de número por renumeração).

**A3** — Anexos: preservação integral; nunca renumerar nem alterar sem emenda expressa.

### Bloco E — Avisos (atualizado na última correção)

**E1a — Correções automáticas permitidas:**  
Erros objetivos de ortografia/concordância que não alteram sentido jurídico.  
Registro obrigatório: `✏️ CORRIGIDO AUTOMATICAMENTE — Emenda N / Art. Xº: [original] → [corrigido]`  
Proibido escrever "preservado como aprovado" para texto que foi alterado.

**E1b — Aponte sem corrigir:**  
Pontuação (Bloco C), referências vagas, técnica redacional imprópria — registrar como aviso.

---

## 5. Correções aplicadas em 25/05/2026 (antes da sessão real)

Baseadas em auditoria externa identificando dois bugs reais:

### Bug 1 — CRÍTICO (corrigido): AI alterava teor de emenda aprovada
**Cenário reproduzido:** Emenda 5 (Modificativa) continha a cláusula:  
`"Atendida a condição prevista no § 1º deste artigo, ficam isentos de contrapartida..."`  
O §1º do mesmo artigo havia sido suprimido por outra emenda (Emenda 3).  
**Comportamento errado:** A IA removeu a cláusula condicional, convertendo isenção condicionada em incondicional — **alteração de teor**.  
**Correção aplicada:** Regra A1 reforçada com instrução verbatim explícita. Sistema deve copiar o absurdo e registrá-lo em ALERTAS_ABSURDOS.

### Bug 2 — MÉDIO (corrigido): Correção sem transparência
**Comportamento errado:** Sistema corrigiu `"serão aplicada"` → `"serão aplicadas"` mas registrou nos avisos "preservado como aprovado".  
**Correção aplicada:** E1 reformulado: correções gramaticais OK, mas aviso deve dizer `CORRIGIDO AUTOMATICAMENTE: [original] → [corrigido]`. Nunca usar "preservado" para texto que foi alterado.

---

## 6. Cenário de stress test — 10 emendas estressantes

Para testar o sistema, use o **texto do PLC 92/2025** (arquivo `PLC_92_2025_limpo.txt`, 49.431 caracteres, 37 artigos, 6 Anexos) com as emendas abaixo. Todas devem ser marcadas como **APROVADAS**.

```
EMENDA Nº 1 — SUPRESSIVA
Autor: Vereador João Silva — PDM

Suprima-se o Art. 5º do PLC 92/2025.

Justificativa: A subdivisão em setores já está contemplada no Anexo II, tornando o Art. 5º redundante.

────────────────────────────────────────

EMENDA Nº 2 — MODIFICATIVA
Autora: Vereadora Ana Costa — MRU

O § 1º do Art. 6º passa a vigorar com a seguinte redação:
"§ 1º O gabarito máximo de que trata o caput poderá ser acrescido de dois pavimentos mediante contrapartida ao Fundo de Desenvolvimento Urbano, conforme regulamentação do Poder Executivo."

Justificativa: Amplia a flexibilidade dos parâmetros de ocupação para incentivar investimentos na AEIU.

────────────────────────────────────────

EMENDA Nº 3 — SUPRESSIVA
Autor: Vereador Pedro Menezes — AR

Suprima-se o § 1º do Art. 8º do PLC 92/2025.

Justificativa: O parágrafo único cria condicionamento desnecessário.

────────────────────────────────────────

EMENDA Nº 4 — MODIFICATIVA
Autor: Vereador Carlos Lima — PDM
[ERRO DE CONCORDÂNCIA INTENCIONAL PARA TESTE]

O Art. 9º passa a vigorar com a seguinte redação:
"Art. 9º As obras de infraestrutura viária indicadas no Anexo I desta Lei Complementar serão executada pelo Poder Público Municipal no prazo de cinco anos contados da publicação desta lei."

Justificativa: Inclui prazo de execução para garantir efetividade.

────────────────────────────────────────

EMENDA Nº 5 — MODIFICATIVA
Autora: Vereadora Márcia Ferreira — MRU
[ABSURDO MANIFESTO INTENCIONAL: referencia §1º suprimido pela Emenda 3]

O § 2º do Art. 8º passa a vigorar com a seguinte redação:
"§ 2º Atendida a condição prevista no § 1º deste artigo, ficam dispensadas de contrapartida ao Fundo de Desenvolvimento Urbano as edificações com área total construída inferior a trezentos metros quadrados."

Justificativa: Desonera pequenos empreendimentos.

────────────────────────────────────────

EMENDA Nº 6 — ADITIVA
Autor: Vereador Roberto Nunes — AR

Acrescente-se ao Art. 14 o seguinte inciso V:
"V — execução de obras de infraestrutura viária indicadas no Anexo I desta Lei Complementar."

Justificativa: Inclui obrigação de contrapartida em obras viárias.

────────────────────────────────────────

EMENDA Nº 7 — SUPRESSIVA
Autora: Vereadora Sandra Lima — PDM
[CONFLITO COM EMENDA 6: ambas afetam Art. 14 — uma adiciona inciso V, outra suprime Art. 14 inteiro]

Suprima-se o Art. 14 do PLC 92/2025.

Justificativa: O art. 14 duplica contrapartidas já previstas no art. 12.

────────────────────────────────────────

EMENDA Nº 8 — MODIFICATIVA
Autor: Vereador Fábio Carvalho — MRU

O Anexo III (Quadro de Parâmetros Urbanísticos) passa a vigorar com a seguinte alteração na linha referente à Subzona AE-1:
O coeficiente de aproveitamento máximo passa de 4,0 para 5,0.

Justificativa: Ajuste para viabilizar projetos de uso misto de maior porte.

────────────────────────────────────────

EMENDA Nº 9 — MODIFICATIVA
Autor: Vereador Gustavo Pinto — AR
[ERRO DE TÉCNICA LEGISLATIVA: inciso começa com letra maiúscula — intencional para teste]

O Art. 17 passa a vigorar acrescido do seguinte inciso IV:
"IV — Apresentação de Estudo de Impacto de Vizinhança (EIV) para empreendimentos com área total construída superior a dois mil metros quadrados."

Justificativa: Exige EIV para grandes empreendimentos no perímetro da AEIU.

────────────────────────────────────────

EMENDA Nº 10 — SUBSTITUTIVA (EMENDA DE REDAÇÃO)
Autora: Vereadora Camila Torres — PDM

O Art. 20 passa a vigorar com a seguinte redação integral:
"Art. 20. O Poder Executivo regulamentará esta Lei Complementar no prazo de noventa dias, contados da data de sua publicação, podendo editar normas complementares para sua aplicação."

Justificativa: Melhora a redação do artigo, tornando-o mais preciso e em conformidade com a técnica legislativa.
```

---

## 7. O que verificar no resultado do stress test

### ✅ Comportamentos CORRETOS esperados

| # | Verificação | Resultado esperado |
|---|---|---|
| 1 | **Emenda 1** (supressão Art. 5º) | Art. 5º removido; artigos seguintes renumerados em sequência; todas as referências internas ao Art. 5º atualizadas |
| 2 | **Emenda 2** (modifica §1º Art. 6º) | Texto novo incorporado verbatim |
| 3 | **Emenda 3** (suprime §1º Art. 8º) | §1º removido; se havia §2º, converte para Parágrafo único |
| 4 | **Emenda 4** (erro de concordância) | Texto incorporado COM CORREÇÃO `serão executada → serão executadas` + aviso `✏️ CORRIGIDO AUTOMATICAMENTE` |
| 5 | **Emenda 5** (absurdo manifesto) | Texto copiado VERBATIM com "§1º deste artigo" intacto + marcador `[[⚠️ CCJ: DISPOSITIVO ININTELIGÍVEL]]` no texto + alerta 🔴 na seção ALERTAS_ABSURDOS |
| 6 | **Emenda 6 + 7** (conflito: adiciona e suprime Art. 14) | Classificado como 🚨 ERRO CRÍTICO; sistema não decide qual prevalece; recomenda reabertura |
| 7 | **Emenda 8** (modifica Anexo III) | Alteração do coeficiente aplicada no Anexo III; outros Anexos intocados |
| 8 | **Emenda 9** (inciso com maiúscula) | Texto incorporado verbatim (não altera teor) + aviso `⚠ inciso inicia com letra maiúscula` |
| 9 | **Emenda 10** (substitutiva Art. 20) | Texto novo incorporado verbatim |
| 10 | **Renumeração geral** | Mapa de renumeração presente; referências cruzadas internas consistentes |

### ❌ Comportamentos PROIBIDOS (falha crítica se ocorrer)

| Comportamento proibido | Por quê |
|---|---|
| Emenda 5: remoção de "Atendida a condição prevista no §1º deste artigo" | Alteração de teor — converte isenção condicionada em incondicional |
| Emenda 4: corrigi sem registrar aviso CORRIGIDO | Falta de transparência — usuário não sabe o que foi mudado |
| Emenda 9: corrigir a letra maiúscula no inciso | Não é erro de gramática objetiva — é decisão de estilo do autor |
| Emendas 6 e 7: escolher qual prevalece | Conflito de emendas aprovadas só o Plenário resolve |
| Qualquer Anexo alterado sem emenda expressa | Preservação integral obrigatória |

---

## 8. Comando para diagnóstico no terminal

```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes && python teste_real.py
```

O script `teste_real.py` executa:
1. Carrega o texto do PLC 92/2025 (real, 49.431 caracteres)
2. Analisa a estrutura (artigos, parágrafos, incisos, alíneas, anexos)
3. Verifica a chave API
4. Testa parsing de 3 emendas sintéticas
5. Testa harmonização com trecho real do PLC
6. Salva resultado em `resultado_teste_real.txt`

---

## 9. URLs e acesso

| Ambiente | URL | Status |
|---|---|---|
| **Streamlit Cloud** *(principal)* | https://ccj-redacoes.streamlit.app | ✅ Sempre disponível |
| **GitHub** *(código-fonte)* | https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj | ✅ Público |
| Local | http://localhost:8501 | Só no computador com `iniciar.bat` |

---

## 10. Estrutura dos arquivos

```
sistema_redacoes/
├── app.py              → Interface Streamlit — 5 tabs + sidebar
│                         Tab 1: Carrega PLC (.docx, .txt ou .pdf)
│                         Tab 2: Recebe e parseia emendas com IA
│                         Tab 3: Controle de votação (aprovada/rejeitada/prejudicada)
│                         Tab 4: Harmonização com IA + exibição dos 3 níveis de alerta
│                         Tab 5: Redação final + exportação .docx/.txt
├── harmonizer.py       → Motor de IA (Claude claude-sonnet-4-6 via streaming)
│                         parsear_emendas_com_ia() — identifica e estrutura emendas
│                         harmonizar_texto() — aplica emendas, renumera, detecta problemas
├── utils.py            → Leitura: ler_docx(), ler_txt(), ler_pdf()
│                         Análise: analisar_estrutura()
│                         Persistência: salvar_sessao(), carregar_sessao()
│                         Exportação: exportar_redacao_final_docx()
├── teste_real.py       → Script de diagnóstico em terminal
├── requirements.txt    → streamlit, anthropic, python-docx, pdfplumber
├── iniciar.bat         → Inicia Streamlit localmente
└── .streamlit/
    └── secrets.toml    → ANTHROPIC_API_KEY (não commitado no GitHub)
```

---

## 11. Parâmetros técnicos da IA

| Parâmetro | Valor | Motivo |
|---|---|---|
| Modelo | `claude-sonnet-4-6` | Equilíbrio custo/performance para textos jurídicos longos |
| max_tokens (harmonização) | 60.000 | Suporta PLCs grandes + 180 emendas (teto real do modelo: 64k) |
| max_tokens (parsing) | 20.000 | Suficiente para extração de 180 emendas em JSON |
| Modo de chamada | Streaming obrigatório | Evita timeout da API em operações >10 min |
| Custo estimado (100 emendas + PLC 50k chars) | ~$0,40–$0,60 | Sonnet: $3/M input, $15/M output |

---

*Gerado em 25/05/2026 — Sistema de Redações CCJ CMRJ*
