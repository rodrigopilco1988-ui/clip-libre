"""Lee progreso de FFmpeg/yt-dlp sin bloquear los latidos de la interfaz."""
import subprocess
import os
import signal
import threading
import queue
import time
import json
from collections import deque
from io import BytesIO
from .media import MediaError


def parse_download(line):
    if not line.startswith('CLIP_PROGRESS '):return None
    try:data=json.loads(line[len('CLIP_PROGRESS '):])
    except (ValueError,TypeError):return None
    total=data.get('total_bytes') or data.get('total_bytes_estimate')
    done=data.get('downloaded_bytes')
    if not total and data.get('fragment_count'):
        total=data['fragment_count'];done=data.get('fragment_index',0)
    return dict(stage='Descargando fuente',phase_key=data.get('filename'),done=done,total=total,speed=data.get('speed') if data.get('total_bytes') else None,eta=data.get('eta'),message='Pista/archivo actual: '+str(data.get('_percent_str') or 'descargando').strip())


def run_observed(args,progress,duration=None,timeout=3600,binary=False,stage='Procesando',cwd=None):
    events=queue.Queue();result=BytesIO();errors=deque(maxlen=35);started=time.monotonic();fields={}
    try:p=subprocess.Popen([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE if binary else subprocess.STDOUT,cwd=cwd,start_new_session=os.name!='nt',creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0) if os.name=='nt' else 0)
    except FileNotFoundError as e:raise MediaError(f'No se encontró {args[0]}.') from e
    def text_reader(stream):
        try:
            for raw in iter(stream.readline,b''):events.put(raw.decode('utf-8',errors='replace').strip())
        finally:events.put(None);stream.close()
    def binary_reader():
        try:
            for block in iter(lambda:p.stdout.read(256*1024),b''):result.write(block)
        finally:p.stdout.close()
    reader=threading.Thread(target=text_reader,args=(p.stderr if binary else p.stdout,),daemon=True);reader.start()
    writer=threading.Thread(target=binary_reader,daemon=True) if binary else None
    if writer:writer.start()
    completed=False
    try:
        finished=False
        while not finished:
            if time.monotonic()-started>timeout:raise MediaError('Se agotó el tiempo de esta etapa. El original se conserva.')
            try:line=events.get(timeout=.25)
            except queue.Empty:progress({});continue
            if line is None:finished=True;continue
            event=parse_download(line)
            if event is not None:progress(event);continue
            if line.startswith(('[Merger]','[Fixup','[VideoRemuxer]')):
                progress(dict(stage='Uniendo y verificando las pistas',message='La descarga terminó; preparando un archivo reproducible.'));continue
            if '=' in line:
                key,value=line.split('=',1)
                if key in {'out_time_us','out_time_ms','speed','progress'}:
                    fields[key]=value
                    if key=='progress':
                        try:done=max(0,float(fields.get('out_time_us',fields.get('out_time_ms',0)))/1e6)
                        except ValueError:done=0
                        try:speed=float(fields.get('speed','0').rstrip('x'))
                        except ValueError:speed=0
                        progress(dict(stage=stage,done=done,total=duration,speed=speed,message='Tiempo de video procesado: '+str(round(done,1))+' s'))
                    continue
            if line:errors.append(line[-400:])
        p.wait(timeout=10)
        if writer:writer.join(timeout=10)
        if p.returncode:raise MediaError('\n'.join(errors)[-3500:] or 'No se pudo completar la etapa.')
        completed=True
        return result.getvalue() if binary else b''
    finally:
        if not completed:
            if os.name=='nt':
                if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15)
            else:
                try:os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            if p.poll() is None:p.kill()
            p.wait()
        reader.join(timeout=5)
        if writer:writer.join(timeout=5)
