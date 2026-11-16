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
