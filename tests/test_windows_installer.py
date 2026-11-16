"""Ejecuta el BAT real en Windows, incluidos lanzadores sin runtime."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

pytestmark=pytest.mark.skipif(sys.platform!='win32',reason='Requiere cmd.exe real')


def setup_case(tmp_path):
    folder=tmp_path/'carpeta con espacios'
    folder.mkdir()
    shutil.copy2(Path(__file__).parents[1]/'Instalar.bat',folder/'Instalar.bat')
    shim=folder/'lanzadores'; shim.mkdir()
    return folder,shim


def invoke(folder,path):
    env=os.environ.copy(); env['PATH']=str(path)
    env.pop('CLIP_PY',None)
    return subprocess.run(['cmd.exe','/d','/c','Instalar.bat','--comprobar'],cwd=folder,env=env,capture_output=True,text=True,errors='replace',timeout=30)


def test_existing_launcher_without_runtime(tmp_path):
    folder,shim=setup_case(tmp_path)
    for exe in ['py','python','python3']:
        (shim/(exe+'.cmd')).write_text('@echo off\nexit /b 0\n')
    result=invoke(folder,shim)
    assert result.returncode==2,result.stdout+result.stderr
    assert 'Tener el lanzador py' in result.stdout
    assert not (folder/'.venv').exists()


def test_python_on_path_without_working_py(tmp_path):
    folder,shim=setup_case(tmp_path)
    (shim/'py.cmd').write_text('@echo off\nexit /b 1\n')
    (shim/'python.cmd').write_text('@echo off\n"'+sys.executable+'" %*\nexit /b %errorlevel%\n')
    result=invoke(folder,shim)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'Python compatible encontrado: python' in result.stdout


def test_real_available_python(tmp_path):
    folder,_=setup_case(tmp_path)
    result=invoke(folder,os.environ['PATH'])
    assert result.returncode==0,result.stdout+result.stderr
    assert 'Python compatible encontrado:' in result.stdout
