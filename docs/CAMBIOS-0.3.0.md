# Minutos, composición y rendimiento · 0.3.0

## Comprobaciones funcionales

- «Analizar todo el contenido importado» está activado inicialmente; el backend usa max_blocks=None. En configuración, 0 bloques significa todos. La duración de un clip no limita el tramo analizado.
- Controles principales en minutos: mínimo orientativo, objetivo y máximo opcional, más inicio/final del editor. max_seconds=None elimina los topes de 60/180 s del backend; las propuestas respetan todavía las fronteras de cada bloque. La duración orientativa inicial es 3 min, no un máximo.
- Se probaron candidatos de más de 300 s. Una prueba manual exportó el intervalo 0,75–4,25 min de un archivo técnico autorizado: 3,5 min, 360×640, audio, dos cuadros y texto. La fuente era color y tono generados localmente, no una prueba de selección semántica. Informe: clip-largo-0.3.0.json.
- Elegir y editar abre el editor, acepta el clip y permite añadir/quitar cuadros. Se guardan texto y configuración. Se prueban colores por cuadro en renders reales de 1/2/3 zonas y se contrastan con la guía estática.
- La prueba de recorte tardío usa un video que cambia de rojo a azul: el clip posterior sale azul y dura lo esperado, verificando que el seek no seleccione otra parte.
- Se probó el texto ASS propio, subtítulos, conservación de audio, reducción de silencios por intervalo en lote y guardado de una palabra que cruza el inicio del clip.
- Se comprueba reutilización de transcripción al cambiar duración y recuperación de análisis antiguos identificables. Se comprueba actualización de propuestas pendientes y conservación de candidatos aceptados, descartados, editados y exportados.
- Chromium verificó la selección, apertura de editor, dos cuadros, texto y reproducción de una vista previa vertical. Las capturas usan el proyecto sintético de demostración de versiones anteriores, no videos de un usuario.

## Ensayo de rendimiento controlado

Sin pruebas pytest concurrentes, caché del modelo Tiny disponible y un archivo técnico de 120 s, 640×360/30 fps. Se comparó el renderer previo del commit 70c6111 con el nuevo, alternando anterior/nuevo/nuevo/anterior. Se exportaron 4 s desde el segundo 110, a 360×640, mismo libx264 ultrafast y sin subtítulos. Medianas: **1,0305 s → 0,2765 s**. Esta comparación aísla el coste de leer material anterior; no mide una exportación 1080p de varias horas ni demuestra aceleración GPU.

El archivo autorizado de 24,95 s se analizó con Tiny CPU y visión rápida. Primer análisis: **2,393 s**. Tras cambiar solo la duración objetivo: **0,005 s**, con una transcripción y un análisis visual reutilizados. El segundo tiempo no es una nueva inferencia. RSS muestreada al finalizar: 217,4 MB; no es el máximo de memoria ni incluye procesos FFmpeg. Datos: rendimiento-0.3.0.json.

El modo visual rápido puede perder cambios entre fotogramas clave; Detallado mantiene más muestras. Ollama, descarga remota, primera descarga de modelos y la velocidad real de la RTX del usuario no forman parte de este ensayo. Los bloques y el análisis local de un directo largo siguen necesitando tiempo. No se promete rendimiento instantáneo.
