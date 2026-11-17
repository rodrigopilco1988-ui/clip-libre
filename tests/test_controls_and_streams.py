from pathlib import Path
import json
import shutil
import numpy as np
import pytest
from cliplivre.controls import parse_clock,clip_limits
from cliplivre.rank import propose
from cliplivre.sources import import_url
from cliplivre.store import Store


def test_half_minute_to_one_and_half_is_thirty_to_ninety():
    assert parse_clock('0:30')==30 and parse_clock('1:30')==90
    assert parse_clock('1:50:00')==6600
    assert clip_limits('Personalizado','0:30','1:30')==(30,90)
    with pytest.raises(ValueError): parse_clock('30')
    with pytest.raises(ValueError): clip_limits('Personalizado','1:30','0:30')


def test_every_proposal_respects_range_and_lengths_vary():
    segments=[dict(start=float(i),end=float(i+10),text=f'Frase {i}',words=[dict(start=float(i),end=float(i+1),text=f'Frase {i}')]) for i in range(0,1200,10)]
    clips=propose(segments,[],[],0,1200,min_seconds=30,max_seconds=90,target_seconds=60,vary=True)
    lengths=[c['end']-c['start'] for c in clips]
    assert len(clips)>=5 and all(30-.001<=d<=90+.001 for d in lengths)
    assert len(set(round(d) for d in lengths))>=2


def test_long_single_transcript_does_not_force_ninety_every_time():
    segment=dict(start=0.,end=600.,text='Una conversación larga',words=[dict(start=float(i),end=float(i+1),text='palabra') for i in range(600)])
    clips=propose([segment],[],[],0,600,min_seconds=30,max_seconds=90,target_seconds=60,vary=True)
    assert len(clips)>=3 and all(30<=c['end']-c['start']<=90 for c in clips)
    assert len({c['end']-c['start'] for c in clips})>1


def test_source_window_thirty_to_one_ten_has_no_fifty_minute_cap(video,tmp_path,monkeypatch):
    from cliplivre import sources
    monkeypatch.setattr(sources,'extract_info',lambda _:dict(duration=7200,title='Stream autorizado'))
    commands=[]
    def download(args,timeout):
        commands.append(args); shutil.copy2(video,Path(args[args.index('-o')+1].replace('%(ext)s','mp4')))
    monkeypatch.setattr(sources,'run',download)
    assert import_url('https://www.twitch.tv/videos/123',tmp_path,1800,6600,True).exists()
    assert commands[0][commands[0].index('--download-sections')+1]=='*1800-6600'
    assert '--force-keyframes-at-cuts' not in commands[0]


def test_whole_youtube_live_means_snapshot_not_five_minutes(video,tmp_path,monkeypatch):
    from cliplivre import sources
    monkeypatch.setattr(sources,'extract_info',lambda _:dict(is_live=True,duration=7200,title='Directo autorizado'))
    commands=[]
    def download(args,timeout):
        commands.append(args); shutil.copy2(video,Path(args[args.index('-o')+1].replace('%(ext)s','mp4')))
    monkeypatch.setattr(sources,'run',download)
    monkeypatch.setattr(sources,'capture_live',lambda *a:pytest.fail('No debe sustituir historial por captura desde ahora'))
    import_url('https://www.youtube.com/live/example',tmp_path,permission=True)
    assert '--live-from-start' in commands[0]
    assert commands[0][commands[0].index('--download-sections')+1]=='*0-7200.0'


def test_twitch_without_history_never_silently_captures_five(tmp_path,monkeypatch):
    from cliplivre import sources
    monkeypatch.setattr(sources,'extract_info',lambda _:dict(is_live=True,duration=7200))
    monkeypatch.setattr(sources,'capture_live',lambda *a:pytest.fail('No se autorizó captura futura'))
    with pytest.raises(RuntimeError,match='videos/ID'): import_url('https://www.twitch.tv/canal',tmp_path,permission=True)


def test_reimport_cache_does_not_mistake_partial_for_full(video,tmp_path):
    s=Store(tmp_path/'cache'); sid=s.register(video)
    original=dict(url='https://www.twitch.tv/videos/123',start=1800,end=6600,mode='Elegir inicio y fin',live=False)
    s.save_settings(sid,{'import':original,'capture_mode':'Todo lo disponible','local_start':0,'local_end':None})
    assert s.find_import(original['url'],1800,6600,'Elegir inicio y fin')[0]==sid
    assert s.find_import(original['url'],0,None,'Todo lo disponible') is None


def test_cache_joins_previous_blocks_for_new_window(video,tmp_path):
    s=Store(tmp_path/'join'); sid=s.register(video)
    for start,end,word in [(0.,6.,dict(start=4.,end=5.,text='Uno')),(6.,12.,dict(start=8.,end=9.,text='Dos'))]:
        s.save_artifact(sid,'asr-v2:tiny:es',start,end,dict(segments=[dict(start=word['start'],end=word['end'],text=word['text'],words=[word])],audio=[],metadata=dict(device='cpu')))
    result=s.artifact(sid,'asr-v2:tiny:es',3,10)
    assert [s['text'] for s in result['segments']]==['Uno','Dos']
    assert s.artifact(sid,'asr-v2:tiny:es',0,13) is None


def test_regeneration_keeps_full_analysis_payload(video,tmp_path):
    s=Store(tmp_path/'payload'); sid=s.register(video)
    payload=dict(segments=[],audio=[],visual=[],metadata=dict(device='cpu'))
    s.save_chunk(sid,'a',0,8,'a',payload,[dict(start=0,end=3,title='Primero')])
    s.save_chunk(sid,'b',0,8,'b',payload,[dict(start=0,end=4,title='Segundo')])
    assert json.loads(s.chunks(sid,'b')[0]['payload'])==payload


def test_old_accepted_long_clip_does_not_hide_new_short_alternative(video,tmp_path):
    s=Store(tmp_path/'alternatives'); sid=s.register(video)
    s.save_chunk(sid,'old',0,8,'old',{},[dict(start=0,end=8,title='Antiguo')])
    old=s.candidates(sid)[0]; s.update(old['id'],state='aceptado')
    s.save_chunk(sid,'new',0,8,'new',{},[dict(start=1,end=4,title='Dentro del rango',duration_limits=dict(minimum=1,maximum=3))])
    result=s.candidates(sid)
    assert len(result)==2 and any(c['id']==old['id'] and c['state']=='aceptado' for c in result)


def test_analysis_range_is_not_clip_duration(video,tmp_path,monkeypatch):
    from cliplivre import pipeline
    s=Store(tmp_path/'analysis-window'); sid=s.register(video)
    payload=dict(segments=[dict(start=3.,end=4.,text='Palabra',words=[dict(start=3.,end=4.,text='Palabra')])],audio=[],metadata=dict(device='cpu'))
    s.save_artifact(sid,'asr-v2:tiny:es',0,8,payload)
    report=pipeline.analyze(s,sid,pipeline.Analysis(model='tiny',source_start=2,source_end=6,min_seconds=1,max_seconds=3,target_seconds=2),transcriber=lambda *a:pytest.fail('Debe reutilizar el bloque que cubre el tramo'))
    assert report['processed_until']==6 and report['transcriptions_reused']==1
    assert all(2<=c['start']<c['end']<=6 and 1<=c['end']-c['start']<=3 for c in s.candidates(sid))
