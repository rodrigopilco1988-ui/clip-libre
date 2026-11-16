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
