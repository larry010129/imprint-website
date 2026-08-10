@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "NEED_VENV=1"
set "PORT=8080"
set "HOST=127.0.0.1"

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
    goto :fail
  )
  echo Installing requirements...
  "%VENV_PY%" -m pip install --upgrade pip
  "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Failed to install requirements.txt
    goto :fail
  )
)

rem If something already answers on the dev port, offer reuse or restart.
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -Uri 'http://%HOST%:%PORT%/' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo Dev server already running at http://%HOST%:%PORT%/
  echo.
  powershell -NoProfile -Command ^
    "$port=%PORT%; $ids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); if (-not $ids.Count) { Write-Host '  (no LISTEN owner found)' }; foreach ($id in $ids) { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $id) -ErrorAction SilentlyContinue; if ($p) { Write-Host ('  PID ' + $p.ProcessId + '  ' + $p.Name); Write-Host ('       ' + $p.CommandLine) } else { Write-Host ('  PID ' + $id) } }"
  echo.
  echo Opening browser...
  start "" "http://%HOST%:%PORT%/"
  echo.
  echo No visible console? An orphan python/uvicorn often holds the port in the background.
  echo.
  choice /C RO /N /M "Press R to kill port %PORT% and restart here, or O to just open/exit: "
  if errorlevel 2 goto :end
  if errorlevel 1 goto :restart_port
)

rem Port held but not serving HTTP - clear stale LISTENING python/uvicorn.
powershell -NoProfile -Command ^
  "$port=%PORT%; $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; if (-not $conns) { exit 0 }; foreach ($c in $conns) { $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue; if ($proc -and ($proc.ProcessName -match '^(python|uvicorn)$')) { Write-Host ('Stopping stale ' + $proc.ProcessName + ' PID ' + $proc.Id + ' on port ' + $port); Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } else { Write-Host ('Port ' + $port + ' in use by PID ' + $c.OwningProcess + ' (' + $(if($proc){$proc.ProcessName}else{'unknown'}) + '). Free it or change PORT in dev.bat.'); exit 2 } }; Start-Sleep -Seconds 1; exit 0"
if errorlevel 2 goto :fail
if errorlevel 1 goto :fail
goto :start_server

:restart_port
echo.
echo Stopping listener(s) on port %PORT%...
powershell -NoProfile -Command ^
  "$port=%PORT%; $killed=@{}; $ids=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); foreach ($id in $ids) { $cur=$id; while ($cur) { $p=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $cur) -ErrorAction SilentlyContinue; if (-not $p) { break }; $isPy=($p.Name -match '^(python|uvicorn)'); $isUv=($p.CommandLine -match 'uvicorn'); if (-not ($isPy -and $isUv)) { if ($cur -eq $id) { Write-Host ('Port ' + $port + ' held by non-uvicorn PID ' + $id + ' (' + $p.Name + '). Not killing.'); exit 2 }; break }; if (-not $killed.ContainsKey($cur)) { Write-Host ('  Stopping PID ' + $cur + ' (' + $p.Name + ')'); Stop-Process -Id $cur -Force -ErrorAction SilentlyContinue; $killed[$cur]=$true }; $cur=$p.ParentProcessId } }; Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^(python|uvicorn)' -and $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match ('--port\s+' + $port) } | ForEach-Object { if (-not $killed.ContainsKey($_.ProcessId)) { Write-Host ('  Stopping PID ' + $_.ProcessId + ' (' + $_.Name + ')'); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $killed[$_.ProcessId]=$true } }; Start-Sleep -Seconds 1; if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { Write-Host ('Port ' + $port + ' still in use.'); exit 2 }; Write-Host 'Port cleared.'; exit 0"
if errorlevel 2 goto :fail
if errorlevel 1 goto :fail
echo Starting fresh in this window...

:start_server
echo.
echo Starting FastAPI + Jinja SSR on http://%HOST%:%PORT%
echo Open the site at http://%HOST%:%PORT%/
echo.
echo Keep this window open while the server runs. Ctrl+C to stop.
echo.

rem Windows + Python 3.14: uvicorn WatchFiles --reload often dies mid-spawn
rem (multiprocessing namedtuple/eval race) after "Shutting down", leaving :8080 dead.
rem Default: no reload. Opt in with DEV_RELOAD=1. Force off with DEV_NO_RELOAD=1.
set "USE_RELOAD=0"
if /I "%DEV_RELOAD%"=="1" set "USE_RELOAD=1"
if /I "%DEV_NO_RELOAD%"=="1" set "USE_RELOAD=0"

if "%USE_RELOAD%"=="0" (
  echo Reload OFF ^(Windows-safe default^). After .py edits, restart this window.
  echo Opt in to WatchFiles reload ^(flaky on Windows^): set DEV_RELOAD=1 ^&^& dev.bat
  echo.
  "%VENV_PY%" -m uvicorn main:app --host %HOST% --port %PORT%
) else (
  echo Reload ON ^(DEV_RELOAD=1^). WatchFiles can still crash spawn on Windows —
  echo server may die after "Shutting down". Prefer default no-reload for admin/uploads.
  echo.
  echo uvicorn cmdline:
  echo   "%VENV_PY%" -m uvicorn main:app --reload --host %HOST% --port %PORT% --reload-dir app --reload-dir config --reload-dir content --reload-delay 1.0 --reload-exclude "__pycache__" --reload-exclude "*.pyc" --reload-exclude "*.log" --reload-exclude ".youtube-embed-cache.json" --reload-exclude ".featured-video-cache.json"
  echo.
  "%VENV_PY%" -m uvicorn main:app --reload --host %HOST% --port %PORT% ^
    --reload-dir app --reload-dir config --reload-dir content ^
    --reload-delay 1.0 ^
    --reload-exclude "__pycache__" --reload-exclude "*.pyc" --reload-exclude "*.log" ^
    --reload-exclude ".youtube-embed-cache.json" --reload-exclude ".featured-video-cache.json"
)
set "UV_EXIT=%ERRORLEVEL%"
if not "%UV_EXIT%"=="0" (
  echo.
  echo uvicorn exited with code %UV_EXIT%.
  goto :fail
)

echo.
echo Server stopped.
echo Press any key to close.
pause >nul
goto :end

:fail
echo.
echo Local dev failed to start. Fix the error above, then run dev.bat again.
echo Press any key to close.
pause >nul
exit /b 1

:end
endlocal
exit /b 0
