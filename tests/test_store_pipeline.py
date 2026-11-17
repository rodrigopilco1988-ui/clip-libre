import json
import pytest
from cliplivre.store import Store
from cliplivre.pipeline import Analysis,analyze

def transcript(samples,*args):
    return [dict(start=.3,end=2.,text='Mira qué sorpresa increíble',words=[dict(start=.3,end=.7,text='Mira'),dict(start=.8,end=1.2,text='sorpresa')])],dict(device='prueba inyectada')

def test_incremental_and_dedup(video,tmp_path):
    s=Store(tmp_path/'db'); sid=s.register(video)
    config=Analysis(block_minutes=.1,model='tiny',min_seconds=5,max_seconds=10)
    first=analyze(s,sid,config,transcriber=transcript)
    assert first['blocks']==2
    candidates=s.candidates(sid)
    assert candidates
    assert all(a['end']<=b['start'] for a,b in zip(candidates,candidates[1:]))
    second=analyze(s,sid,config,transcriber=lambda *a:pytest.fail('No debe repetir transcripción'))
    assert second['blocks']==0
    assert len(s.candidates(sid))==len(candidates)
    changed=Analysis(block_minutes=.1,model='base',min_seconds=5,max_seconds=10)
    analyze(s,sid,changed,transcriber=transcript)
    assert len(s.candidates(sid))==len(candidates)

def test_failed_chunk_resume(video,tmp_path):
    s=Store(tmp_path/'db'); sid=s.register(video); calls=[]
    def fail_second(*args):
        calls.append(1)
        if len(calls)==2: raise RuntimeError('fallo intencional')
        return transcript(*args)
    config=Analysis(block_minutes=.1,model='tiny',min_seconds=5)
    with pytest.raises(RuntimeError): analyze(s,sid,config,transcriber=fail_second)
    assert analyze(s,sid,config,transcriber=transcript)['blocks']==1

def test_store_states(video,tmp_path):
    s=Store(tmp_path/'db'); sid=s.register(video)
    assert s.register(video)==sid
    assert s.source(sid)['path']==str(video)
    s.save_chunk(sid,'a',0,8,'c',{},[dict(start=1,end=3,score=50)])
    c=s.candidates(sid)[0]; s.update(c['id'],state='aceptado')
    assert s.candidates(sid)[0]['state']=='aceptado'
    with pytest.raises(ValueError): s.update(c['id'],state='incorrecto')
    s.export(c['id'],video,{})
    with s.connect() as db: assert db.execute('SELECT count(*) FROM exports').fetchone()[0]==1

def test_next_review_processes_only_new_minutes(video,tmp_path):
    s=Store(tmp_path/'db'); sid=s.register(video)
    config=Analysis(block_minutes=.1,model='tiny',min_seconds=5)
    first=analyze(s,sid,config,transcriber=transcript,max_blocks=1)
    assert first['blocks']==1 and first['processed_until']==6
    second=analyze(s,sid,config,transcriber=transcript,max_blocks=1)
    assert second['blocks']==1 and second['processed_until']==8
    assert analyze(s,sid,config,transcriber=transcript)['blocks']==0


def test_duration_change_reuses_expensive_transcription(video,tmp_path):
    s=Store(tmp_path/'cache'); sid=s.register(video)
    first=Analysis(block_minutes=1,model='tiny',min_seconds=1,target_seconds=3)
    analyze(s,sid,first,transcriber=transcript)
    second=Analysis(block_minutes=1,model='tiny',min_seconds=2,target_seconds=6,max_seconds=None)
    report=analyze(s,sid,second,transcriber=lambda *args:pytest.fail('No debe repetir Whisper por cambiar la duración'))
    assert report['transcriptions_reused']==1 and report['cache_hits']==2


def test_legacy_transcription_can_be_reused(video,tmp_path):
    import hashlib
    s=Store(tmp_path/'legacy'); sid=s.register(video)
    config=dict(block_minutes=50,model='tiny',device='cpu',language='es',ollama=False,ollama_model='qwen3:4b',visual_step=2,min_seconds=12,max_seconds=60,max_candidates=20)
    key=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    segments,metadata=transcript(None)
    s.save_chunk(sid,'legacy',0,8,key,dict(segments=segments,audio=[],visual=[],metadata=metadata),[])
    s.job('legacy',sid,'completado',json.dumps(dict(config=config)))
    report=analyze(s,sid,Analysis(model='tiny',min_seconds=1),transcriber=lambda *args:pytest.fail('Debe reutilizar el análisis anterior'))
    assert report['transcriptions_reused']==1


def test_long_clips_have_no_sixty_or_180_second_limit():
    from cliplivre.rank import propose
    segments=[dict(start=float(i),end=float(i+20),text='Conversación con contexto',words=[]) for i in range(0,600,20)]
    result=propose(segments,[],[],0,600,min_seconds=240,max_seconds=None,target_seconds=300)
    assert result and result[0]['end']-result[0]['start']>=300


def test_longer_proposals_replace_automatic_short_ones(video,tmp_path):
    s=Store(tmp_path/'replace'); sid=s.register(video)
    s.save_chunk(sid,'old',0,8,'old',{},[dict(start=0,end=2,title='Corto'),dict(start=3,end=5,title='Otro corto')])
    s.save_chunk(sid,'new',0,8,'new',{},[dict(start=0,end=7,title='Contexto largo')])
    candidates=s.candidates(sid)
    assert len(candidates)==1 and candidates[0]['end']==7 and candidates[0]['title']=='Contexto largo'


@pytest.mark.parametrize('protection',['aceptado','descartado','editado','exportado'])
def test_regeneration_preserves_human_work(video,tmp_path,protection):
    s=Store(tmp_path/protection); sid=s.register(video)
    s.save_chunk(sid,'old',0,8,'old',{},[dict(start=1,end=3,title='Conservar')])
    item=s.candidates(sid)[0]
    if protection in {'aceptado','descartado'}: s.update(item['id'],state=protection)
    if protection=='editado': s.update(item['id'],payload=dict(item,edited_words=[]))
    if protection=='exportado': s.export(item['id'],video,{})
    s.save_chunk(sid,'new',0,8,'new',{},[dict(start=0,end=7,title='Nuevo')])
    preserved=s.candidates(sid)
    assert len(preserved)==1 and preserved[0]['title']=='Conservar' and preserved[0]['start']==1
