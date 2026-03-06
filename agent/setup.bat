@echo off
REM setup.bat - Primeiro setup da REBEKA
REM Este script ajuda a configurar o ambiente de forma segura

echo ================================================
echo   REBEKA - Configuracao Inicial
echo ================================================
echo.
echo Este setup ira orienta-lo na configuracao.
echo Nenhum dado sera armazenado no codigo.
echo.

REM Verificar se .env existe
if exist ".env" (
    echo [AVISO] Arquivo .env ja existe!
    set /p OVERWRITE="Deseja reconfigurar? (s/n): "
    if /i not "%OVERWRITE%"=="s" goto :end
)

echo.
echo --- Configuracao do LLM ---
echo.
echo Escolha seu provedor de LLM:
echo 1) Moonshot AI (Kimi) - Recomendado
echo 2) Google AI (Gemini)
echo 3) OpenAI (GPT-4)
echo 4) Anthropic (Claude)
set /p LLM_CHOICE="Escolha (1-4): "

if "%LLM_CHOICE%"=="1" (
    set PROVIDER=moonshot
    echo Obtenha a chave em: https://platform.moonshot.ai/
    set /p API_KEY="Cole sua API Key: "
    echo MOONSHOT_API_KEY=%API_KEY% > .env
    echo OPENAI_API_BASE=https://api.moonshot.ai/v1 >> .env
) else if "%LLM_CHOICE%"=="2" (
    set PROVIDER=google
    echo Obtenha a chave em: https://aistudio.google.com/app/apikey
    set /p API_KEY="Cole sua API Key: "
    echo GOOGLE_API_KEY=%API_KEY% > .env
) else if "%LLM_CHOICE%"=="3" (
    set PROVIDER=openai
    echo Obtenha a chave em: https://platform.openai.com/api-keys
    set /p API_KEY="Cole sua API Key: "
    echo OPENAI_API_KEY=%API_KEY% > .env
) else if "%LLM_CHOICE%"=="4" (
    set PROVIDER=anthropic
    echo Obtenha a chave em: https://console.anthropic.com/
    set /p API_KEY="Cole sua API Key: "
    echo ANTHROPIC_API_KEY=%API_KEY% > .env
)

echo.
echo --- Configuracao do Banco de Dados ---
echo.
echo 1) SQLite (padrao, para desenvolvimento)
echo 2) PostgreSQL (para producao)
set /p DB_CHOICE="Escolha (1-2): "

if "%DB_CHOICE%"=="1" (
    echo DATABASE_URL=sqlite:///causal_bank.db >> .env
) else (
    echo Informe os dados do PostgreSQL:
    set /p DB_HOST="Host: "
    set /p DB_USER="Usuario: "
    set /p DB_PASS="Senha: "
    set /p DB_NAME="Nome do Banco: "
    echo DATABASE_URL=postgresql://%DB_USER%:%DB_PASS%@%DB_HOST%/%DB_NAME% >> .env
)

echo.
echo --- Configuracao Opcional ---
echo.

set /p EMAIL="Email Gmail (para deixe vazio para pular): "
if not "%EMAIL%"=="" (
    echo GMAIL_IMAP_USER=%EMAIL% >> .env
    echo.
    echo Para Gmail, você precisa gerar um App Password:
    echo 1) Va para: https://myaccount.google.com/signinoptions/two-step-verification
    echo 2) Ative a verificacao em duas etapas
    echo 3) Va para: https://myaccount.google.com/apppasswords
    echo 4) Gere uma senha para 'E-mail'
    set /p EMAIL_PASS="Cole o App Password: "
    echo GMAIL_IMAP_PASSWORD=%EMAIL_PASS% >> .env
)

set /p TELEGRAM="Token do Bot Telegram (deixe vazio para pular): "
if not "%TELEGRAM%"=="" (
    echo TELEGRAM_BOT_TOKEN=%TELEGRAM% >> .env
)

echo.
echo ================================================
echo   Configuracao Concluida!
echo ================================================
echo.
echo O arquivo .env foi criado com suas credenciais.
echo Este arquivo NAO deve ser commitado (ja está no .gitignore).
echo.

:end
pause
