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
                overlap = c.execute('SELECT 1 FROM candidates WHERE source=? AND start < ? AND end > ?', (sid,item['end'],item['start'])).fetchone()
                if not overlap:
                    cid = uuid.uuid4().hex
                    c.execute('INSERT INTO candidates(id,source,start,end,payload) VALUES(?,?,?,?,?)', (cid,sid,item['start'],item['end'],json.dumps(item,ensure_ascii=False)))
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
