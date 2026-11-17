import hashlib
import json
import sqlite3
import uuid
from pathlib import Path
from contextlib import contextmanager

class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'history.sqlite3'
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS project_settings(source TEXT PRIMARY KEY, payload TEXT);
            CREATE TABLE IF NOT EXISTS artifacts(source TEXT, kind TEXT, start REAL, end REAL, payload TEXT, PRIMARY KEY(source,kind,start,end));
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS chunks(source TEXT, session TEXT, start REAL, end REAL, config TEXT, payload TEXT, PRIMARY KEY(source,start,end,config));
            CREATE TABLE IF NOT EXISTS candidates(id TEXT PRIMARY KEY, source TEXT, start REAL, end REAL, payload TEXT, state TEXT DEFAULT 'pendiente');
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, source TEXT, state TEXT, message TEXT, updated TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS exports(id TEXT PRIMARY KEY, candidate TEXT, path TEXT, config TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
            ''')
    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()
    def register(self, path, name=None):
        path = Path(path).resolve()
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024*1024), b''):
                h.update(block)
        sid = h.hexdigest()
        with self.connect() as c:
            c.execute('INSERT OR IGNORE INTO sources(id,name,path) VALUES(?,?,?)', (sid, name or path.name, str(path)))
        return sid
    def sources(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM sources ORDER BY created DESC')]
    def source(self, sid):
        with self.connect() as c:
            r = c.execute('SELECT * FROM sources WHERE id=?', (sid,)).fetchone()
        if not r:
            raise ValueError('Proyecto no encontrado.')
        return dict(r)
    def chunks(self, sid, config):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT * FROM chunks WHERE source=? AND config=? ORDER BY start', (sid,config))]
    def save_chunk(self, sid, session, start, end, config, payload, candidates):
        # El progreso y los candidatos se confirman juntos, solo después de completar el bloque.
        with self.connect() as c:
            for item in candidates:
                overlaps=c.execute('SELECT * FROM candidates WHERE source=? AND start < ? AND end > ? ORDER BY start',(sid,item['end'],item['start'])).fetchall()
                if not overlaps:
                    cid=uuid.uuid4().hex
                    c.execute('INSERT INTO candidates(id,source,start,end,payload) VALUES(?,?,?,?,?)',(cid,sid,item['start'],item['end'],json.dumps(item,ensure_ascii=False)))
                    continue
                protected=[]; mutable=[]
                for row in overlaps:
                    old_payload=json.loads(row['payload'])
                    has_export=c.execute('SELECT 1 FROM exports WHERE candidate=? LIMIT 1',(row['id'],)).fetchone()
                    if row['state']!='pendiente' or 'edited_words' in old_payload or 'edit_settings' in old_payload or has_export: protected.append(row)
                    else: mutable.append(row)
                limits=item.get('duration_limits',{}); lo=limits.get('minimum',0); hi=limits.get('maximum')
                if protected:
                    # Conserva trabajo humano. Un rango nuevo puede crear alternativas sin borrarlo.
                    if hi is None or any(lo-.01<=row['end']-row['start']<=hi+.01 for row in protected): continue
                if mutable:
                    keeper=mutable[0]['id']
                    for row in mutable[1:]: c.execute('DELETE FROM candidates WHERE id=?',(row['id'],))
                    c.execute('UPDATE candidates SET start=?,end=?,payload=? WHERE id=?',(item['start'],item['end'],json.dumps(item,ensure_ascii=False),keeper))
                else:
                    c.execute('INSERT INTO candidates(id,source,start,end,payload) VALUES(?,?,?,?,?)',(uuid.uuid4().hex,sid,item['start'],item['end'],json.dumps(item,ensure_ascii=False)))
            c.execute('INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?)', (sid,session,start,end,config,json.dumps(payload,ensure_ascii=False)))
    def candidates(self, sid):
        with self.connect() as c:
            return [dict(json.loads(r['payload']),id=r['id'],state=r['state']) for r in c.execute('SELECT * FROM candidates WHERE source=? ORDER BY start',(sid,))]
    def update(self, cid, payload=None, state=None):
        with self.connect() as c:
            if payload is not None:
                if not 0 <= payload['start'] < payload['end']:
                    raise ValueError('Intervalo inválido.')
                c.execute('UPDATE candidates SET start=?,end=?,payload=? WHERE id=?',(payload['start'],payload['end'],json.dumps(payload,ensure_ascii=False),cid))
            if state is not None:
                if state not in {'pendiente','aceptado','descartado'}:
                    raise ValueError('Estado inválido.')
                c.execute('UPDATE candidates SET state=? WHERE id=?',(state,cid))
    def job(self, jid, sid, state, message):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,CURRENT_TIMESTAMP)',(jid,sid,state,message))
    def export(self, cid, path, config):
        with self.connect() as c:
            c.execute('INSERT INTO exports(id,candidate,path,config) VALUES(?,?,?,?)',(uuid.uuid4().hex,cid,str(path),json.dumps(config)))

    def artifact(self,sid,kind,start,end):
        with self.connect() as c:
            row=c.execute('SELECT payload FROM artifacts WHERE source=? AND kind=? AND start=? AND end=?',(sid,kind,start,end)).fetchone()
            if row: return json.loads(row[0])
            if not kind.startswith('asr-v2:'): return None
            rows=[dict(r) for r in c.execute('SELECT start,end,payload FROM artifacts WHERE source=? AND kind=? AND start<? AND end>? ORDER BY start',(sid,kind,end,start))]
        cursor=start; chosen=[]
        while cursor<end-.001:
            options=[r for r in rows if r['start']<=cursor+.001 and r['end']>cursor+.001]
            if not options: return None
            row=max(options,key=lambda r:r['end']); stop=min(end,row['end'])
            chosen.append((cursor,stop,json.loads(row['payload']))); cursor=stop
        if not chosen: return None
        segments=[]; audio={}; seen=set()
        for a,b,payload in chosen:
            for segment in payload.get('segments',[]):
                if segment['start']>=b or segment['end']<=a: continue
                words=[]
                for word in segment.get('words',[]):
                    if word['start']>=b or word['end']<=a: continue
                    key=(word['start'],word['end'],word['text'])
                    if key in seen: continue
                    seen.add(key); words.append(dict(word,start=max(a,word['start']),end=min(b,word['end'])))
                segments.append(dict(segment,start=max(a,segment['start']),end=min(b,segment['end']),words=words,text=' '.join(w['text'] for w in words) if words else segment['text']))
            for f in payload.get('audio',[]):
                if a<=f['time']<b: audio[f['time']]=f
        return dict(segments=sorted(segments,key=lambda s:s['start']),audio=sorted(audio.values(),key=lambda f:f['time']),metadata=dict(chosen[0][2].get('metadata',{}),cache_slice=True))

    def save_artifact(self,sid,kind,start,end,payload):
        with self.connect() as c:
            c.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?)',(sid,kind,start,end,json.dumps(payload,ensure_ascii=False)))

    def compatible_transcript(self,sid,model,language,start,end):
        # Migra resultados de versiones anteriores sin adivinar qué modelo los produjo.
        with self.connect() as c:
            reports=c.execute("SELECT message FROM jobs WHERE source=? AND state='completado' ORDER BY updated DESC",(sid,)).fetchall()
            for row in reports:
                try:
                    config=json.loads(row[0])['config']
                    if config.get('model')!=model or config.get('language')!=language: continue
                    key=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
                    old=c.execute('SELECT payload FROM chunks WHERE source=? AND config=? AND start=? AND end=?',(sid,key,start,end)).fetchone()
                    if old:
                        payload=json.loads(old[0])
                        if all(k in payload for k in ['segments','audio','metadata']):
                            return {k:payload[k] for k in ['segments','audio','metadata']}
                except (KeyError,ValueError,TypeError): continue
        return None

    def settings(self,sid):
        with self.connect() as c: row=c.execute('SELECT payload FROM project_settings WHERE source=?',(sid,)).fetchone()
        return json.loads(row[0]) if row else {}

    def save_settings(self,sid,settings):
        with self.connect() as c: c.execute('INSERT OR REPLACE INTO project_settings VALUES(?,?)',(sid,json.dumps(settings,ensure_ascii=False)))

    def find_import(self,url,start,end,mode):
        with self.connect() as c:
            rows=c.execute('SELECT sources.*,project_settings.payload AS settings FROM sources JOIN project_settings ON project_settings.source=sources.id').fetchall()
        for row in rows:
            settings=json.loads(row['settings']); original=settings.get('import',{})
            if original.get('live'): continue
            if original.get('url')==url and original.get('start')==start and original.get('end')==end and original.get('mode')==mode and Path(row['path']).is_file():
                return row['id'],settings
        return None
