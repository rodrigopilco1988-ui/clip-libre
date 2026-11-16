@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto falta_entorno
echo Descargando soporte NVIDIA opcional. Puede superar 1,3 GB.
echo Cierra Clip Libre antes de continuar para evitar archivos bloqueados.
".venv\Scripts\python.exe" -m cliplivre.gpu_runtime install
if errorlevel 1 goto error
echo Reinicia la aplicacion y elige auto. Comprueba el procesador usado al analizar.
if /i not "%~1"=="--sin-pausa" pause
exit /b 0
:falta_entorno
echo Ejecuta Instalar.bat primero.
goto error
:error
echo No se pudo confirmar el soporte GPU. Revisa el mensaje anterior.
if /i not "%~1"=="--sin-pausa" pause
exit /b 1
