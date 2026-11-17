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

Release prevista para esta versión: https://github.com/rodrigopilco1988-ui/clip-libre/releases/tag/v0.3.0

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

## Versión 0.2.2: Ver clip, reparación NVIDIA y rendimiento

CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43980626584

Commit de código probado: `70c61116b067032d31582c3caabe9048017a6e15`.

- Windows: **45 pruebas aprobadas en 20,73 s**.
- Linux: **42 aprobadas y 3 omitidas específicas de Windows en 13,57 s**.
- La regresión AppTest pulsa Ver clip, comprueba ausencia de excepción y vuelve a cambiar un filtro manteniendo la apertura. El fallo anterior era modificar st.session_state usando la misma clave del botón ya creado.
- Chromium real comprobó el clic y esperó la aparición de un video visible, sin excepción Streamlit. También comprobó la presencia de controles de reparación. Capturas `view-0.2.2.png` y `gpu-0.2.2.png`; usan el proyecto sintético de demostración descrito en la validación 0.2.0.
- El instalador normal y RepararGPU.bat se ejecutaron de verdad en Windows. Se instalaron las bibliotecas NVIDIA en .venv y se cargaron por ruta absoluta **cublasLt64_12.dll, cublas64_12.dll y cudnn64_9.dll**. El informe mostró errors=[] y missing=[]. pip check no encontró incompatibilidades.
- Las pruebas del cargador verifican búsqueda de directorios, retención y reutilización de handles, y rechazo de bibliotecas ausentes. La prueba del comprobador garantiza que use CUDA sin alternativa CPU; se controla tanto éxito como fallo.
- El runner de Windows no dispone de una RTX para inferencia. La carga de DLL no se presenta como prueba de aceleración física. El botón Probar transcripción en GPU ejecuta un modelo Tiny en un subproceso y solo muestra éxito si completa la inferencia CUDA. Puede requerir descargar Tiny y actualizar el controlador NVIDIA.
- Vistas previas limitadas a 24 fps y guardadas por renombrado atómico; una prueba reproduce un fallo FFmpeg con archivo parcial y comprueba su eliminación.

### Ensayo CPU

Whisper Tiny int8, una sola carga de modelo, calentamiento previo y audio sintético autorizado de 24,95 s. Cuatro ejecuciones alternadas con beam_size 3,1,1,3: medianas **1,037 s** para 3 y **0,7665 s** para 1; 70 y 69 palabras respectivamente. Datos en `cpu-beam-0.2.2.json`. La versión usa búsqueda de ancho 1 en CPU y conserva 3 en CUDA. Es un ensayo pequeño de transcripción, no tiempo total de la app, no una prueba de calidad ni una garantía para videos largos o para el hardware del usuario.

Las bibliotecas opcionales de NVIDIA son propietarias gratuitas y no se redistribuyen dentro del ZIP. Se descargan desde PyPI; no se copian DLL a System32 ni se instalan controladores. La exportación y OpenCV siguen en CPU. Los fallos irrecuperables de inferencia en el comprobador no cierran el proceso principal porque se ejecuta como hijo.

## Versión 0.3.0: minutos, editor y reducción de esperas

CI final: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/43991112722

Commit de código probado: `78c5645523de60f714311e0b0d2391f3ea1ad9a9`.

- Windows: **63 pruebas aprobadas en 37,86 s**.
- Linux: **60 aprobadas y 3 omitidas específicas de Windows en 15,52 s**.
- Instalador normal, reparación NVIDIA, carga real de DLL y pip check volvieron a terminar correctamente en Windows. No equivale a inferencia en una RTX física; se conserva el botón de comprobación del equipo del usuario.
- Se verifican controles en minutos, análisis completo y máximo desactivado por defecto; propuestas de más de 300 s; selección que abre el editor; cuadros añadidos/quitados; configuración/texto guardados; colores de zonas de origen/destino en exportaciones de 1/2/3 cuadros y coincidencia con la guía; texto ASS y subtítulos; seek real a un tramo posterior; caché y migración de transcripciones anteriores; regeneración de propuestas pendientes con preservación de aceptación, descarte, edición y exportaciones.
- Se verifican el audio propio de cada clip al exportar un lote con reducción de silencios y el guardado de palabras que cruzan el borde del intervalo.
- Chromium, contra un proceso nuevo de Streamlit, comprobó selección automática del editor, dos cuadros, texto y aparición del reproductor de la vista previa vertical sin excepción. Se necesita reiniciar la aplicación al actualizar para no conservar módulos importados de una versión anterior. Capturas editor-0.3.0.png y editor-video-0.3.0.png, con el proyecto sintético de demostración ya descrito.
- Prueba manual: fuente técnica local de 260 s, intervalo 45–255 s (0,75–4,25 min), dos cuadros y texto: **MP4 de 210 s (3,5 min), 360×640, audio conservado, 6,473 s de render**. Color y tono, no contenido real ni prueba de semántica. Informe clip-largo-0.3.0.json.

Ensayo controlado sin pytest concurrente: recorte tardío de 4 s en fuente de 120 s, mismo libx264 ultrafast y 360×640, mediana de renderer anterior **1,0305 s** frente a nuevo **0,2765 s**. En ejemplo autorizado de 24,95 s, Tiny CPU y visión rápida: primer análisis **2,393 s**; tras cambiar duración y reutilizar resultados **0,005 s**, con dos aciertos de caché y una transcripción reutilizada. Memoria RSS muestreada al final 217,4 MB, no máximo del sistema. Ver rendimiento-0.3.0.json y CAMBIOS-0.3.0.md. No se extrapolan esos tiempos a videos largos, red o hardware del usuario.

Limitaciones actuales: propuestas dentro de los límites de cada bloque, composición de zonas del mismo archivo mediante controles (sin arrastre ni multipista), guía estática y render de video a demanda; muestreo rápido puede perder cambios entre fotogramas clave. Procesamiento de audio, filtros y exportación libx264 siguen en CPU. Las limitaciones de proveedores remotos y validación física GPU anteriores se mantienen.

## Versión 0.4.0: configuración única, límites y recorte interactivo

Código: `1663ad2e96b62fb1a765c8f4a188106ec2b764a0`.
CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44003240521

Prueba local completa: **74 aprobadas, 3 omitidas de Windows, 33,46 s**. CI final: **77 aprobadas en Windows (44,15 s)** y **74 aprobadas + 3 omitidas en Linux (29,20 s)**. Instalar.bat, RepararGPU.bat, carga real de DLL NVIDIA y pip check completados correctamente. Informe NVIDIA sin bibliotecas ausentes ni errores. No hubo inferencia en GPU física; registro íntegro `ci-0.4.0.txt`.

- La pantalla inicial guarda una única configuración por proyecto. AppTest comprueba que 0:30–1:30 se convierte en 30–90 segundos, mientras que 30–110 minutos se convierte en 1800–6600 segundos de la fuente. No existe una pestaña adicional de configuración de análisis.
- El clasificador respeta límites también en propuestas por audio/visión y transcripciones de un solo segmento largo; se prueban duraciones variadas. Los clips humanos incompatibles se conservan sin impedir nuevas alternativas dentro del rango.
- Se prueban generación del comando de descarga completa y 30–110 minutos, ausencia del límite de 50 minutos y ausencia de sustitución oculta por cinco minutos. Twitch sin historial devuelve error; YouTube usa una instantánea histórica. Son pruebas controladas; no validan descarga real de los proveedores.
- Se comprueba que un archivo importado parcialmente no se reutilice como VOD completo, que se unan bloques ASR previos solo cuando cubren todo el intervalo pedido y que SQLite conserve el análisis completo al regenerar candidatos.
- Servidor HTTP local con pruebas reales GET/HEAD, rangos, sufijos, errores 404/416 y lectura acotada. Evita cargar todo el archivo o recodificar para verlo.
- Exportación FFmpeg real de composición con foto, logo y títulos temporizados; se mantienen pruebas de 1/2/3 cuadros, subtítulos, audio, seek y exportación.

### Flujo real en Chromium

Fuente propia autorizada: patrón visual y voz sintética de `examples/autorizado.mp4`, repetido por copia de paquetes hasta 10 minutos. Tiny CPU, idioma inglés, pesos ya descargados. Generación desde el botón inicial: **20,79 s** hasta la galería. Ocho candidatos: **38,74; 76,86; 51,68; 65,96; 41,00; 76,90; 76,90; 51,84 s**. Todos cumplen 30–90 s; no todos duran el máximo.

El mismo flujo eligió un clip, abrió el editor, esperó video decodificado, arrastró el recorte y reprodujo el video; guardó y comprobó SQLite. Coordenada horizontal normalizada de origen: **0,341796875 → 0,441796875**. Sin excepciones Streamlit ni errores JavaScript registrados. Informe `browser-0.4.0.json`; capturas `source-0.4.0.png`, `clips-0.4.0.png`, `editor-0.4.0.png` y `editor-recorte-0.4.0.png`.

Es un ensayo sintético pequeño con contenido repetido, no un benchmark de streams reales ni una garantía de tiempo. El analizador registró 19,452 s y RSS muestreada de 330,8 MB (no máximo de memoria del sistema); informe `rendimiento-0.4.0.json`. La descarga remota real YouTube/Twitch, inferencia Ollama y aceleración en una RTX 3060 física siguen pendientes; se mantienen los límites documentados anteriormente. El recorte interactivo requiere un códec que el navegador pueda decodificar; FFmpeg ofrece vista previa compatible. La composición interactiva no sustituye la revisión del render final para tipografía, animaciones y seguimiento.

## Versión 0.4.1: guía antes de importar un canal Twitch

Código probado: `13c7ba3dd8e4dd71b8ebb649e560ccaa41354ff5`.
CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44005078623

Prueba local: **76 aprobadas, 3 omitidas específicas de Windows, 31,38 s**.

La interfaz identifica localmente un enlace HTTPS de canal Twitch; no lo confunde con `/videos/ID`, clips, rutas reservadas ni otros dominios. Antes de importar, muestra un enlace a los videos públicos del canal y explica la grabación futura. Generar permanece desactivado para el intento de historial del canal y se habilita al elegir «Grabar desde ahora» con permiso confirmado. Cambiar al enlace de VOD devuelve el flujo normal. No graba ni consulta metadatos automáticamente por pegar el enlace.

AppTest verifica las transiciones sin acceso a red. Chromium real comprueba el href de videos del canal, bloqueo/habilitación del botón y aparición del control de minutos de grabación, sin excepción Streamlit. Captura `twitch-ayuda-0.4.1.png`. El backend conserva el rechazo de historial inaccesible y su mensaje ofrece ambas alternativas.

Esta validación no descarga ni graba Twitch real, no garantiza que exista un VOD público y no añade recuperación histórica de un canal activo. No altera las restricciones de acceso ni la duración elegida por el usuario.

CI final 0.4.1: **79 aprobadas en Windows (38,54 s)**; **76 aprobadas y 3 omitidas en Linux (29,26 s)**. Instalar.bat, RepararGPU.bat y pip check correctos; DLL NVIDIA cargadas sin errores ni bibliotecas ausentes. Sin inferencia en una GPU física. Registro `ci-0.4.1.txt`.

## Versión 0.5.0: análisis por lotes y exportación rápida

Código final: `92cc0642c83a084545ffc32858129f002b393f46`.
CI final: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44016541366

Implementación:

- El perfil Rápido usa BatchedInferencePipeline con Tiny: lote 4 CPU / 8 CUDA y beam 1, manteniendo marcas por palabra. Equilibrado/Calidad conservan la ruta secuencial. Los resultados pueden variar; no se certifica una equivalencia de precisión semántica. Las transcripciones válidas previas siguen siendo reutilizables. Fallos CUDA, incluidos errores durante iteración, descartan el parcial y liberan GPU antes de continuar en CPU.
- Codificador automático con prueba FFmpeg real NVENC de un fotograma. No se infiere disponibilidad a partir de CUDA ni de la lista de codificadores compilados. Ante error de codificación NVENC del clip se elimina el parcial y se reintenta con libx264. Se registra encoder_used en edicion.json. Esto acelera codificación cuando está disponible; no mueve los filtros a GPU.
- Velocidad de exportación visible: Rápida (ultrafast CPU / p1 NVENC) inicial para nuevos clips, Equilibrada o Mayor compresión. Conserva preferencias guardadas y resolución; Rápida puede producir archivos considerablemente mayores.
- Un solo cuadro que ocupa el lienzo se recorta y escala directamente, sin construir un canvas y superposición redundantes. Varios cuadros, foto, logo y títulos conservan su ruta.
- Seguimiento facial opcional con zona muerta de 0,035 del ancho y desplazamiento limitado a 0,025 por segundo, con límite de avance tras pérdidas de detección. Reduce temblor, a costa de seguir más lentamente. No estabiliza el movimiento presente en el video original ni identifica al hablante. El encuadre normal sigue fijo y el zoom desactivado inicialmente.

Prueba local final completa: **83 aprobadas + 3 omitidas específicas de Windows en 35,44 s**. Se incluye fallback NVENC con exportación CPU real, tiempos por palabra en lotes, fallo perezoso CUDA y descarga del modelo antes de CPU, trayectoria facial acotada y reimportación de VOD sin consultas de red. La CI ejecuta el conjunto final completo.

### Mediciones reales CPU

Fuentes autorizadas propias: examples/autorizado.mp4, patrón visual y voz sintética CC0. Para el análisis se repitió por copia de paquetes hasta 600,03 s. Pesos Tiny previamente descargados, idioma inglés, sin descarga de fuente, sin otros ensayos concurrentes. No equivalen a streams reales.

Análisis alternado secuencial/lotes/secuencial/lotes: 18,970 / 14,512 / 17,104 / 15,118 s. Medianas **18,037 → 14,815 s**, reducción aproximada del 18 %. Todas las propuestas respetaron 30–90 s, con distintos largos; los candidatos pueden diferir al cambiar la transcripción. RSS muestreada al terminar cada análisis entre 218,0 y 362,9 MB; no es máximo del sistema ni incluye todos los procesos hijos. Última ejecución exportó un candidato de 49,59 s a MP4 1080×1920, audio y subtítulos, en **9,222 s**. Repetición del mismo análisis: cero bloques nuevos. Informe `analysis-benchmark-0.5.0.json`.

Exportación de 15 s, un cuadro vertical 1080×1920, CPU: tres alternancias con el renderer anterior/veryfast y nuevo/ultrafast. Medianas **8,6493 → 2,4946 s**, aproximadamente 3,47 veces más rápido. Tamaños: unos **2,96 → 8,44 MB**. La comparación combina optimización de composición y cambio de compresión; no atribuye toda la mejora a una sola de ellas ni afirma misma eficiencia de compresión. Informe `render-benchmark-0.5.0.json`.

No se dispone de RTX 3060 física: la ruta NVENC real solo se probó como no disponible en este equipo; éxito y fallo tardío se cubren controladamente. Los lotes CUDA se verifican con dobles, incluida limpieza antes del fallback. No se garantiza terminar un directo de duración arbitraria en dos o tres minutos: la descarga, duración, calidad, GPU y efectos determinan el tiempo. Las limitaciones remotas YouTube/Twitch y de inferencia Ollama se mantienen.


La reimportación de un VOD disponible en disco comprueba caché antes de consultar metadatos. AppTest sustituye consulta y descarga por fallos explícitos y comprueba que Generar clips reutilice el proyecto sin llamar ninguna. El descriptor inmutable sigue excluyendo grabaciones en vivo y separa archivo completo de intervalos. Descargas nuevas solicitan cuatro fragmentos concurrentes cuando el protocolo/proveedor lo permite, sin reducir resolución ni el intervalo pedido. El comando se verifica controladamente; no se midió su efecto en YouTube/Twitch real. El estado de la UI distingue comprobación, descarga y análisis.

Chromium real abrió un candidato ya analizado, verificó Rápida inicialmente y exportó con los controles de la app. Archivo real, preset ultrafast, encuadre paneles con zoom 1, codificador efectivo libx264, sin excepción Streamlit ni errores JS registrados. Tiempo observado 9,751 s desde el clic hasta registrar la exportación. Captura exportacion-0.5.0.png e informe browser-0.5.0.json. No es tiempo de análisis ni de descarga.

CI final: **86 aprobadas en Windows (29,06 s)**; **83 aprobadas y 3 omitidas en Linux (33,22 s)**. Instalar.bat, RepararGPU.bat y pip check terminaron correctamente; carga de DLL NVIDIA sin errores ni bibliotecas ausentes. Esto no demuestra inferencia CUDA ni NVENC en GPU física. Registro ci-0.5.0.txt.

## Versión 0.6.0: vista previa corta y detección Ultrarrápida

Código final: `3242eef7c77457fa258417b463782fd3e5169a6d`.
CI final: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44020050161

Prueba local completa: **88 aprobadas y 3 omitidas específicas de Windows en 49,38 s**.

### Corrección de Ver clip

La versión anterior servía el video original al reproductor y detenía la reproducción en el límite. El control nativo seguía mostrando la duración total del original. Una tarjeta con 1,33 minutos decimales representa unos 80 segundos, pero el reproductor de siete horas daba una impresión distinta. Se sustituye por un MP4 horizontal real del tramo, generado a demanda con seek directo, 640 píxeles de ancho, 24 fps, ultrafast, audio y caché por identidad/tamaño/mtime/intervalo. La primera apertura requiere renderizar solo ese tramo; las siguientes reutilizan el archivo. No se preparan todas las vistas previas al generar candidatos.

La barra del reproductor de clips usa tiempos relativos y limita la búsqueda y reproducción al tramo. La tarjeta presenta Duración en min:seg y la posición de origen por separado. La vista general de la fuente conserva su reproductor completo. No se cambia ni elimina el original. Los límites 30–90 s de candidatos y la exportación recortada se mantienen.

Prueba real Chromium con fuente propia sintética de **26574 s (7:22:54)**, color estático 160×90 a 1 fps, sin audio, creada con FFmpeg. Candidato predefinido de **7882 a 7962 s**, duración 80 s, para probar interfaz y recorte sin atribuir detección semántica. Se abrió Ver clip, se esperó decodificación, se comprobó **duración física del MP4 80 s**, barra máxima 80, texto **0:00 / 1:20**, reproducción y detención al llegar al final. Sin excepción Streamlit ni errores JavaScript registrados. Informe browser-0.6.0.json y captura vista-corta-0.6.0.png.

Pruebas automatizadas: duración real del archivo corto, reutilización sin render repetido, estado del botón al cambiar filtros, subtítulos/audio/exportación de las rutas existentes, controles relativos y restricciones de búsqueda del HTML. No se afirma que toda copia de un contenedor dure exactamente al milisegundo; se permite el margen de fotograma/audio del codificador.

### Detección Ultrarrápida

Nuevo modo visible e inicial para proyectos nuevos. Extrae audio y usa energía/cambios acústicos y muestreo visual, sin cargar Whisper para todo el directo. Las propuestas iniciales no tienen transcripción ni interpretación semántica; usan títulos genéricos de revisión. Los límites y la variación de duración se aplican a candidatos sin diálogo. El editor conserva el botón para generar subtítulos solo del candidato elegido. Los modos de transcripción completa siguen disponibles y los proyectos anteriores conservan sus preferencias.

Caché audio-only separada: un bloque sin transcribir no se guarda como ASR completo, y no se migra a ASR completo por accidente. Tests prohíben llamar al transcriptor en ese modo, comprueban el espacio de caché, duración/variación e incremental sin repetir bloques. Una selección de Ollama sin evidencia textual no fabrica contexto.

Ensayo con fuente sintética propia autorizada de **600,03 s**, repetida desde examples/autorizado.mp4, sin descarga y sin otro benchmark concurrente: **0,687 / 0,867 / 0,734 s**, mediana **0,734 s**. Seis candidatos: **81, 75, 81, 48, 69 y 30,03 s**, todos 30–90 s. RSS muestreada al final entre **55,6 y 56,0 MB**, no máximo del sistema ni de los procesos hijos. Vista previa real de 81 s: **2,001 s**, 640×360, audio conservado. Transcripción posterior de ese clip: **4,041 s**, Tiny CPU, 223 palabras, pesos previamente descargados. Informe ultra-benchmark-0.6.0.json.

Estos tiempos corresponden a detección audiovisual con menos información que el análisis completo. Diferir ASR cambia las posibilidades de clasificar humor/conversación; no se afirma calidad semántica equivalente. Descargar una fuente larga sigue costando tiempo y espacio. No se garantiza menos de dos minutos para cualquier stream. RTX/NVENC físico, descarga real YouTube/Twitch e inferencia Ollama siguen sin validación nueva.


Regresiones adicionales: la migración de transcripciones antiguas rechaza expresamente config.transcription=false; no trata los bloques de solo audio como transcripción terminada. El selector del editor usa etiquetas únicas (número + duración + título) para evitar que títulos genéricos repetidos cambien el candidato al enviar otro control. AppTest verifica selección y guardado de subtítulos con títulos duplicados.

Segundo flujo real Chromium: proyecto de 10 minutos, modo Ultrarrápido, Generar clips con reutilización de análisis de audio ya almacenado, Elegir y editar y Generar / actualizar subtítulos. Se transcribió únicamente el candidato **494–563 s (69 s)** y se guardaron **192 palabras** dentro de ese intervalo. Se comprobó ausencia de excepción Streamlit. Informe ultra-editor-0.6.0.json. Este segundo flujo comprueba la integración de UI, no mide la primera detección; los tiempos de detección provienen del ensayo independiente descrito antes.

CI final 0.6.0: **91 aprobadas en Windows (39,72 s)**; **88 aprobadas y 3 omitidas específicas de Windows en Linux (35,73 s)**. Instalar.bat, RepararGPU.bat y pip check correctos; bibliotecas NVIDIA cargadas sin errores ni ausencias. El runner no tiene GPU física: esto no certifica inferencia CUDA/NVENC. Registro ci-0.6.0.txt.

## Versión 0.7.0: cuadros estables y descarga directa para CapCut

Código: `fbe33dc1e1c0ee4027ac567bd9431d4ae67d4925`.
CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44022094375

Pruebas locales completas: **93 aprobadas y 3 omitidas específicas de Windows en 44,33 s**. Tras el último ajuste defensivo del selector, las dos regresiones de interfaz afectadas pasaron en 5,31 s; la CI ejecuta de nuevo todo el código final.

- El componente del editor usa una clave estable por clip. Un identificador de configuración cambia los cuadros sin destruir el iframe ni recargar el video. Valores enviados desde una configuración anterior se rechazan. Se mantiene una revisión por composición para no sobrescribir un arrastre reciente. El reporte de altura solo se envía cuando cambia.
- Se usa un MP4 corto compatible en el editor; no se abre de nuevo el original de varias horas en cada cambio de cuadros. Las coordenadas siguen normalizadas y la exportación recorta la fuente original. Se conserva el origen temporal de los subtítulos opcionales. La vista interactiva de una edición manual larga se limita a los primeros 120 s; los límites reales del archivo descargado siguen siendo los elegidos.
- El selector de cantidad y los botones usan el mismo estado, sin defaults conflictivos. Los títulos duplicados siguen teniendo etiquetas únicas. Añadir, quitar y elegir directamente un número comparten configuración.
- Subtítulos desactivados inicialmente y apartado opcional cerrado. Se conservan datos, herramientas y exportación tradicional para quien los active; no se requieren para descargar. El botón principal de descarga editada fuerza burn=false y no ejecuta Whisper.
- Descarga horizontal desde la galería y descarga editada desde el editor mediante data callable de Streamlit 1.67, ejecutada en trabajador separado y on_click=ignore. Se capturan intervalo y ajustes como valores del clic para evitar mezclarlos con cambios posteriores. El trabajador no ejecuta comandos Streamlit.
- Horizontal conserva dimensiones/fps y audio del archivo importado mediante recodificación MP4 H.264/AAC; no se promete copia bit a bit. Prueba NVENC y recurre a CPU si falla. Archivos temporales, renombrado atómico, caché y bloqueo por trabajo evitan descargas parciales y trabajo repetido. La descarga editada reutiliza el renderer de cuadros/texto/logo y su propia caché. Los originales no se modifican.

### Navegador y archivos reales

Chromium, con material sintético propio autorizado de 10 minutos y un candidato de **494–563 s**, hizo **1 → 2 → 3 → 2 → 1** con los botones y eligió **3** directamente desde el desplegable. El mismo objeto iframe y la URL del video se conservaron. En la comprobación final, cambios medidos **1,022 / 0,945 / 0,414 / 0,952 s**, sin errores JavaScript ni excepciones Streamlit. No son garantías para otro equipo ni reproducen el archivo concreto de la captura del usuario. Informe browser-0.7.0-final.json y captura cuadros-0.7.0.png.

El navegador pulsó cada botón de descarga, recibió el archivo mediante el mecanismo real de descarga y lo guardó. Se comparó el hash del MP4 editado recibido con el archivo que registró SQLite y se comprobó configuración de **dos cuadros y burn=false**. El botón Añadir cuadro seguía habilitado durante la preparación. Archivos verificados con FFprobe: **horizontal 69 s, 640×360, audio**; **editado 69 s, 1080×1920, audio**. Informe descargas-0.7.0.json.

Primer ensayo: descarga editada con render real **28,621 s**, archivo de unos 98 MB con ultrafast; horizontal unos 17 MB. Segundo ensayo con caché: **3,627 s** desde clic hasta recibir/guardar/verificar la descarga editada. El tiempo incluye trabajo de navegador y transferencia local; no equivale a tiempo puro de codificación. Informes browser-0.7.0.json y browser-0.7.0-final.json. Las opciones de mayor compresión siguen disponibles para producir archivos más pequeños.

Pruebas nuevas verifican descarga horizontal acotada, dimensiones/audio y conservación byte a byte del archivo fuente; descarga editada de dos cuadros sin quemar subtítulos; reutilización sin nuevo render; fallo NVENC con recuperación CPU; eliminación de parciales ante fallo CPU; y subtítulos apagados aun con un ajuste guardado anterior activo.

No se probaron de nuevo inferencia en RTX física, descarga real YouTube/Twitch ni Ollama. Se mantienen sus límites anteriores. La codificación y transferencia de la primera descarga necesitan tiempo y espacio; se ejecutan sin bloquear el script de la página. El ejemplo grande se mantiene fuera del repositorio y ZIP, que incluyen únicamente las capturas e informes propios.

CI final 0.7.0: **96 aprobadas en Windows (47,02 s)**; **93 aprobadas y 3 omitidas específicas de Windows en Linux (38,19 s)**. Instalar.bat, RepararGPU.bat y pip check correctos; carga de bibliotecas NVIDIA sin errores ni ausencias. No certifica inferencia CUDA/NVENC en una GPU física. Registro ci-0.7.0.txt.

## Versión 0.8.0: progreso medido y validación de duración completa

Código: `6f0b71b432c7a8ddc4f6c6a99169592367d17266`.
CI: https://github.com/rodrigopilco1988-ui/clip-libre/actions/runs/44095443779

Prueba local completa: **102 aprobadas y 3 omitidas específicas de Windows en 48,60 s**.

### Progreso y estimaciones

Progress mantiene estado protegido por bloqueo, etapa, datos medidos, reloj monotónico, tiempo total y ETA por etapa. La ETA se basa en bytes/segundos por segundo o ritmo observado; permanece desconocida al no haber datos suficientes. El tiempo transcurrido se congela al finalizar o fallar. Los trabajos activos no se descartan al conservar el historial reciente.

run_observed lee el stdout/stderr en trabajadores con cola; entrega eventos antes de que termine el proceso y mantiene latidos sin inventar porcentajes. FFmpeg aporta out_time_us y speed; yt-dlp, bytes/fracciones/ETA y fragmentos cuando están disponibles. No se muestra ni persiste el info_dict de yt-dlp con URLs temporales. Los formatos/pistas cambian la medición de etapa; unión/fixup se muestran como una fase distinta. Copia local y hash de registro informan bytes. La extracción de audio mantiene el contenido binario separado del progreso. Whisper informa segundos de audio leídos, carga de modelo y procesador real.

La interfaz consulta un endpoint local por token mediante un panel HTML, sin necesitar que el script principal se repinte durante la espera. Las tareas puras ejecutadas en un trabajador no llaman a Streamlit. El panel también sigue las descargas directas cuyo callback no relanza la página. Muestra claramente «restante de esta etapa», no una estimación ficticia del trabajo completo. El porcentaje se omite cuando no hay tamaño o avance observable. Los timeouts terminan el grupo de procesos propio (o el árbol con taskkill en Windows).

Tests: aritmética ETA/fin congelado, eventos recibidos antes de salida del subproceso, timeout, extracción FFmpeg con progreso y muestras idénticas a la ruta anterior, endpoint tokenizado sin caché y posición real de Whisper. Se conserva la prueba de limpieza y fallback de codificación de versiones anteriores.

### Ocho horas y archivos parciales

No se encontró un máximo fijo de cuatro horas en los controles; la barra dependía de la duración informada/importada. Existía una ruta que reutilizaba un archivo VOD por URL/intervalo sin comprobar duración nueva. Se añade comprobación reciente de metadatos al volver a pegar el enlace (cinco minutos), comparación de duración esperada contra archivo y exclusión de importaciones marcadas incompletas. No se puede determinar retrospectivamente si esa fue la única causa en el PC del usuario, al no disponer de su archivo local.

Al importar, se registra expected_duration/actual_duration y se verifica el resultado antes de anunciar análisis completo. Un archivo cuatro horas para un VOD de ocho queda marcado incompleto, se conserva y se avisa. Un proyecto parcial puede analizar su contenido disponible; la actualización del enlace no elimina el proyecto anterior. No se une automáticamente un tramo nuevo con uno anterior. La actualización puede volver a descargar todo.

El botón Actualizar desde el enlace abre el enlace original y comprueba su duración. Comprobar enlace y el encabezado distinguen duración anunciada de duración del archivo local. La barra usa la duración completa y su extremo inicial ahora ocupa todo el VOD al elegir inicio/fin sin ajustes anteriores. Usar todo el intervalo disponible permite salir de una selección corta guardada. Se detiene la descarga ante fragmentos no disponibles en lugar de saltarlos silenciosamente; se ignoran configuraciones externas de yt-dlp para que no añadan límites ocultos.

Tests de UI verifican máximo **29050/60 = 484,1667 minutos**, cambio a intervalo completo y conservación con aviso de una descarga simulada de 14400 frente a 29050 s. El caché rechaza explícitamente un archivo de cuatro horas cuando se esperan ocho. El selector de calidad ofrece 360/720/1080p; el máximo inicial sigue siendo 1080, y bajar resolución requiere elegirlo.

El muestreo visual rápido aplica fps antes de escala para evitar escalar fotogramas que no se usarán. No se cambia el intervalo pedido ni se reduce el contenido temporal. No se midió una aceleración universal y no se promete procesar ocho horas remotas en dos minutos.

### Validación real del VOD 2926826151 y sus límites

1. El extractor con el almacén certifi inicial falló por cadena de certificado en esta red. Con los certificados del sistema y la verificación TLS habilitada, la extracción pública sí terminó. La app utiliza compat_opts no-certifi y su equivalente CLI; no usa nocheckcertificate, cookies ni autenticación añadida.
2. Metadatos reales: duración **29050 s = 8:04:10**, live_status was_live, no directo activo. Formatos ofrecidos hasta 1080p60, con 360p disponible. Informe twitch-metadata-0.8.0.json.
3. Playlist real de 360p: **2905 segmentos**, suma **29050 s**, EXT-X-ENDLIST presente. Informe twitch-playlist-0.8.0.json. Esto confirma la duración anunciada y accesible de la playlist; no prueba que todos los segmentos se hayan descargado.
4. Se recuperó un fragmento público de la posición aproximada **25000 s (6:56:40)**, junto con su inicialización fMP4 pública. Sin claves de cifrado ni discontinuidades antes del fragmento. Al normalizar timestamps localmente, FFprobe verificó **10,015333 s, 640×360, video y audio**. Los medios de esa validación permanecen fuera del repositorio/ZIP. Informe twitch-fragmento-0.8.0.json.
5. Un intento separado de import_url con yt-dlp/FFmpeg y download-sections para 25000–25005 s tardó **158,874 s** y produjo un contenedor sin pista de video válida; la función devolvió error. Informe twitch-intento-rango-0.8.0.json. Ese intento no se presenta como descarga correcta ni confirma la importación de rangos de este VOD.
6. No se descargaron ni analizaron las ocho horas completas. La consulta de metadatos/playlist y el fragmento posterior a cuatro horas no se extrapolan a garantía de todo Twitch o Twitch Live. YouTube/Live y RTX/Ollama físicos mantienen sus limitaciones de validación anteriores.

### Interfaz real y descarga con ETA

Chromium abrió la app y comprobó el enlace real, mostró **Duración anunciada por el enlace: 8:04:10**, y permitió un fin superior a 480 minutos. Después, con el ejemplo local propio autorizado, inició una descarga editada con tres cuadros. Mientras FFmpeg codificaba, el panel mostró **1 %**, video procesado **0,6 s**, tiempo total transcurrido **0:02**, restante estimado de etapa **0:57** y aviso de que puede cambiar. El archivo se descargó correctamente; sin errores JavaScript ni excepción Streamlit. Ese tiempo restante era una estimación intermedia, no el tiempo final ni una garantía. Informes browser-0.8.0.json, capturas progreso-real-0.8.0.png y vod-ocho-horas-0.8.0.png.

CI final 0.8.0: **105 aprobadas en Windows (75,19 s)**; **102 aprobadas y 3 omitidas específicas de Windows en Linux (42,12 s)**. Instalar.bat, RepararGPU.bat y pip check correctos; carga de bibliotecas NVIDIA sin errores ni ausencias. No equivale a inferencia CUDA/NVENC en GPU física. Registro ci-0.8.0.txt.
