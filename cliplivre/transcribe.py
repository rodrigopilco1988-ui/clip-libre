import gc

MODELS = ['tiny','base','small','medium']

def transcribe(samples, model='small', device='auto', language=None):
    if model not in MODELS:
        raise ValueError('Modelo Whisper no permitido.')
    from faster_whisper import WhisperModel
    import ctranslate2
    gpu = ctranslate2.get_cuda_device_count() > 0 if device == 'auto' else device == 'cuda'
    actual = 'cuda' if gpu else 'cpu'
    engine = None
    try:
        engine = WhisperModel(model, device=actual, compute_type='int8_float16' if gpu else 'int8')
        segments, info = engine.transcribe(samples, language=language or None, word_timestamps=True, vad_filter=True, beam_size=3)
        result = []
        for s in segments:
            result.append(dict(start=float(s.start),end=float(s.end),text=s.text.strip(),
                words=[dict(start=float(w.start),end=float(w.end),text=w.word.strip()) for w in (s.words or [])]))
        return result, dict(device=actual, language=info.language)
    except Exception as e:
        raise RuntimeError(f'No se pudo transcribir en {actual}: {e}. En CUDA revisa CUDA/cuDNN o elige CPU.') from e
    finally:
        if engine is not None:
            del engine
        gc.collect()  # Se libera Whisper antes de pedir clasificación a Ollama.
