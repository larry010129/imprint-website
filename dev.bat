@echo off
cd /d "%~dp0"

set "VENV_PY=.venv\Scripts\python.exe"
set "NEED_VENV=1"

if exist "%VENV_PY%" (
  "%VENV_PY%" --version >nul 2>&1
  if not errorlevel 1 set "NEED_VENV=0"
)

if "%NEED_VENV%"=="1" (
  if exist ".venv" (
    echo Removing broken virtual environment...
    rmdir /s /q .venv
  )
  echo Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo Starting FastAPI + Jinja SSR on http://127.0.0.1:8080
echo Open the site at http://127.0.0.1:8080/
echo.
echo Note: On Windows, brief "SpawnProcess" tracebacks during reload are harmless.
echo       If the site loads in the browser, you can ignore them.
echo.

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080 ^
  --reload-dir app --reload-dir config --reload-dir content ^
  --reload-delay 0.25
