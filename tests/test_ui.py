from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_empty_ui():
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert any(t.value=='Tu video, tus clips' for t in app.title)

def test_ui_with_candidates(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'ui'))
    s=Store(tmp_path/'ui'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=6.,score=55,title='Prueba',hook='Hola',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    assert not app.exception
    assert len(app.tabs)==3
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
    source=next(x for x in app.radio if x.label=='Fuente')
    assert source.options==['Pegar enlace','Subir archivo']
    source.set_value('Subir archivo').run()
    assert not app.exception and any(x.label=='Ruta del archivo en tu equipo' for x in app.text_input)
    next(x for x in app.radio if x.label=='Fuente').set_value('Pegar enlace').run()
    assert not app.exception and any(x.label=='Enlace de YouTube o Twitch' for x in app.text_input)


def test_view_clip_button_and_persistent_open_state(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'view-regression'))
    s=Store(tmp_path/'view-regression'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=4.,score=60,title='Clip de prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    app.session_state['workflow']='2 · Clips'
    app.run()
    next(b for b in app.button if b.label=='Ver clip').click().run(timeout=30)
    assert not app.exception and not app.error
    assert app.session_state['view_open_'+s.candidates(sid)[0]['id']]
    previews=list((tmp_path/'view-regression').glob('vistas_previas/*.mp4'))
    from cliplivre.media import probe
    assert len(previews)==1 and abs(probe(previews[0])['duration']-3)<.15
    assert any('Duración: 0:03' in x.value for x in app.caption)
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
    assert not app.exception and app.session_state['workflow']=='3 · Editor'
    assert next(x for x in app.selectbox if x.label=='Formato').value=='9:16'
    assert any(x.label=='Inicio (min:seg)' for x in app.text_input)
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
    assert next(x for x in app.radio if x.label=='Captura').value=='Todo lo disponible'
    assert next(x for x in app.selectbox if x.label=='Duración de cada clip').value=='30–90 s · variado'
    assert not any('análisis' in x.label.lower() for x in app.tabs)


def test_editor_settings_and_text_are_saved(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'save-editor'))
    s=Store(tmp_path/'save-editor'); sid=s.register(video)
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),[dict(start=1.,end=6.,score=55,title='Prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    next(b for b in app.button if b.label=='＋ Añadir título').click().run()
    next(x for x in app.text_input if x.label=='Texto').set_value('Mi título nuevo').run()
    next(b for b in app.button if b.label=='Añadir cuadro').click().run()
    next(b for b in app.button if b.label=='Guardar revisión y configuración').click().run()
    assert not app.exception and not app.error
    saved=s.candidates(sid)[0]
    assert saved['edit_settings']['titles'][0]['text']=='Mi título nuevo'
    assert len(saved['edit_settings']['panels'])==2


def test_batch_silence_uses_each_clips_audio(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    from cliplivre.media import probe
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'batch'))
    s=Store(tmp_path/'batch'); sid=s.register(video)
    audio=[dict(time=float(t),end=float(t+1),silence=True,db=-80,change=0) for t in range(4,7)]
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=audio,visual=[]),[dict(start=a,end=b,score=55,title=f'Clip {a}',reason='Prueba',classification='heurística',visual_samples=1,words=[]) for a,b in [(0.,3.),(4.,8.)]])
    for item in s.candidates(sid): s.update(item['id'],state='aceptado')
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    next(x for x in app.selectbox if x.label=='Resolución base').select(360).run()
    next(x for x in app.checkbox if x.label=='Reducir silencios (revisar contexto)').check().run()
    next(b for b in app.button if b.label=='Exportar lote de 2 clips aceptados').click().run(timeout=40)
    assert not app.exception and not app.error
    with s.connect() as db: paths=[r[0] for r in db.execute('SELECT path FROM exports ORDER BY rowid')]
    assert len(paths)==2
    assert abs(probe(paths[0])['duration']-3)<.2
    assert abs(probe(paths[1])['duration']-3.2)<.2


def test_word_crossing_clip_boundary_can_be_saved(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'word-bounds'))
    s=Store(tmp_path/'word-bounds'); sid=s.register(video)
    word=dict(start=.5,end=1.5,text='Palabra')
    s.save_chunk(sid,'a',0,8,'cfg',dict(segments=[dict(start=.5,end=1.5,text='Palabra',words=[word])],audio=[],visual=[]),[dict(start=1.,end=4.,score=55,title='Prueba',reason='Prueba',classification='heurística',visual_samples=1,words=[word])])
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    next(b for b in app.button if b.label=='Guardar revisión y configuración').click().run()
    assert not app.exception and not app.error
    assert s.candidates(sid)[0]['edited_words'][0]['start']==1.


def test_first_screen_keeps_custom_thirty_to_ninety_and_stream_window(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    from cliplivre import media,pipeline
    from dataclasses import asdict
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'one-screen'))
    s=Store(tmp_path/'one-screen'); sid=s.register(video)
    monkeypatch.setattr(media,'probe',lambda path:dict(duration=7200.,width=320,height=180,audio=True))
    calls=[]
    def fake_analyze(store,source,config,progress,*args,**kwargs):
        calls.append(config)
        assert config.source_start==1800 and config.source_end==6600
        store.save_chunk(source,'one',1800,6600,'test',dict(segments=[],audio=[],visual=[]),[dict(start=1800.,end=1845.,score=65,title='Dentro de rango',reason='Prueba',classification='test',words=[],visual_samples=1)])
        return dict(warnings=[],config=asdict(config))
    monkeypatch.setattr(pipeline,'analyze',fake_analyze)
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(x for x in app.radio if x.label=='Captura').set_value('Elegir inicio y fin').run()
    next(x for x in app.number_input if x.label=='Inicio del stream (min)').set_value(30.).run()
    next(x for x in app.number_input if x.label=='Fin del stream (min)').set_value(110.).run()
    next(x for x in app.selectbox if x.label=='Duración de cada clip').select('Personalizado').run()
    next(x for x in app.text_input if x.label=='Mínimo (min:seg)').set_value('0:30').run()
    next(x for x in app.text_input if x.label=='Máximo (min:seg)').set_value('1:30').run()
    next(x for x in app.checkbox if x.label.startswith('Tengo acceso permitido')).check().run()
    next(b for b in app.button if b.label=='Generar clips').click().run(timeout=30)
    assert not app.exception and not app.error
    assert len(calls)==1 and calls[0].min_seconds==30 and calls[0].max_seconds==90 and calls[0].duration_variation
    assert app.session_state['workflow']=='2 · Clips' and len(app.tabs)==3
    assert s.settings(sid)['clip_max']==90
    app.session_state['workflow']='1 · Fuente y ajustes'; app.run()
    assert next(x for x in app.text_input if x.label=='Máximo (min:seg)').value=='1:30'


def test_twitch_channel_offers_vod_and_explicit_recording_before_import(tmp_path,monkeypatch):
    from cliplivre import sources
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'twitch-help'))
    monkeypatch.setattr(sources,'inspect_url',lambda *a: (_ for _ in ()).throw(AssertionError('No debe consultar la red al pegar el enlace')))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(x for x in app.text_input if x.label=='Enlace de YouTube o Twitch').set_value('https://www.twitch.tv/canal_prueba').run()
    next(x for x in app.checkbox if x.label.startswith('Tengo acceso permitido')).check().run()
    assert not app.exception and not app.error
    assert any('Este es el enlace del canal' in x.value for x in app.info)
    assert next(b for b in app.button if b.label=='Generar clips').disabled
    next(x for x in app.radio if x.label=='Captura').set_value('Grabar desde ahora').run()
    assert not app.exception and not app.error
    assert not next(b for b in app.button if b.label=='Generar clips').disabled
    assert any(x.label=='Minutos a grabar desde ahora' for x in app.number_input)
    next(x for x in app.radio if x.label=='Captura').set_value('Todo lo disponible').run()
    next(x for x in app.text_input if x.label=='Enlace de YouTube o Twitch').set_value('https://www.twitch.tv/videos/123').run()
    assert not app.exception and not next(b for b in app.button if b.label=='Generar clips').disabled


def test_reused_vod_generates_without_network_metadata(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    from cliplivre import sources,pipeline
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'cached-vod-ui'))
    store=Store(tmp_path/'cached-vod-ui');sid=store.register(video)
    url='https://www.twitch.tv/videos/123'
    store.save_settings(sid,{'import':dict(url=url,start=0,end=None,mode='Todo lo disponible',live=False)})
    def no_network(*a,**kw): raise AssertionError('Un VOD ya descargado no necesita consultar ni descargar de nuevo')
    monkeypatch.setattr(sources,'inspect_url',no_network);monkeypatch.setattr(sources,'import_url',no_network)
    calls=[]
    def analysis(store,source,config,progress):
        calls.append(source);return dict(warnings=[])
    monkeypatch.setattr(pipeline,'analyze',analysis)
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    next(x for x in app.radio if x.label=='Fuente').set_value('Pegar enlace').run()
    next(x for x in app.text_input if x.label=='Enlace de YouTube o Twitch').set_value(url).run()
    next(x for x in app.selectbox if x.label=='Duración de cada clip').select('Personalizado').run()
    next(x for x in app.text_input if x.label=='Mínimo (min:seg)').set_value('0:01').run()
    next(x for x in app.text_input if x.label=='Máximo (min:seg)').set_value('0:03').run()
    next(x for x in app.checkbox if x.label.startswith('Tengo acceso permitido')).check().run()
    next(b for b in app.button if b.label=='Generar clips').click().run(timeout=30)
    assert not app.exception and not app.error and calls==[sid]


def test_duplicate_titles_keep_selected_clip_for_deferred_subtitles(video,tmp_path,monkeypatch):
    from cliplivre.store import Store
    from cliplivre import transcribe
    monkeypatch.setenv('CLIP_LIBRE_DATA',str(tmp_path/'duplicate-title'))
    store=Store(tmp_path/'duplicate-title');sid=store.register(video)
    clips=[dict(start=1.,end=3.,score=90,title='Cambio de audio: revisar',reason='Prueba',classification='heurística',visual_samples=0,words=[]),dict(start=4.,end=6.,score=80,title='Cambio de audio: revisar',reason='Prueba',classification='heurística',visual_samples=0,words=[])]
    store.save_chunk(sid,'a',0,8,'cfg',dict(segments=[],audio=[],visual=[]),clips)
    wanted=next(c for c in store.candidates(sid) if c['start']==1)['id']
    monkeypatch.setattr(transcribe,'transcribe',lambda *a,**kw:([dict(start=0.,end=1.,text='Prueba',words=[dict(start=.1,end=.9,text='Prueba')])],dict(device='cpu')))
    app=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run(timeout=30)
    app.session_state['workflow']='2 · Clips';app.run()
    next(b for b in app.button if b.label=='Elegir y editar').click().run()
    selector=next(x for x in app.selectbox if x.label=='Clip')
    assert len(set(selector.options))==2 and selector.value==wanted
    next(b for b in app.button if b.label=='Generar / actualizar subtítulos').click().run(timeout=30)
    assert not app.exception and not app.error
    assert next(x for x in app.selectbox if x.label=='Clip').value==wanted
    assert next(c for c in store.candidates(sid) if c['id']==wanted)['edited_words'][0]['text']=='Prueba'
