from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
import pytest
from cliplivre.media import run,probe,frame
from cliplivre.render import render,Edit
from cliplivre.composition import default_panels,guide,geometry


@pytest.fixture
def color_video(tmp_path):
    path=tmp_path/'colores.mp4'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
         'color=c=red:s=300x180:d=3:r=12,drawbox=x=100:y=0:w=100:h=180:color=lime:t=fill,drawbox=x=200:y=0:w=100:h=180:color=blue:t=fill',
         '-f','lavfi','-i','sine=duration=3','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',path])
    return path


@pytest.mark.parametrize('count',[1,2,3])
def test_real_panel_layout_matches_guide(color_video,tmp_path,count):
    panels=default_panels(count)
    for i,p in enumerate(panels): p['source']=[i/3,0,1/3,1]
    output=render(color_video,0,2,[],tmp_path/'out',Edit(resolution=360,framing='paneles',panels=panels,burn=False,preset='ultrafast'))
    actual=np.array(Image.open(BytesIO(frame(output,1,width=360))).convert('RGB'))
    expected=np.array(Image.open(BytesIO(guide(frame(color_video,1),panels))))
    for i in range(count):
        x,y,w,h=geometry(panels[i],360,640)
        a=actual[y+h//2,x+w//2]; b=expected[y+h//2,x+w//2]
        assert a[i]>180 and b[i]>180
        assert np.max(np.abs(a.astype(float)-b.astype(float)))<25
    assert probe(output)['audio']


def test_custom_text_and_subtitles_render(color_video,tmp_path):
    output=render(color_video,0,2,[dict(start=.2,end=1.8,text='Subtítulo')],tmp_path/'out',Edit(resolution=360,preset='ultrafast',overlay_text='Mi título {seguro}',overlay_y=.2,overlay_size=110))
    ass=(output.parent/'texto.ass').read_text(encoding='utf-8')
    assert 'Mi título （seguro）' in ass and '\\pos(' in ass
    pixels=np.array(Image.open(BytesIO(frame(output,1,width=360))).convert('RGB'))
    assert np.sum(np.all(pixels[70:180]>210,axis=2))>10


def test_fast_seek_uses_actual_late_interval(tmp_path):
    path=tmp_path/'timeline.mp4'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=red:s=160x90:d=3:r=10',
         '-f','lavfi','-i','color=blue:s=160x90:d=3:r=10','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0',
         '-c:v','libx264','-preset','ultrafast',path])
    output=render(path,4,5,[],tmp_path/'out',Edit(resolution=360,aspect='16:9',burn=False,preset='ultrafast'))
    pixels=np.array(Image.open(BytesIO(frame(output,.2,width=320))).convert('RGB'))
    assert pixels[:,:,2].mean()>200 and pixels[:,:,0].mean()<20
    assert abs(probe(output)['duration']-1)<.2
