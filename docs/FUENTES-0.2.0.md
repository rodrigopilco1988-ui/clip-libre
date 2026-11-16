# Fuentes e interfaz · 0.2.0

## Implementación y evidencia

| Entrada | Implementación | Validación real disponible |
|---|---|---|
| MP4/MOV/MKV y otros videos | Importación preservando el original | Pruebas FFmpeg e interfaz |
| Podcasts MP3/WAV/M4A/AAC/OGG/FLAC/OPUS | Onda visual y flujo de transcripción/edición | WAV sintético de 24,96 s: 70 palabras, exportación 720×1280 con audio y subtítulos, original preservado; 16,35 s totales en CPU |
| YouTube, Shorts y episodios | Inspección, VOD completo o tramos con yt-dlp y Deno local | Comandos y metadatos controlados; consulta real bloqueada por proxy 403 |
| Twitch VOD y clips | Dominios y rutas admitidos, mismo descargador | Validación de enlaces y comandos controlados; consulta real falló al verificar certificado |
| Directo desde ahora | FFmpeg captura una duración finita desde flujos accesibles | HLS por HTTP local autorizado, captura real de 3 s con video/audio; no equivale a validar Twitch/YouTube |
| YouTube Live histórico | Intento con live-from-start y tramo | Solo ruta implementada; DVR y descarga real pendientes |
| Twitch activo histórico | Mensaje específico y alternativa VOD | Rechazo probado con metadatos controlados |
| Spotify, RSS u otros podcasts por enlace | No implementado | Importar archivo autorizado de audio/video |

No se garantiza cualquier enlace. DRM, contenidos privados, permisos del proveedor, falta de DVR, emisores desconectados, red, certificados y cambios del extractor pueden impedir la recuperación. No se usan cookies, claves privadas ni opciones de desactivar verificación TLS. No se intenta sortear esas limitaciones.

La consulta de metadatos se intentó con el video público Big Buck Bunny del canal Blender (`YE7VzlLtp-4`) y con el canal público NASA de Twitch, sin descargar ni redistribuir sus contenidos. Los errores de esta red no prueban el comportamiento en el Windows del usuario. La prueba HLS local usa únicamente un patrón y un tono generados localmente.

## Interfaz

Diseño propio oscuro, selección de cuatro tipos de fuente, importación automática con generación de candidatos, biblioteca lateral, tarjetas con puntuación estimada, reproducción de vistas previas cortas, aceptación/rechazo y editor existente. Las capturas `home-0.2.0.png`, `twitch-0.2.0.png` y `clips-0.2.0.png` se hicieron en Chromium headless contra la aplicación real. Para ilustrar la biblioteca se cargó un proyecto sintético con transcripción real y una tarjeta de demostración; ese proyecto y su puntuación no se entregan como datos predeterminados ni como evidencia de calidad de selección.

Se comprobó navegación desde inicio a Twitch y a Mis clips con Playwright. Los AppTest comprueban las cuatro fuentes y el editor/exportación. No es un editor multipista ni una copia de la interfaz propietaria de OpusClip.
