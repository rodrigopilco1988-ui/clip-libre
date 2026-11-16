import pytest
from cliplivre.subtitles import timestamp,map_words,write
from cliplivre.render import render,Edit,retained,dimensions,face_expression
from cliplivre.media import probe,preview,audio

def test_subtitles_and_mapping(tmp_path):
    assert timestamp(59.9996)=='00:01:00,000'
    assert timestamp(59.999,True)=='0:01:00.00'
    words=[dict(start=1,end=2,text='Hola {x}'),dict(start=4,end=5,text='mundo')]
    mapped=map_words(words,[(0,2),(4,6)])
    assert mapped[1]['start']==2
    srt,ass=write(mapped,tmp_path/'sub',animated=True)
    assert '00:00:01,000 --> 00:00:03,000' in srt.read_text(encoding="utf-8")
    assert '（x）' in ass.read_text(encoding="utf-8") and '\\1c' in ass.read_text(encoding="utf-8")
    assert retained(0,6,[(2,4)])==[(0,2),(4,6)]
    with pytest.raises(ValueError): retained(0,6,[(0,6)])

@pytest.mark.parametrize('framing,aspect',[('ajustar','9:16'),('centro','1:1'),('rostros','16:9'),('streamer','9:16')])
def test_render_real(video,tmp_path,framing,aspect):
    edit=Edit(resolution=360,aspect=aspect,framing=framing,zoom=1.05,fade=True,preset='ultrafast',streamer_roi=(0.,0.,.3,.4))
    result=render(video,0,6,[dict(start=1,end=2,text='Prueba autorizada'),dict(start=4,end=5,text='Final')],tmp_path/'output',edit,[(2,3)])
    info=probe(result)
    assert (info['width'],info['height'])==dimensions(aspect,360)
    assert abs(info['duration']-5)<.2
    assert info['audio'] and result.stat().st_size>1000
    assert (result.parent/'subtitulos.srt').exists()
    assert len(audio(result,0,2))>0

def test_preview(video,tmp_path):
    result=preview(video,1,3,tmp_path/'preview.mp4')
    assert abs(probe(result)['duration']-2)<.2

def test_invalid_render(video,tmp_path):
    with pytest.raises(ValueError): render(video,0,99,[],tmp_path)
    with pytest.raises(ValueError): dimensions('2:3',1080)
    assert 'if(' in face_expression([dict(time=0,faces=[[.1,.1,.1,.1]]),dict(time=1,faces=[[.5,.1,.1,.1]])],[(0,2)],1080)
