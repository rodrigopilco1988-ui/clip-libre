from dataclasses import asdict
from pathlib import Path
from cliplivre import downloads
from cliplivre.media import probe
from cliplivre.render import Edit
from cliplivre.composition import default_panels
import pytest


def test_horizontal_download_is_bounded_preserves_size_audio_and_cache(video,tmp_path,monkeypatch):
    before=video.read_bytes()
    monkeypatch.setattr(downloads,'choose_encoder',lambda _: 'libx264')
    output=downloads.source_clip(video,2,5,tmp_path/'out')
    info=probe(output);original=probe(video)
    assert abs(info['duration']-3)<.15 and info['audio']
    assert (info['width'],info['height'])==(original['width'],original['height'])
    assert before==video.read_bytes()
    def forbidden(*a,**kw): raise AssertionError('La descarga debe reutilizarse')
    monkeypatch.setattr(downloads,'run',forbidden)
    assert downloads.source_clip(video,2,5,tmp_path/'out')==output


def test_edited_download_two_panels_without_subtitles_is_reused(video,tmp_path,monkeypatch):
    settings=asdict(Edit(resolution=360,burn=False,framing='paneles',panels=default_panels(2),encoder='cpu',preset='ultrafast'))
    output=downloads.edited_clip(video,1,4,tmp_path/'out',settings)
    info=probe(output)
    assert info['width']==360 and info['height']==640 and info['audio'] and abs(info['duration']-3)<.15
    assert 'ass=' not in (output.parent/'filters.txt').read_text()
    import cliplivre.render
    monkeypatch.setattr(cliplivre.render,'render',lambda *a,**kw:pytest.fail('No debe exportar otra vez'))
    assert downloads.edited_clip(video,1,4,tmp_path/'out',settings)==output


def test_horizontal_nvenc_failure_retries_cpu_and_cleans_partial(video,tmp_path,monkeypatch):
    real=downloads.run;calls=[]
    monkeypatch.setattr(downloads,'choose_encoder',lambda _: 'h264_nvenc')
    def attempt(args,**kw):
        calls.append(args[args.index('-c:v')+1])
        if calls[-1]=='h264_nvenc':
            Path(args[-1]).write_bytes(b'partial');raise RuntimeError('NVENC no disponible')
        return real(args,**kw)
    monkeypatch.setattr(downloads,'run',attempt)
    output=downloads.source_clip(video,1,3,tmp_path/'out')
    assert calls==['h264_nvenc','libx264'] and probe(output)['audio']
    assert not list(output.parent.glob('*.building.mp4'))


def test_horizontal_failed_cpu_download_never_caches_partial(video,tmp_path,monkeypatch):
    monkeypatch.setattr(downloads,'choose_encoder',lambda _: 'libx264')
    def fail(args,**kw): Path(args[-1]).write_bytes(b'partial');raise RuntimeError('fallo')
    monkeypatch.setattr(downloads,'run',fail)
    with pytest.raises(RuntimeError,match='original se conserva'): downloads.source_clip(video,1,3,tmp_path/'out')
    assert not list((tmp_path/'out').rglob('*.mp4'))
