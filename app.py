from pathlib import Path
import json
import uuid
import os
import html
import hashlib
import streamlit as st
from cliplivre.store import Store
from cliplivre.sources import import_local,import_url,inspect_url,EXTENSIONS
from cliplivre.pipeline import Analysis,analyze
from cliplivre.render import Edit,render
from cliplivre.media import probe,preview
from cliplivre.signals import silent_intervals

ROOT=Path(os.environ.get('CLIP_LIBRE_DATA',str(Path(__file__).resolve().parent/'data')))
st.set_page_config(page_title='Clip Libre · Estudio de clips',page_icon='🎬',layout='wide')
store=Store(ROOT)
st.markdown('''<style>
.block-container{max-width:1440px;padding-top:2rem}
h1{font-size:2.5rem!important;letter-spacing:-.05em;font-weight:750!important}
h2,h3{letter-spacing:-.025em} [data-testid="stSidebar"]{border-right:1px solid #2a3040}
[data-testid="stSidebar"] .block-container{padding-top:2rem}
.stTabs [data-baseweb="tab-list"]{gap:24px;border-bottom:1px solid #30384b;margin-bottom:22px}
.stTabs [aria-selected="true"]{color:#b7f171!important}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px}
div.stButton>button{border-radius:10px;min-height:42px;font-weight:650}
div.stButton>button[kind="primary"]{background:#b7f171;color:#10160b;border:0}
.cl-pill{display:inline-block;color:#b7f171;font-size:11px;letter-spacing:.14em;font-weight:700;padding:7px 12px;border:1px solid #34462b;border-radius:100px}
.cl-lead{font-size:18px;color:#aeb8c9;max-width:740px;line-height:1.6;margin-bottom:24px}
.cl-source{color:#aeb8c9;font-size:13px;border:1px solid #30394c;border-radius:9px;padding:9px 13px;display:inline-block;margin:4px}
.cl-score{color:#b7f171;font-size:24px;font-weight:750}
</style>''',unsafe_allow_html=True)


def show_clip(path,start,end):
    key=hashlib.sha256(f'{path}:{start:.3f}:{end:.3f}'.encode()).hexdigest()[:24]
    folder=ROOT/'vistas_previas'; folder.mkdir(exist_ok=True)
    dest=folder/(key+'.mp4')
    if not dest.exists():
        with st.spinner('Preparando vista previa del clip…'):
            preview(path,start,end,dest)
    st.video(str(dest))

with st.sidebar:
    st.title('Clip Libre')
    st.caption('TU ESTUDIO DE CLIPS · LOCAL')
    st.divider()
    st.header('Mis proyectos')
    sources=store.sources()
    if st.session_state.get('pending_project'):
        st.session_state['project_pick']=st.session_state.pop('pending_project')
    sid=st.selectbox('Proyecto',options=[s['id'] for s in sources],format_func=lambda k:next(s['name'] for s in sources if s['id']==k),key='project_pick') if sources else None
    if sid:
        count=len(store.candidates(sid))
        st.caption(f'{count} clips propuestos en este proyecto')
    st.divider()
    st.write('YouTube · Twitch · Videos · Podcasts')
    st.caption('Procesamiento en tu equipo. Sin créditos ni suscripción.')
    with st.expander('Actividad y errores'):
        with store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT state,message,updated FROM jobs ORDER BY updated DESC LIMIT 15')]
        for row in rows: st.write(row)
    with st.expander('Dónde están mis archivos'):
        st.write(str(ROOT))
        st.caption('Originales, clips editados y subtítulos en carpetas separadas. Los modelos se descargan la primera vez.')

def gpu_controls():
    with st.expander('Preparar mi tarjeta NVIDIA para acelerar el análisis'):
        st.write('Si la aplicación pasó a CPU por una biblioteca ausente, instala el soporte NVIDIA una vez. La descarga puede superar 1,3 GB y requiere espacio libre. Son componentes gratuitos del fabricante, opcionales para usar la app.')
        if st.button('Instalar o reparar soporte NVIDIA',key='repair_gpu'):
            try:
                import sys
                from cliplivre.media import run
                with st.status('Descargando y comprobando soporte NVIDIA…',expanded=True) as status:
                    run([sys.executable,'-m','cliplivre.gpu_runtime','install'],timeout=3600)
                    status.update(label='Bibliotecas cargadas. Cierra y vuelve a abrir la aplicación; después elige auto.',state='complete')
                st.info('La instalación no demuestra que la GPU esté procesando. Al analizar se mostrará el dispositivo utilizado. Puede ser necesario actualizar el controlador NVIDIA.')
            except Exception as e: st.error(str(e))
        if st.button('Probar transcripción en GPU',key='probe_gpu'):
            try:
                import sys
                from cliplivre.media import run
                with st.spinner('Probando la GPU con Tiny; la primera vez puede descargar el modelo…'):
                    result=json.loads(run([sys.executable,'-m','cliplivre.gpu_runtime','probe'],timeout=900))
                if result.get('device')!='cuda' or not result.get('inference_completed'):
                    raise RuntimeError('No se confirmó inferencia CUDA.')
                from cliplivre.gpu_runtime import prepare_libraries
                from cliplivre import transcribe
                prepare_libraries(); transcribe._CUDA_FAILURE=None
                st.success('La prueba de transcripción sí usó la GPU. Ya puedes analizar con auto.')
            except Exception as e:
                st.error('La GPU no superó la prueba. '+str(e))
                st.write('Instala el soporte anterior y comprueba tu controlador desde https://www.nvidia.com/drivers/ .')
        if st.button('Ver diagnóstico de la GPU',key='diagnose_gpu'):
            from cliplivre.gpu_runtime import prepare_libraries
            from cliplivre import transcribe
            st.json(dict(libraries=prepare_libraries(),last_cuda_error=transcribe._CUDA_FAILURE))

@st.cache_data(show_spinner=False,max_entries=32)
def cached_frame(path,time,mtime):
    from cliplivre.media import frame
    return frame(path,time)


def db_stamp():
    files=[store.db,Path(str(store.db)+'-wal')]
    return tuple((p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else (0,0) for p in files)


@st.cache_data(show_spinner=False,max_entries=16)
def clip_context(db,sid,start,end,stamp):
    import sqlite3
    with sqlite3.connect(db) as connection:
        payloads=[json.loads(row[0]) for row in connection.execute('SELECT payload FROM chunks WHERE source=? AND start<? AND end>? ORDER BY start',(sid,end,start))]
    words=[]; seen=set(); audio=[]
    for payload in payloads:
        for segment in payload.get('segments',[]):
            for word in segment.get('words',[]):
                key=(round(word['start'],3),round(word['end'],3))
                if key not in seen and word['start']<end and word['end']>start:
                    words.append(dict(word,start=max(start,word['start']),end=min(end,word['end']))); seen.add(key)
        audio.extend(f for f in payload.get('audio',[]) if f['time']<end and f['end']>start)
    unique_audio={(f['time'],f['end']):f for f in audio}
    return sorted(words,key=lambda w:w['start']),sorted(unique_audio.values(),key=lambda f:f['time'])


def choose_clip(source_id,clip_id):
    store.update(clip_id,state='aceptado')
    st.session_state['editor_clip_'+source_id]=clip_id
    st.session_state['workflow']='4 · Editor y exportación'


def resize_panel_count(key,delta):
    st.session_state[key]=max(1,min(3,st.session_state[key]+delta))


tabs=st.tabs(['1 · Crear clips','2 · Configurar análisis','3 · Mis clips','4 · Editor y exportación'],key='workflow',on_change='rerun')
with tabs[0]:
    st.markdown('<span class="cl-pill">DE CONTENIDO LARGO A CLIPS CORTOS</span>',unsafe_allow_html=True)
    st.title('Tu próximo clip empieza aquí')
    st.markdown('<div class="cl-lead">Pega un enlace o sube tu contenido. Encuentra momentos, revisa los clips y edítalos con subtítulos en un solo lugar.</div>',unsafe_allow_html=True)
    st.markdown(''.join(f'<span class="cl-source">{s}</span>' for s in ['YouTube y Shorts','Twitch: videos y clips','Directos accesibles','Podcasts de audio y video']),unsafe_allow_html=True)
    with st.container(border=True):
        mode=st.radio('¿De dónde viene tu contenido?',['YouTube','Twitch','Podcast','Archivo local'],horizontal=True)
        podcast_input=st.radio('Tipo de podcast',['Archivo de audio o video','Enlace de YouTube o Twitch'],horizontal=True) if mode=='Podcast' else None
        remote=mode in {'YouTube','Twitch'} or podcast_input=='Enlace de YouTube o Twitch'
        remote_start=0; remote_end=None; live_mode='actual'; path=''; upload=None; url=''
        if remote:
            url=st.text_input('Pega el enlace de tu video, episodio o directo',placeholder='https://www.youtube.com/watch?v=…' if mode!='Twitch' else 'https://www.twitch.tv/videos/… o https://www.twitch.tv/canal')
            if st.button('Comprobar enlace',disabled=not url.strip()):
                try:
                    with st.spinner('Comprobando acceso y tipo de contenido…'):
                        st.session_state['link_info']=dict(url=url.strip(),**inspect_url(url))
                except Exception as e:
                    st.session_state.pop('link_info',None); st.error(str(e))
            info=st.session_state.get('link_info',{})
            info=info if info.get('url')==url.strip() else {}
            if info:
                st.success(info['title'])
                st.caption(f"{info['provider']} · {info['kind']}"+(f" · {info['duration']/60:.1f} min" if info.get('duration') else ''))
            content_type=st.radio('Qué quieres importar',['Video completo / VOD / episodio','Un tramo del video','Directo: capturar desde ahora','YouTube Live: intentar historial'],index=2 if info.get('live') else 0)
            if content_type=='Un tramo del video' or content_type=='YouTube Live: intentar historial':
                a,b=st.columns(2)
                remote_start=a.number_input('Desde el minuto',min_value=0.,value=0.,step=1.)*60
                duration=b.number_input('Cuántos minutos',min_value=1.,max_value=50.,value=10.,step=1.)*60
                remote_end=remote_start+duration
                if 'historial' in content_type: live_mode='historial'
            elif content_type=='Directo: capturar desde ahora':
                remote_end=st.number_input('Minutos que quieres capturar desde ahora',1,50,5)*60
                st.caption('La captura tarda lo que dure el tramo elegido. Después podrás generar los clips. No recupera minutos anteriores.')
            with st.expander('Qué enlaces puedes usar'):
                st.write('YouTube: videos, Shorts, episodios y directos. Twitch: /videos/…, clips.twitch.tv/… y canales en emisión. Podcasts de otras plataformas: descarga el archivo con permiso y súbelo aquí.')
                st.caption('La importación depende del acceso del proveedor. No se eluden bloqueos, DRM ni autenticación. Twitch activo no permite aquí recuperar el pasado: usa su VOD o captura desde ahora. Las rutas remotas siguen pendientes de validación con contenido real.')
        else:
            st.subheader('Sube tu podcast' if mode=='Podcast' else 'Sube tu video')
            upload=st.file_uploader('Arrastra un archivo o haz clic para seleccionarlo',type=[x[1:] for x in sorted(EXTENSIONS)])
            st.caption('Videos MP4, MOV, MKV y más. Audio MP3, WAV, M4A, AAC, OGG, FLAC y OPUS. Los podcasts de audio reciben una onda visual para exportarlos como video.')
            with st.expander('Mi archivo pesa más de 200 MB'):
                path=st.text_input('Pega la ruta del archivo en tu equipo',placeholder=r'C:\Videos\episodio.mkv')
                st.caption('Puedes copiar la ruta desde el Explorador de Windows. El archivo se procesa desde el disco.')
        permission=st.checkbox('Tengo acceso permitido y permiso para procesar y reutilizar este contenido.')
        automatic=st.toggle('Generar clips automáticamente al importar',value=True)
        with st.expander('Ajustes de creación'):
            a,b=st.columns(2)
            initial_model=a.selectbox('Calidad de transcripción',['small','tiny','base','medium'],format_func=lambda m:{'tiny':'Tiny · más rápido','base':'Base · ligero','small':'Small · equilibrado','medium':'Medium · más lento'}[m])
            initial_language=b.selectbox('Idioma del contenido',['es','en','auto'])
            initial_full=st.checkbox('Analizar todo el contenido importado',value=True)
            initial_min=st.number_input('Duración mínima del clip (min)',min_value=.1,value=.5,step=.5)
            initial_target=st.number_input('Duración orientativa del clip (min)',min_value=.1,value=3.,step=.5)
            initial_unlimited=st.checkbox('Sin límite máximo de duración del clip',value=True)
            initial_max=None if initial_unlimited else st.number_input('Duración máxima del clip (min)',min_value=initial_min,value=max(5.,initial_min),step=.5)*60
            st.caption('Se procesa todo el archivo por bloques guardados. La duración de cada clip es independiente de la duración del directo.')
        if st.button('Crear clips' if automatic else 'Importar contenido',type='primary',disabled=not permission,width='stretch'):
            try:
                with st.status('Importando contenido…',expanded=True) as status:
                    if remote:
                        if not info:
                            info=inspect_url(url)
                        if info.get('live') and remote_end is None:
                            remote_end=300
                            status.update(label='Directo detectado: capturando los próximos 5 minutos…')
                        dest=import_url(url,ROOT,remote_start,remote_end,permission,live_mode=live_mode)
                        name=info.get('title') or url.strip()
                    elif upload:
                        temp=ROOT/'temporales'; temp.mkdir(exist_ok=True)
                        p=temp/(uuid.uuid4().hex+Path(upload.name).suffix)
                        p.write_bytes(upload.getbuffer())
                        try: dest=import_local(p,ROOT,permission)
                        finally: p.unlink(missing_ok=True)
                        name=upload.name
                    else:
                        dest=import_local(path,ROOT,permission); name=Path(path).name
                    new_sid=store.register(dest,name)
                    if automatic:
                        bar=st.progress(0.)
                        def initial_progress(f,m):
                            bar.progress(min(1.,max(0.,f))); status.update(label=m)
                        report=analyze(store,new_sid,Analysis(model=initial_model,language='' if initial_language=='auto' else initial_language,min_seconds=initial_min*60,max_seconds=initial_max,target_seconds=initial_target*60,visual_step=6),initial_progress,max_blocks=None if initial_full else 1)
                        st.session_state['import_warnings']=report['warnings']
                        for warning in report['warnings']: st.warning(warning)
                    status.update(label='Tu proyecto está listo',state='complete')
                st.session_state['pending_project']=new_sid
                st.session_state['import_notice']='Contenido listo. Abre Mis clips para revisar tus propuestas.' if automatic else 'Contenido importado. Abre Configurar análisis para generar tus clips.'
                st.rerun()
            except Exception as e: st.error(str(e))
    if st.session_state.get('import_notice'): st.success(st.session_state.pop('import_notice'))
    for warning in st.session_state.pop('import_warnings',[]): st.warning(warning)
    st.caption('1. Añade contenido   →   2. Genera clips   →   3. Revisa y edita   →   4. Exporta')
    gpu_controls()

if sid:
    source=store.source(sid); metadata=probe(source['path'])
    with tabs[1]:
        st.subheader('Análisis incremental')
        st.write(f"Duración: {metadata['duration']/60:.1f} min · {metadata['width']} × {metadata['height']}")
        a,b,c=st.columns(3)
        model=a.selectbox('Modelo Whisper',['tiny','base','small','medium'],index=2,format_func=lambda m:{'tiny':'Tiny · más rápido','base':'Base · ligero','small':'Small · equilibrado','medium':'Medium · más lento'}[m])
        device=b.selectbox('Procesador',['auto','cpu','cuda'])
        st.caption('Auto usa la GPU si funciona. Si falta una biblioteca o falla CUDA, se continúa en CPU automáticamente y se conserva el progreso.')
        block=c.number_input('Minutos por bloque',min_value=1,max_value=120,value=50)
        language=st.selectbox('Idioma',['es','en','auto'])
        a,b=st.columns(2)
        min_m=a.number_input('Duración mínima propuesta (min)',min_value=.1,value=.5,step=.5)
        target_m=b.number_input('Duración orientativa propuesta (min)',min_value=.1,value=3.,step=.5)
        unlimited=st.checkbox('Sin máximo de duración por clip',value=True)
        max_m=None if unlimited else st.number_input('Duración máxima propuesta (min)',min_value=min_m,value=max(5.,min_m),step=.5)
        fast_profile=st.radio('Análisis visual',['Rápido','Detallado'],horizontal=True)
        st.caption('Rápido usa muestras de fotogramas clave y deja la detección de rostros para el editor. Detallado usa muestras más frecuentes.')
        use_ollama=st.checkbox('Clasificar con Ollama local (opcional)')
        ollama_model=st.text_input('Modelo Ollama',value='qwen3:4b')
        st.caption('Whisper se descarga y libera antes de usar Ollama. Detén otros modelos GPU para conservar VRAM. Ollama no recibe imágenes; recibe transcripción.')
        max_blocks=st.number_input('Bloques por revisión (0 = todos)',min_value=0,max_value=100,value=0)
        if st.button('Analizar minutos pendientes',type='primary'):
            progress=st.progress(0.); status=st.empty()
            def update(f,m): progress.progress(min(1.,max(0.,f))); status.info(m)
            try:
                report=analyze(store,sid,Analysis(block_minutes=block,model=model,device=device,language='' if language=='auto' else language,ollama=use_ollama,ollama_model=ollama_model,min_seconds=min_m*60,max_seconds=None if max_m is None else max_m*60,target_seconds=target_m*60,visual_step=6 if fast_profile=='Rápido' else 2,visual_fast=fast_profile=='Rápido'),update,max_blocks=max_blocks or None)
                st.success(f"Completado: {report['blocks']} bloques nuevos en {report['elapsed_seconds']:.1f} s. RAM muestreada: {report['rss_sampled_mb']:.0f} MB.")
                st.caption('Procesador de la transcripción: '+', '.join(report.get('devices',[]) or ['sin bloques nuevos']))
                if report.get('transcriptions_reused'): st.info(f"Se reutilizaron {report['transcriptions_reused']} bloques de transcripción. No fue necesario volver a procesarlos con Whisper.")
                for warning in report['warnings']: st.warning(warning)
            except Exception as e: st.error(str(e))
        st.caption('La reanudación usa la misma fuente y configuración. Un cambio de configuración permite reanálisis; los candidatos solapados existentes se conservan. Los bloques no cortan ni modifican el original.')
    candidates=store.candidates(sid)
    with tabs[2]:
        st.subheader('Tus clips, listos para revisar')
        a,b,c=st.columns(3)
        a.metric('Clips propuestos',len(candidates))
        b.metric('Aceptados',sum(x['state']=='aceptado' for x in candidates))
        c.metric('Por revisar',sum(x['state']=='pendiente' for x in candidates))
        st.caption('La puntuación estima interés; no garantiza viralidad. Los títulos y motivos de IA requieren comprobarse en el video.')
        a,b,c=st.columns(3)
        threshold=a.slider('Puntuación mínima',0,100,0)
        states=b.multiselect('Estados',['pendiente','aceptado','descartado'],default=['pendiente','aceptado'])
        order=c.selectbox('Ordenar por',['Puntuación','Inicio'])
        items=[x for x in candidates if x['score']>=threshold and x['state'] in states]
        items.sort(key=lambda x:-x['score'] if order=='Puntuación' else x['start'])
        grid=st.columns(2)
        for index,item in enumerate(items):
            with grid[index%2]:
                with st.container(border=True):
                    st.markdown(f"<span class='cl-score'>{item['score']}</span> <span style='color:#aeb8c9'>/ 100 · interés estimado</span>",unsafe_allow_html=True)
                    st.subheader(item['title'])
                    st.caption(f"{item['start']/60:.2f}–{item['end']/60:.2f} min · {(item['end']-item['start'])/60:.2f} min de duración · {item['state']}")
                    st.write(item['reason'])
                    if st.button('Ver clip',key='view_button_'+item['id']): st.session_state['view_open_'+item['id']]=True
                    if tabs[2].open and st.session_state.get('view_open_'+item['id']): show_clip(source['path'],item['start'],item['end'])
                    st.button('Elegir y editar',key='edit_'+item['id'],on_click=choose_clip,args=(sid,item['id']))
                    a,b=st.columns(2)
                    if a.button('Aceptar',key='accept'+item['id']): store.update(item['id'],state='aceptado'); st.rerun()
                    if b.button('Descartar',key='reject'+item['id']): store.update(item['id'],state='descartado'); st.rerun()
                    with st.expander('Por qué se propuso este clip'):
                        st.write('Gancho sugerido:',item.get('hook',''))
                        st.caption(f"Método: {item['classification']} · muestras visuales: {item['visual_samples']}")
        if not candidates: st.info('Analiza el video para generar propuestas. No se fuerza un número fijo de clips.')
    if tabs[3].open:
        with tabs[3]:
            from dataclasses import asdict,replace
            from cliplivre.composition import default_panels,guide
            from cliplivre.media import frame
            st.subheader('Configura tu clip en vertical')
            eligible=[c for c in candidates if c['state']!='descartado']
            if eligible:
                cid=st.selectbox('Clip',options=[c['id'] for c in eligible],format_func=lambda k:next(c['title'] for c in eligible if c['id']==k),key='editor_clip_'+sid)
                item=next(c for c in eligible if c['id']==cid)
                a,b=st.columns(2)
                start_m=a.number_input('Inicio del clip (min)',min_value=0.,max_value=metadata['duration']/60,value=float(item['start'])/60,step=.1,format='%.3f',key='start_min_'+cid)
                end_m=b.number_input('Final del clip (min)',min_value=0.,max_value=metadata['duration']/60,value=float(item['end'])/60,step=.1,format='%.3f',key='end_min_'+cid)
                start,end=start_m*60,end_m*60
                title=st.text_input('Título del clip',value=item['title'],key='title'+cid)
                st.caption(f'Duración seleccionada: {max(0,end-start)/60:.2f} min. Puedes ampliar el intervalo dentro de todo el material analizado.')
                if end<=start:
                    st.error('El final debe ser posterior al inicio.'); st.stop()
                if st.button('Reproducir original horizontal',key='original_'+cid): st.session_state['original_open_'+cid]=True
                if st.session_state.get('original_open_'+cid): show_clip(source['path'],start,end)
                stamp=db_stamp()
                all_words,audio_context=clip_context(str(store.db),sid,start,end,stamp)
                words=[dict(word,start=max(start,word['start']),end=min(end,word['end'])) for word in item.get('edited_words',all_words) if word['start']<end and word['end']>start]
                with st.expander('Corregir palabras y sincronización'):
                    st.caption('Ajuste fino: las marcas de palabra usan segundos para sincronizar el audio. La duración del clip se configura arriba en minutos.')
                    edited=st.data_editor(words or [{'start':float(start),'end':float(min(end,start+1)),'text':''}],num_rows='dynamic',key='words'+cid,width='stretch')
                saved=item.get('edit_settings',{})
                template=st.selectbox('Plantilla',['Limpia','Dinámica','Gameplay + cámara'])
                a,b,c=st.columns(3)
                aspect=a.selectbox('Formato',['9:16','1:1','16:9'],index=['9:16','1:1','16:9'].index(saved.get('aspect','9:16')))
                resolution=b.selectbox('Resolución base',[1080,720,360],index=[1080,720,360].index(saved.get('resolution',1080)))
                framing=c.selectbox('Encuadre',['paneles','ajustar','centro','rostros','streamer'],format_func=lambda x:{'paneles':'Cuadros editables','ajustar':'Video completo con bandas','centro':'Recortar al centro','rostros':'Seguir rostros','streamer':'Gameplay + cámara'}[x],index=['paneles','ajustar','centro','rostros','streamer'].index(saved.get('framing','streamer' if template=='Gameplay + cámara' else 'paneles')))
                panels=None; roi=None; cx=.5; cy=.5
                if framing=='paneles':
                    count_key='panel_count_'+cid
                    a,b,c=st.columns([2,1,1])
                    n=a.selectbox('Número de cuadros',[1,2,3],index=max(0,min(2,len(saved.get('panels') or [1])-1)),key=count_key)
                    b.button('Añadir cuadro',disabled=n==3,on_click=resize_panel_count,args=(count_key,1),key='add_'+cid)
                    c.button('Quitar último cuadro',disabled=n==1,on_click=resize_panel_count,args=(count_key,-1),key='remove_'+cid)
                    saved_arrangement=item.get('editor_arrangement','Arriba / abajo')
                    arrangement=st.radio('Distribución inicial',['Arriba / abajo','Lado a lado'],index=1 if saved_arrangement=='Lado a lado' else 0,horizontal=True,key='arrangement_'+cid)
                    defaults=default_panels(n,arrangement=='Lado a lado')
                    old_panels=saved.get('panels') or []
                    panels=[]
                    for i,default in enumerate(defaults):
                        initial_source=old_panels[i]['source'] if i<len(old_panels) else default['source']
                        initial_destination=old_panels[i]['destination'] if i<len(old_panels) and n==len(old_panels) and arrangement==saved_arrangement else default['destination']
                        with st.expander(f'Cuadro {i+1}: recortar, mover y cambiar tamaño',expanded=n==1):
                            st.write('Zona del video original que quieres mostrar')
                            cols=st.columns(4)
                            values=[cols[j].number_input(label,min_value=0. if j<2 else 1.,max_value=99. if j<2 else 100.,value=float(initial_source[j]*100),step=1.,key=f'src_{cid}_{i}_{j}')/100 for j,label in enumerate(['Izquierda (%)','Arriba (%)','Ancho (%)','Alto (%)'])]
                            x,y,pw,ph=values; source_roi=[x,y,min(pw,1-x),min(ph,1-y)]
                            st.write('Posición y tamaño dentro del lienzo de salida')
                            cols=st.columns(4)
                            dest_values=[cols[j].number_input(label,min_value=0. if j<2 else 1.,max_value=99. if j<2 else 100.,value=float(initial_destination[j]*100),step=1.,key=f'dst_{cid}_{n}_{arrangement}_{i}_{j}')/100 for j,label in enumerate(['X del cuadro (%)','Y del cuadro (%)','Ancho del cuadro (%)','Alto del cuadro (%)'])]
                            dx,dy,dw,dh=dest_values; dest_roi=[dx,dy,min(dw,1-dx),min(dh,1-dy)]
                            fit=st.selectbox('Contenido del cuadro',['cover','contain'],format_func=lambda f:'Llenar y recortar' if f=='cover' else 'Mostrar todo con bandas',index=1 if i<len(old_panels) and old_panels[i].get('fit')=='contain' else 0,key=f'fit_{cid}_{i}')
                            panels.append(dict(source=source_roi,destination=dest_roi,fit=fit))
                else:
                    a,b=st.columns(2)
                    cx=a.slider('Centro horizontal',0.,1.,.5); cy=b.slider('Centro vertical',0.,1.,.5)
                    if framing=='streamer':
                        from cliplivre.signals import visual_features
                        if st.button('Sugerir región de cámara por rostros'):
                            frames=visual_features(source['path'],start,min(end,start+10),1.)
                            boxes=[r for f in frames for r in f['faces'] if (r[0]<.3 or r[0]>.65) and (r[1]<.3 or r[1]>.6)]
                            if boxes:
                                x,y,pw,ph=boxes[0]; x=max(0,x-pw); y=max(0,y-ph*.5)
                                st.session_state['roi'+cid]=(x,y,min(1-x,pw*3),min(1-y,ph*2.5))
                            else: st.warning('No se encontró un rostro en una esquina. Puedes definir la cámara manualmente.')
                        defaults=st.session_state.get('roi'+cid,(0.,0.,.25,.3)); cols=st.columns(4)
                        roi=tuple(cols[i].number_input(label,0.,1.,float(defaults[i]),.01,key=f'roi{cid}{i}{defaults}') for i,label in enumerate(['X cámara','Y cámara','Ancho cámara','Alto cámara']))
                with st.expander('Añadir texto propio',expanded=bool(saved.get('overlay_text'))):
                    overlay_text=st.text_area('Texto sobre el video',value=saved.get('overlay_text',''),max_chars=2000,key='overlay_'+cid)
                    a,b=st.columns(2)
                    text_color=a.color_picker('Color del texto',value='#'+saved.get('overlay_color','FFFFFF'),key='text_color_'+cid)
                    text_size=b.slider('Tamaño del texto',24,120,int(saved.get('overlay_size',64)),key='text_size_'+cid)
                    a,b=st.columns(2)
                    text_x=a.slider('Posición horizontal del texto (%)',0,100,round(saved.get('overlay_x',.5)*100),key='text_x_'+cid)/100
                    text_y=b.slider('Posición vertical del texto (%)',0,100,round(saved.get('overlay_y',.15)*100),key='text_y_'+cid)/100
                burn=st.checkbox('Incrustar subtítulos',value=saved.get('burn',True))
                animated=st.checkbox('Animar subtítulos',value=saved.get('animated',template=='Dinámica'))
                a,b,c=st.columns(3)
                font=a.selectbox('Fuente',['Arial','Verdana','DejaVu Sans'],index=['Arial','Verdana','DejaVu Sans'].index(saved.get('font','Arial')))
                color=b.color_picker('Color de palabra activa','#'+saved.get('color','FFFF00'))
                position=c.selectbox('Posición de subtítulos',['Abajo','Centro','Arriba'],index={2:0,5:1,8:2}[saved.get('subtitle_position',2)])
                size=st.slider('Tamaño de subtítulos',24,90,saved.get('font_size',54))
                with st.expander('Zoom, silencios y efectos'):
                    zoom=st.slider('Zoom suave máximo',1.,1.2,1.08 if template=='Dinámica' else 1.,.01)
                    fade=st.checkbox('Fundidos de entrada y salida',value=template=='Dinámica')
                    reduce=st.checkbox('Reducir silencios (revisar contexto)')
                edit=Edit(aspect=aspect,resolution=resolution,framing=framing,center_x=cx,center_y=cy,zoom=zoom,fade=fade,burn=burn,animated=animated,font=font,font_size=size,color=color.lstrip('#'),subtitle_position={'Abajo':2,'Centro':5,'Arriba':8}[position],streamer_roi=roi,panels=panels,overlay_text=overlay_text,overlay_size=text_size,overlay_color=text_color.lstrip('#'),overlay_x=text_x,overlay_y=text_y)
                st.subheader('Encuadre: vista inmediata')
                try:
                    from cliplivre.render import dimensions
                    w,h=dimensions(aspect,360)
                    source_image=cached_frame(source['path'],min(start+.2,end-.01),Path(source['path']).stat().st_mtime_ns)
                    guide_panels=panels
                    if not guide_panels:
                        guide_panels=default_panels(1); guide_panels[0]['fit']='contain' if framing=='ajustar' else 'cover'
                        if framing=='streamer' and roi:
                            guide_panels=[dict(source=list(roi),destination=[0,0,1,1/3],fit='cover'),dict(source=[0,0,1,1],destination=[0,1/3,1,2/3],fit='contain')]
                        elif framing in {'centro','rostros'}:
                            ratio=metadata['width']/metadata['height']; output_ratio=w/h
                            rw=min(1.,output_ratio/ratio); rh=min(1.,ratio/output_ratio)
                            guide_panels[0]['source']=[(1-rw)*cx,(1-rh)*cy,rw,rh]
                    picture=guide(source_image,guide_panels,w,h,overlay_text,text_x,text_y,text_color.lstrip('#'),text_size)
                    st.image(picture,width=min(400,w))
                    st.caption('Guía estática rápida de cuadros y texto. Para comprobar subtítulos sincronizados, seguimiento, zoom y animaciones, genera la vista previa editada.')
                except Exception as e: st.error('No se pudo mostrar la guía: '+str(e))
                if st.button('Guardar revisión y configuración'):
                    try:
                        checked=[]
                        for word in edited:
                            if word['text']:
                                if not start<=float(word['start'])<float(word['end'])<=end: raise ValueError('Cada palabra debe estar dentro del clip.')
                                checked.append(dict(start=float(word['start']),end=float(word['end']),text=str(word['text'])))
                        item.update(start=start,end=end,title=title,edited_words=checked,edit_settings=asdict(edit),editor_arrangement=arrangement if framing=='paneles' else 'Arriba / abajo')
                        store.update(cid,payload=item); st.success('Clip y configuración guardados.')
                    except Exception as e: st.error(str(e))
                status=st.empty()
                def make(candidate,settings,preview_mode=False):
                    selected_words=candidate.get('edited_words')
                    if selected_words is None: selected_words=all_words
                    candidate_audio=clip_context(str(store.db),sid,candidate['start'],candidate['end'],db_stamp())[1] if reduce else []
                    cuts=silent_intervals(candidate_audio,candidate['start'],candidate['end']) if reduce else []
                    fingerprint=hashlib.sha256(json.dumps(dict(source=sid,start=candidate['start'],end=candidate['end'],words=selected_words,edit=asdict(settings),cuts=cuts),sort_keys=True).encode()).hexdigest()
                    manifest=ROOT/'vistas_previas'/('edited_'+fingerprint+'.json')
                    manifest.parent.mkdir(exist_ok=True)
                    if preview_mode and manifest.exists():
                        saved_output=Path(json.loads(manifest.read_text())['path'])
                        if saved_output.exists(): return saved_output
                    result=render(source['path'],candidate['start'],candidate['end'],selected_words,ROOT/'editados',settings,cuts,lambda m:status.info(m))
                    if preview_mode: manifest.write_text(json.dumps(dict(path=str(result))))
                    return result
                if st.button('Generar vista previa editada'):
                    try:
                        with st.spinner('Renderizando solo el intervalo elegido…'):
                            result=make(dict(item,start=start,end=end,edited_words=list(edited)),replace(edit,resolution=360,preset='ultrafast'),True)
                        st.session_state['preview'+cid]=str(result)
                    except Exception as e: st.error(str(e))
                if st.session_state.get('preview'+cid): st.video(st.session_state['preview'+cid])
                st.caption('La vista previa en video incluye los efectos reales y se reutiliza si no cambias los ajustes.')
                if st.button('Exportar clip con estos ajustes',type='primary'):
                    try:
                        with st.spinner('Exportando el clip configurado…'): result=make(dict(item,start=start,end=end,edited_words=list(edited)),edit)
                        store.export(cid,result,asdict(edit)); st.session_state['export'+cid]=str(result)
                    except Exception as e: st.error(str(e))
                if st.session_state.get('export'+cid):
                    result=Path(st.session_state['export'+cid]); st.success(str(result)); st.video(str(result))
                    for name in ['editado.mp4','subtitulos.srt','subtitulos.ass','texto.ass','edicion.json']:
                        p=result.parent/name
                        if p.exists(): st.download_button('Descargar '+name,p.read_bytes(),file_name=name,key=str(p))
                accepted=[c for c in eligible if c['state']=='aceptado']
                st.caption('Lote: aplica estos ajustes a los clips aceptados. Las palabras guardadas se conservan.')
                if st.button(f'Exportar lote de {len(accepted)} clips aceptados',disabled=not accepted):
                    for candidate in accepted:
                        try:
                            batch_words,_=clip_context(str(store.db),sid,candidate['start'],candidate['end'],db_stamp())
                            result=make(dict(candidate,edited_words=candidate.get('edited_words',batch_words)),edit)
                            store.export(candidate['id'],result,asdict(edit)); st.success(str(result))
                        except Exception as e: st.error(f"{candidate['title']}: {e}")
            else: st.info('Elige un clip en Mis clips para configurarlo.')

else:
    for tab in tabs[1:]:
        with tab: st.info('Importa un video y selecciona un proyecto en la biblioteca.')
