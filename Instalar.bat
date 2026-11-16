@echo off
setlocal
cd /d "%~dp0"
set "CLIP_PY="
set "CLIP_CHECK=%TEMP%\clip-libre-python-%RANDOM%-%RANDOM%.txt"
set "CLIP_NO_PAUSE="
if /i "%~1"=="--sin-pausa" set "CLIP_NO_PAUSE=1"
if /i "%~1"=="--comprobar" set "CLIP_NO_PAUSE=1"

rem No basta con que exista py.exe: debe ejecutar un Python compatible real.
if exist ".venv\Scripts\python.exe" call :probar ".venv\Scripts\python.exe"
if not defined CLIP_PY call :probar py -3.12
if not defined CLIP_PY call :probar py -3.11
if not defined CLIP_PY call :probar python
if not defined CLIP_PY call :probar python3
if not defined CLIP_PY call :probar py
if not defined CLIP_PY goto falta_python

echo Python compatible encontrado: %CLIP_PY%
if /i "%~1"=="--comprobar" exit /b 0
if exist ".venv\Scripts\python.exe" goto instalar_dependencias
call %CLIP_PY% -m venv .venv
if errorlevel 1 goto error_entorno
if not exist ".venv\Scripts\python.exe" goto error_entorno

:instalar_dependencias
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] in [(3,11),(3,12)] and sys.maxsize.bit_length()==63 else 1)"
if errorlevel 1 goto error_entorno
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
where ffmpeg >nul 2>nul
if errorlevel 1 goto falta_ffmpeg
where ffprobe >nul 2>nul
if errorlevel 1 goto falta_ffmpeg
echo Instalacion terminada. Abre Iniciar.bat.
call :pausa
exit /b 0

:probar
if exist "%CLIP_CHECK%" del /q "%CLIP_CHECK%" >nul 2>nul
call %* -c "import sys,pathlib; sys.exit(1) if sys.version_info[:2] not in [(3,11),(3,12)] or sys.maxsize.bit_length()!=63 else pathlib.Path(sys.argv[1]).write_text(sys.executable,encoding='utf-8')" "%CLIP_CHECK%" >nul 2>nul
if errorlevel 1 exit /b 1
if not exist "%CLIP_CHECK%" exit /b 1
set "CLIP_PY=%*"
del /q "%CLIP_CHECK%" >nul 2>nul
exit /b 0

:falta_python
echo No se encontro Python 3.12 o 3.11 de 64 bits instalado y ejecutable.
echo Tener el lanzador py no significa que Python este instalado.
echo Descarga Python 3.12 de https://www.python.org/downloads/windows/
echo En el instalador marca Add python.exe to PATH y completa Install Now.
echo Despues cierra esta ventana y vuelve a abrir Instalar.bat.
echo No se han intentado instalar dependencias sin un interprete valido.
call :pausa
exit /b 2

:error_entorno
echo No se pudo crear o validar .venv\Scripts\python.exe.
echo Si hay un entorno incompleto, renombra .venv como .venv-anterior y reintenta.
echo Tus videos y proyectos de data no se modifican.
call :pausa
exit /b 3

:falta_ffmpeg
echo Falta FFmpeg o FFprobe. Instala FFmpeg con libass y agregalo al PATH.
echo Si tienes winget: winget install --id Gyan.FFmpeg -e
echo Cierra esta ventana y vuelve a ejecutar Instalar.bat despues de instalarlo.
call :pausa
exit /b 4

:error
echo No se pudo completar la instalacion. Revisa el mensaje anterior.
call :pausa
exit /b 1

:pausa
if not defined CLIP_NO_PAUSE pause
exit /b 0
