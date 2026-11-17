import pytest
from cliplivre.sources import validate_url,import_local,import_url

def test_import_and_permissions(video,tmp_path):
    with pytest.raises(ValueError): import_local(video,tmp_path)
    dest=import_local(video,tmp_path,True)
    assert dest.read_bytes()==video.read_bytes() and dest!=video
    for url in ['http://youtube.com/a','https://example.com','https://youtube.com.evil.test','https://user@youtube.com/a','https://youtube.com:8080/a']:
        with pytest.raises(ValueError): validate_url(url)
    assert validate_url('https://www.youtube.com/watch?v=example')
    with pytest.raises(ValueError): import_url('https://youtu.be/example',tmp_path,permission=False)

def test_live_history_error_without_bypass(tmp_path,monkeypatch):
    import yt_dlp
    class Y:
        def __init__(self,options):
            assert not options.get('cookiefile') and not options.get('username')
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,*args,**kwargs): return dict(is_live=True)
    monkeypatch.setattr(yt_dlp,'YoutubeDL',Y)
    with pytest.raises(RuntimeError,match='histórica'):
        import_url('https://www.twitch.tv/example',tmp_path,30,60,True)


def test_drm_rejected(tmp_path,monkeypatch):
    import yt_dlp
    class Y:
        def __init__(self,options): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def extract_info(self,*args,**kwargs): return dict(has_drm=True)
    monkeypatch.setattr(yt_dlp,'YoutubeDL',Y)
    with pytest.raises(RuntimeError,match='restringido'):
        import_url('https://youtu.be/example',tmp_path,0,60,True)


def test_podcast_audio_preserved_and_exportable(tmp_path):
    from cliplivre.media import run,probe
    from cliplivre.render import render,Edit
    path=tmp_path/'episodio.wav'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=4',path])
    result=import_local(path,tmp_path/'podcasts',True)
    assert result.name=='podcast_visual.mp4'
    assert (result.parent/path.name).read_bytes()==path.read_bytes()
    assert probe(result)['audio'] and abs(probe(result)['duration']-4)<.2
    exported=render(result,0,3,[dict(start=.3,end=1.5,text='Podcast autorizado')],tmp_path/'salida',Edit(resolution=360,preset='ultrafast'))
    assert probe(exported)['width']==360 and probe(exported)['audio']


def test_supported_link_types():
    for url in ['https://www.twitch.tv/videos/123','https://clips.twitch.tv/Example',
                'https://www.twitch.tv/canal','https://www.youtube.com/shorts/example',
                'https://www.youtube.com/live/example','https://music.youtube.com/watch?v=example']:
        assert validate_url(url)==url


def test_full_vod_and_segment_commands(video,tmp_path,monkeypatch):
    from cliplivre import sources
    from pathlib import Path
    import shutil
    commands=[]
    monkeypatch.setattr(sources,'extract_info',lambda url:dict(title='VOD autorizado',duration=8))
    def fake_download(args,timeout):
        commands.append(args)
        target=Path(args[args.index('-o')+1].replace('%(ext)s','mp4'))
        shutil.copy2(video,target)
    monkeypatch.setattr(sources,'run',fake_download)
    assert import_url('https://www.twitch.tv/videos/123',tmp_path,permission=True).exists()
    assert '--download-sections' not in commands[-1]
    assert import_url('https://youtu.be/example',tmp_path,start=1,end=4,permission=True).exists()
    assert commands[-1][commands[-1].index('--download-sections')+1]=='*1-4'
    assert not any('cookie' in str(a) for cmd in commands for a in cmd)


def test_inspection_and_live_options(tmp_path,monkeypatch):
    from cliplivre import sources
    monkeypatch.setattr(sources,'extract_info',lambda url:dict(title='Canal',is_live=True))
    assert sources.inspect_url('https://www.twitch.tv/canal')['live']
    with pytest.raises(RuntimeError,match='recuperación histórica'):
        import_url('https://www.twitch.tv/canal',tmp_path,permission=True)
    with pytest.raises(RuntimeError,match='recuperación histórica'):
        import_url('https://www.twitch.tv/canal',tmp_path,0,60,True,live_mode='historial')


def test_capture_local_authorized_hls(video,tmp_path):
    from cliplivre.media import run,probe
    from cliplivre.sources import capture_live
    from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
    from functools import partial
    import threading
    folder=tmp_path/'hls'; folder.mkdir()
    run(['ffmpeg','-v','error','-y','-i',video,'-c:v','libx264','-g','15','-c:a','aac',
         '-f','hls','-hls_time','1','-hls_list_size','0',folder/'index.m3u8'])
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(folder)))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        url=f'http://127.0.0.1:{server.server_port}/index.m3u8'
        output=capture_live(dict(url=url),tmp_path,3)
        info=probe(output)
        assert info['audio'] and 2.8<=info['duration']<=3.5
    finally:
        server.shutdown(); thread.join(); server.server_close()


def test_clear_source_errors():
    from cliplivre.sources import source_message
    assert 'red de este equipo' in source_message(RuntimeError('proxy 403 Forbidden'))
    assert 'certificado' in source_message(RuntimeError('CERTIFICATE_VERIFY_FAILED'))
    assert 'acceso restringido' in source_message(RuntimeError('Sign in to confirm'))
    assert 'No se encontró' in source_message(RuntimeError('404 video unavailable'))


def test_local_javascript_runtime():
    from cliplivre.sources import local_deno
    from cliplivre.media import run
    runtime=local_deno()
    assert runtime, 'La instalación debe incluir Deno para el extractor de YouTube.'
    assert run([runtime,'eval','console.log(1 + 1)'],timeout=30).strip()==b'2'
