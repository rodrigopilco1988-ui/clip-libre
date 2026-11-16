import numpy as np
import pytest
from cliplivre.signals import audio_features,visual_features,silent_intervals
from cliplivre.rank import propose,classify
from cliplivre import transcribe

def test_audio_silence_scene(video):
    samples=np.concatenate([np.zeros(32000,dtype=np.float32),np.ones(32000,dtype=np.float32)*.3])
    features=audio_features(samples)
    assert features[0]['silence'] and not features[-1]['silence']
    assert features[2]['change']>10
    assert silent_intervals(features,0,4)
    frames=visual_features(video,0,8,1)
    assert len(frames)==8 and all('faces' in f for f in frames)

def test_proposals_do_not_force_twenty():
    segments=[dict(start=2,end=6,text='mira qué sorpresa',words=[]),dict(start=3,end=7,text='mira',words=[])]
    candidates=propose(segments,[],[],0,30)
    assert len(candidates)==1
    assert 0<=candidates[0]['score']<=100
    assert candidates[0]['evidence']

def test_ollama_fallback_and_quote_validation(monkeypatch):
    import requests
    c=dict(evidence='hola mundo',title='hola',score=40)
    def unavailable(*a,**k): raise requests.ConnectionError('apagado')
    monkeypatch.setattr(requests.Session,'post',unavailable)
    result,warnings=classify([c.copy()]); assert warnings and result[0]['score']==40
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'response':'{"title":"Falso", "hook":"x", "reason":"x", "score":99,"evidence_quote":"explosión"}'}
    monkeypatch.setattr(requests.Session,'post',lambda *a,**k:Response())
    result,warnings=classify([c.copy()]); assert warnings and result[0]['title']=='hola'
    class Valid(Response):
        def json(self): return {'response':'{"title":"Saludo", "hook":"hola", "reason":"saludo", "score":52,"evidence_quote":"hola"}'}
    monkeypatch.setattr(requests.Session,'post',lambda *a,**k:Valid())
    result,warnings=classify([c.copy()]); assert not warnings and result[0]['score']==52
    with pytest.raises(ValueError): classify([],endpoint='https://external.example')

def test_whisper_model_validation():
    with pytest.raises(ValueError): transcribe.transcribe(np.zeros(100),'large')

def test_visual_only_candidates():
    out=propose([],[],[dict(time=7.,scene=.8,faces=[])],0,20)
    assert out and out[0]['classification']=='heurística visual'


def test_whisper_success_and_cleanup(monkeypatch):
    import faster_whisper,ctranslate2
    from types import SimpleNamespace
    class Fake:
        def __init__(self,*args,**kwargs): assert kwargs['device']=='cpu'
        def transcribe(self,*args,**kwargs):
            word=SimpleNamespace(start=.1,end=.2,word=' Hola')
            segment=SimpleNamespace(start=.1,end=.2,text=' Hola',words=[word])
            return iter([segment]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Fake)
    segments,info=transcribe.transcribe(np.ones(16000,dtype=np.float32),'tiny','cpu','es')
    assert segments[0]['words'][0]['text']=='Hola' and info['device']=='cpu'
    def fail(*args,**kwargs): raise RuntimeError('DLL de prueba')
    monkeypatch.setattr(faster_whisper,'WhisperModel',fail)
    with pytest.raises(RuntimeError,match='No se pudo transcribir'): transcribe.transcribe(np.ones(16000),'tiny','cpu')
