@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

echo Starting FastAPI API on http://127.0.0.1:8080
echo Starting Next.js site on http://127.0.0.1:3000
echo Open the site at http://127.0.0.1:3000/  (not :8080)
echo.

start "imprint-api" /D "%~dp0" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080"
start "imprint-web" /D "%~dp0" cmd /k "npm run dev:web"

echo Both windows launched. Browse http://127.0.0.1:3000/
