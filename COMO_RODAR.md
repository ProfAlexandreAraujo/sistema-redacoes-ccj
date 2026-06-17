# Como rodar o Sistema de Redações — CCJ

## 1. Configurar a chave da API (só na primeira vez)
1. Na pasta `sistema_redacoes\.streamlit\`, copie `secrets.toml.exemplo` e renomeie a cópia para **`secrets.toml`**.
2. Abra o `secrets.toml` e troque o valor pela sua chave real da Anthropic:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-...sua-chave-aqui..."
   ```
3. Salve. (O `secrets.toml` fica só no seu PC — nunca vai pro GitHub.)
   - Alternativa: definir a variável de ambiente `ANTHROPIC_API_KEY` no Windows.

## 2. Iniciar o app
- **Duplo clique** em `iniciar.bat`, **ou** no terminal:
  ```
  cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes
  python -m streamlit run app.py
  ```
- Abre no navegador em **http://localhost:8501**.
- Na barra lateral deve aparecer **"✅ API configurada pelo administrador"**.

## 3. Fluxo do PLC 92 (Abas 1 → 5)
1. **Aba 1 · Projeto** — identifique ("PLC 92/2025 — AEIU Praça XI Maravilha") e cole/carregue o **texto integral do PLC 92 original** (Poder Executivo). Tipo: *Redação Final*.
2. **Aba 2 · Emendas** — cole/carregue o bloco das **75 peças aprovadas**. Use a versão **com "TRADUZIK"** (`Entrada_Pura_75_Pecas...docx`) — é ela que exercita o alerta da palavra desconexa. Clique **🤖 Processar com IA**. Confira tipo/alvo e, para as subemendas, o campo "SubEmenda da Emenda Nº".
3. **Aba 3 · Votação** — marque as 75 peças como **Aprovadas** (e nada das rejeitadas: E6, E84, E41, E29, E77, E9, E34, E95, E79, E143).
4. **Aba 4 · Harmonizar** — clique **🔄 Harmonizar agora**. Pode levar alguns minutos; não recarregue a página.
5. **Aba 5 · Redação Final** — revise e exporte `.docx`/`.txt`.

## 4. Aba 6 · Auditoria (a verificação de convergência)
- Abre automaticamente após a harmonização.
- Mostra o **score 0–100** de convergência com a redação final publicada (gabarito), item a item.
- Confira contra o `gabaritos\CHECKLIST_VALIDACAO_PLC92.md`:
  - Estrutura: **63 artigos contíguos**; Subemendas: 9 aplicadas; sem conflito com peças rejeitadas;
  - "TRADUZIK" apenas **apontado** (preservado, não removido);
  - Anexos sem conteúdo gráfico = **aviso §1º** (não erro crítico).
- Botão para baixar o **texto oficial** (gabarito) para cotejo dispositivo a dispositivo.

## 5. (Opcional) Re-rodar a suíte de verificação técnica
```
cd C:\Users\Admin\Documents\Claude\CCJ\sistema_redacoes
python tests\verificar_calibracao.py
```
Confirma a calibração sem gastar crédito de API (esperado: "TODOS OS TESTES PASSARAM ✓").
