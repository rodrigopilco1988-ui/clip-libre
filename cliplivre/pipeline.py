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
    visual_fast: bool = True
    min_seconds: float = 30
    max_seconds: float | None = None
    target_seconds: float = 180
    max_candidates: int = 20
    duration_variation: bool = False
    transcription: bool = True
    fast_asr: bool = False
    source_start: float = 0
    source_end: float | None = None


def analyze(store,sid,config=None,progress=lambda fraction,message:None,transcriber=None,max_blocks=None):
    config=config or Analysis()
    if config.block_minutes<=0 or config.visual_step<.5 or not 1<=config.max_candidates<=20 or config.min_seconds<=0 or config.target_seconds<=0 or (config.max_seconds is not None and config.max_seconds<config.min_seconds):
        raise ValueError('Configuración de análisis inválida.')
    source=store.source(sid); info=media.probe(source['path'])
    range_start=float(config.source_start)
    range_end=float(config.source_end) if config.source_end is not None else info['duration']
    if not 0<=range_start<range_end<=info['duration']+.01: raise ValueError('El inicio y el fin deben estar dentro del video.')
    range_end=min(range_end,info['duration'])
    # La configuración forma parte de la clave; cambiarla permite reanalizar explícitamente.
    fingerprint=hashlib.sha256(json.dumps(asdict(config),sort_keys=True).encode()).hexdigest()
    done=store.chunks(sid,fingerprint)
    cursor=range_start
    for row in done:
        if row['start']<=cursor+.01: cursor=max(cursor,row['end'])
    session=uuid.uuid4().hex; started=time.perf_counter(); warnings=[]; blocks=0; devices=[]; stage_times={}; cache_hits=0; reused_transcriptions=0
    memory=psutil.Process().memory_info().rss
    store.job(session,sid,'procesando','Iniciando análisis')
    try:
        while cursor<range_end-.01 and (max_blocks is None or blocks<max_blocks):
            end=min(range_end,cursor+config.block_minutes*60)
            progress((cursor-range_start)/(range_end-range_start),f'Analizando {cursor/60:.1f}–{end/60:.1f} min')
            from concurrent.futures import ThreadPoolExecutor
            stage_start=time.perf_counter()
            asr_key=f'asr-v2:{config.model}:{config.language}' if config.transcription else 'audio-only-v1'
            visual_key=f'visual-v2:{config.visual_step}:{config.visual_fast}'
            cached=store.artifact(sid,asr_key,cursor,end)
            if cached is None and config.transcription:
                cached=store.compatible_transcript(sid,config.model,config.language,cursor,end)
                if cached is not None: store.save_artifact(sid,asr_key,cursor,end,cached)
            visual=store.artifact(sid,visual_key,cursor,end)
            with ThreadPoolExecutor(max_workers=1) as worker:
                visual_job=worker.submit(visual_features,source['path'],cursor,end,config.visual_step,False,config.visual_fast) if visual is None else None
                if cached:
                    segments=cached['segments']; audio=cached['audio']; metadata=cached['metadata']; cache_hits+=1; reused_transcriptions+=int(config.transcription)
                    progress((cursor-range_start)/(range_end-range_start),'Reutilizando análisis guardado…')
                else:
                    samples=media.audio(source['path'],cursor,end-cursor) if info['audio'] else []
                    if len(samples) and not config.transcription:
                        segments,metadata=[],dict(device='sin transcripción',transcription='pendiente para el clip elegido')
                    elif len(samples):
                        if transcriber:
                            segments,metadata=transcriber(samples,config.model,config.device,config.language)
                        else:
                            segments,metadata=transcribe.transcribe(samples,config.model,config.device,config.language,fast=config.fast_asr,progress=lambda m:progress((cursor-range_start)/(range_end-range_start),m))
                    else: segments,metadata=[],dict(device='sin audio')
                    for seg in segments:
                        seg['start']+=cursor; seg['end']+=cursor
                        for word in seg.get('words',[]): word['start']+=cursor; word['end']+=cursor
                    audio=audio_features(samples)
                    for feature in audio: feature['time']+=cursor; feature['end']+=cursor
                    del samples
                    store.save_artifact(sid,asr_key,cursor,end,dict(segments=segments,audio=audio,metadata=metadata))
                stage_times['audio_transcription']=stage_times.get('audio_transcription',0)+time.perf_counter()-stage_start
                wait_start=time.perf_counter()
                if visual_job:
                    progress((cursor-range_start)/(range_end-range_start),'Finalizando muestreo visual…')
                    visual=visual_job.result()
                    store.save_artifact(sid,visual_key,cursor,end,visual)
                else: cache_hits+=1
                stage_times['visual_wait']=stage_times.get('visual_wait',0)+time.perf_counter()-wait_start
            actual=metadata.get('device','desconocido')
            if actual not in devices: devices.append(actual)
            note=metadata.get('warning')
            if note and not cached and note not in warnings: warnings.append(note)
            candidates=propose(segments,audio,visual,cursor,end,config.max_candidates,config.min_seconds,config.max_seconds,config.target_seconds,config.duration_variation)
            for candidate in candidates:
                candidate['duration_limits']={'minimum':config.min_seconds,'maximum':config.max_seconds}
            if config.ollama:
                progress((cursor-range_start)/(range_end-range_start),'Clasificando con Ollama local…')
                candidates,notes=classify(candidates,config.ollama_model); warnings+=notes
            memory=max(memory,psutil.Process().memory_info().rss)
            store.save_chunk(sid,session,cursor,end,fingerprint,dict(segments=segments,audio=audio,visual=visual,metadata=metadata),candidates)
            cursor=end; blocks+=1
            progress((cursor-range_start)/(range_end-range_start),f'Bloque guardado: {cursor/60:.1f} min')
        report=dict(session=session,blocks=blocks,processed_until=cursor,elapsed_seconds=round(time.perf_counter()-started,3),rss_sampled_mb=round(memory/1024**2,1),warnings=warnings,devices=devices,cache_hits=cache_hits,transcriptions_reused=reused_transcriptions,stage_seconds={k:round(v,3) for k,v in stage_times.items()},config=asdict(config))
        store.job(session,sid,'completado',json.dumps(report,ensure_ascii=False))
        return report
    except Exception as e:
        store.job(session,sid,'error',str(e))
        raise
