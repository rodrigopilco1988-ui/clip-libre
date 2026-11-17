import json
import subprocess
from types import SimpleNamespace
import numpy as np
from cliplivre import encoding,transcribe
from cliplivre.render import render,Edit
from cliplivre.media import probe
from cliplivre.composition import default_panels


def test_probe_checks_real_nvenc_encode_and_caches(monkeypatch):
    encoding.nvenc_available.cache_clear(); calls=[]
    monkeypatch.setattr(encoding,'run',lambda args,timeout:calls.append(args))
    assert encoding.choose_encoder('auto')=='h264_nvenc'
    assert encoding.choose_encoder('nvidia')=='h264_nvenc'
    assert len(calls)==1 and '-frames:v' in calls[0]
    assert encoding.choose_encoder('cpu')=='libx264'
    encoding.nvenc_available.cache_clear()


def test_unavailable_nvenc_uses_cpu(monkeypatch):
    encoding.nvenc_available.cache_clear()
    def fail(*a,**k): raise RuntimeError('driver no compatible')
    monkeypatch.setattr(encoding,'run',fail)
    assert encoding.choose_encoder('auto')=='libx264'
    encoding.nvenc_available.cache_clear()


def test_failed_nvenc_export_retries_cpu_and_preserves_audio(video,tmp_path,monkeypatch):
    real_run=subprocess.run; attempts=[]
    monkeypatch.setattr(encoding,'choose_encoder',lambda _: 'h264_nvenc')
    def command(args,**kwargs):
        if '-c:v' in args:
            encoder=args[args.index('-c:v')+1]; attempts.append(encoder)
            if encoder=='h264_nvenc':
                from pathlib import Path
                Path(args[-1]).write_bytes(b'partial')
                return SimpleNamespace(returncode=1,stderr=b'NVENC session unavailable')
        return real_run(args,**kwargs)
    monkeypatch.setattr(subprocess,'run',command)
    messages=[]
    output=render(video,1,3,[],tmp_path/'out',Edit(resolution=360,framing='paneles',panels=default_panels(1),preset='ultrafast'),progress=messages.append)
    assert attempts==['h264_nvenc','libx264']
    info=probe(output); assert info['audio'] and abs(info['duration']-2)<.2
    assert json.loads((output.parent/'edicion.json').read_text())['encoder_used']=='libx264'
    assert any('reintentando en CPU' in m for m in messages)


def test_fast_transcription_uses_batches_and_word_timestamps(monkeypatch):
    import faster_whisper
    calls=[]; unloaded=[]
    class Engine:
        def __init__(self,*a,**kw):
            self.model=SimpleNamespace(unload_model=lambda:unloaded.append(True))
    class Batch:
        def __init__(self,engine): pass
        def transcribe(self,samples,**kw):
            calls.append(kw)
            word=SimpleNamespace(start=.1,end=.9,word=' palabra')
            return iter([SimpleNamespace(start=0.,end=1.,text='palabra',words=[word])]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    monkeypatch.setattr(faster_whisper,'BatchedInferencePipeline',Batch)
    result,metadata=transcribe.transcribe(np.ones(16000),'tiny','cpu','es',fast=True)
    assert calls[0]['batch_size']==4 and calls[0]['beam_size']==1 and calls[0]['word_timestamps']
    assert result[0]['words'][0]['text']=='palabra' and metadata['batched'] and unloaded


def test_face_tracking_ignores_jitter_and_limits_speed():
    from cliplivre.render import face_track
    frames=[dict(time=float(i),faces=[[x-.05,.1,.1,.1]]) for i,x in enumerate([.5,.51,.48,.52,.9,.1,.9,.1])]
    points=face_track(frames,[(0,8)])
    assert [x for t,x in points[:4]]==[.5,.5,.5,.5]
    assert all(abs(b-a)<=(tb-ta)*.025+.00001 for (ta,a),(tb,b) in zip(points,points[1:]))


def test_batched_cuda_failure_releases_gpu_before_cpu(monkeypatch):
    import faster_whisper,ctranslate2
    monkeypatch.setattr(transcribe,'_CUDA_FAILURE',None)
    monkeypatch.setattr(ctranslate2,'get_cuda_device_count',lambda:1)
    events=[]
    class Engine:
        def __init__(self,*a,device,**kw):
            self.device=device; events.append('load '+device)
            self.model=SimpleNamespace(unload_model=lambda:events.append('unload '+device))
    class Batch:
        def __init__(self,engine): self.engine=engine
        def transcribe(self,samples,**kw):
            events.append((self.engine.device,kw['batch_size']))
            segment=SimpleNamespace(start=0.,end=1.,text=self.engine.device,words=[])
            if self.engine.device=='cuda':
                def partial():
                    yield segment
                    raise RuntimeError('GPU out of memory')
                return partial(),SimpleNamespace(language='es')
            return iter([segment]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    monkeypatch.setattr(faster_whisper,'BatchedInferencePipeline',Batch)
    result,metadata=transcribe.transcribe(np.ones(16000),'tiny','auto','es',fast=True)
    assert result[0]['text']=='cpu' and metadata['device']=='cpu' and metadata['warning']
    assert ('cuda',8) in events and ('cpu',4) in events
    assert events.index('unload cuda')<events.index('load cpu')
