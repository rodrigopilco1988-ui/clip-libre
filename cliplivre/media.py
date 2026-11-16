from pathlib import Path
import json
import subprocess

class MediaError(RuntimeError):
    pass

def run(args, timeout=3600):
    try:
        p = subprocess.run([str(a) for a in args], capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise MediaError(f"No se encontró {args[0]}. Instala FFmpeg y reinicia la aplicación.") from e
    except subprocess.TimeoutExpired as e:
        raise MediaError("La operación superó el tiempo máximo; el original se conserva.") from e
    if p.returncode:
        raise MediaError(p.stderr.decode('utf-8', errors='replace')[-3500:])
    return p.stdout

def probe(path):
    raw = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]))
    video = next((s for s in raw['streams'] if s['codec_type'] == 'video'), None)
    if not video:
        raise MediaError('El archivo no contiene una pista de video válida.')
    duration = float(raw['format'].get('duration', video.get('duration', 0)))
    if duration <= 0:
        raise MediaError('No se conoce la duración. Recupera primero un segmento finito del directo.')
    return dict(duration=duration, width=video['width'], height=video['height'],
                audio=any(s['codec_type'] == 'audio' for s in raw['streams']))

def audio(path, start, duration, rate=16000):
    import numpy as np
    raw = run(['ffmpeg', '-v', 'error', '-ss', start, '-i', path, '-t', duration,
               '-vn', '-ac', '1', '-ar', rate, '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(raw, dtype=np.float32).copy()

def preview(path, start, end, output):
    import uuid
    output=Path(output)
    temp=output.with_name(output.stem+'.'+uuid.uuid4().hex+'.building.mp4')
    try:
        run(['ffmpeg', '-v', 'error', '-y', '-threads', '2', '-ss', start, '-i', path, '-t', end-start,
             '-vf', 'scale=640:-2,fps=24', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '27',
             '-c:a', 'aac', '-movflags', '+faststart', temp])
        temp.replace(output)
        return output
    finally:
        temp.unlink(missing_ok=True)
