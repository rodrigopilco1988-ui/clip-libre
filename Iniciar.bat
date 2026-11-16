@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Primero ejecuta Instalar.bat.
 pause
 exit /b 1
)
set "HF_HOME=%~dp0data\modelos"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
if errorlevel 1 pause
