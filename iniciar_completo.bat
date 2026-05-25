@echo off
title Sistema de Redacoes CCJ - CMRJ
color 0A
cls

echo ==========================================================
echo   SISTEMA DE REDACOES - CCJ CMRJ
echo   Comissao de Constituicao, Justica e Redacao
echo ==========================================================
echo.

:: Verificar se Python esta disponivel
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Verifique a instalacao.
    pause
    exit /b 1
)

:: Verificar se Node.js esta disponivel
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Node.js nao encontrado. Verifique a instalacao.
    pause
    exit /b 1
)

:: Matar processos anteriores nas portas 8501 (se houver)
echo [1/3] Verificando processos anteriores...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8501" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Iniciar Streamlit em background
echo [2/3] Iniciando Streamlit na porta 8501...
cd /d "%~dp0"
start /B python -m streamlit run app.py --server.port 8501 --server.headless true > logs_streamlit.txt 2>&1
timeout /t 4 /nobreak >nul

:: Verificar se Streamlit subiu
netstat -ano | find ":8501" | find "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Streamlit pode ainda estar inicializando...
    timeout /t 3 /nobreak >nul
)

:: Iniciar localtunnel em background
echo [3/3] Iniciando tunel localtunnel (ccj-redacoes.loca.lt)...
set LT_PATH=C:\Users\Admin\AppData\Roaming\npm\node_modules\localtunnel\bin\lt.js
start /B node "%LT_PATH%" --port 8501 --subdomain ccj-redacoes > logs_tunnel.txt 2>&1
timeout /t 5 /nobreak >nul

echo.
echo ==========================================================
echo   SISTEMA INICIADO COM SUCESSO!
echo ==========================================================
echo.
echo   Acesso LOCAL:  http://localhost:8501
echo   Acesso REMOTO: https://ccj-redacoes.loca.lt
echo.
echo   INSTRUCOES PARA A EQUIPE:
echo   1. Acesse https://ccj-redacoes.loca.lt
echo   2. Na tela de seguranca, digite o IP: 179.82.230.85
echo   3. Clique em Continue
echo   4. O sistema abrira automaticamente
echo.
echo   IMPORTANTE: Mantenha esta janela ABERTA durante a sessao!
echo   Para encerrar: feche esta janela ou pressione Ctrl+C
echo.
echo ==========================================================
echo   Logs: logs_streamlit.txt e logs_tunnel.txt
echo ==========================================================
echo.

:loop
timeout /t 30 /nobreak >nul

:: Verificar se Streamlit ainda esta rodando
netstat -ano | find ":8501" | find "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%time%] ATENCAO: Streamlit parou! Reiniciando...
    start /B python -m streamlit run app.py --server.port 8501 --server.headless true >> logs_streamlit.txt 2>&1
    timeout /t 5 /nobreak >nul
    echo [%time%] Streamlit reiniciado.
)

goto loop
