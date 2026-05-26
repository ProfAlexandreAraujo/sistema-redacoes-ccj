# Prompt de Auditoria Externa — Sistema de Redações CCJ CMRJ
### Versão rev.18 — 26/05/2026

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
| **Conflito** | **Duas subemendas aprovadas para o mesmo pai** | **`erros_criticos` (§2º)** → rascunho; nenhuma substituição automática |
| **P1 — Auto-referência** | **`subemenda_de == numero` próprio** | **`erros_criticos` (§2º)**; emenda excluída da lista |
| **P2 — Pai inexistente** | **Pai não consta em `todas_emendas`** | **`erros_criticos` (§2º)**; deliberação sem efeito |
| **P3 — Cadeia** | **Pai é ele próprio uma subemenda** | **`erros_criticos` (§2º)**; subemenda encadeada excluída |

**Bugs corrigidos em rev.14 e rev.15 (apontados por auditoria externa):**

- **rev.14:** conflito de subemendas ia para `avisos` (§1º) — não disparava rascunho.
- **rev.15/P1:** auto-referência (`subemenda_de == numero`) removia a emenda silenciosamente
  sem gerar nenhum erro ou aviso.
- **rev.15/P2:** pai inexistente gerava `avisos` §1º — uma deliberação do Plenário aprovada
  sem efeito deve ser §2º (equivalente à regra A4.2).
- **rev.15/P3:** subemenda encadeada (Sub8 da Sub7 da E3) não era detectada; a cadeia não
  era resolvida — E3 recebia o texto de Sub7, não de Sub8.

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

**Histórico de correções em rev.14 e rev.15 (conflitos de subemendas):**
- rev.14: retorno 3→4 valores; conflito de subemendas agora em `erros_criticos` (§2º).
- rev.15: 3 edge cases corrigidos por auditoria externa (P1 auto-ref, P2 pai inexistente,
  P3 cadeia) — todos roteados para `erros_criticos` (§2º) com detecção no mapeamento.

---

### 6. verificar.py — estado atual (rev.18)

- **Seção 8:** 4 testes de análise estrutural (inclui novo teste B1 — "Art sem ponto")
- **Seção 11:** valida 8 tags XML (inclui `NOTAS_TECNICAS` e `SUGESTOES_NORMATIVAS`)
- **Seção 13:** 11 testes estruturais (sem API) para A4.1 e A4.2
- **Seção 14:** 12 testes estruturais (sem API) para E2 + SUGESTOES_NORMATIVAS
- **Seção 15:** 23 testes estruturais (sem API) para subemendas, incluindo:
  - Caso normal: substituição, remoção da lista, log
  - Caso inoperante: aviso §1º, não vai à IA
  - Caso rejeitada: texto pai preservado
  - **Conflito → `erros_criticos` §2º** (positivo + negativo §1º)
  - **P1 auto-referência → `erros_criticos` §2º; excluída** (positivo + negativo + exclusão)
  - **P2 pai inexistente → `erros_criticos` §2º** (positivo + negativo §1º + exclusão)
  - **P3 cadeia → `erros_criticos` §2º; excluída** (positivo + negativo + exclusão)
  - parsear reconhece `subemenda_de`; app.py exibe painel
  - **2 novos testes em rev.17:** fallback multi-lote [1,2,3,4] e offset após fallback = 4
  - **5 novos testes em rev.19 (seção 7g):** Normal Arial 11pt, 1 tabela apenas, ementa como parágrafo, corpo Arial, heading fonts
- **Resultado: 123/124** (1 falha esperada: chave API não configurada localmente)

Novo teste adicionado em rev.16 (Seção 8):
```python
TEXTO_EST_SEM_PONTO = (
    "Art. 1º Disposição.\n"
    "Art 14. Dispositivo sem ponto após Art.\n"
    "Art. 15. Normal.\n"
    "Art. 21. Último.\n"
)
est2 = analisar_estrutura(TEXTO_EST_SEM_PONTO)
chk("4 artigos (inclui Art sem ponto)", est2["artigos"] == 4,
    f"encontrado: {est2['artigos']} — esperado 4 (Art 14. deve ser contado)")
```

---

## Correções da rev.16 — bugs encontrados em teste real na Câmara (26/05/2026)

O sistema foi testado em produção com o **PLC 55/2025** na Câmara Municipal do Rio de Janeiro.
Quatro bugs foram identificados e corrigidos:

---

### B1 — `analisar_estrutura()`: "Art" sem ponto não era contado (utils.py)

**Problema:** O PLC 55/2025 contém uma linha `Art 14.` (sem ponto após "Art") — typo no
PDF original. A regex anterior exigia o ponto como caractere literal, falhando silenciosamente.
O sistema exibia 20 artigos em vez de 21.

```python
# Antes (bug — ponto obrigatório):
artigos = re.findall(r'^Art\.\s*\d+[ºo°]?', texto, re.MULTILINE | re.IGNORECASE)

# Depois (fix — ponto opcional):
artigos = re.findall(r'^Art\.?\s*\d+[ºo°]?', texto, re.MULTILINE | re.IGNORECASE)
```

**Risco aceito:** `Art\.?` poderia em tese capturar "Art " sem número — o `\d+` obrigatório
na sequência impede falso positivo ("Artigo" falha porque "igo" ≠ dígito).

---

### B2 — `ler_pdf()`: stop markers não usavam mínimo (utils.py)

**Problema:** A primeira tentativa de fix do bug B1 resultou em 23 artigos (em vez de 21),
pois o laço de stop markers usava `break` na primeira ocorrência encontrada na lista.
`'TRAMITAÇÃO DO PROJETO'` (posição 24805 no PDF) era acionado antes de `'JUSTIFICATIVA'`
(posição 17241) por estar antes na lista — apesar de JUSTIFICATIVA aparecer mais cedo no documento.
Isso deixava a seção `LEGISLAÇÃO CITADA` no texto extraído (com Art. 169 e Art. 5°, não pertencentes ao projeto).

```python
# Antes (bug — break na primeira ocorrência da lista, não a mais próxima no texto):
for marcador in _stop_marcadores:
    idx = texto_completo.find(marcador)
    if idx > 500:
        texto_completo = texto_completo[:idx]
        break  # ← errado: 'TRAMITAÇÃO' (pos 24805) disparava antes de 'JUSTIFICATIVA' (pos 17241)

# Depois (fix — mínimo entre todas as ocorrências):
_stop_marcadores = (
    'JUSTIFICATIVA', 'Texto Original:', 'LEGISLAÇÃO CITADA',
    'MENSAGEM Nº', 'TRAMITAÇÃO DO PROJETO', 'Distribuição =>', 'Informações Básicas',
)
stop_pos = len(texto_completo)
for marcador in _stop_marcadores:
    idx = texto_completo.find(marcador)
    if idx > 500:
        stop_pos = min(stop_pos, idx)
texto_completo = texto_completo[:stop_pos]
```

**Nota de encoding:** marcadores com acentos (`'LEGISLAÇÃO CITADA'`, `'Distribuição =>'`)
podem retornar -1 quando pdfplumber substitui caracteres por `?` ou símbolos de reposição.
Apenas marcadores ASCII puros são confiáveis; os acentuados são incluídos como fallback para
PDFs corretamente codificados.

---

### B3 — `ler_pdf()`: regex de URL deixava sufixo de paginação (utils.py)

**Problema:** O PDF do PLC 55/2025 contém URLs do tipo:
`https://www.camara.rio/atividade-parlamentar/processo-legislativo/plc 8/15`
O padrão `\S+` parava no espaço antes de `8/15`, deixando esse sufixo no texto extraído
e contribuindo para a contagem errada de artigos.

```python
# Antes (bug): capturava até o primeiro espaço
r'https?://www\.camara\.rio/\S+\s*\n?'

# Depois (fix): captura toda a linha
r'https?://www\.camara\.rio/[^\n]+'
```

---

### B4 — `exportar_redacao_final_docx()`: formato DOCX não seguia modelo oficial CMRJ (utils.py)

**Problema:** O DOCX gerado tinha formatação "quebrada" e não correspondia ao padrão oficial
da CMRJ. Problemas identificados:
- Fonte 12pt em vez de 10pt (Times New Roman)
- Artigos em negrito (modelos oficiais não usam negrito em artigos)
- Cabeçalho "CÂMARA MUNICIPAL" não pertence ao modelo da CCJ
- Ementa e Autor(es) ausentes no DOCX
- Fecho ("Sala da Comissão, DD de mês de YYYY.") ausente
- Assinaturas dos três vereadores ausentes

**Solução:** reescrita completa de `exportar_redacao_final_docx()` com base nos modelos
oficiais da CMRJ, e nova função `extrair_ementa_autor()`.

**Nova assinatura da função:**
```python
def exportar_redacao_final_docx(
    texto: str,
    nome_projeto: str,
    avisos: list[str],
    erros: list[str],
    alertas_absurdos: list[str],
    mapa: dict[str, str],
    log: list[str],
    tipo_redacao: str = "REDAÇÃO FINAL",
    prosseguir_com_alerta_sec_2: bool = False,
    ementa: str = "",   # ← NEW rev.16
    autor: str = "",    # ← NEW rev.16
) -> bytes:
```

**Configuração da página:**
```python
section = doc.sections[0]
section.page_width  = Cm(21.0)   # A4
section.page_height = Cm(29.7)
section.left_margin = section.right_margin = Cm(2.5)
section.top_margin  = section.bottom_margin = Cm(2.5)

# Estilo normal: Arial 11pt, espaçamento simples (rev.18 — B7)
_FONT  = 'Arial'
_FSIZE = 11
normal = doc.styles['Normal']
normal.font.name = _FONT
normal.font.size = Pt(_FSIZE)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after  = Pt(0)
normal.paragraph_format.line_spacing = 1.0
```

**Estrutura do DOCX (ordem obrigatória — rev.18):**
1. Título: CENTER, BOLD, UNDERLINE (ou vermelho se RASCUNHO)
2. 3 parágrafos em branco
3. Número do projeto: CENTER, BOLD, uppercase (com sufixo -A quando formal)
4. EMENTA: label BOLD + conteúdo como **parágrafo simples** (não tabela — rev.18 B7)
5. Autor(es): JUSTIFY, BOLD
6. 2 parágrafos em branco
7. Corpo do texto:
   - Linha "A CÂMARA MUNICIPAL...": BOLD, JUSTIFY
   - Linha "D E C R E T A": BOLD, RIGHT
   - Demais linhas: JUSTIFY, sem negrito (artigos NÃO são negritados)
8. Fecho: "Sala da Comissão, DD de mês de YYYY." CENTER, sp_before=6, sp_after=6
9. Assinatura Átila Nunes + título "Presidente" (CENTER)
10. Tabela 2×2 sem bordas: Dr. Gilberto | Inaldo Silva / Vice-Presidente | Vogal

**Nova função auxiliar `extrair_ementa_autor()`:**
```python
def extrair_ementa_autor(texto: str) -> tuple[str, str]:
    """Extrai ementa e autor(es) do texto bruto do projeto."""
    ementa = ""
    autor  = ""
    m_em = re.search(
        r'EMENTA:\s*\n([\s\S]*?)(?=\n\s*(?:Autor\(es\)|A\s+C[ÂA]MARA|$))',
        texto, re.IGNORECASE
    )
    if m_em:
        ementa = ' '.join(m_em.group(1).split())
    m_aut = re.search(r'(Autor\(es\)\s*:.*)', texto, re.IGNORECASE)
    if m_aut:
        autor = m_aut.group(1).strip()
    return ementa, autor
```

**Helper `_remover_bordas_tabela()` (novo em rev.16):**
```python
def _remover_bordas_tabela(tabela) -> None:
    for row in tabela.rows:
        for cell in row.cells:
            tc   = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                tag = OxmlElement(f'w:{edge}')
                tag.set(qn('w:val'),   'none')
                tag.set(qn('w:sz'),    '0')
                tag.set(qn('w:space'), '0')
                tag.set(qn('w:color'), 'auto')
                tcBorders.append(tag)
            tcPr.append(tcBorders)
```

**Detecção de linhas especiais do corpo:**
```python
_CAMARA_RE  = re.compile(r'^\s*A\s+C[ÂA]MARA\s+MUNICIPAL', re.IGNORECASE)
_DECRETA_RE = re.compile(r'^\s*D[\s]*E[\s]*C[\s]*R[\s]*E[\s]*T[\s]*A', re.IGNORECASE)
_MARKER_RE  = re.compile(r'\[\[⚠️.*?\]\]')

# "A CÂMARA MUNICIPAL..." → BOLD + JUSTIFY
# "D E C R E T A"        → BOLD + RIGHT
# Demais linhas          → JUSTIFY, sem negrito
```

**Chamada em app.py:**
```python
_ementa_doc, _autor_doc = extrair_ementa_autor(
    st.session_state.get('texto_original', '')
)
docx_bytes = exportar_redacao_final_docx(
    texto=texto_editavel,
    nome_projeto=nome_projeto,
    avisos=res.avisos,
    erros=res.erros_criticos,
    alertas_absurdos=getattr(res, 'alertas_absurdos', []),
    mapa=res.mapa_renumeracao,
    log=res.log_alteracoes,
    tipo_redacao=_tipo_rdz_aba5,
    prosseguir_com_alerta_sec_2=_prosseguir_sec_2,
    ementa=_ementa_doc,
    autor=_autor_doc,
)
```

**Evolução histórica da formatação DOCX:**

| Elemento | rev.15 (quebrado) | rev.16 B4 (modelo CMRJ) | **rev.18 B7 (atual)** |
|---|---|---|---|
| Fonte | 12pt | Times New Roman 10pt | **Arial 11pt** |
| Margens | padrão Word | 2.5cm todos os lados | 2.5cm (inalterado) |
| Artigos | **negritados** | sem negrito | sem negrito (inalterado) |
| "A CÂMARA MUNICIPAL" | sem negrito | **BOLD** | **BOLD** (inalterado) |
| "D E C R E T A" | sem negrito | **BOLD** + à direita | **BOLD** + à direita (inalterado) |
| EMENTA | ausente | tabela sem bordas | **parágrafo simples** |
| Autor(es) | ausente | parágrafo BOLD + JUSTIFY | parágrafo BOLD (inalterado) |
| Fecho | ausente | "Sala da Comissão..." CENTER | "Sala da Comissão..." (inalterado) |
| Assinaturas | ausente | Átila Nunes + tabela 2×2 | tabela 2×2 (inalterado) |

### B5 — `utils.py`: imports de API interna do python-docx no topo do módulo (hotfix rev.16.1, commit 39420c4)

**Problema:** `from docx.oxml.ns import qn` e `from docx.oxml import OxmlElement` foram
adicionados no topo de `utils.py` como imports de módulo. No ambiente Streamlit Cloud
(Linux, versão específica do python-docx instalada), esses imports falhavam com
`ImportError`, derrubando o app inteiro na inicialização. O erro NÃO se reproduzia
localmente (Python 3.14, python-docx 1.2.0).

```python
# Antes (bug — imports no topo do módulo):
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Depois (fix — imports lazy dentro da função que os usa):
def _remover_bordas_tabela(tabela) -> None:
    from docx.oxml.ns import qn as _qn
    from docx.oxml import OxmlElement as _OxmlElement
    ...
```

**Gap identificado:** o sistema não tem nenhum teste que verifique "o módulo carrega
limpo em ambiente Linux/Cloud". O `verificar.py` roda localmente (Windows), logo
divergências de ambiente só aparecem em produção.

**Lição:** APIs internas de pacotes terceiros (`docx.oxml.*`) nunca devem ser importadas
no nível de módulo. Usar apenas a API pública no topo; APIs internas como imports lazy
dentro das funções que as consomem.

### B6 — `harmonizer.py`: fallback de parsing numerava errado em múltiplos lotes (rev.17)

**Problema:** a função `parsear_emendas_com_ia()` processa emendas em lotes. O caminho
de fallback (quando o JSON da IA é inválido) usava `offset + len(todas_emendas) + 1`
para numerar cada emenda bruta. Com múltiplos lotes, `len(todas_emendas)` já inclui
as emendas de lotes anteriores — o `offset` era somado duas vezes, produzindo buracos
na numeração.

```python
# Cenário: lote 1 ok → [E1, E2], offset=2; lote 2 cai no fallback

# Antes (bug — double-counting):
num = offset + len(todas_emendas) + 1
# Para parte 1: 2 + 2 + 1 = 5  (correto seria 3)
# Para parte 2: 2 + 3 + 1 = 6  (correto seria 4)
# Resultado: [1, 2, 5, 6] — afeta votação e subemenda_de

# Depois (fix — idx relativo ao lote):
idx_fb = 0
for parte in partes:
    if parte.strip():
        num = offset + idx_fb + 1   # 2+0+1=3, 2+1+1=4 ✓
        todas_emendas.append(...)
        idx_fb += 1
```

**Novos testes em verificar.py:** 2 verificações do cenário multi-lote com fallback
(118/119 após fix de B6; 123/124 após rev.19 com 5 novos testes B7; 1 falha esperada = API key ausente).

---

## Arquitetura de proteções (estado atual — rev.19)

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
| Subemendas — inoperante (pai rejeitado) | Python (pré-IA) | Aviso §1º; subemenda não vai à IA |
| Subemendas — P1 auto-referência | Python (pré-IA) | **ERROS_CRITICOS §2º**; emenda excluída |
| Subemendas — P2 pai inexistente | Python (pré-IA) | **ERROS_CRITICOS §2º**; deliberação sem efeito |
| Subemendas — P3 cadeia (sub de sub) | Python (pré-IA) | **ERROS_CRITICOS §2º**; subemenda excluída |
| Detecção estrutural absurdos | Python | Circular, inoperante — independe do modelo |
| Escalada de §1º para §2º | Python | Padrões semânticos nos avisos |
| Validação XML | Python | Par completo de 8 tags ou ValueError |
| Rascunho de trabalho | Python + App | §2º → DOCX sai como rascunho até relator confirmar |
| `_invalidar_resultado()` | App | Qualquer mudança limpa resultado anterior |
| Skip set completo | Python | Strings "Nenhum/a..." filtradas corretamente |
| Limpeza de marcadores inline | Python + App | `[[⚠️ CCJ:...]]` removido de DOCX e TXT antes da exportação |
| **B1 — Art sem ponto** | **Python (utils)** | **`Art\.?` captura typos como "Art 14." em `analisar_estrutura()`** |
| **B2 — Stop markers mínimo** | **Python (utils)** | **`min()` entre todas as posições; nunca `break` no primeiro encontrado** |
| **B3 — URL regex linha inteira** | **Python (utils)** | **`[^\n]+` em vez de `\S+` elimina sufixos de paginação** |
| **B4 — DOCX formato CMRJ** | **Python (utils)** | **Reescrita completa; ementa, autor, fecho e assinaturas presentes** |
| **B5 — Imports lazy (API interna)** | **Python (utils)** | **`qn`/`OxmlElement` movidos para dentro de `_remover_bordas_tabela`; ✅ confirmado — download DOCX funciona no Cloud** |
| **B6 — Fallback numeração multi-lote** | **Python (harmonizer)** | **`offset + idx_fb + 1` relativo ao lote; elimina double-counting que gerava buracos [1,2,5,6]** |
| **B7 — Ementa em tabela + fontes inconsistentes** | **Python (utils)** | **Ementa movida para `_para()` simples; corpo e assinaturas unificados para Arial 11pt via `_FONT`/`_FSIZE`** |

---

## Perguntas para sua auditoria

### Sobre as correções da rev.16 (novos — teste real PLC 55/2025)

1. **B1 — regex `Art\.?`:**
   - O ponto opcional resolve o caso "Art 14." sem introduzir falsos positivos para
     outras línguas ou abreviações? Algum padrão de texto legal poderia ativar um falso positivo?
   - Deveríamos adicionar um aviso ao usuário quando `Art` sem ponto for detectado,
     para que ele corrija o PDF original?

2. **B2 — stop markers com `min()`:**
   - A lista atual de stop markers é suficiente? Há outros marcadores típicos de PDFs
     da Câmara Municipal do Rio de Janeiro que deveriam ser adicionados?
   - O threshold `idx > 500` (para ignorar marcadores nos primeiros 500 caracteres) é
     adequado? Poderia truncar um projeto muito curto?
   - Marcadores acentuados (`'LEGISLAÇÃO CITADA'`, `'Distribuição =>'`) falham silenciosamente
     em PDFs com encoding incorreto. Deveríamos tratar esse caso explicitamente
     (ex: normalizar o texto antes de buscar, ou usar unidecode)?

3. **B3 — regex URL:**
   - `[^\n]+` captura toda a linha. Se a URL estiver seguida de texto legítimo na mesma
     linha (ex: "Veja mais em https://camara.rio/... e também o art. 5º"), o art. 5º seria removido?
     É um cenário plausível em PDFs de projetos da CMRJ?

4. **B5 — Paridade local ↔ Cloud (gap de ambiente):**
   - O `verificar.py` roda em Windows/Python 3.14 localmente. O app roda em Linux/Python 3.11
     no Streamlit Cloud. Que outros imports ou comportamentos podem divergir entre os dois
     ambientes? Quais testes deveriam ser adicionados a `verificar.py` para detectar isso?
   - Existe um padrão sistemático para distinguir "API pública do pacote" (segura no topo do
     módulo) de "API interna do pacote" (só lazy, dentro da função)? Como aplicá-lo no
     restante do código?

5. **B4 — DOCX formato CMRJ:**
   - A extração de ementa via `extrair_ementa_autor()` depende de "EMENTA:" como marcador.
     Projetos que não seguem esse padrão deixarão o campo em branco no DOCX. Essa degradação
     silenciosa é aceitável, ou deveríamos avisar o usuário na interface?
   - O fecho usa a data do dia do download. Isso é correto? Ou a data deveria ser
     inserida pelo relator (data da sessão, não do download)?
   - A tabela 2×2 sem bordas para Dr. Gilberto e Inaldo Silva usa a API de XML do python-docx
     (`OxmlElement`). Existe risco de incompatibilidade com versões do Word ou LibreOffice?
   - Redações do Vencido têm formato diferente (só 1 assinatura)? O sistema trata isso?

### Sobre as versões anteriores (rev.15 e anteriores)

6. **Os edge cases de subemendas (rev.15) foram bem cobertos?**
   - Para P3 (cadeia), a abordagem de **proibir com ERRO CRÍTICO** é a mais segura, ou
     deveríamos tentar **resolver recursivamente** (neto prevalece sobre filho)?
   - Para P2 (pai inexistente), a equiparação com A4.2 (§2º) é a abordagem correta,
     ou seria mais útil um aviso §1º com a instrução de corrigir o vínculo manualmente?
   - Há algum edge case adicional que ainda não cobrimos?
     (ex: dois conflitos encadeados? pai aprovado mas `novo_texto` vazio?)

7. **A regra E2 reformulada é suficientemente robusta?**
   - A política de "aplicar emenda de menor número como cautela" é a abordagem correta?
   - Há risco de o modelo não realizar a varredura prévia e detectar o conflito apenas
     depois de aplicar as emendas?
   - As sugestões normativas podem criar viés para que o relator as adote sem análise crítica?

8. **A regra A4 está bem formulada?**
   - A distinção A4.1 (aditiva: posiciona) vs A4.2 (modificativa: não aplica) é a abordagem correta?
   - Os critérios de posicionamento para unidades menores (parágrafo, inciso, alínea, item)
     são suficientes?

9. **A separação AVISOS / NOTAS_TECNICAS / SUGESTOES_NORMATIVAS é robusta?**
   - A regra E1.5 é suficiente para o modelo não "vazar" mérito nos AVISOS?
   - Há risco de sugestões normativas aparecerem em ERROS_CRITICOS em vez de SUGESTOES_NORMATIVAS?

10. **Há algo que deveria ter sido implementado e não foi?**
    - Considerando o fluxo completo (upload → parsing → subemendas → votação → harmonização
      → exportação), há algum ponto cego evidente?

11. **O prompt tem riscos de regressão com E2 + A4 + E1.5 + subemendas?**
    - Há conflito potencial com A1 (preservação verbatim) ou com as regras do Bloco B
      (renumeração)?

12. **Sugestões livres** — o que você mudaria ou acrescentaria?

---

## Nota sobre o contexto de uso

- O relator é também o assessor que opera o sistema — não há separação de papéis.
- Projetos típicos: PLCs de zoneamento urbano (30–50 artigos, 10–180 emendas).
- O modelo usado é `claude-sonnet-4-6` com `max_tokens=60000`.
- A chave API fica nos Secrets do Streamlit Cloud — não há chave local em produção.
- O app está em: https://ccj-redacoes.streamlit.app
- O código-fonte está em: https://github.com/ProfAlexandreAraujo/sistema-redacoes-ccj
- **rev.16 foi o resultado do primeiro teste em produção real** (PLC 55/2025, Câmara Municipal
  do Rio de Janeiro, 26/05/2026) — os bugs B1–B4 foram identificados em uso real,
  não em testes sintéticos.
- **rev.16.1 (hotfix):** B5 — imports lazy para `qn`/`OxmlElement`; o app ficou fora do ar
  após o deploy de rev.16 por ImportError no Streamlit Cloud (não reproduzível localmente).
  Gap confirmado: ausência de smoke test de carregamento de módulo em ambiente Linux.
- **rev.17:** B5 ✅ **FECHADO** — download de DOCX confirmado funcionando no Cloud.
  B6 — fallback de parsing multi-lote corrigido (`offset + idx_fb + 1`);
  2 novos testes em verificar.py (118/119 na época). Arquivos de referência CMRJ (4 DOCX + 1 PDF)
  agora rastreados no Git. Inconsistência de nome em `730-A_2026` documentada.
- **rev.18:** B7 — formatação DOCX unificada: ementa movida para parágrafo simples (elimina
  tabela de ementa e reduz uso de `oxml`); corpo e assinaturas com Arial 11pt via constantes
  `_FONT`/`_FSIZE`; `size_pt=10` explícito removido de título, nº projeto, EMENTA:, Autor(es).
- **rev.19:** resposta à auditoria externa do rev.18 — 5 testes B7 adicionados em verificar.py
  (seção 7g): Normal Arial 11pt, 1 tabela apenas, ementa como parágrafo, corpo Arial;
  Heading 1/2/3 unificados para Arial 11pt em utils.py; PROMPT_AUDITORIA_EXTERNA.md e
  AUDITORIA.md corrigidos: critérios B4 históricos marcados, contagens atualizadas (123/124).
