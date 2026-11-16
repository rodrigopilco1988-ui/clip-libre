# Clip Libre · 0.1.2

Aplicación local nueva para convertir videos en clips revisables. Interfaz propia en español, sin servicios de IA de pago. Primera entrega funcional; no equivale todavía a todas las capacidades de un editor comercial.

## Windows: instalar y abrir

1. Extrae todo el proyecto en una carpeta con espacio libre. Los originales se copian: reserva al menos el tamaño de tus videos más las exportaciones.
2. Instala Python **3.12 de 64 bits** (o 3.11) desde https://www.python.org/downloads/windows/.
3. Instala FFmpeg y FFprobe con el filtro ASS/libass, por ejemplo la distribución enlazada en https://ffmpeg.org/download.html. Añade su carpeta `bin` al PATH. `Instalar.bat` detecta si falta y muestra la alternativa con winget. Las licencias del binario dependen de su compilación.
4. Haz doble clic en **Instalar.bat**. Requiere internet para descargar dependencias. No instala Ollama, controladores NVIDIA ni CUDA automáticamente.
5. Haz doble clic en **Iniciar.bat**. Abre la aplicación en http://127.0.0.1:8501. Cierra esa ventana para detenerla. El uso diario no requiere terminal.
6. Importa `examples/autorizado.mp4`, confirma permiso, configura idioma inglés y Tiny para reproducir la prueba rápida. Para tus videos en español puedes usar Small, la opción inicial. La primera transcripción descarga el modelo; requiere internet y espacio de disco. Después se reutiliza la caché en `data/modelos/`.
7. Analiza, acepta candidatos, corrige palabras e intervalos, genera vista previa y exporta. Los archivos aparecen en `data/editados/clip_…/`. El original está separado en `data/originales/`.

## RTX 3060 12 GB / 32 GB RAM

Small y bloques de 50 minutos son el punto de partida configurable, no un rendimiento certificado. Los bloques usan audio mono de 16 kHz en memoria (aprox. 192 MB por 50 minutos, aparte de modelos y datos). La muestra visual se reduce a 320×180. FFmpeg exporta en CPU con libx264 para evitar añadir dependencias de NVENC; CUDA se usa para Whisper cuando está disponible.

Para CUDA instala un controlador NVIDIA y las bibliotecas CUDA/cuDNN compatibles con la versión instalada de CTranslate2, siguiendo https://github.com/SYSTRAN/faster-whisper#gpu. La detección de GPU no garantiza que estén las DLL correctas. Si ocurre un error, la UI lo muestra: selecciona CPU para continuar. **Pasan 26 pruebas en Windows y 23 en Linux mediante GitHub Actions. El instalador BAT completo también se validó en Windows sin la pausa final. Iniciar.bat, CUDA y la RTX 3060 siguen sin validar.**

Ollama es opcional: instala https://ollama.com/ y descarga **Qwen3 4B** (`qwen3:4b`, pesos con licencia Apache 2.0) desde su interfaz o, una sola vez, con `ollama pull qwen3:4b`. Activa Ollama en la aplicación cuando el servicio local esté listo. No hay descarga automática de ese modelo desde Clip Libre. Se solicita salida JSON y descarga de memoria tras cada petición (`keep_alive: 0`). Whisper se libera primero. Detén otros modelos GPU; no hay un gestor que pueda garantizar VRAM libre en todos los procesos. El modo sin Ollama está disponible y el fallo del servicio conserva las propuestas heurísticas.

## Archivos y privacidad

- `data/history.sqlite3`: proyectos, sesiones, bloques, candidatos y exportaciones.
- `data/originales/`: copias intactas de las fuentes importadas.
- `data/editados/`: videos editados, SRT, ASS, filtros y decisiones JSON.
- El código no envía videos/transcripciones a una IA remota. Enlaces y primeras descargas de modelos/dependencias sí usan internet. Streamlit se inicia sin telemetría y solo en loopback. No expongas el servidor a internet.
- Usa únicamente contenido con acceso permitido y permiso de reutilización. No introduzcas cookies ni credenciales; no se eluden DRM ni restricciones.

## Qué puedes usar

Importación local de MP4/MOV/MKV/WebM y otros formatos que FFmpeg soporte; bloques incrementales por revisión; Whisper y palabras; heurísticas acústicas/visuales; integración Ollama con alternativa sin servicio; revisión, filtro y aceptación; ajuste de tiempos y texto; vista previa renderizada; MP4 9:16, 1:1, 16:9 hasta 1080×1920/1920×1080; subtítulos SRT/ASS resaltados y opcionalmente incrustados; zoom suave, silencios configurables, fundidos, encuadre por centro/rostros y cámara/gameplay con región manual; exportación en lote de aceptados.

Los enlaces YouTube/Twitch son **experimentales y no validados en vivo**. Se descargan tramos finitos de hasta 50 minutos. No hay captura continua ni reanudación remota de un directo. Los tiempos de esos clips son relativos al segmento descargado. Un directo sin historial recuperable puede requerir esperar al VOD o usar una grabación autorizada.

Consulta `docs/ARQUITECTURA.md` y `docs/VALIDACION.md` para límites y resultados concretos. No se implementaron identificación de personas, seguimiento fiable de hablante activo, editor multipista ni comprensión semántica visual.

## Pruebas y reproducción

Abre `Probar.bat` para pruebas automatizadas (FFmpeg necesario). Para el flujo real de voz incluida: `.venv\Scripts\python.exe examples\run_e2e.py`. Este comando de desarrollo utiliza Tiny CPU, descarga el modelo si falta y exporta a 1080×1920. La UI permite hacer el mismo recorrido sin terminal. El informe de la ejecución realizada se incluye en `examples/resultado/informe.json`.

El video de prueba fue generado localmente con FFmpeg testsrc2 y voz Flite, con texto propio. No contiene material de terceros ni personas reales. Su texto se incluye en `examples/voz.txt`. Se autoriza su reutilización bajo CC0. Flite no es necesario para usar ni probar la aplicación con el MP4 incluido.

## Código y distribución

Código nuevo bajo MIT. Dependencias y modelos tienen sus licencias independientes: `docs/LICENCIAS.md`. No se distribuyen FFmpeg, Ollama, Python, CUDA ni pesos de modelos dentro del ZIP. La instalación y descarga inicial requieren internet; los proveedores pueden cambiar disponibilidad o condiciones.

Para desarrollo: crea un entorno virtual e instala `pip install -r requirements.txt`, luego `python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false`.

## Si aparece «No runtime installed that matches 3.12»

El lanzador `py` está instalado pero no encuentra un intérprete compatible. Instala Python 3.12 de 64 bits desde python.org, marca **Add python.exe to PATH**, completa la instalación y vuelve a abrir `Instalar.bat`. No hace falta instalar Python 3.11 además. La versión 0.1.2 comprueba que el intérprete realmente se ejecuta, permite usar Python del PATH sin depender de `py`, y no continúa hacia una ruta `.venv` inexistente. Si conserva un entorno incompleto, renombra únicamente `.venv` como `.venv-anterior` y vuelve a instalar; conserva `data/`.
