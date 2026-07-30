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

echo Starting FastAPI + Jinja SSR on http://127.0.0.1:8080
echo Open the site at http://127.0.0.1:8080/
echo.

python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080
