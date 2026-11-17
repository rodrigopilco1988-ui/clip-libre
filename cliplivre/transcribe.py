import gc
import time

MODELS = ['tiny','base','small','medium']
_CUDA_FAILURE = None


def _once(samples, model, device, language,notify=lambda message:None,fast=False,process_progress=None):
    from .gpu_runtime import prepare_libraries
    if device=='cuda': prepare_libraries()
    from faster_whisper import WhisperModel
    engine = None
    segments = None
    try:
        if process_progress:process_progress(dict(stage='Cargando Whisper en '+device.upper(),message='La primera carga puede descargar el modelo local.'))
        engine = WhisperModel(model, device=device, compute_type='int8_float16' if device=='cuda' else 'int8')
        decode_started=time.monotonic()
        batch_size=(8 if device=='cuda' else 4) if fast else 1
        if fast:
            from faster_whisper import BatchedInferencePipeline
            runner=BatchedInferencePipeline(engine)
            segments,info=runner.transcribe(samples,language=language or None,word_timestamps=True,vad_filter=True,beam_size=1,batch_size=batch_size)
        else:
            segments,info=engine.transcribe(samples,language=language or None,word_timestamps=True,vad_filter=True,beam_size=1 if device=='cpu' else 3)
        result=[]
        reported=-10.
        # Whisper es perezoso: una DLL puede fallar al iterar, no al construir.
        for s in segments:
            if float(s.end)-reported>=10:
                notify(f'Transcripción en {device.upper()}: {float(s.end)/60:.1f} min leídos del bloque')
                reported=float(s.end)
            if process_progress:process_progress(dict(stage='Transcribiendo bloque',done=float(s.end),total=len(samples)/16000,origin=decode_started,message='Transcripción en '+device.upper()))
            result.append(dict(start=float(s.start),end=float(s.end),text=s.text.strip(),
                words=[dict(start=float(w.start),end=float(w.end),text=w.word.strip()) for w in (s.words or [])]))
        return result, dict(device=device,language=info.language,batched=fast,batch_size=batch_size)
    finally:
        if segments is not None:
            close=getattr(segments,'close',None)
            if close:
                try: close()
                except Exception: pass
            del segments
        if engine is not None:
            backend=getattr(engine,'model',None)
            unload=getattr(backend,'unload_model',None)
            if unload:
                try: unload()
                except Exception: pass
            del backend
            del engine
        gc.collect()


def transcribe(samples, model='small', device='auto', language=None, progress=lambda message:None,fast=False,process_progress=None):
    global _CUDA_FAILURE
    if model not in MODELS:
        raise ValueError('Modelo Whisper no permitido.')
    if device not in {'auto','cpu','cuda'}:
        raise ValueError('Procesador no permitido.')
    warning=None
    use_cuda=False
    if device!='cpu':
        if _CUDA_FAILURE:
            warning='La GPU no está disponible en esta sesión. Se continúa en CPU.'
        else:
            try:
                from .gpu_runtime import prepare_libraries
                prepare_libraries()
                import ctranslate2
                use_cuda=device=='cuda' or ctranslate2.get_cuda_device_count()>0
            except Exception as e:
                _CUDA_FAILURE=str(e)[:400]
                warning='No se pudo comprobar la GPU. Se continúa en CPU.'
    if use_cuda:
        progress('Transcribiendo con la GPU…')
        try:
            result,metadata=_once(samples,model,'cuda',language,progress,fast,process_progress)
            metadata['requested_device']=device
            return result,metadata
        except Exception as e:
            _CUDA_FAILURE=str(e)[:400]
            warning='No se pudo usar la GPU. Se continúa automáticamente en CPU; no necesitas instalar CUDA para generar clips.'
            # _once ya cerró el generador y liberó el modelo antes del reintento.
    progress(warning or 'Transcribiendo en CPU…')
    try:
        result,metadata=_once(samples,model,'cpu',language,progress,fast,process_progress)
    except Exception as e:
        detail=f' GPU: {_CUDA_FAILURE}.' if warning else ''
        raise RuntimeError(f'No se pudo transcribir en CPU: {e}.{detail} El bloque no se guardó como terminado; puedes reintentarlo.') from e
    metadata['requested_device']=device
    if warning:
        metadata['warning']=warning
        metadata['cuda_error']=_CUDA_FAILURE
    return result,metadata
