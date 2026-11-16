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
