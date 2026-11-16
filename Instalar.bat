@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
 echo Instala Python 3.11 o 3.12 de python.org y vuelve a ejecutar este archivo.
 pause
 exit /b 1
)
py -3.12 -m venv .venv
if errorlevel 1 py -3.11 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
where ffmpeg >nul 2>nul
if errorlevel 1 (
 echo Falta FFmpeg. Instala FFmpeg con libass y agregalo al PATH.
 echo Si tienes winget: winget install --id Gyan.FFmpeg -e
 echo Cierra esta ventana y abre Instalar.bat otra vez despues de instalarlo.
 pause
 exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 goto error
echo Instalacion terminada. Abre Iniciar.bat.
pause
exit /b 0
:error
echo No se pudo completar la instalacion. Revisa el mensaje anterior.
pause
exit /b 1
