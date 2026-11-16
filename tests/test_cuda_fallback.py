from types import SimpleNamespace
import numpy as np
import pytest
from cliplivre import transcribe


@pytest.fixture(autouse=True)
def reset_cuda(monkeypatch):
    monkeypatch.setattr(transcribe,'_CUDA_FAILURE',None)


def segment(text):
    return SimpleNamespace(start=0.,end=1.,text=text,words=[SimpleNamespace(start=0.,end=1.,word=text)])


@pytest.mark.parametrize('device',['auto','cuda'])
def test_missing_cublas_automatically_uses_cpu(monkeypatch,device):
    import faster_whisper,ctranslate2
    monkeypatch.setattr(ctranslate2,'get_cuda_device_count',lambda:1)
    calls=[]; unloaded=[]; messages=[]
    class Engine:
        def __init__(self,model,device,compute_type):
            self.device=device; calls.append(device)
            self.model=SimpleNamespace(unload_model=lambda:unloaded.append(device))
        def transcribe(self,*args,**kwargs):
            if self.device=='cuda': raise RuntimeError('Library cublas64_12.dll is not found or cannot be loaded')
            return iter([segment('CPU correcta')]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    result,metadata=transcribe.transcribe(np.ones(16000,dtype=np.float32),'tiny',device,'es',messages.append)
    assert calls==['cuda','cpu'] and unloaded==['cuda','cpu']
    assert result[0]['text']=='CPU correcta' and metadata['device']=='cpu'
    assert 'automáticamente' in metadata['warning'] and 'cublas64_12.dll' in metadata['cuda_error']
    assert any('CPU' in m for m in messages)
    transcribe.transcribe(np.ones(16000),'tiny',device,'es')
    assert calls==['cuda','cpu','cpu']


def test_cuda_failure_during_lazy_iteration_discards_partial_output(monkeypatch):
    import faster_whisper,ctranslate2
    monkeypatch.setattr(ctranslate2,'get_cuda_device_count',lambda:1)
    events=[]
    class Engine:
        def __init__(self,model,device,compute_type):
            self.device=device; events.append('load '+device)
            self.model=SimpleNamespace(unload_model=lambda:events.append('unload '+device))
        def transcribe(self,*args,**kwargs):
            if self.device=='cpu': return iter([segment('CPU completa')]),SimpleNamespace(language='es')
            def lazy():
                yield segment('GPU parcial')
                raise RuntimeError('cuDNN no disponible')
            return lazy(),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    result,metadata=transcribe.transcribe(np.ones(16000),'tiny','auto','es')
    assert [s['text'] for s in result]==['CPU completa']
    assert events.index('unload cuda')<events.index('load cpu')


def test_cpu_failure_is_not_reported_as_success(monkeypatch):
    import faster_whisper
    def fail(*args,**kwargs): raise RuntimeError('No se puede cargar el modelo')
    monkeypatch.setattr(faster_whisper,'WhisperModel',fail)
    with pytest.raises(RuntimeError,match='bloque no se guardó'):
        transcribe.transcribe(np.ones(16000),'tiny','cpu')


def test_working_cuda_stays_on_gpu(monkeypatch):
    import faster_whisper,ctranslate2
    monkeypatch.setattr(ctranslate2,'get_cuda_device_count',lambda:1)
    class Engine:
        def __init__(self,model,device,compute_type): assert device=='cuda'
        def transcribe(self,*args,**kwargs): return iter([segment('GPU válida')]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    result,metadata=transcribe.transcribe(np.ones(16000),'tiny','auto','es')
    assert metadata['device']=='cuda' and 'warning' not in metadata


def test_fallback_keeps_incremental_progress(video,tmp_path,monkeypatch):
    import faster_whisper,ctranslate2
    from cliplivre.store import Store
    from cliplivre.pipeline import Analysis,analyze
    monkeypatch.setattr(ctranslate2,'get_cuda_device_count',lambda:1)
    calls=[]
    class Engine:
        def __init__(self,model,device,compute_type):
            calls.append(device)
            if device=='cuda': raise RuntimeError('cublas64_12.dll not found')
        def transcribe(self,*args,**kwargs): return iter([segment('CPU válida')]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    store=Store(tmp_path/'history'); sid=store.register(video)
    config=Analysis(model='tiny',block_minutes=.1,min_seconds=5,max_seconds=10)
    first=analyze(store,sid,config,max_blocks=1)
    assert first['processed_until']==6 and first['devices']==['cpu'] and first['warnings']
    second=analyze(store,sid,config,max_blocks=1)
    assert second['processed_until']==8 and second['blocks']==1
    assert analyze(store,sid,config)['blocks']==0
    assert calls==['cuda','cpu','cpu']
