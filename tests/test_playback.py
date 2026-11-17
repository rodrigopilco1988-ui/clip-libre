import requests
from cliplivre.playback import MediaServer


def test_local_player_uses_ranges_and_no_public_file_listing(tmp_path):
    path=tmp_path/'archivo.bin'; data=bytes(range(256))*40; path.write_bytes(data)
    server=MediaServer()
    try:
        url=server.url(path)
        response=requests.get(url,headers={'Range':'bytes=100-199'},timeout=5)
        assert response.status_code==206 and response.content==data[100:200]
        assert response.headers['Content-Range']==f'bytes 100-199/{len(data)}'
        assert requests.get(url,headers={'Range':'bytes=-10'},timeout=5).content==data[-10:]
        head=requests.head(url,timeout=5)
        assert int(head.headers['Content-Length'])==len(data) and not head.content
        assert requests.get(url,headers={'Range':'bytes=999999-'},timeout=5).status_code==416
        assert requests.get(url.rsplit('/',1)[0]+'/../secrets',timeout=5).status_code==404
    finally: server.close()


def test_clip_player_has_relative_controls_and_bounded_seek():
    from cliplivre.playback import player_html
    html=player_html('http://127.0.0.1/media/test',7882.,7962.)
    assert 'Posición dentro del clip' in html and 'finish-begin' in html
    assert '<video controls' not in html
    assert 'video.currentTime>finish' in html and 'video.currentTime<begin' in html
    assert '7882.0' in html and '7962.0' in html
    assert '<video controls' in player_html('http://127.0.0.1/media/test')


def test_preview_is_real_short_file_and_reused(video,tmp_path,monkeypatch):
    from cliplivre import media
    output=media.clip_preview(video,2,5,tmp_path/'previews')
    assert output!=video and abs(media.probe(output)['duration']-3)<.15
    def forbidden(*a,**kw): raise AssertionError('No se debe renderizar otra vez')
    monkeypatch.setattr(media,'preview',forbidden)
    assert media.clip_preview(video,2,5,tmp_path/'previews')==output
