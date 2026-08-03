@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "NEED_VENV=1"

if exist "%VENV_PY%" (
  "%VENV_PY%" -c "import uvicorn" >nul 2>&1
  if not errorlevel 1 set "NEED_VENV=0"
)

if "%NEED_VENV%"=="1" (
  if exist "%~dp0.venv" (
    echo Removing broken virtual environment...
    rmdir /s /q "%~dp0.venv"
  )
  echo Creating virtual environment...
  python -m venv "%~dp0.venv"
  if errorlevel 1 (
    echo Failed to create .venv. Is Python on PATH?
    exit /b 1
  )
  echo Installing requirements...
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Failed to install requirements.txt
    exit /b 1
  )
)

echo.
echo Starting FastAPI + Jinja SSR on http://127.0.0.1:8080
echo Open the site at http://127.0.0.1:8080/
echo.
echo Note: On Windows, brief "SpawnProcess" tracebacks during reload are harmless.
echo       If the site loads in the browser, you can ignore them.
echo.

"%VENV_PY%" -m uvicorn main:app --reload --host 127.0.0.1 --port 8080 ^
  --reload-dir app --reload-dir config --reload-dir content ^
  --reload-delay 0.25

