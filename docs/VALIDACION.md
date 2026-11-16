# Validación realizada · 16 de noviembre de 2026

## Entorno real

Linux x86_64, Python 3.12.14, FFmpeg del entorno (`ffmpeg-validado.txt`), sin GPU CUDA detectable (CTranslate2 devolvió 0 dispositivos). Dependencias exactas instaladas en `entorno-validado.txt`. No se ejecutó Windows ni una RTX 3060. Los tiempos no son extrapolables a ese hardware.

## Pruebas automatizadas

**23 pruebas aprobadas**, 21,99 s en la ejecución final. Salida completa: `pruebas.txt`. `pip check` no encontró dependencias incompatibles. La compilación de los archivos Python no produjo errores.

Se verificaron:

- SQLite: identidad de archivo, estados, exportaciones y transacciones por bloque.
- Reanálisis sin repetir, continuación en una revisión posterior y reanudación tras fallo en el segundo bloque.
- Rechazo de candidatos solapados incluso al cambiar la configuración; número de propuestas sin forzar 20.
- Audio: energía, cambios, silencio; OpenCV: muestreo, histogramas y salida del detector (con patrón sintético, no con personas reales).
- Ollama: respuestas controladas válidas, citas inválidas y fallo de conexión. Una llamada real a 127.0.0.1:11434 confirmó ausencia del servicio y retorno al análisis heurístico; no se validó generación real con el modelo Qwen3.
- Transcripción: validación de opciones y adaptación de resultados mediante dobles de prueba. La inferencia real de Tiny está documentada abajo.
- Subtítulos: agrupación SRT, escape de ASS, resaltado por palabra, precisión de tiempos y remapeo tras eliminar silencio.
- FFmpeg real: cuatro exportaciones de prueba para ajuste, centro, modo rostros sin detección y composición streamer con ROI manual; zoom/fundidos/subtítulos, duración tras recortar silencio, audio y dimensiones.
- Fuentes: copia intacta del original, permiso obligatorio, validación de dominios; rechazo de DRM e historial de directo mediante metadatos simulados. **Estas últimas pruebas no validan YouTube/Twitch reales.**
- Streamlit AppTest: inicio vacío, proyecto con candidatos, aceptación, generación de vista previa y exportación real desde botones del editor. No se realizó inspección visual del navegador ni ensayo de instalación en Windows.

## Flujo completo real con voz

`examples/run_e2e.py` procesa `examples/autorizado.mp4`: 24,95 s, 640×360, voz Flite sintética en inglés y patrón visual generado localmente. Texto propio incluido, reutilización autorizada CC0.

En la última ejecución:

| Medida | Resultado |
|---|---:|
| Transcriptor | faster-whisper Tiny CPU int8 |
| Bloques nuevos | 1 |
| Tiempo de análisis | 5,258 s |
| Candidatos | 1 |
| Palabras con tiempos | 70 |
| Render más comprobación de reanudación | 14,453 s |
| Tiempo total | 19,876 s |
| RAM máxima muestreada del proceso Python | 322,0 MB |
| Video exportado | 1080×1920, 24,95 s, H.264/AAC |
| Bloques en segunda revisión | 0 |

Las mediciones de RAM son RSS muestreada cada 50 ms del proceso Python: no incluyen los procesos FFmpeg ni VRAM. No son el máximo exacto del sistema. La descarga inicial de Tiny ya estaba en caché en esta ejecución y no se incluye en el tiempo medido.

El MP4 se volvió a abrir con FFprobe y se extrajo un fotograma para inspección: subtítulos visibles, palabra activa amarilla y video preservado con bandas en modo ajustar. La prueba confirma mecánica y sincronización de ese ejemplo; no mide calidad de selección en contenido real.

## Sin validar o sin implementar por completo

- Windows, scripts BAT en Windows, CUDA/cuDNN, RTX 3060, NVENC (no se utiliza).
- Inferencia real con Small/Base/Medium y Ollama Qwen3 4B.
- Captura o recuperación real de YouTube/Twitch, DVR y VOD; no se declara compatibilidad operativa validada.
- Videos de varias horas, consumo conjunto de todos los procesos y rendimiento con carga GPU real.
- Calidad de rostros y cámara del streamer con personas reales. No hay identificación ni hablante activo.
- Captura incremental continua de directos, tracking robusto y editor multipista.

## Entrega

El primer intento de adjuntar el ZIP en el chat no pudo utilizar la ruta de salida del cliente porque estaba montada como solo lectura. Posteriormente se conectó GitHub y el usuario proporcionó el repositorio de destino.

Código: https://github.com/rodrigopilco1988-ui/clip-libre

Release prevista para esta versión: https://github.com/rodrigopilco1988-ui/clip-libre/releases/tag/v0.1.0

La Release enlaza el ZIP de código, documentación y ejemplos y `SHA256SUMS.txt`, guardados en la carpeta `distribucion/` del repositorio. Esta vía evita depender del servicio de subida de adjuntos de Releases, que rechazó la autenticación en esta sesión. El checksum se publica por separado para evitar una referencia circular dentro del ZIP. La existencia y descarga de esos adjuntos debe comprobarse al publicar. El ZIP no contiene entornos virtuales, pesos de modelos, ejecutables externos ni la base de datos con rutas de esta máquina.

La matriz de CI se ejecuta en GitHub Actions para Linux y Windows. Sus resultados son adicionales a las 23 pruebas locales documentadas arriba; no validan GPU, scripts BAT interactivos, fuentes remotas ni calidad de seguimiento sobre personas reales. Consulta el estado real en https://github.com/rodrigopilco1988-ui/clip-libre/actions .
