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
