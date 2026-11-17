# Clip Libre · 0.3.0

Tu estudio local de clips: pega un enlace o carga un video o podcast, genera propuestas, revisa los momentos y exporta con subtítulos. Interfaz propia en español. Sin créditos, suscripciones ni APIs de IA de pago.

## Lo nuevo en 0.3.0

- **Duraciones en minutos**, sin máximo artificial de 60 o 180 segundos. La duración mínima y la orientativa se configuran al importar o al reanalizar. «Sin límite máximo» está activado; si lo desmarcas, el máximo también se expresa en minutos.
- **Todo el contenido importado** se analiza por defecto. Eso es independiente de cuánto dura cada clip. Para un directo pasado usa su archivo o VOD accesible; no se puede recuperar contenido que el proveedor no entrega.
- **Mis clips → Elegir y editar** lleva directamente al editor y acepta ese clip para revisión. La salida inicial es vertical 9:16. Puedes añadir o quitar cuadros hasta tener uno, dos o tres; recortar la zona original y cambiar posición y tamaño de cada cuadro; añadir texto, corregir subtítulos y generar una vista previa editada.
- **Menos trabajo repetido**: no se vuelve a transcribir al cambiar solo la duración de las propuestas, se cachean fotogramas y vistas previas, y FFmpeg salta directamente al inicio del clip en lugar de recorrer todo lo anterior. El muestreo visual rápido se solapa con Whisper.

Cambiar la duración regenera propuestas pendientes automáticas, incluso si antes eran cortas. Se conservan las aceptadas, descartadas, editadas o exportadas. Para ampliar una de esas, abre el editor y cambia Inicio/Final en minutos.

## Instalar una vez en Windows

1. Extrae el ZIP completo en una carpeta nueva.
2. Instala **Python 3.12 de 64 bits** desde https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe . Marca **Add python.exe to PATH**.
3. Necesitas **FFmpeg y FFprobe con libass**, disponibles desde https://ffmpeg.org/download.html . Añade su carpeta `bin` al PATH. Si faltan, el instalador te lo indicará. Una opción con winget es `winget install --id Gyan.FFmpeg -e`.
4. Haz doble clic en **Instalar.bat**. Descarga las dependencias, incluidos los componentes de compatibilidad de enlaces. Si falla, lee el mensaje que deja abierto.
5. Haz doble clic en **Iniciar.bat**. Abre http://127.0.0.1:8501 . Para el uso diario basta con ese archivo.

Si ya utilizabas otra versión, conserva tu carpeta **data/**: contiene tus proyectos y archivos. Puedes copiarla a la nueva carpeta con la aplicación cerrada. No borres esa carpeta para reparar una instalación.

## Preparar tu RTX 3060 (opcional, una vez)

1. Abre **Crear clips → Preparar mi tarjeta NVIDIA para acelerar el análisis**.
2. Pulsa **Instalar o reparar soporte NVIDIA**. Descarga bibliotecas oficiales desde PyPI; puede superar 1,3 GB. Reserva unos 4 GB libres entre descarga y archivos instalados.
3. Cierra y vuelve a abrir la aplicación.
4. En el mismo apartado, pulsa **Probar transcripción en GPU**. La primera prueba puede descargar Tiny. Solo informa de éxito si termina una inferencia CUDA real; no recurre a CPU para esa prueba.
5. Si pasa, analiza con **Procesador: auto**. Si falla por el controlador, actualízalo desde https://www.nvidia.com/drivers/ y vuelve a probar.

También puedes cerrar la aplicación y ejecutar **RepararGPU.bat**, sin escribir comandos. Las bibliotecas se instalan dentro del entorno de Clip Libre; no se copian DLL a System32 ni se instala un controlador del sistema. Son componentes propietarios gratuitos de NVIDIA, opcionales para CPU. La transcripción en GPU sigue dependiendo de un controlador y hardware compatibles.

## Crear tu primer clip

1. Abre **Crear clips**.
2. Elige **YouTube**, **Twitch**, **Podcast** o **Archivo local**.
3. Pega el enlace o selecciona tu archivo. En videos muy grandes, abre «Mi archivo pesa más de 200 MB» y pega la ruta desde el Explorador de Windows.
4. Confirma que tienes acceso y permiso para reutilizar el material.
5. Pulsa **Crear clips**. La generación automática está activada inicialmente.
6. Abre **Mis clips**: revisa la puntuación estimada y pulsa **Ver clip** para revisar el original. Pulsa **Elegir y editar** para preparar el clip vertical. También puedes aceptar o descartar propuestas.
7. En **Editor y exportación**, ajusta el intervalo, corrige subtítulos, elige formato y encuadre, genera una vista previa y exporta.

Por defecto se analiza **todo el archivo o VOD importado**, guardando avances por bloques de 50 minutos. Puedes limitarlo a un bloque desmarcando la opción de analizar todo. Configurar análisis usa 0 bloques como «todos» y reanuda los ya confirmados. La puntuación no garantiza viralidad y los títulos requieren revisión humana.

## Qué contenido puedes introducir

| Contenido | Cómo introducirlo |
|---|---|
| YouTube, Shorts o un episodio publicado allí | Pega el enlace; elige video completo o tramo |
| Twitch VOD | Pega el enlace `twitch.tv/videos/…` |
| Clip de Twitch | Pega el enlace `clips.twitch.tv/…` |
| Canal en directo | Pega el enlace y elige **capturar desde ahora** |
| Video de tu disco | Carga MP4, MOV, MKV, WebM, AVI, M4V o TS |
| Podcast de audio | Carga MP3, WAV, M4A, AAC, OGG, FLAC u OPUS |
| Podcast en video | Carga su archivo de video o su enlace de YouTube/Twitch |

**Comprobar enlace** consulta el título y detecta si está en directo. No confirma derechos ni garantiza la descarga posterior. Spotify, RSS y otros proveedores por enlace no están implementados; puedes importar un archivo autorizado.

Un podcast de audio conserva el original y obtiene una onda visual para crear clips en video con subtítulos.

### Directos y restricciones

La captura desde ahora guarda los próximos minutos elegidos: tarda lo mismo que la grabación. Si importas un directo sin elegir duración, se intenta una captura inicial de 5 minutos. No hay captura continua ni reanudación automática de streams.

YouTube Live permite **intentar** un tramo histórico cuando el proveedor ofrece DVR. Para el pasado de un directo activo de Twitch, utiliza su VOD. Nadie puede garantizar recuperación de contenido que el proveedor no entrega.

No se usan cookies ni credenciales, no se eluden DRM, autenticación o restricciones y no se desactiva TLS. La descarga puede fallar por permisos, red, certificados, ausencia de historial o cambios de la plataforma. La UI muestra errores específicos.

**Estado real:** las rutas remotas están implementadas y probadas con respuestas controladas y un flujo HLS local autorizado. Esta red bloqueó la consulta real a YouTube y falló la verificación TLS con Twitch. No se declara descarga real validada en esas plataformas. Los archivos locales y los podcasts sí tienen pruebas de extremo a extremo. Detalles: `docs/FUENTES-0.2.0.md` y `docs/VALIDACION.md`.

## IA y hardware

Small es la opción inicial de faster-whisper. Tiny reduce el tiempo de espera; Base y Medium también están disponibles. Los modelos se descargan la primera vez. Los bloques usan audio mono de 16 kHz (aprox. 192 MB por 50 minutos aparte de modelos y datos). Las muestras visuales son de 320×180.

La RTX 3060 de 12 GB y los 32 GB de RAM son la referencia de configuración, sin rendimiento certificado en esa GPU. Para CUDA necesitas un controlador y las bibliotecas CUDA/cuDNN compatibles con CTranslate2: https://github.com/SYSTRAN/faster-whisper#gpu . Si CUDA devuelve un error, la aplicación libera el modelo y reintenta el bloque automáticamente en CPU. Informa del cambio y no vuelve a intentar la GPU durante esa sesión. Tras instalar o reparar CUDA, reinicia la aplicación para volver a probarla. La exportación usa libx264 en CPU.

Ollama es opcional. Instálalo desde https://ollama.com/ y prepara `qwen3:4b` desde su interfaz o una vez con `ollama pull qwen3:4b`. Actívalo en Configurar análisis. El modelo es configurable. Whisper se libera antes y Ollama se descarga de memoria tras cada petición; detén otros modelos GPU para conservar VRAM. Si el servicio está apagado, se mantiene el análisis heurístico. Ollama recibe texto, no imágenes. La inferencia real con ese modelo sigue pendiente de validación.

Deno y yt-dlp-ejs se instalan como componentes abiertos locales para el extractor de enlaces. No son servicios de IA remotos.

## Edición y archivos

Formatos 9:16, 1:1 y 16:9; hasta 1080×1920 o 1920×1080. Corrección de palabras y tiempos, subtítulos SRT/ASS, palabra activa resaltada, animación opcional, encuadre por centro/rostros o cámara y gameplay, zoom suave, fundidos y reducción configurable de silencios. Exportación individual o por lotes de aceptados. Cada efecto puede desactivarse.

El encuadre facial es aproximado; no identifica personas ni al hablante activo. La región de cámara requiere confirmación. No hay editor multipista ni comprensión semántica completa del video.

- **data/originales/**: copias de fuentes y audio original de podcasts.
- **data/editados/**: MP4, SRT, ASS y decisiones de edición JSON.
- **data/history.sqlite3**: biblioteca, progreso, candidatos y trabajos.
- **data/modelos/**: caché de modelos al iniciar con el BAT.

Los videos y transcripciones no se envían a IA remota. Las descargas de fuentes, modelos y dependencias sí necesitan internet. El servidor escucha solo en tu equipo y se inicia sin telemetría de Streamlit.

## Probar y resolver problemas

Para una prueba rápida, carga **examples/autorizado.mp4**, elige inglés y Tiny en Ajustes de creación. Es voz sintética con texto propio y patrón visual generado localmente, reutilizable bajo CC0.

**Probar.bat** ejecuta las pruebas automatizadas. Para desarrollo, `examples/run_e2e.py` reproduce el flujo real con Tiny CPU y exporta un ejemplo de 1080×1920. El informe original se incluye en `examples/resultado/informe.json`.

Si aparece «No runtime installed that matches 3.12», `py` existe pero no encuentra Python compatible. Instala el Python indicado arriba y vuelve a abrir Instalar.bat. El instalador también busca Python 3.11/3.12 de 64 bits en el PATH. Si hay una `.venv` incompleta, renombra únicamente esa carpeta como `.venv-anterior` y reintenta, conservando `data/`.

## Código y licencias

Código original MIT. Dependencias y modelos conservan sus licencias: `docs/LICENCIAS.md`. No se incluyen Python, FFmpeg, Ollama, CUDA ni pesos en el ZIP. CUDA/cuDNN son componentes propietarios gratuitos del fabricante y opcionales: CPU funciona sin ellos.

Arquitectura y límites: `docs/ARQUITECTURA.md`. La interfaz utiliza un diseño propio y no copia marcas, recursos ni código de OpusClip.

Para desarrollo: crea un entorno virtual, instala `pip install -r requirements.txt` y ejecuta `python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false`.

## Si aparece cublas64_12.dll o un error CUDA

En 0.2.1, un fallo recuperable de CUDA ya no detiene el análisis: el bloque se reintenta en CPU, se informa del procesador utilizado y se conserva el progreso confirmado. No necesitas instalar CUDA para usar Clip Libre; CPU puede tardar más. Los resultados parciales del intento fallido se descartan para evitar palabras duplicadas.

En versiones anteriores, selecciona **Configurar análisis → Procesador → cpu → Analizar minutos pendientes** para continuar. No borres tus proyectos. La aceleración GPU requiere todavía sus bibliotecas compatibles; esta actualización permite seguir trabajando cuando no están disponibles.

## Corrección 0.2.2: Ver clip y rendimiento

El botón **Ver clip** ya no reutiliza su clave como estado de apertura. Se probó el clic y la reproducción en Chromium, además de su permanencia al cambiar filtros. Las vistas previas se generan a 24 fps, se guardan de forma atómica y se reutilizan; un fallo no deja un archivo parcial que se confunda con una vista válida.

La transcripción CPU usa una búsqueda más rápida (puede dar palabras algo distintas, por lo que conviene revisar subtítulos). Tiny aparece identificado como opción rápida y Small como equilibrada. Esto no convierte el resto del procesamiento en GPU: audio, OpenCV y exportación libx264 siguen usando CPU. Los resultados y límites están en `docs/VALIDACION.md`.

## Editor: uno, dos o tres cuadros

En Encuadre elige **Cuadros editables**. Usa Número de cuadros o Añadir/Quitar; dos cuadros se reparten inicialmente por mitades y tres por tercios. Puedes empezar arriba/abajo o lado a lado y después mover y redimensionar cada cuadro con porcentajes. Cada cuadro recorta una zona independiente del mismo video original: no es un editor multipista de varios archivos.

En **Añadir texto propio** escribe el texto, elige color, tamaño y posición. Los subtítulos tienen sus propios controles de fuente, color de palabra activa, tamaño, posición y animación. La guía estática de encuadre cambia rápidamente sin recodificar el clip; subtítulos sincronizados, animación y seguimiento se revisan con **Generar vista previa editada**. El render idéntico se reutiliza si no cambias nada.

**Guardar revisión y configuración** conserva los ajustes del clip. **Exportar clip con estos ajustes** produce el MP4. El lote aplica los ajustes actuales a los aceptados y conserva las palabras corregidas de cada uno. El original se mantiene separado.

Las marcas de tiempo de las palabras se mantienen en segundos dentro del ajuste fino de sincronización; los controles principales de duración, inicio y final del clip usan minutos. Si amplías un clip a una zona no analizada, analiza primero los minutos pendientes para obtener sus subtítulos.

## Rendimiento: qué se midió

En un ensayo local controlado, recortar 4 s al final de un video de 2 min pasó de una mediana de 1,0305 s a 0,2765 s. Reanalizar el ejemplo autorizado de 24,95 s tras cambiar la duración reutilizó la transcripción: 0,005 s frente a 2,393 s del primer análisis Tiny CPU. Una exportación técnica real de 3,5 minutos con dos cuadros dio un MP4 de 210 s. Estos ejemplos no garantizan tiempos para directos largos, tu conexión o tu hardware. Detalles en `docs/CAMBIOS-0.3.0.md` y `docs/VALIDACION.md`.

Al actualizar, cierra la aplicación por completo, conserva data/ y ejecuta Instalar.bat antes de volver a abrir Iniciar.bat. La tabla de caché se añade automáticamente a SQLite. Cuando se puede identificar el modelo y el idioma de un análisis anterior, se reutiliza su transcripción.
