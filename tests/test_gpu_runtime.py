from pathlib import Path
from types import SimpleNamespace
from cliplivre import gpu_runtime as gpu
import pytest


def test_windows_dll_directories_and_explicit_loading(tmp_path,monkeypatch):
    directory=tmp_path/'nvidia'/'cublas'/'bin'; directory.mkdir(parents=True)
    for name in gpu.REQUIRED_DLLS: (directory/name).write_bytes(b'fixture')
    monkeypatch.setattr(gpu,'IS_WINDOWS',True)
    monkeypatch.setattr(gpu,'library_directories',lambda:[directory])
    monkeypatch.setattr(gpu,'_DLL_HANDLES',[])
    monkeypatch.setattr(gpu,'_LIB_HANDLES',{})
    monkeypatch.setenv('PATH','original')
    added=[]; loaded=[]
    monkeypatch.setattr(gpu.os,'add_dll_directory',lambda p:added.append(p) or object(),raising=False)
    monkeypatch.setattr(gpu.ctypes,'WinDLL',lambda p:loaded.append(p) or object(),raising=False)
    report=gpu.prepare_libraries()
    assert report['loaded']==gpu.REQUIRED_DLLS and not report['missing'] and not report['errors']
    assert str(directory) in gpu.os.environ['PATH'] and added==[str(directory)]
    gpu.prepare_libraries()
    assert len(loaded)==3 and len(added)==1


def test_missing_dlls_not_reported_as_installed(monkeypatch):
    monkeypatch.setattr(gpu,'IS_WINDOWS',True)
    monkeypatch.setattr(gpu,'library_directories',lambda:[])
    report=gpu.prepare_libraries()
    assert report['missing']==gpu.REQUIRED_DLLS and not report['loaded']


def test_gpu_probe_never_falls_back_to_cpu(monkeypatch):
    import faster_whisper
    monkeypatch.setattr(gpu,'prepare_libraries',lambda:{})
    seen=[]
    class Engine:
        def __init__(self,model,device,compute_type): seen.append(device)
        def transcribe(self,*args,**kwargs):
            assert kwargs['vad_filter'] is False
            return iter([]),SimpleNamespace(language='es')
    monkeypatch.setattr(faster_whisper,'WhisperModel',Engine)
    assert gpu.verify_gpu()['inference_completed'] and seen==['cuda']
    def fail(*args,**kwargs): raise RuntimeError('cublas64_12.dll')
    monkeypatch.setattr(faster_whisper,'WhisperModel',fail)
    with pytest.raises(RuntimeError,match='cublas'): gpu.verify_gpu()
