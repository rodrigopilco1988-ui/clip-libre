"""Descargas a demanda: sin llamadas a Streamlit ni transcripción en los trabajadores."""
from pathlib import Path
from functools import lru_cache
from threading import Lock
import hashlib
import json
import uuid
from .media import run
from .encoding import choose_encoder,encoder_options


@lru_cache(maxsize=128)
def _lock(key): return Lock()


def _identity(path):
    source=Path(path).resolve(); stat=source.stat()
    return str(source),stat.st_size,stat.st_mtime_ns


def source_clip(path,start,end,root,progress=None):
    if not 0<=start<end: raise ValueError('Intervalo de descarga inválido.')
    identity=_identity(path)
    key=hashlib.sha256(json.dumps([identity,start,end,'source-v1']).encode()).hexdigest()
    folder=Path(root)/'descargas';folder.mkdir(parents=True,exist_ok=True)
    output=folder/(key+'.mp4')
    with _lock(key):
        if output.is_file(): return output
        temp=folder/(key+'.'+uuid.uuid4().hex+'.building.mp4')
        cmd=['ffmpeg','-v','error','-y','-threads','2','-ss',str(start),'-i',identity[0],'-t',str(end-start),
             '-map','0:v:0','-map','0:a:0?','-c:a','aac','-b:a','192k']
        encoder=choose_encoder('auto')
        ending=['-pix_fmt','yuv420p','-movflags','+faststart',str(temp)]
        try:
            def encode(options):
                command=cmd+options+ending
                if progress:
                    from .observed import run_observed
                    return run_observed(command[:-1]+['-progress','pipe:1','-nostats',command[-1]],progress,duration=end-start,stage='Preparando MP4 horizontal')
                return run(command)
            try: encode(encoder_options(encoder,'ultrafast'))
            except Exception:
                if encoder!='h264_nvenc': raise
                temp.unlink(missing_ok=True)
                encode(encoder_options('libx264','ultrafast'))
            temp.replace(output)
        except Exception as e:
            raise RuntimeError('No se pudo preparar el MP4 del clip. El original se conserva. '+str(e)) from e
        finally: temp.unlink(missing_ok=True)
    return output


def edited_clip(path,start,end,root,settings,words=(),cuts=(),progress=None):
    from .render import render,Edit
    key=hashlib.sha256(json.dumps([_identity(path),start,end,settings,words,cuts],sort_keys=True).encode()).hexdigest()
    folder=Path(root)/'descargas';folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/(key+'.json')
    with _lock(key):
        if manifest.exists():
            result=Path(json.loads(manifest.read_text())['path'])
            if result.is_file(): return result
        result=render(path,start,end,words,Path(root)/'editados',Edit(**settings),cuts,process_progress=progress)
        temp=manifest.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        temp.write_text(json.dumps(dict(path=str(result))))
        temp.replace(manifest)
    return result
