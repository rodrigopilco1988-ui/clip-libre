from dataclasses import dataclass, asdict
import hashlib
import json
import time
import uuid
import psutil
from . import media, transcribe
from .signals import audio_features, visual_features
from .rank import propose, classify

@dataclass
class Analysis:
    block_minutes: float = 50
    model: str = 'small'
    device: str = 'auto'
    language: str = 'es'
    ollama: bool = False
    ollama_model: str = 'qwen3:4b'
    visual_step: float = 2
    min_seconds: int = 12
    max_seconds: int = 60
    max_candidates: int = 20


def analyze(store,sid,config=None,progress=lambda fraction,message:None,transcriber=None,max_blocks=None):
    config=config or Analysis()
    if config.block_minutes<=0 or config.visual_step<.5 or not 1<=config.max_candidates<=20 or not 1<=config.min_seconds<=config.max_seconds<=180:
        raise ValueError('Configuración de análisis inválida.')
    source=store.source(sid); info=media.probe(source['path'])
    # La configuración forma parte de la clave; cambiarla permite reanalizar explícitamente.
    fingerprint=hashlib.sha256(json.dumps(asdict(config),sort_keys=True).encode()).hexdigest()
    done=store.chunks(sid,fingerprint)
    cursor=0.
    for row in done:
        if row['start']<=cursor+.01: cursor=max(cursor,row['end'])
    session=uuid.uuid4().hex; started=time.perf_counter(); warnings=[]; blocks=0
    memory=psutil.Process().memory_info().rss
    store.job(session,sid,'procesando','Iniciando análisis')
    try:
        while cursor<info['duration']-.01 and (max_blocks is None or blocks<max_blocks):
            end=min(info['duration'],cursor+config.block_minutes*60)
            progress(cursor/info['duration'],f'Transcribiendo {cursor/60:.1f}–{end/60:.1f} min')
            samples=media.audio(source['path'],cursor,end-cursor) if info['audio'] else []
            if len(samples):
                segments,metadata=(transcriber or transcribe.transcribe)(samples,config.model,config.device,config.language)
            else: segments,metadata=[],dict(device='sin audio')
            for s in segments:
                s['start']+=cursor; s['end']+=cursor
                for w in s.get('words',[]): w['start']+=cursor; w['end']+=cursor
            audio=audio_features(samples)
            for f in audio: f['time']+=cursor; f['end']+=cursor
            progress(cursor/info['duration'],'Midiendo cambios visuales…')
            visual=visual_features(source['path'],cursor,end,config.visual_step)
            candidates=propose(segments,audio,visual,cursor,end,config.max_candidates,config.min_seconds,config.max_seconds)
            if config.ollama:
                progress(cursor/info['duration'],'Clasificando con Ollama local…')
                candidates,notes=classify(candidates,config.ollama_model); warnings+=notes
            memory=max(memory,psutil.Process().memory_info().rss)
            store.save_chunk(sid,session,cursor,end,fingerprint,dict(segments=segments,audio=audio,visual=visual,metadata=metadata),candidates)
            del samples
            cursor=end; blocks+=1
            progress(cursor/info['duration'],f'Bloque guardado: {cursor/60:.1f} min')
        report=dict(session=session,blocks=blocks,processed_until=cursor,elapsed_seconds=round(time.perf_counter()-started,3),rss_sampled_mb=round(memory/1024**2,1),warnings=warnings,config=asdict(config))
        store.job(session,sid,'completado',json.dumps(report,ensure_ascii=False))
        return report
    except Exception as e:
        store.job(session,sid,'error',str(e))
        raise
