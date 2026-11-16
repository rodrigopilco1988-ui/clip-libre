from pathlib import Path
import shutil
import uuid
from urllib.parse import urlparse
from .media import probe,run

EXTENSIONS={'.mp4','.mkv','.mov','.webm','.avi','.m4v','.ts'}

def import_local(path,root,permission=False):
    if not permission: raise ValueError('Confirma que tienes permiso para procesar y reutilizar este material.')
    path=Path(path).resolve()
    if path.suffix.lower() not in EXTENSIONS: raise ValueError('Formato no admitido.')
    probe(path)
    target=Path(root)/'originales'/uuid.uuid4().hex
    target.mkdir(parents=True)
    dest=target/path.name
    shutil.copy2(path,dest)
    return dest


def validate_url(url):
    u=urlparse(url)
    allowed={'youtube.com','www.youtube.com','m.youtube.com','youtu.be','twitch.tv','www.twitch.tv'}
    if u.scheme!='https' or u.hostname not in allowed or u.username or u.password or u.port not in {None,443}:
        raise ValueError('Usa un enlace HTTPS público de YouTube o Twitch.')
    return url


def import_url(url,root,start=0,end=300,permission=False):
    if not permission: raise ValueError('Debes confirmar el permiso de acceso y reutilización.')
    validate_url(url)
    if not 0<=start<end or end-start>3000: raise ValueError('Importa un tramo entre 1 segundo y 50 minutos.')
    from yt_dlp import YoutubeDL
    try:
        with YoutubeDL({'quiet':True,'no_warnings':True,'noplaylist':True,'skip_download':True,'socket_timeout':20,'retries':1}) as y:
            info=y.extract_info(url,download=False)
        if info.get('has_drm') or info.get('availability') in {'private','premium_only','subscriber_only','needs_auth'}:
            raise ValueError('El contenido está restringido. No se intentará eludir el acceso.')
        if info.get('is_live') and start>0:
            raise ValueError('No se ha validado la recuperación histórica de este directo. Usa un VOD autorizado o un archivo local; no se asumirá que tiene DVR.')
        folder=Path(root)/'originales'/uuid.uuid4().hex; folder.mkdir(parents=True)
        # Sin cookies, credenciales ni opciones de bypass. Cada importación es un tramo finito.
        import sys
        cmd=[sys.executable,'-m','yt_dlp','--no-playlist','--no-progress','--socket-timeout','20','--retries','1',
             '--download-sections',f'*{start}-{end}','--force-keyframes-at-cuts','-f','bv*[height<=1080]+ba/b[height<=1080]',
             '--merge-output-format','mkv','-o',str(folder/'fuente.%(ext)s'),url]
        run(cmd,timeout=max(180,int((end-start)*3)))
        files=[p for p in folder.iterdir() if p.suffix.lower() in EXTENSIONS]
        if not files: raise ValueError('No se obtuvo un segmento reproducible.')
        probe(files[0]); return files[0]
    except Exception as e:
        raise RuntimeError(f'No se pudo recuperar el contenido: {e}. El directo puede no ofrecer historial, estar restringido o requerir un extractor actualizado. No se eluden restricciones.') from e
