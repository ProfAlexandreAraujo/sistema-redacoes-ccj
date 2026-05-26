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

## Mudanças implementadas nesta sessão (para auditoria)

### 1. Regra A4 — "acrescente-se onde couber" (harmonizer.py)

**Problema identificado:** emendas aditivas que não especificam o dispositivo de destino
(ex: "acrescente-se onde couber o seguinte artigo...") não tinham tratamento explícito.
O modelo poderia inserir silenciosamente sem registrar ou, pior, recusar aplicar.

**Solução implementada:** adicionada a regra A4 ao prompt de harmonização:

```
A4. EMENDAS ADITIVAS SEM ALVO DEFINIDO — "acrescente-se onde couber"
    Quando uma emenda aditiva, substitutiva ou de qualquer tipo não especificar o dispositivo
    exato de destino (ex: "acrescente-se onde couber", "inclua-se no local adequado",
    "onde cabível", ou quando o alvo estiver simplesmente omisso):

    a) POSICIONAMENTO — identifique o lugar mais coerente tematicamente no texto:
       — Afinidade de matéria: insira próximo a artigos que tratam do mesmo tema
       — Sequência lógica: respeite a progressão normativa do capítulo ou seção
       — Nunca crie "ilhas" temáticas: não insira artigo sobre tema X no meio de tema Y
       — Em caso de empate entre dois locais igualmente coerentes, prefira o final
         do capítulo temático correspondente

    b) OBRIGATÓRIO — registrar no LOG_ALTERACOES:
       "A4 / Emenda N: inserida após Art. Xº — [motivo breve da escolha] (alvo não especificado na emenda)"

    c) OBRIGATÓRIO — gerar aviso em AVISOS:
       "⚠ Emenda N / alvo não especificado: inserida após Art. Xº por coerência temática
        com [tema]. Posicionamento definido pela CCJ — alvo não especificado na emenda original."

    NUNCA insira silenciosamente sem AVISO e sem LOG.
    NUNCA recuse aplicar a emenda por ausência de alvo — posicionar é responsabilidade da CCJ.
```

---

### 2. Tag NOTAS_TECNICAS — separação de mérito e forma (harmonizer.py + app.py)

**Problema identificado:** o modelo às vezes colocava em `AVISOS` observações sobre
coeficiente de aproveitamento (CA), gabaritos e parâmetros urbanísticos — que são matéria
de **mérito**, fora da competência da CCJ na Redação Final.

**Solução implementada:**
- Nova tag `<NOTAS_TECNICAS>` adicionada ao formato XML de saída
- Regra E1.5 no prompt proíbe expressamente colocar análises de mérito em AVISOS:

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

- `NOTAS_TECNICAS` aparecem na interface como expander colapsável com disclaimer:
  *"Não são avisos formais da CCJ e não constam no documento exportado."*
- `NOTAS_TECNICAS` **não são passadas** para `exportar_redacao_final_docx()`

---

### 3. Correção de bug — skip set incompleto (harmonizer.py)

**Bug:** a função `parse_linhas()` filtrava strings como `"Nenhum aviso."` e `"Nenhum."`,
mas não filtrava `"Nenhuma nota técnica."` — frase que o modelo escreve quando não há
notas. Resultado: o expander de notas técnicas aparecia com "1 nota técnica" cujo conteúdo
era "Nenhuma nota técnica." — falso positivo visual.

**Correção:**
```python
# Antes:
skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.", "Sem renumeração necessária."}

# Depois:
skip = {"Nenhum aviso.", "Nenhum erro crítico.", "Nenhum.", "Sem renumeração necessária.", "Nenhuma nota técnica."}
```

---

### 4. Atualização do verificar.py (rev.8)

O arquivo de testes foi atualizado:
- Seção 11: `_TODAS_TAGS` agora valida **7 tags** (incluindo `NOTAS_TECNICAS`)
- `_OUTRAS_TAGS` para truncamento inclui `NOTAS_TECNICAS`
- Resposta de teste completa `_resp_completa` inclui tag `NOTAS_TECNICAS`
- Descrição "6 pares" → "7 pares"
- Nova **seção [13]**: 6 testes estruturais (sem API) para a regra A4:
  - A4 presente no prompt
  - "onde couber" no prompt
  - Formato `"A4 / Emenda"` no LOG
  - "alvo não especificado" no AVISO
  - Proibição de inserção silenciosa
  - Proibição de recusar aplicar

**Resultado atual: 73/74 verificações passam** (1 falha esperada: chave API não local)

---

## Arquitetura de proteções já existentes (contexto para a auditoria)

Para você entender o que já existe e não sugerir o que já foi feito:

| Proteção | Onde | O que faz |
|---|---|---|
| Preservação verbatim (A1) | Prompt | Emenda aprovada nunca é alterada em conteúdo |
| Referências cruzadas (A2) | Prompt | Única alteração automática de conteúdo permitida |
| Renumeração (B1–B5) | Prompt | LC 95/98 + LC 48/2000 |
| E1 — correções linguísticas | Prompt | Concordância, caixa, pontuação — registradas no LOG |
| E1.5 — sem mérito em AVISOS | Prompt | Mérito vai para NOTAS_TECNICAS |
| A4 — alvo omisso | Prompt | Posicionamento temático com AVISO + LOG (novo) |
| Detecção estrutural absurdos | Python | Circular, inoperante — independe do modelo |
| Escalada de §1º para §2º | Python | Padrões semânticos nos avisos |
| Validação XML | Python | Par completo de todas as 7 tags ou ValueError |
| Rascunho de trabalho | Python + App | Se há §2º, DOCX sai como rascunho até relator confirmar |
| `_invalidar_resultado()` | App | Qualquer mudança limpa resultado anterior |
| Skip set completo | Python | "Nenhuma nota técnica." não aparece como item falso |

---

## Perguntas para sua auditoria

1. **A regra A4 está bem formulada?**
   - Os critérios de posicionamento (afinidade temática, sequência lógica, sem "ilhas") são suficientes para o modelo tomar uma decisão razoável?
   - O AVISO gerado é informativo o suficiente sem ser redundante?
   - Há alguma situação de "acrescente-se onde couber" que a regra A4 não cobre adequadamente?

2. **A separação AVISOS / NOTAS_TECNICAS é robusta?**
   - A regra E1.5 com o auto-teste ("Este aviso é sobre um erro de PORTUGUÊS ou TÉCNICA REDACIONAL FORMAL?") é suficiente para o modelo não "vazar" mérito nos AVISOS?
   - Há risco de o modelo colocar algo relevante em NOTAS_TECNICAS que deveria estar em AVISOS?

3. **Há algo que deveria ter sido implementado e não foi?**
   - Considerando o fluxo completo (upload → parsing → votação → harmonização → exportação), há algum ponto cego evidente?

4. **O prompt como um todo tem riscos de regressão?**
   - Com as novas regras A4 e E1.5 adicionadas, há risco de conflito com regras já existentes (especialmente A1 — preservação verbatim)?

5. **Sugestões livres** — o que você mudaria ou acrescentaria?

---

## Nota sobre o contexto de uso

- O relator é também o assessor que opera o sistema — não há separação de papéis.
- Projetos típicos: PLCs de zoneamento urbano (30–50 artigos, 10–180 emendas).
- O modelo usado é `claude-sonnet-4-6` com `max_tokens=60000`.
- A chave API fica nos Secrets do Streamlit Cloud — não há chave local em produção.
- O app está em: https://ccj-redacoes.streamlit.app
