"""Bibliotecas NVIDIA opcionales y carga explícita de DLL en Windows."""
from pathlib import Path
import ctypes
import importlib.util
import json
import os
import subprocess
import sys
import sysconfig

IS_WINDOWS=sys.platform=='win32'
_DLL_HANDLES=[]
_LIB_HANDLES={}
REQUIREMENTS=['nvidia-cublas-cu12>=12.4,<13','nvidia-cudnn-cu12>=9,<10',
              'nvidia-cuda-runtime-cu12>=12.4,<13','nvidia-cuda-nvrtc-cu12>=12.4,<13']
REQUIRED_DLLS=['cublasLt64_12.dll','cublas64_12.dll','cudnn64_9.dll']


def library_directories():
    roots={Path(sysconfig.get_path('purelib'))/'nvidia'}
    spec=importlib.util.find_spec('nvidia')
    if spec and spec.submodule_search_locations:
        roots.update(Path(p) for p in spec.submodule_search_locations)
    return sorted({(root/part/'bin').resolve() for root in roots
                   for part in ['cuda_runtime','cuda_nvrtc','cublas','cudnn'] if (root/part/'bin').is_dir()})


def prepare_libraries():
    report=dict(platform=sys.platform,directories=[],loaded=[],errors=[],missing=[])
    if not IS_WINDOWS: return report
    directories=library_directories()
    report['directories']=[str(p) for p in directories]
    existing=os.environ.get('PATH','').split(os.pathsep)
    for directory in directories:
        if str(directory) not in existing:
            existing.insert(0,str(directory))
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
    os.environ['PATH']=os.pathsep.join(existing)
    # Se conservan los handles: cerrarlos retiraría las rutas durante la inferencia.
    for name in REQUIRED_DLLS:
        dll=next((p/name for p in directories if (p/name).is_file()),None)
        if dll is None:
            report['missing'].append(name)
            continue
        try:
            if str(dll) not in _LIB_HANDLES: _LIB_HANDLES[str(dll)]=ctypes.WinDLL(str(dll))
            report['loaded'].append(name)
        except OSError as e:
            report['errors'].append(f'{name}: {e}')
    return report


def install():
    if not IS_WINDOWS: raise RuntimeError('Esta reparación está preparada para Windows de 64 bits.')
    result=subprocess.run([sys.executable,'-m','pip','install',*REQUIREMENTS])
    if result.returncode: raise RuntimeError('No se completó la descarga de bibliotecas NVIDIA. Revisa la conexión y el espacio libre.')
    report=prepare_libraries()
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if report['missing'] or report['errors']:
        raise RuntimeError('Las bibliotecas no se pudieron cargar completamente. Revisa el diagnóstico y el controlador NVIDIA. No se confirmó aceleración GPU.')
    print('Bibliotecas NVIDIA cargadas. Reinicia Clip Libre y usa auto. La inferencia GPU debe confirmarse con tu video.',flush=True)
    return report


def verify_gpu():
    """Prueba sin alternativa CPU; el padre debe ejecutarla en un subproceso."""
    import time
    prepare_libraries()
    from faster_whisper import WhisperModel
    import numpy as np
    started=time.perf_counter()
    engine=WhisperModel('tiny',device='cuda',compute_type='int8_float16')
    try:
        segments,_=engine.transcribe(np.zeros(16000,dtype=np.float32),language='es',
                                    vad_filter=False,word_timestamps=False,beam_size=1)
        list(segments)  # Obliga a ejecutar la inferencia, incluso con audio de silencio.
        return dict(device='cuda',model='tiny',inference_completed=True,seconds=round(time.perf_counter()-started,2))
    finally:
        model=getattr(engine,'model',None)
        if model is not None:
            unload=getattr(model,'unload_model',None)
            if unload: unload()


if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='install': install()
        elif len(sys.argv)>1 and sys.argv[1]=='probe': print(json.dumps(verify_gpu()))
        else: print(json.dumps(prepare_libraries(),ensure_ascii=False,indent=2))
    except Exception as e:
        print(str(e),file=sys.stderr)
        raise SystemExit(1)
