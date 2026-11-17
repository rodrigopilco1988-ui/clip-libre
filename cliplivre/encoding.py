"""Selección de codificador con prueba real de NVENC, independiente de CUDA/Whisper."""
from functools import lru_cache
from .media import run


@lru_cache(maxsize=1)
def nvenc_available():
    try:
        run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=128x128:r=30',
             '-frames:v','1','-c:v','h264_nvenc','-f','null','-'],timeout=20)
        return True
    except Exception:
        return False


def choose_encoder(requested):
    if requested not in {'auto','cpu','nvidia'}:
        raise ValueError('Codificador no permitido.')
    return 'h264_nvenc' if requested!='cpu' and nvenc_available() else 'libx264'


def encoder_options(encoder,preset):
    if encoder=='h264_nvenc':
        return ['-c:v','h264_nvenc','-preset','p1' if preset=='ultrafast' else 'p4','-rc','vbr','-cq','23','-b:v','0']
    return ['-c:v','libx264','-preset',preset,'-crf','20']
