from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_empty_ui():
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert any(t.value=='Tu próximo clip empieza aquí' for t in app.title)

def test_ui_with_candidates(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'ui'))
    s=Store(tmp_path/'ui'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=6.,score=55,title='Prueba',hook='Hola',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==4
    accept=next(b for b in app.button if b.label=='Aceptar')
    accept.click().run()
    assert not app.exception
    assert s.candidates(sid)[0]['state']=='aceptado'

def test_ui_preview_and_export(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'ui'))
    s=Store(tmp_path/'ui'); sid=s.register(video)
    words=[dict(start=1.,end=2.,text='Prueba'),dict(start=3.,end=4.,text='autorizada')]
    payload=dict(segments=[dict(start=1.,end=4.,text='Prueba autorizada',words=words)],audio=[],visual=[])
    s.save_chunk(sid,'a',0,8,'cfg',payload,[dict(start=1.,end=6.,score=55,title='Prueba',hook='Hola',reason='Prueba',classification='heurística',visual_samples=1,words=words)])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    next(x for x in app.selectbox if x.label=='Resolución base').select(360).run()
    next(b for b in app.button if b.label=='Generar vista previa editada').click().run(timeout=30)
    assert not app.exception and not app.error
    next(b for b in app.button if b.label=='Exportar clip con estos ajustes').click().run(timeout=30)
    assert not app.exception and not app.error
    with s.connect() as db:
        row=db.execute('SELECT path FROM exports').fetchone()
    assert row and Path(row[0]).exists()


def test_home_source_choices(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'new-ui'))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    source=next(x for x in app.radio if x.label=='¿De dónde viene tu contenido?')
    assert source.options==['YouTube','Twitch','Podcast','Archivo local']
    source.set_value('Podcast').run()
    assert not app.exception
    assert any('podcast' in x.value.lower() for x in app.subheader)
    next(x for x in app.radio if x.label=='¿De dónde viene tu contenido?').set_value('Twitch').run()
    assert not app.exception
    assert any('Pega el enlace' in x.label for x in app.text_input)


def test_view_clip_button_and_persistent_open_state(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'view-regression'))
    s=Store(tmp_path/'view-regression'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=4.,score=60,title='Clip de prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    app.session_state['workflow']='3 · Mis clips'
    app.run()
    next(b for b in app.button if b.label=='Ver clip').click().run(timeout=30)
    assert not app.exception and not app.error
    assert list((tmp_path/'view-regression'/'vistas_previas').glob('*.mp4'))
    next(x for x in app.slider if x.label=='Puntuación mínima').set_value(10).run(timeout=30)
    assert not app.exception and not app.error


def test_select_clip_goes_to_editor_and_panels_can_be_added(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'editor'))
    s=Store(tmp_path/'editor'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=6.,score=55,title='Prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not any(x.label=='Resolución base' for x in app.selectbox)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    assert not app.exception and app.session_state['workflow']=='4 · Editor y exportación'
    assert next(x for x in app.selectbox if x.label=='Formato').value=='9:16'
    assert any(x.label=='Inicio del clip (min)' for x in app.number_input)
    next(b for b in app.button if b.label=='Añadir cuadro').click().run()
    assert not app.exception
    assert next(x for x in app.selectbox if x.label=='Número de cuadros').value==2
    next(b for b in app.button if b.label=='Añadir cuadro').click().run()
    assert next(x for x in app.selectbox if x.label=='Número de cuadros').value==3
    next(b for b in app.button if b.label=='Quitar último cuadro').click().run()
    assert not app.exception and next(x for x in app.selectbox if x.label=='Número de cuadros').value==2


def test_minutes_and_full_content_are_defaults(tmp_path,monkeypatch):
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'defaults'))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert next(x for x in app.checkbox if x.label=='Analizar todo el contenido importado').value
    assert next(x for x in app.checkbox if x.label=='Sin límite máximo de duración del clip').value
    assert next(x for x in app.number_input if x.label=='Duración orientativa del clip (min)').value==3.


def test_editor_settings_and_text_are_saved(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'save-editor'))
    s=Store(tmp_path/'save-editor'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=6.,score=55,title='Prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    next(x for x in app.text_area if x.label=='Texto sobre el video').set_value('Mi título nuevo').run()
    next(b for b in app.button if b.label=='Añadir cuadro').click().run()
    next(b for b in app.button if b.label=='Guardar revisión y configuración').click().run()
    assert not app.exception and not app.error
    saved=s.candidates(sid)[0]
    assert saved['edit_settings']['overlay_text']=='Mi título nuevo'
    assert len(saved['edit_settings']['panels'])==2
