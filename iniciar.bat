@echo off
title Sistema de Redacoes - CCJ CMRJ
echo.
echo  ====================================================
echo   SISTEMA DE REDACOES - CCJ CMRJ
echo   Comissao de Constituicao, Justica e Redacao
echo  ====================================================
echo.

REM Verifica se ANTHROPIC_API_KEY esta definida
if "%ANTHROPIC_API_KEY%"=="" (
    echo  AVISO: Variavel ANTHROPIC_API_KEY nao encontrada.
    echo  Voce podera informar a chave API diretamente no sistema.
    echo.
)

echo  Iniciando o sistema...
echo  Acesse em: http://localhost:8501
echo.
echo  Para encerrar, pressione CTRL+C nesta janela.
echo.

python -m streamlit run "%~dp0app.py" --server.port 8501 --browser.gatherUsageStats false

pause
