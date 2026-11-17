# Clip Libre · 0.7.0

Estudio local para generar, revisar y editar clips. Interfaz original en español, sin créditos, suscripciones ni APIs de IA de pago. Usa únicamente material con acceso y permiso de reutilización.

## Descargar para CapCut y cuadros estables (0.7.0)

- En **Clips**, pulsa **Descargar clip para CapCut · horizontal**. Un solo botón prepara y descarga el tramo elegido, sin subtítulos ni entrada obligatoria al editor. Mantiene la resolución y frecuencia de imagen del archivo importado y conserva su audio, con codificación MP4 compatible; no es copia bit a bit.
- Si quieres encuadrar antes, pulsa **Elegir y editar**, añade/quita hasta tres cuadros o usa el selector y arrastra cada recorte. Después pulsa **Descargar MP4 editado · sin subtítulos**. Incluye el formato, cuadros, títulos y logo configurados, sin subtítulos automáticos.
- Ambas descargas se preparan al pulsar, en segundo plano, y se reutilizan si no cambias ajustes. La interfaz sigue disponible. La primera descarga tiene que codificar el clip; no es instantánea ni garantiza un tiempo fijo.
- El reproductor del editor permanece abierto al cambiar cuadros. Usa una vista previa corta compatible, conservando la fuente original para descargar/exportar. En ediciones manuales de más de dos minutos, la vista interactiva muestra los primeros dos minutos; la descarga mantiene el intervalo completo elegido.
- Los subtítulos están **apagados por defecto**, incluso al abrir un clip que antes los guardó activados. Se conservan como opción en el apartado cerrado «Subtítulos opcionales · puedes hacerlos en CapCut». No necesitas generarlos para descargar. El botón principal de descarga editada siempre entrega MP4 sin subtítulos automáticos.

Prueba real Chromium: 1 → 2 → 3 → 2 → 1 cuadros, selector directo y ambas descargas. Se mantuvieron el mismo reproductor y la misma URL del video; no hubo errores JavaScript ni excepción Streamlit. Archivos descargados de 69 s con audio: horizontal 640×360 y editado de dos cuadros 1080×1920. Informes en docs/VALIDACION.md.

## Vista previa corregida y modo Ultrarrápido (0.6.0)

**Ver clip** crea un MP4 horizontal corto del tramo elegido, con salto directo al inicio. Lo guarda y reutiliza al abrirlo de nuevo. El reproductor usa una barra relativa al clip: **0:00 / 1:20**, aunque la fuente dure siete horas. La tarjeta muestra **Duración: 1:20** y por separado la posición en el directo, en min:seg u horas:min:seg. El original se conserva completo y la exportación sigue recortando el intervalo.

**Velocidad → Ultrarrápido** detecta candidatos por energía/cambios de audio y cambios visuales sin transcribir todo el directo. Es la opción inicial para proyectos nuevos; los proyectos anteriores conservan su modo hasta que lo cambies. Los títulos son genéricos y requieren revisión: tiene menos contexto de conversaciones, humor y diálogos. No interpreta semánticamente imágenes. Elige un candidato, abre el editor y pulsa **Generar / actualizar subtítulos** para transcribir solo ese clip. Los modos **Rápido, Equilibrado y Calidad alta** conservan el análisis con transcripción completa.

Ensayo local con video sintético autorizado de 10 minutos, sin descarga: tres ejecuciones de detección Ultrarrápida **0,687 / 0,867 / 0,734 s**, mediana **0,734 s**. Se propusieron seis clips de 30,03 a 81 s. La vista previa de un candidato de 81 s tardó **2,001 s** y transcribirlo después con Tiny CPU tardó **4,041 s**, con pesos ya disponibles. La mejora procede de diferir la transcripción del directo: la clasificación inicial tiene menos información. No garantiza ese tiempo en streams reales ni incluye descargar la fuente. Pruebas y límites en docs/VALIDACION.md.

## Rendimiento en 0.5.0

- Al reutilizar un VOD ya descargado no se consulta la plataforma. Las descargas nuevas solicitan cuatro fragmentos simultáneos si el proveedor/protocolo lo permite; sin medición remota de rendimiento todavía. El estado indica cuándo se descarga y cuándo se analiza.
- **Generar clips → Rápido** usa Tiny con transcripción por lotes: 4 en CPU y 8 en CUDA. Conserva marcas por palabra; los resultados pueden diferir ligeramente del modo secuencial. Se mantienen Small/Medium y los ajustes avanzados.
- **Velocidad de exportación → Rápida** está visible en el editor y es la opción inicial para clips nuevos. Usa menor compresión para reducir espera: archivos más grandes, misma resolución. Puedes elegir Equilibrada o Mayor compresión; se respetan los ajustes guardados.
- **Codificador automático** prueba una codificación NVENC real, no solo la presencia de una tarjeta. Usa NVIDIA si pasa; si falla durante el clip, elimina el parcial y reintenta en CPU. CUDA/Whisper y NVENC son rutas independientes: que una funcione no demuestra que la otra funcione. Los filtros siguen en CPU.
- El encuadre de un solo cuadro evita la composición y el escalado redundantes. Se mantienen varios cuadros, subtítulos, audio y formatos.
- Encuadre fijo y zoom desactivado inicialmente. Si activas seguimiento facial, ignora pequeños temblores y limita el desplazamiento para evitar saltos bruscos. El movimiento que ya existe dentro del video original no se estabiliza.

Mediciones CPU con fuente sintética autorizada, sin descarga y con pesos disponibles: análisis de 10 minutos, mediana **18,04 → 14,82 s**; exportación rápida de 15 s a 1080×1920, mediana **8,65 → 2,49 s**, con archivo mayor. Un clip de 49,6 s con subtítulos se exportó en **9,22 s**. No son tiempos garantizados para streams reales o para tu equipo; descargar la fuente tarda aparte. Aceleración NVENC y lotes CUDA pendientes de medir en una RTX física. Informes en docs/VALIDACION.md.

## Si pegas un canal de Twitch

La app muestra las opciones antes de intentar importar: **Abrir videos guardados de este canal** para buscar un VOD y pegar su enlace, o **Grabar desde ahora** para capturar los próximos minutos elegidos. No empieza a grabar automáticamente. El canal por sí solo no permite recuperar aquí lo que ya pasó; si no hay VOD público, importa una grabación autorizada. Abrir la página de videos no garantiza que exista un VOD accesible.

## Tres pasos

1. **Fuente y ajustes**: pega un enlace, carga un archivo o abre un proyecto. Elige la parte del stream, la duración de los clips y la velocidad. Confirma el permiso y pulsa **Generar clips**. Toda la configuración está aquí; se guarda por proyecto.
2. **Clips**: revisa las propuestas y descarga directamente el clip horizontal para CapCut. Si quieres encuadrarlo aquí, pulsa **Elegir y editar**. La puntuación es estimada, no garantiza viralidad.
3. **Editor**: elige Vertical, Dúo, Tres cuadros o Foto + clip. Arrastra el recorte sobre el video. Añade títulos o logo si quieres y pulsa **Descargar MP4 editado · sin subtítulos**. También se mantienen vista previa, guardado y exportación tradicionales.

## Dos intervalos diferentes

- **Parte del stream**: «Todo lo disponible» o «Elegir inicio y fin». Aquí los controles y la barra usan MINUTOS del stream: 30 → 110 equivale a 0:30:00 → 1:50:00. La barra aparece al conocer la duración del archivo o después de comprobar el enlace. Los bloques internos de 50 minutos no limitan el intervalo total.
- **Duración de cada clip**: inicialmente **30–90 s · variado**. Personalizado usa **min:seg**: mínimo **0:30**, máximo **1:30**. Los nuevos candidatos respetan ambos límites y se intentan distintas duraciones dentro del rango. No se rellena una cuota de 20 ni se alargan todos al máximo. Puede haber menos candidatos si no hay suficiente material.

Los clips guardados de una configuración anterior se conservan. La galería los oculta inicialmente si no cumplen los límites actuales; activa «Mostrar clips de otras configuraciones» para recuperarlos. Un recorte editado manualmente puede tener otra duración.

## Instalar una vez en Windows

1. Extrae el ZIP completo en una carpeta nueva.
2. Instala **Python 3.12 de 64 bits** desde https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe . Marca **Add python.exe to PATH**.
3. Necesitas **FFmpeg y FFprobe con libass**, disponibles desde https://ffmpeg.org/download.html . Añade su carpeta `bin` al PATH. Si faltan, el instalador te lo indicará. Una opción con winget es `winget install --id Gyan.FFmpeg -e`.
4. Haz doble clic en **Instalar.bat**. Descarga las dependencias, incluidos los componentes de compatibilidad de enlaces. Si falla, lee el mensaje que deja abierto.
5. Haz doble clic en **Iniciar.bat**. Abre http://127.0.0.1:8501 . Para el uso diario basta con ese archivo.

Si ya utilizabas otra versión, conserva tu carpeta **data/**: contiene tus proyectos y archivos. Puedes copiarla a la nueva carpeta con la aplicación cerrada. No borres esa carpeta para reparar una instalación.

## Preparar tu RTX 3060 (opcional, una vez)

1. Abre el apartado lateral **Preparar mi tarjeta NVIDIA para acelerar el análisis**.
2. Pulsa **Instalar o reparar soporte NVIDIA**. Descarga bibliotecas oficiales desde PyPI; puede superar 1,3 GB. Reserva unos 4 GB libres entre descarga y archivos instalados.
3. Cierra y vuelve a abrir la aplicación.
4. En el mismo apartado, pulsa **Probar transcripción en GPU**. La primera prueba puede descargar Tiny. Solo informa de éxito si termina una inferencia CUDA real; no recurre a CPU para esa prueba.
5. Si pasa, analiza con **Procesador: auto**. Si falla por el controlador, actualízalo desde https://www.nvidia.com/drivers/ y vuelve a probar.

También puedes cerrar la aplicación y ejecutar **RepararGPU.bat**, sin escribir comandos. Las bibliotecas se instalan dentro del entorno de Clip Libre; no se copian DLL a System32 ni se instala un controlador del sistema. Son componentes propietarios gratuitos de NVIDIA, opcionales para CPU. La transcripción en GPU sigue dependiendo de un controlador y hardware compatibles.

## Velocidad y GPU

**Rápido** usa Tiny; **Equilibrado**, Small; **Calidad alta**, Medium. Base y el procesador se eligen en Más opciones. La primera descarga del modelo tarda más. Tiny prioriza tiempo y puede transcribir peor.

La reproducción de la fuente y el recorte interactivo leen por rangos. La galería prepara un archivo corto solo al pulsar Ver clip y lo reutiliza; no recodifica el directo entero. Cambiar límites de clips reutiliza transcripciones compatibles, incluso de bloques previos que cubren el intervalo nuevo. No vuelve a descargar un VOD idéntico ya importado si el archivo existe. El análisis visual rápido trabaja en paralelo con la transcripción. El render final y los efectos aún requieren FFmpeg. La codificación final prueba NVENC cuando está disponible.

Ensayo real de navegador con 10 minutos de video sintético autorizado repetido: ocho clips entre 38,74 y 76,90 s en 20,79 s con Tiny CPU y pesos previamente descargados. No equivale a un directo real ni garantiza ese tiempo en otro equipo. No se dispone aquí de una RTX 3060 física para certificar aceleración. El botón de prueba CUDA comprueba tu equipo sin sustituir CPU por un éxito ficticio.

Si falla CUDA, la app informa del cambio a CPU y conserva el progreso; CPU puede tardar más. Usa el apartado lateral de reparación NVIDIA. Los filtros de FFmpeg, OpenCV y el audio siguen en CPU; la codificación prueba NVENC y utiliza libx264 si no está disponible. Los análisis se guardan por bloques en SQLite y se reanudan desde los bloques confirmados.

## Fuentes y directos

- Archivos de video: MP4, MKV, MOV, WebM, AVI, M4V y TS. Para archivos grandes, usa «Archivo de más de 200 MB» y pega la ruta de Windows, con o sin comillas.
- Podcasts: MP3, WAV, M4A, AAC, OGG, FLAC y OPUS. Se conserva el audio y se genera una onda visual. No hay importador RSS ni Spotify.
- Enlaces implementados mediante yt-dlp: videos/Shorts de YouTube, Twitch VOD `/videos/ID`, clips de Twitch y directos compatibles.

**Todo lo disponible** intenta descargar el archivo/VOD completo. En YouTube Live intenta una instantánea de todo el historial recuperable hasta el momento consultado; necesita DVR disponible. Para el pasado de un canal activo de Twitch, pega su VOD. Si no hay historial, aparece un error: no se sustituye por una grabación oculta de cinco minutos.

**Grabar desde ahora** es una opción explícita con duración en minutos. Graba el futuro en tiempo real y por eso tarda lo mismo que el intervalo pedido. No es captura continua ni recupera el pasado. No existe un límite oculto de 5 o 50 minutos. En importaciones parciales, el corte de descarga puede aproximarse al fotograma clave para evitar recodificar la fuente entera.

Las rutas YouTube/Twitch están cubiertas por pruebas controladas y captura HLS local autorizada. La descarga real en esos proveedores sigue sin validarse: esta red bloqueó YouTube y falló TLS con Twitch. No se garantiza que cualquier enlace funcione. No se usan credenciales ni cookies ni se eluden DRM, autenticación o restricciones. Comprobar enlace consulta metadatos, no garantiza la descarga.

## Editor

El recorte sobre el video y la composición vertical se actualizan al arrastrar. Puedes añadir/quitar hasta tres cuadros, usar una foto en un cuadro y un logo del canal; añadir, duplicar o quitar títulos con tiempos y posición. Subtítulos con palabra activa, fuente, colores, tamaño y animación opcional. «Generar / actualizar subtítulos» reutiliza palabras disponibles o transcribe únicamente el intervalo elegido. Se pueden corregir texto y tiempos.

La composición interactiva ayuda a encuadrar. **Generar vista previa editada** ejecuta FFmpeg para revisar el resultado con efectos, animación y seguimiento. Algunos contenedores/códecs no se reproducen directamente en el navegador: usa la reproducción compatible del original o la vista previa editada. El tamaño, espaciado y fuente de la vista interactiva pueden diferir del render final.

Se mantienen formatos 9:16, 1:1 y 16:9, exportación hasta 1080×1920, SRT/ASS, exportación por lotes, encuadre por rostro o cámara/gameplay, zoom, fundidos y reducción de silencios desactivables. El seguimiento facial es aproximado y no identifica al hablante. Los cuadros de video proceden de la misma fuente; no es un editor de varias pistas de video independientes.

## IA local y datos

Ollama es opcional: instálalo desde https://ollama.com/ y prepara `qwen3:4b` (una vez: `ollama pull qwen3:4b`). Actívalo en **Fuente y ajustes → Más opciones** y cambia el modelo si lo necesitas. Si está apagado, continúa el análisis heurístico. Recibe texto, no imágenes; la inferencia real con ese modelo sigue pendiente de validación. Los títulos requieren revisión humana.

- **data/originales/**: fuentes importadas y audio original de podcasts.
- **data/editados/**: MP4, SRT, ASS y decisiones JSON.
- **data/descargas/**: clips horizontales y referencias de caché para las descargas directas.
- **data/history.sqlite3**: proyectos, configuración, progreso y candidatos.
- **data/modelos/**: caché de modelos al iniciar con el BAT.

Los medios y transcripciones no se envían a IA remota. Las fuentes, modelos y dependencias necesitan internet para descargarse. La app y el servidor de reproducción escuchan solo en tu equipo. No hay publicación automática.

## Pruebas y solución de problemas

**Probar.bat** ejecuta pruebas automatizadas. `examples/autorizado.mp4` es una demostración CC0 creada localmente; dura menos de 30 segundos, así que para probarla usa el rango 15–30 s y el idioma inglés. `examples/run_e2e.py` reproduce transcripción y exportación real con Tiny CPU. Resultados y capturas: [docs/VALIDACION.md](docs/VALIDACION.md).

Si aparece «No runtime installed that matches 3.12», instala el Python indicado arriba. El instalador también busca Python 3.11/3.12 de 64 bits en PATH. Si hay una .venv incompleta, renombra únicamente esa carpeta y reintenta, conservando data/.

Para actualizar: cierra completamente la versión anterior, extrae el ZIP en una carpeta nueva, copia **data/**, ejecuta **Instalar.bat** y después **Iniciar.bat**. No copies la .venv anterior.

Código original MIT. Licencias de dependencias y modelos: [docs/LICENCIAS.md](docs/LICENCIAS.md). No se incluyen Python, FFmpeg, Ollama, CUDA ni pesos. CUDA/cuDNN son componentes propietarios gratuitos opcionales; se descargan del proveedor y no se redistribuyen en el ZIP. CPU funciona sin ellos. El diseño es propio y no copia marcas, recursos ni código de OpusClip.

Para desarrollo: instala `pip install -r requirements.txt` y ejecuta `python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false`.
