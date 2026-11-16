from pathlib import Path
import shutil
import uuid
import sys
import os
from urllib.parse import urlparse
from .media import probe,run

VIDEO_EXTENSIONS={'.mp4','.mkv','.mov','.webm','.avi','.m4v','.ts'}
AUDIO_EXTENSIONS={'.mp3','.wav','.m4a','.aac','.ogg','.flac','.opus'}
EXTENSIONS=VIDEO_EXTENSIONS|AUDIO_EXTENSIONS


def audio_to_video(path,output):
    """Un podcast de audio conserva su original y obtiene una pista visual local."""
    run(['ffmpeg','-v','error','-y','-i',path,'-filter_complex',
         '[0:a]showwaves=s=1280x720:mode=cline:colors=0xb7f171:rate=25,format=yuv420p[v]',
         '-map','[v]','-map','0:a:0','-c:v','libx264','-preset','veryfast','-crf','23',
         '-c:a','aac','-b:a','192k','-movflags','+faststart',output],timeout=21600)
    probe(output)
    return Path(output)


def import_local(path,root,permission=False):
    if not permission: raise ValueError('Confirma que tienes permiso para procesar y reutilizar este material.')
    path=Path(path).resolve()
    if path.suffix.lower() not in EXTENSIONS: raise ValueError('Formato no admitido. Usa un video o un podcast MP3, WAV, M4A, AAC, OGG, FLAC u OPUS.')
    if not path.is_file(): raise ValueError('No se encontró el archivo. Comprueba la ruta.')
    if path.suffix.lower() in VIDEO_EXTENSIONS: probe(path)
    target=Path(root)/'originales'/uuid.uuid4().hex
    target.mkdir(parents=True)
    dest=target/path.name
    shutil.copy2(path,dest)
    if path.suffix.lower() in AUDIO_EXTENSIONS:
        return audio_to_video(dest,target/'podcast_visual.mp4')
    return dest


def validate_url(url):
    url=url.strip()
    u=urlparse(url)
    allowed={'youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be',
             'twitch.tv','www.twitch.tv','clips.twitch.tv'}
    if u.scheme!='https' or u.hostname not in allowed or u.username or u.password or u.port not in {None,443}:
        raise ValueError('Pega un enlace HTTPS de YouTube o Twitch. Para otros podcasts, importa el archivo de audio o video.')
    return url


def local_deno():
    bundled=Path(sys.executable).with_name('deno.exe' if os.name=='nt' else 'deno')
    return str(bundled) if bundled.is_file() else shutil.which('deno')


def source_message(error):
    text=str(error); lower=text.lower()
    if 'certificate_verify_failed' in lower or 'certificate verify failed' in lower:
        return 'No se pudo verificar el certificado de la conexión. Revisa la red, el antivirus o sus certificados. Se mantiene la verificación de seguridad.'
    if 'proxy' in lower and ('403' in lower or 'forbidden' in lower):
        return 'La red de este equipo bloquea la conexión con el proveedor. Revisa sus permisos de red o importa un archivo autorizado.'
    if any(t in lower for t in ['sign in','login required','private video','members-only','subscriber-only']):
        return 'Este contenido requiere una cuenta o un acceso restringido. Importa un archivo autorizado o elige contenido público accesible.'
    if any(t in lower for t in ['404','video unavailable','does not exist','offline']):
        return 'No se encontró contenido accesible. Comprueba si el video existe o si el canal está emitiendo.'
    return text.split('; please report')[0].replace('ERROR:','').strip()[:700]


def extract_info(url):
    from yt_dlp import YoutubeDL
    try:
        runtime=local_deno()
        with YoutubeDL({'js_runtimes':{'deno':{'path':runtime}} if runtime else {},'quiet':True,'no_warnings':True,'noplaylist':True,'skip_download':True,
                        'socket_timeout':20,'retries':1}) as y:
            info=y.extract_info(validate_url(url),download=False)
    except Exception as e:
        raise ValueError(source_message(e)) from e
    if not info or info.get('_type') in {'playlist','multi_video'}:
        raise ValueError('Pega el enlace de un video, episodio o canal en directo, no una lista de reproducción.')
    if info.get('has_drm') or info.get('availability') in {'private','premium_only','subscriber_only','needs_auth'}:
        raise ValueError('El contenido está restringido. No se intentará eludir el acceso.')
    if info.get('live_status')=='is_upcoming':
        raise ValueError('Este directo todavía no empezó. Vuelve cuando esté emitiendo.')
    return info


def inspect_url(url):
    info=extract_info(url)
    provider='Twitch' if 'twitch.tv' in urlparse(url).hostname else 'YouTube'
    live=bool(info.get('is_live') or info.get('live_status')=='is_live')
    return dict(title=info.get('title') or 'Contenido disponible',duration=info.get('duration'),
                live=live,provider=provider,kind='Directo en emisión' if live else 'Video / episodio / VOD',
                license=info.get('license') or 'Comprueba tu permiso de reutilización')


def capture_live(info,folder,seconds):
    streams=info.get('requested_formats') or [info]
    if len(streams)>2 or any(not s.get('url') for s in streams):
        raise ValueError('El proveedor no entregó un flujo capturable. Usa un VOD o un archivo autorizado.')
    cmd=['ffmpeg','-v','error','-y']
    for stream in streams:
        # URLs proporcionadas por el extractor público, sin cookies ni credenciales añadidas.
        cmd+=['-i',stream['url']]
    if len(streams)==2: cmd+=['-map','0:v:0','-map','1:a:0']
    else: cmd+=['-map','0:v:0','-map','0:a:0?']
    output=folder/'directo.mkv'
    cmd+=['-t',seconds,'-c','copy','-avoid_negative_ts','make_zero',output]
    run(cmd,timeout=max(180,int(seconds*3)))
    probe(output)
    return output


def import_url(url,root,start=0,end=None,permission=False,live_mode='actual'):
    if not permission: raise ValueError('Debes confirmar el permiso de acceso y reutilización.')
    url=validate_url(url)
    if (end is None and start!=0) or start<0 or (end is not None and (end<=start or end-start>3000)):
        raise ValueError('El tramo debe durar entre 1 segundo y 50 minutos. También puedes importar el video completo.')
    try:
        info=extract_info(url)
        live=bool(info.get('is_live') or info.get('live_status')=='is_live')
        if live and start>0 and live_mode!='historial':
            raise ValueError('La recuperación histórica no está garantizada. Elige capturar desde ahora o usa el VOD.')
        if live and end is None:
            raise ValueError('Para un directo, elige una duración de captura finita.')
        if live_mode not in {'actual','historial'}: raise ValueError('Modo de directo inválido.')
        if live and live_mode=='historial' and 'twitch.tv' in urlparse(url).hostname:
            raise ValueError('Twitch no ofrece aquí recuperación histórica del directo activo. Usa su enlace /videos/ o captura desde ahora.')
        folder=Path(root)/'originales'/uuid.uuid4().hex; folder.mkdir(parents=True)
        if live and live_mode=='actual':
            return capture_live(info,folder,end-start)
        import sys
        cmd=[sys.executable,'-m','yt_dlp','--no-playlist','--no-progress','--socket-timeout','20','--retries','1',
             '-f','bv*[height<=1080]+ba/b[height<=1080]',
             '--merge-output-format','mkv','-o',str(folder/'fuente.%(ext)s')]
        runtime=local_deno()
        if runtime: cmd+=['--js-runtimes','deno:'+runtime]
        if end is not None:
            cmd+=['--download-sections',f'*{start}-{end}','--force-keyframes-at-cuts']
        if live: cmd+=['--live-from-start']
        cmd+=[url]
        duration=(end-start) if end is not None else (info.get('duration') or 1800)
        run(cmd,timeout=min(21600,max(180,int(duration*4+120))))
        files=[p for p in folder.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS]
        if not files: raise ValueError('No se obtuvo un video reproducible.')
        probe(files[0]); return files[0]
    except Exception as e:
        raise RuntimeError(f'No se pudo importar el enlace: {e}. Si requiere acceso privado, no tiene historial o el proveedor lo bloquea, usa un VOD o archivo autorizado.') from e
