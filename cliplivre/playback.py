"""Reproducción local por rangos, sin cargar ni recodificar el archivo completo."""
from functools import lru_cache
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread,Lock
import mimetypes
import re
import secrets

class MediaServer:
    def __init__(self):
        self.paths={}; self.keys={}; self.lock=Lock()
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_HEAD(self): self.send_media(False)
            def do_GET(self): self.send_media(True)
            def send_media(self,body):
                token=self.path.split('?',1)[0].removeprefix('/media/')
                with owner.lock: path=owner.paths.get(token)
                if path is None or not path.is_file(): self.send_error(404); return
                size=path.stat().st_size; start,end=0,size-1
                header=self.headers.get('Range')
                if header:
                    match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
                    if not match or (not match[1] and not match[2]): self.send_error(416); return
                    if match[1]: start=int(match[1]); end=min(end,int(match[2])) if match[2] else end
                    else: start=max(0,size-int(match[2]))
                    if start>=size or end<start:
                        self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.end_headers(); return
                self.send_response(206 if header else 200)
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Access-Control-Allow-Origin','*')
                self.send_header('Access-Control-Expose-Headers','Content-Range,Accept-Ranges,Content-Length')
                self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
                self.send_header('Content-Length',str(max(0,end-start+1)))
                self.send_header('Cache-Control','private, max-age=3600')
                if header: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                self.end_headers()
                if not body: return
                try:
                    with path.open('rb') as f:
                        f.seek(start); remaining=end-start+1
                        while remaining>0:
                            chunk=f.read(min(128*1024,remaining))
                            if not chunk: break
                            self.wfile.write(chunk); remaining-=len(chunk)
                except (BrokenPipeError,ConnectionResetError): pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.thread=Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
    def url(self,path):
        path=Path(path).resolve()
        if not path.is_file(): raise FileNotFoundError('No se encontró el video original.')
        key=(str(path),path.stat().st_size,path.stat().st_mtime_ns)
        with self.lock:
            if key not in self.keys:
                token=secrets.token_urlsafe(24); self.keys[key]=token; self.paths[token]=path
            token=self.keys[key]
        return f'http://127.0.0.1:{self.server.server_port}/media/{token}'
    def close(self): self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)

@lru_cache(maxsize=1)
def media_server(): return MediaServer()


def player_html(url,start=0,end=None):
    import json
    return '''<style>body{margin:0;background:#0d1017}video{display:block;width:100%;max-height:440px;background:#05070c;border-radius:10px}</style>
<video controls playsinline preload="metadata"></video><script>
const video=document.querySelector('video');
video.src='''+json.dumps(url)+''';const begin='''+json.dumps(start)+''';const finish='''+json.dumps(end)+''';
video.addEventListener('loadedmetadata',()=>{if(begin>0)video.currentTime=begin;});
video.addEventListener('timeupdate',()=>{if(finish!==null&&video.currentTime>=finish){video.pause();video.currentTime=finish;}});
video.addEventListener('play',()=>{if(finish!==null&&video.currentTime>=finish-.05)video.currentTime=begin;});
video.addEventListener('seeking',()=>{if(video.currentTime<begin)video.currentTime=begin;});
</script>'''
