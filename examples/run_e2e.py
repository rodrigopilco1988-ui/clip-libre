"""Prueba real: sin transcriptor simulado. Descarga Tiny la primera vez."""
from pathlib import Path
import json
import threading
import time
import psutil
from cliplivre.sources import import_local
from cliplivre.store import Store
from cliplivre.pipeline import Analysis,analyze
from cliplivre.render import Edit,render
from cliplivre.media import probe

base=Path(__file__).resolve().parent
store=Store(base/'resultado'/'biblioteca')
source=import_local(base/'autorizado.mp4',store.root,permission=True)
sid=store.register(source,'Prueba de voz sintética autorizada')
peak=[0]; stop=threading.Event()
def sample():
    while not stop.wait(.05): peak[0]=max(peak[0],psutil.Process().memory_info().rss)
thread=threading.Thread(target=sample,daemon=True); thread.start()
try:
    t=time.perf_counter()
    report=analyze(store,sid,Analysis(model='tiny',device='cpu',language='en',block_minutes=1),lambda f,m:print(f'{f:.0%}: {m}',flush=True))
    candidates=store.candidates(sid)
    assert candidates,'No se detectaron candidatos'
    clip=candidates[0]
    assert clip['words'],'No se generaron marcas por palabra'
    render_start=time.perf_counter()
    path=render(source,clip['start'],clip['end'],clip['words'],base/'resultado'/'exportaciones',Edit(resolution=1080,zoom=1.05,fade=True),progress=lambda m:print(m,flush=True))
    info=probe(path)
    assert info['width']==1080 and info['height']==1920 and info['audio']
    repeat=analyze(store,sid,Analysis(model='tiny',device='cpu',language='en',block_minutes=1))
    assert repeat['blocks']==0
    result=dict(analysis=report,export_seconds=round(time.perf_counter()-render_start,3),total_seconds=round(time.perf_counter()-t,3),rss_peak_sampled_mb=round(peak[0]/1024**2,1),output=str(path.relative_to(base)),media=info,candidates=len(candidates),words=len(clip['words']),repeat_blocks=repeat['blocks'])
    (base/'resultado'/'informe.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
finally:
    stop.set(); thread.join()
