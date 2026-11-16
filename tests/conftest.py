import pytest
from cliplivre.media import run

@pytest.fixture
def video(tmp_path):
    path=tmp_path/'autorizado.mp4'
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=320x180:rate=15:duration=8',
         '-f','lavfi','-i','sine=frequency=600:sample_rate=16000:duration=8','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',path])
    return path
