@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python 3 is required.& exit /b 1)
where node >nul 2>nul || (echo Node.js is required.& exit /b 1)
where npm >nul 2>nul || (echo npm is required.& exit /b 1)

if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,numpy,requests,httpx,shapefile,rasterio,tifffile" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 exit /b 1
  ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
  if errorlevel 1 exit /b 1
)

if not exist "node_modules\.bin\vite.cmd" (
  call npm ci
  if errorlevel 1 exit /b 1
)

start "Lunar Navigator Backend - LIVE HORIZONS" cmd /k "cd /d ""%~dp0backend"" && set ENABLE_LIVE_HORIZONS=1 && ..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
start "Lunar Navigator Frontend" cmd /k "cd /d ""%~dp0"" && set VITE_API_BASE_URL=http://127.0.0.1:8000 && npm run dev -- --host 127.0.0.1"
echo Started the backend and frontend in separate windows.
echo Open http://127.0.0.1:3000 in your browser.
endlocal
