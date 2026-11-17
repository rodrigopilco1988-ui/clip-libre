import json,sys,time
import numpy as np
import requests
from cliplivre.progress import Progress
from cliplivre.observed import run_observed,parse_download
from cliplivre.sources import incomplete_duration


def test_eta_is_measured_phase_specific_and_finished_time_stops():
    clock=[0.];job=Progress(clock=lambda:clock[0]);job.start('Descargando')
    assert job.snapshot()['eta'] is None
    clock[0]=10.;job.update(done=10,total=100)
    assert job.snapshot()['eta']==90
    clock[0]=15.;assert job.snapshot()['eta']==85 and job.snapshot()['fraction']==.1
    job.start('Analizando');assert job.snapshot()['eta'] is None and job.snapshot()['fraction'] is None
    clock[0]=20.;job.finish();clock[0]=50.
    assert job.snapshot()['elapsed']==20 and job.snapshot()['status']=='completado'


def test_subprocess_progress_is_delivered_before_exit_and_without_fake_percent():
    events=[];started=time.monotonic()
    script="import time;print('CLIP_PROGRESS '+%r,flush=True);time.sleep(.8)" % json.dumps(dict(downloaded_bytes=10,total_bytes=100,eta=9,speed=10))
    run_observed([sys.executable,'-u','-c',script],lambda e:events.append((time.monotonic()-started,e)),timeout=5)
    progress=next(t for t,e in events if e.get('done')==10)
    assert progress<time.monotonic()-started-.5 and any(not e for t,e in events)
    assert parse_download('garbage') is None


def test_real_audio_extraction_reports_ffmpeg_time_without_corrupting_samples(video):
    from cliplivre.media import audio
    events=[]
    measured=audio(video,1,3,progress=events.append);reference=audio(video,1,3)
    assert np.array_equal(measured,reference)
    assert any(e.get('done',0)>2.5 for e in events) and all(e.get('total',3)==3 for e in events)


def test_progress_endpoint_is_local_and_token_bound():
    from cliplivre.playback import MediaServer
    job=Progress();job.start('Preparando')
    server=MediaServer()
    try:
        url=server.progress_url(lambda:[job.snapshot()])
        response=requests.get(url,timeout=5)
        assert response.json()[0]['stage']=='Preparando' and response.headers['Cache-Control']=='no-store'
        assert requests.get(url.rsplit('/',1)[0]+'/unknown',timeout=5).status_code==404
    finally:server.close()


def test_incomplete_four_hour_file_cannot_match_eight_hour_vod_cache(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    from cliplivre import media
    store=Store(tmp_path/'partial-cache');sid=store.register(video)
    url='https://www.twitch.tv/videos/2926826151'
    store.save_settings(sid,{'import':dict(url=url,start=0,end=None,mode='Todo lo disponible',live=False)})
    monkeypatch.setattr(media,'probe',lambda p:dict(duration=14400))
    assert store.find_import(url,0,None,'Todo lo disponible',expected_duration=29050) is None
    assert incomplete_duration(29050,14400) and not incomplete_duration(29050,29049.99)


def test_observed_process_timeout_stops_owned_task():
    from cliplivre.media import MediaError
    import pytest
    started=time.monotonic()
    with pytest.raises(MediaError,match='agotó el tiempo'):
        run_observed([sys.executable,'-u','-c','import time;time.sleep(20)'],lambda event:None,timeout=.4)
    assert time.monotonic()-started<8


def test_whisper_reports_actual_audio_position_without_fake_timer(monkeypatch):
    import faster_whisper
    from types import SimpleNamespace
    from cliplivre.transcribe import transcribe
    class Engine:
        def __init__(self,*a,**kw):pass
        def transcribe(self,*a,**kw):return iter([SimpleNamespace(start=0.,end=2.,text='Prueba',words=[])]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    events=[]
    transcribe(np.ones(4*16000,dtype=np.float32),'tiny','cpu','es',process_progress=events.append)
    measured=next(e for e in events if e.get('stage')=='Transcribiendo bloque')
    assert measured['done']==2 and measured['total']==4 and measured['origin']>0
