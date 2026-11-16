# Arquitectura y orden de implementación

Proyecto nuevo e independiente. Python 3.11/3.12 y Streamlit sirven la interfaz exclusivamente en 127.0.0.1. El navegador no procesa IA. SQLite guarda fuentes, sesiones de análisis, bloques confirmados, candidatos, estado humano y exportaciones. FFmpeg y FFprobe son procesos separados. No hay API de pago.

1. `sources.py` / `media.py`: validación, permiso de reutilización, copia de originales, información multimedia y segmentos finitos de enlaces públicos.
2. `store.py` / `pipeline.py`: proyectos, hash del contenido, progreso transaccional por fuente/configuración y sesión. Procesa uno o varios bloques por revisión; reanuda bloques confirmados. Un fallo en un bloque repite solo ese bloque. La deduplicación rechaza cualquier intersección con candidatos existentes, incluidos los descartados.
3. `transcribe.py`: faster-whisper, palabras y VAD. Small inicial; Tiny/Base/Medium disponibles. CPU int8 y selección CUDA int8_float16. Libera el modelo antes de Ollama, sin mantener una caché GPU de Whisper.
4. `signals.py` / `rank.py`: RMS por segundo, cambios de energía, silencios, histogramas de escenas y rostros Haar. Contexto verbal y márgenes para candidatos. Hasta 20 propuestas por bloque, sin cuotas. Ollama opcional usa texto y exige cita verificable; no ve imágenes. Las citas no garantizan la veracidad de todos los títulos: revisión humana obligatoria.
5. `subtitles.py` / `render.py`: línea temporal remapeada al reducir silencios, SRT, ASS con palabra activa y animación, encuadres, detección facial aproximada, composición de cámara/gameplay, zoom oscilante y fundidos. MP4 H.264/AAC y registro JSON de edición. No modifica originales.
6. `app.py`: biblioteca, configuración, estados de aceptación, edición de palabras/tiempos, encuadre, vista previa renderizada y exportación individual o por lotes.

## Decisiones y límites

- Son trabajos locales síncronos. El estado real se escribe en SQLite y se muestra por etapa/bloque. La codificación no presenta un porcentaje inventado: muestra que FFmpeg sigue trabajando. No hay cancelación interactiva ni cola multiusuario. Interrumpir el proceso conserva los originales y los bloques confirmados.
- La reanudación incremental está implementada para sucesivas revisiones de un archivo finito importado. No hay vigilancia continua de un archivo creciente, ensamblado de segmentos de directo ni deduplicación de importaciones remotas solapadas. Un enlace se importa como un segmento independiente; sus tiempos son relativos al archivo descargado.
- Un bloque es una frontera de contexto: no se proponen clips que crucen dos bloques. No es un analizador semántico de video completo. Los cambios de escena se estiman con histogramas muestreados; pueden perder eventos breves.
- Haar detecta rostros frontales y el encuadre suaviza sus centros. No es reconocimiento de identidad, seguimiento de hablante, segmentación de personas ni tracking por identidad. La región de cámara se sugiere por rostros en esquinas y exige confirmación manual; no se validó con gameplay real.
- El editor tiene reproducción y controles visuales, no una línea de tiempo multipista ni manipuladores de recorte sobre el lienzo. Las plantillas cambian ajustes reales. Los efectos disponibles son zoom y fundidos; no hay catálogo de transiciones ni B-roll.
- La puntuación y las palabras clave son heurísticas, sin predictor entrenado de viralidad. Ollama añade análisis textual, pero no garantiza reconocer humor o sorpresa ni acontecimientos visuales. No se incluye VLM ni diarización audiovisual.
- El backend soporta archivos sin audio y propone cambios visuales si los detecta; no fabrica transcripción. La sugerencia automática es opcional y puede no generar clips.
- Ajustes del editor se guardan como metadatos junto a cada render. Los cambios de palabras e intervalo pueden guardarse en SQLite. El lote usa los ajustes globales actuales; no hay una configuración de efectos distinta por candidato persistida antes del render.
- Una descarga remota puede fallar por restricciones, DRM, autenticación, falta de DVR o cambios del proveedor. No se usan cookies ni credenciales y no se intenta sortear restricciones.

## Trabajo pendiente para una edición completa

Validación de instalación interactiva en Windows y de RTX 3060, servicio Ollama real con Qwen3 4B, modelos Small/Medium, videos largos y concurrencia; pruebas autorizadas en YouTube/Twitch; captura incremental persistente de directos, detector de personas y hablante activo, seguimiento robusto y editor multipista. Cada avance requiere pruebas específicas y actualización del estado de validación.

## Ampliación 0.2.0

`import_local` admite audio y conserva una copia íntegra antes de crear la onda visual con FFmpeg. `inspect_url` consulta metadatos; `import_url` importa VOD completos o tramos. `capture_live` guarda segmentos finitos a partir de los flujos accesibles devueltos por el extractor, sin credenciales. La captura no tiene historial automático ni reanudación continua. Las previsualizaciones de candidatos se generan y cachean como archivos cortos: la UI no carga el video largo entero para reproducir un clip. La interfaz mantiene las herramientas del editor y añade creación automática tras importar. Deno y yt-dlp-ejs se instalan como dependencias locales para el extractor; el backend detecta el ejecutable del entorno virtual y lo comunica al extractor API y CLI.

Los límites anteriores sobre tramos remotos finitos se amplían para permitir VOD completos. Se mantienen los límites de acceso de los proveedores y las limitaciones de análisis visual/seguimiento. El estado más reciente de las fuentes está en `FUENTES-0.2.0.md`.

## Transcripción tolerante a errores CUDA · 0.2.1

La detección de un dispositivo NVIDIA no se interpreta como prueba de que CUDA/cuDNN estén operativos. El intento GPU se ejecuta completamente, incluida la iteración del generador perezoso de Whisper, dentro de una operación que libera el motor en finally. Ante una excepción recuperable de CUDA se descarta toda salida parcial, se cierra el generador, se descarga el modelo y se reintenta desde el inicio del bloque en CPU int8. Un fallo de GPU se recuerda en memoria para no repetirlo en cada bloque; se restablece al reiniciar la aplicación. Esto se aplica también si se eligió cuda explícitamente. Si falla CPU, el bloque no se confirma como terminado.

El backend real y su aviso se guardan en los metadatos del bloque. El pipeline incluye los avisos y los dispositivos utilizados en su informe; la UI muestra el cambio durante el trabajo y conserva el aviso tras el rerun de importación. La configuración y su hash no cambian al recurrir a CPU, de modo que la reanudación usa los bloques ya confirmados. No es un instalador de bibliotecas NVIDIA ni una validación de CUDA en RTX 3060. Las excepciones recuperables están cubiertas; un aborto nativo del proceso no se convierte en una excepción Python.

## Corrección de revisión y soporte GPU · 0.2.2

El botón Ver clip usa view_button_ID y el estado view_open_ID; nunca escribe el estado del propio widget. Las vistas previas de 24 fps se escriben a un archivo temporal exclusivo y se renombran solo después de terminar. El reintento limpia temporales fallidos.

`gpu_runtime.py` localiza exclusivamente los directorios NVIDIA instalados en el entorno Python, añade sus bin a la búsqueda de DLL, conserva los handles y carga por ruta absoluta cuBLASLt, cuBLAS y cuDNN. La reparación instala cuatro paquetes opcionales oficiales. No cambia System32 ni instala controladores. La comprobación de inferencia se ejecuta en un subproceso sin alternativa CPU, evitando que un aborto nativo del comprobador cierre Streamlit. Solo tras éxito CUDA se limpia la caché de fallo de la sesión principal. La propia transcripción conserva la alternativa CPU y utiliza beam_size 1 en CPU y 3 en CUDA.
