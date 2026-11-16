# Historial de validación · 16 de noviembre de 2026

## Entorno real

Linux x86_64, Python 3.12.14, FFmpeg del entorno (`ffmpeg-validado.txt`), sin GPU CUDA detectable (CTranslate2 devolvió 0 dispositivos). Dependencias exactas instaladas en `entorno-validado.txt`. El entorno local no dispone de Windows ni de una RTX 3060; la validación adicional en Windows Server mediante GitHub Actions se documenta al final. Los tiempos no son extrapolables a ese hardware.

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

- Inicio mediante Iniciar.bat y uso manual en el Windows del usuario, CUDA/cuDNN, RTX 3060, NVENC (no se utiliza). El instalador BAT sí se ejecutó automáticamente en Windows para 0.1.2.
- Inferencia real con Small/Base/Medium y Ollama Qwen3 4B.
- Captura o recuperación real de YouTube/Twitch, DVR y VOD; no se declara compatibilidad operativa validada.
- Videos de varias horas, consumo conjunto de todos los procesos y rendimiento con carga GPU real.
- Calidad de rostros y cámara del streamer con personas reales. No hay identificación ni hablante activo.
- Captura incremental continua de directos, tracking robusto y editor multipista.

## Entrega

El primer intento de adjuntar el ZIP en el chat no pudo utilizar la ruta de salida del cliente porque estaba montada como solo lectura. Posteriormente se conectó GitHub y el usuario proporcionó el repositorio de destino.

Código: https://github.com/rodrigopilco1988-ui/clip-libre

Release prevista para esta versión: https://github.com/rodrigopilco1988-ui/clip-libre/releases/tag/v0.2.1

La Release enlaza el ZIP de código, documentación y ejemplos y `SHA256SUMS.txt`, guardados en la carpeta `distribucion/` del repositorio. Esta vía evita depender del servicio de subida de adjuntos de Releases, que rechazó la autenticación en esta sesión. El checksum se publica por separado para evitar una referencia circular dentro del ZIP. La existencia y descarga de esos adjuntos debe comprobarse al publicar. El ZIP no contiene entornos virtuales, pesos de modelos, ejecutables externos ni la base de datos con rutas de esta máquina.

La matriz de CI se ejecuta en GitHub Actions para Linux y Windows. Sus resultados son adicionales a las 23 pruebas locales documentadas arriba; no validan GPU, scripts BAT interactivos, fuentes remotas ni calidad de seguimiento sobre personas reales. Consulta el estado real en https://github.com/rodrigopilco1988-ui/clip-libre/actions .

## Corrección 0.1.1 para Windows

La primera ejecución de Actions (43962091397) aprobó Linux y detectó seis fallos en Windows: cinco por la eliminación de `-filter_complex_script` en el FFmpeg reciente del runner y uno por lectura de ASS sin codificación explícita en una prueba. Se añade selección compatible entre el parámetro antiguo y `-/filter_complex`; la prueba lee UTF-8 explícitamente. La ejecución de la corrección aprobó las 23 pruebas en ambos sistemas: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43962614502 . Commit de código probado: `43a0dde469e436d39641947f0cdb29c0b6acd75c`. Incluye exportaciones reales con FFmpeg y vista previa/exportación desde Streamlit AppTest. Esta prueba usa el runner Windows de GitHub, no la máquina del usuario ni su GPU. La instalación de dependencias se hizo con pip en CI; no se probaron los BAT interactivos. La salida de resumen se conserva en `ci-0.1.1.txt`.

## Corrección 0.1.2 del instalador

El usuario encontró un lanzador `py` sin runtime 3.12 y un posterior intento de usar una ruta inexistente. El BAT ahora verifica la ejecución real de Python 3.12/3.11 de 64 bits mediante un archivo temporal de comprobación, busca también Python del PATH y comprueba que se haya creado el intérprete de `.venv`. Si falta Python, se detiene con instrucciones concretas. No instala Python automáticamente.

CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43963645017

Commit de código validado: `b5ae16b1c4bb917d287be01357d479ca6fad52db`.

- Windows: **26 pruebas aprobadas en 16,58 s**. Tres pruebas ejecutan el BAT real: lanzadores que retornan éxito sin ejecutar Python, alternativa del PATH con `py` fallando, e intérprete real disponible. Se utiliza una carpeta con espacios.
- Linux: **23 aprobadas y 3 omitidas en 8,42 s**; las omitidas requieren cmd.exe de Windows.
- En Windows se ejecutó además `Instalar.bat --sin-pausa`: creó `.venv`, instaló las dependencias y mostró «Instalacion terminada». `pip check` confirmó dependencias consistentes. El registro se resume en `ci-0.1.2.txt`.
- El modo sin pausa evita únicamente la tecla final para CI. No constituye prueba de Iniciar.bat, de la GPU ni de la máquina del usuario.

## Versión 0.2.0: interfaz, enlaces y podcasts

CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43972307282

Commit de código probado: `1fd3c3904ce2958794d050b6f0504317ae7cdba5`.

- Windows: **34 pruebas aprobadas en 16,85 s**.
- Linux: **31 aprobadas y 3 omitidas, específicas de cmd.exe, en 12,07 s**.
- `Instalar.bat --sin-pausa` volvió a completar la instalación en Windows con Deno y los componentes adicionales del extractor. `pip check` confirmó consistencia.
- Nuevas pruebas: podcast de audio y original intacto, exportación subtitulada de ese podcast, dominios Twitch clips/YouTube Shorts y Live, comandos de VOD completo y tramos con descargador simulado, metadatos de directo y rechazos, HLS real por HTTP local con captura finita, mensajes de red/certificado/acceso y ejecución real local de JavaScript con Deno.
- Streamlit AppTest verifica las cuatro opciones de fuente. Chromium headless comprobó el inicio, la selección Twitch y la pantalla Mis clips; se inspeccionó la captura del inicio terminado, sin los indicadores temporales de carga.
- Flujo adicional con audio autorizado de voz sintética: 24,96 s, 70 palabras con Tiny CPU, exportación 720×1280 con audio y subtítulos, original preservado; 16,35 s totales en este entorno. Informe en `podcast-0.2.0.json`.

No se descargó contenido de terceros para estas pruebas. Los intentos de consulta de metadatos reales fallaron: YouTube por bloqueo proxy 403 y Twitch por certificado no verificable en esta red. Se mantuvo TLS y no se eludió el bloqueo. Las pruebas controladas no sustituyen la validación de descargas/directos de esos proveedores. Consulta `FUENTES-0.2.0.md` para la matriz de compatibilidad y límites.

Las secciones anteriores conservan el historial de versiones previas. Las capturas de interfaz con una tarjeta de demostración no prueban calidad de selección en videos reales ni anuncian una clonación de un producto de terceros.

## Versión 0.2.1: fallo CUDA y continuación CPU

CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43975505469

Commit de código probado: `5e93443bf5bb78235cd0a5400a6bf4198515e334`.

- Windows: **40 pruebas aprobadas en 23,56 s**.
- Linux: **37 aprobadas y 3 omitidas específicas de Windows en 13,07 s**.
- Instalador BAT completo y `pip check` vuelven a finalizar correctamente en Windows.
- Se reproduce de forma controlada el error `Library cublas64_12.dll is not found or cannot be loaded` tanto en auto como en cuda. Se verifica el cambio a CPU, el aviso y que no se reintente la GPU en el siguiente bloque de la sesión.
- Se inyecta un error tras producir un segmento parcial GPU: se verifica que se descarte y que el modelo GPU se descargue antes de cargar CPU. Se comprueba que una GPU funcional se siga usando y que un fallo CPU no se informe como éxito.
- La prueba de integración verifica progreso incremental de 6 a 8 segundos usando CPU tras el fallo, y cero bloques repetidos en la siguiente revisión.
- Prueba real adicional, sin dobles de Whisper: se forzó CUDA en el entorno local no compatible; CTranslate2 devolvió «CUDA driver version is insufficient for CUDA runtime version» y se transcribieron después 70 palabras en CPU. Metadatos: `transcribe-0.2.1-fallback-real.json`. También pasó una transcripción CPU directa.

El error exacto de DLL se cubre con un doble de prueba, no con una RTX 3060 física. La prueba real cubre otro fallo recuperable del mismo backend. La aceleración en el equipo del usuario y los abortos nativos no se presentan como validados. El progreso se guarda solo al completar cada bloque y el hash de configuración no cambia al recurrir a CPU.
