from pathlib import Path
import json
import uuid
import os
import html
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from cliplivre.progress import Jobs
from cliplivre.controls import clock
import streamlit as st
from cliplivre.store import Store
from cliplivre.sources import import_local,import_url,inspect_url,EXTENSIONS,twitch_channel_videos
from cliplivre.pipeline import Analysis,analyze
from cliplivre.render import Edit,render
from cliplivre.media import probe,preview
from cliplivre.signals import silent_intervals

ROOT=Path(os.environ.get('CLIP_LIBRE_DATA',str(Path(__file__).resolve().parent/'data')))
st.set_page_config(page_title='Clip Libre · Estudio de clips',page_icon='🎬',layout='wide')
store=Store(ROOT)
if 'progress_jobs' not in st.session_state:st.session_state['progress_jobs']=Jobs()
progress_jobs=st.session_state['progress_jobs']

def monitored(job,stage,fn,*args,**kwargs):
    job.start(stage)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(fn,*args,**kwargs)
        while not future.done():time.sleep(.15)
        return future.result()

st.markdown('''<style>
.block-container{max-width:1440px;padding-top:2rem}
h1{font-size:2.5rem!important;letter-spacing:-.05em;font-weight:750!important}
h2,h3{letter-spacing:-.025em} [data-testid="stSidebar"]{border-right:1px solid #2a3040}
[data-testid="stSidebar"] .block-container{padding-top:2rem}
.stTabs [data-baseweb="tab-list"]{gap:24px;border-bottom:1px solid #30384b;margin-bottom:22px}
.stTabs [aria-selected="true"]{color:#b7f171!important}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px}
div.stButton>button{border-radius:10px;min-height:42px;font-weight:650}
div.stButton>button[kind="primary"]{background:#3e78ff;color:#ffffff;border:0}
.cl-pill{display:inline-block;color:#b7f171;font-size:11px;letter-spacing:.14em;font-weight:700;padding:7px 12px;border:1px solid #34462b;border-radius:100px}
.cl-lead{font-size:18px;color:#aeb8c9;max-width:740px;line-height:1.6;margin-bottom:24px}
.cl-source{color:#aeb8c9;font-size:13px;border:1px solid #30394c;border-radius:9px;padding:9px 13px;display:inline-block;margin:4px}
.cl-score{color:#b7f171;font-size:24px;font-weight:750}
</style>''',unsafe_allow_html=True)


def legacy_show_clip(path,start,end):
    key=hashlib.sha256(f'{path}:{start:.3f}:{end:.3f}'.encode()).hexdigest()[:24]
    folder=ROOT/'vistas_previas'; folder.mkdir(exist_ok=True)
    dest=folder/(key+'.mp4')
    if not dest.exists():
        with st.spinner('Preparando vista previa del clip…'):
            preview(path,start,end,dest)
    st.video(str(dest))

def direct_player(path,start=0,end=None):
    from cliplivre.playback import media_server,player_html
    import streamlit.components.v1 as components
    st.iframe(player_html(media_server().url(path),start,end),height=460)


def show_clip(path,start,end):
    from cliplivre.media import clip_preview
    with st.spinner('Abriendo solo este clip…'):
        excerpt=clip_preview(path,start,end,ROOT/'vistas_previas')
    direct_player(excerpt,0,end-start)


def new_project():
    st.session_state['source_mode']='Pegar enlace'
    st.session_state['source_url']=''


def reopen_source(url):
    st.session_state['source_mode']='Pegar enlace'
    st.session_state['source_url']=url
    st.session_state.pop('link_info',None)
    st.session_state['refresh_url_pending']=url
    st.session_state['new_source_settings']={'force_refresh':True}
    st.session_state['capture_new']='Todo lo disponible'


def select_full_source(context):st.session_state['capture_'+str(context)]='Todo lo disponible'


def sync_source_inputs(context,key,lower,upper):
    if not key: return
    start=st.session_state.get('capture_start_'+context,lower)
    end=st.session_state.get('capture_end_'+context,upper)
    st.session_state[key]=tuple(sorted((max(lower,min(upper,start)),max(lower,min(upper,end)))))


def sync_source_range(key,context):
    start,end=st.session_state[key]
    st.session_state['capture_start_'+context]=start
    st.session_state['capture_end_'+context]=end


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
    st.session_state['workflow']='3 · Editor'


def resize_panel_count(key,delta):
    st.session_state[key]=max(1,min(3,st.session_state[key]+delta))


def precise_clock(value):
    minutes,seconds=divmod(float(value),60)
    part=f'{seconds:06.3f}'.rstrip('0').rstrip('.')
    if seconds<10 and not part.startswith('0'): part='0'+part
    return f'{int(minutes)}:{part}'


def sync_clip_timeline(key,cid):
    start,end=st.session_state[key]
    st.session_state['edit_start_'+cid]=precise_clock(start*60)
    st.session_state['edit_end_'+cid]=precise_clock(end*60)


def count_layout_changed(cid):
    n=st.session_state.get('panel_count_'+cid) or 1
    st.session_state['panel_count_'+cid]=n
    if n==2 and st.session_state['layout_'+cid]=='Foto + clip': return
    st.session_state['layout_'+cid]={1:'Vertical',2:'Dúo',3:'Tres cuadros'}[n]


def set_layout(cid):
    st.session_state['panel_count_'+cid]={'Vertical':1,'Dúo':2,'Tres cuadros':3,'Foto + clip':2}[st.session_state['layout_'+cid]]


def change_panel_count(cid,delta):
    n=max(1,min(3,st.session_state['panel_count_'+cid]+delta))
    st.session_state['panel_count_'+cid]=n
    st.session_state['layout_'+cid]={1:'Vertical',2:'Dúo',3:'Tres cuadros'}[n]


def add_title(key,duration):
    st.session_state[key]=st.session_state.get(key,[])+[dict(id=uuid.uuid4().hex,text='Nuevo título',start=0.,end=duration,x=.5,y=.15,size=64,color='#FFFFFF')]


def remove_title(key): st.session_state[key]=st.session_state.get(key,[])[:-1]


def duplicate_title(key,index):
    tracks=st.session_state[key]; st.session_state[key]=tracks+[dict(tracks[index],id=uuid.uuid4().hex)]


def clear_logo(cid):
    st.session_state['logo_'+cid]=None
    st.session_state['logo_revision_'+cid]=st.session_state.get('logo_revision_'+cid,0)+1


def save_image(upload):
    from PIL import Image
    from io import BytesIO
    data=upload.getvalue(); image=Image.open(BytesIO(data)).convert('RGBA')
    folder=ROOT/'assets'; folder.mkdir(exist_ok=True)
    path=folder/(hashlib.sha256(data).hexdigest()+'.png')
    if not path.exists(): image.save(path)
    return str(path)


if st.session_state.get('pending_workflow'): st.session_state['workflow']=st.session_state.pop('pending_workflow')
labels=['1 · Fuente y ajustes','2 · Clips','3 · Editor']
from cliplivre.playback import media_server,progress_html
if 'progress_url' not in st.session_state:st.session_state['progress_url']=media_server().progress_url(progress_jobs.recent)
st.iframe(progress_html(st.session_state['progress_url']),height=155)
tabs=st.tabs(labels,key='workflow',on_change='rerun')
with tabs[0]:
    from cliplivre.controls import PRESETS,clip_limits,clock
    from dataclasses import asdict
    st.title('Tu video, tus clips')
    st.caption('1. Elige la parte del stream.  2. Define cuánto durarán los clips.  3. Genera y edita.')
    if st.session_state.get('pending_mode'):
        st.session_state['source_mode']=st.session_state.pop('pending_mode')
    choices=['Proyecto actual','Pegar enlace','Subir archivo'] if sid else ['Pegar enlace','Subir archivo']
    if st.session_state.get('source_mode') not in choices: st.session_state['source_mode']=choices[0]
    mode=st.radio('Fuente',choices,horizontal=True,key='source_mode')
    ctx=sid if mode=='Proyecto actual' else 'new'
    saved_source=store.settings(sid) if mode=='Proyecto actual' else st.session_state.get('new_source_settings',{})
    url=''; path=''; upload=None; remote_info={}; local_info=None
    if mode=='Proyecto actual':
        selected_source=store.source(sid)
        try: local_info=probe(selected_source['path'])
        except Exception as e: st.error(str(e))
        st.subheader(selected_source['name'])
        if local_info:
            st.caption('Duración del archivo importado: '+clock(local_info['duration']))
            if tabs[0].open: direct_player(selected_source['path'])
        original_import=saved_source.get('import',{})
        original_url=original_import.get('url') or saved_source.get('url')
        expected=original_import.get('expected_duration')
        if expected and local_info and expected>local_info['duration']+3:
            st.warning('Archivo parcial: '+clock(local_info['duration'])+' descargadas de '+clock(expected)+' esperadas. Analizar este proyecto usa solo el archivo disponible.')
        if original_url:
            st.button('Actualizar desde el enlace · revisar duración completa',on_click=reopen_source,args=(original_url,),key='refresh_source')
        st.button('＋ Nuevo proyecto',on_click=new_project,key='new_project')
    elif mode=='Pegar enlace':
        url=st.text_input('Enlace de YouTube o Twitch',placeholder='Pega el enlace del video, VOD o directo',key='source_url')
        refresh_pending=st.session_state.pop('refresh_url_pending',None)==url.strip()
        if st.button('Comprobar enlace',disabled=not url.strip()) or refresh_pending:
            try:
                job=progress_jobs.new('Comprobando duración del enlace')
                info=monitored(job,'Comprobando duración del enlace',inspect_url,url)
                st.session_state['link_info']=dict(url=url.strip(),checked_at=time.time(),**info)
                job.finish('Duración anunciada: '+clock(info['duration']) if info.get('duration') else 'Enlace comprobado')
            except Exception as e: job.fail(e); st.session_state.pop('link_info',None); st.error(str(e))
        remote_info=st.session_state.get('link_info',{})
        if remote_info.get('url')!=url.strip(): remote_info={}
        if remote_info:
            st.success(remote_info['title'])
            if remote_info.get('duration'): st.caption('Duración anunciada por el enlace: '+clock(remote_info['duration']))
    else:
        upload=st.file_uploader('Video o podcast',type=[x[1:] for x in sorted(EXTENSIONS)])
        with st.expander('Archivo de más de 200 MB'):
            path=st.text_input('Ruta del archivo en tu equipo',placeholder=r'C:\Videos\directo.mkv')
            st.caption('Puedes pegar la ruta copiada desde el Explorador de Windows.')
    channel_videos=twitch_channel_videos(url) if mode=='Pegar enlace' else None
    duration=(local_info or remote_info).get('duration')
    origin=float(saved_source.get('import',{}).get('start',0)) if mode=='Proyecto actual' else 0.
    if origin and local_info: st.caption('Este archivo corresponde al stream desde '+clock(origin)+' hasta '+clock(origin+local_info['duration'])+'. Para otro tramo, pega de nuevo el enlace.')
    with st.container(border=True):
        st.subheader('Parte del stream que quieres usar')
        if duration:st.caption('Duración disponible: '+clock(duration)+' · '+str(round(duration/60,2))+' minutos, sin límite de cuatro horas.')
        capture_options=['Todo lo disponible','Elegir inicio y fin']+(['Grabar desde ahora'] if mode=='Pegar enlace' else [])
        capture_default=saved_source.get('capture_mode','Todo lo disponible') if saved_source.get('last_mode')==mode else 'Todo lo disponible'
        if capture_default not in capture_options: capture_default=capture_options[0]
        capture_mode=st.radio('Captura',capture_options,index=capture_options.index(capture_default),horizontal=True,key='capture_'+str(ctx))
        source_start=origin; source_end=None
        if duration:st.button('Usar todo el intervalo disponible',on_click=select_full_source,args=(ctx,),disabled=capture_mode=='Todo lo disponible',key='full_'+str(ctx))
        if capture_mode=='Elegir inicio y fin':
            a,b=st.columns(2)
            initial_start=(origin+float(saved_source.get('local_start',0)))/60 if mode=='Proyecto actual' else float(saved_source.get('capture_start',0))/60
            initial_end=(origin+float(saved_source.get('local_end') or duration or 1800))/60 if mode=='Proyecto actual' else float(saved_source.get('capture_end') or duration or 1800)/60
            range_key=f'source_range_{ctx}_{duration:.3f}' if duration else ''
            start_minutes=a.number_input('Inicio del stream (min)',min_value=origin/60,value=initial_start,step=1.,key='capture_start_'+str(ctx),on_change=sync_source_inputs,args=(str(ctx),range_key,origin/60,(origin+(duration or 864000))/60))
            end_minutes=b.number_input('Fin del stream (min)',min_value=origin/60,value=max(initial_start+.1,initial_end),step=1.,key='capture_end_'+str(ctx),on_change=sync_source_inputs,args=(str(ctx),range_key,origin/60,(origin+(duration or 864000))/60))
            source_start=start_minutes*60; source_end=end_minutes*60
            if duration and duration>1 and tabs[0].open:
                slider_key=f'source_range_{ctx}_{duration:.3f}'
                slider_default=tuple(sorted((max(origin/60,min(start_minutes,(origin+duration)/60)),max(origin/60,min(end_minutes,(origin+duration)/60)))))
                if slider_key not in st.session_state: st.session_state[slider_key]=slider_default
                st.slider('Barra del tramo (min)',min_value=float(origin/60),max_value=float((origin+duration)/60),step=.1,value=slider_default,key=slider_key,on_change=sync_source_range,args=(slider_key,str(ctx)))
            st.caption('Se usará '+clock(source_start)+' → '+clock(source_end)+'. Ejemplo: 30 → 110 min es de 0:30:00 a 1:50:00 del stream.')
        elif capture_mode=='Grabar desde ahora':
            source_end=st.number_input('Minutos a grabar desde ahora',min_value=1.,value=30.,step=1.,key='record_'+str(ctx))*60
            st.caption('Solo esta opción espera tiempo real. No recupera el pasado del directo.')
        else:
            st.caption('Archivo o VOD completo. En un directo activo, todo el historial que el proveedor permita recuperar. No se reemplaza por cinco minutos.')
        if mode=='Pegar enlace' and (remote_info.get('live') or capture_mode=='Grabar desde ahora'):
            st.caption('Para el pasado de Twitch usa el VOD /videos/ID. Un canal activo no entrega aquí su historial. YouTube Live necesita historial disponible.')
    needs_vod=bool(channel_videos and capture_mode!='Grabar desde ahora')
    if needs_vod:
        st.info('Este es el enlace del canal. Para lo que ya pasó, abre sus videos guardados y pega el enlace del video elegido. Para lo que ocurra desde ahora, selecciona «Grabar desde ahora» arriba y elige cuántos minutos grabar.')
        st.link_button('Abrir videos guardados de este canal',channel_videos)
        st.caption('Si no hay video guardado público, importa una grabación autorizada. No se empieza a grabar sin que elijas esa opción.')
    with st.container(border=True):
        st.subheader('Duración de los clips que vas a generar')
        preset_names=list(PRESETS)
        preset_default=saved_source.get('preset','30–90 s · variado')
        preset=st.selectbox('Duración de cada clip',preset_names,index=preset_names.index(preset_default) if preset_default in preset_names else 0,key='clip_preset_'+str(ctx))
        custom_min='0:30'; custom_max='1:30'
        if preset=='Personalizado':
            a,b=st.columns(2)
            custom_min=a.text_input('Mínimo (min:seg)',value=saved_source.get('custom_min','0:30'),key='clip_min_'+str(ctx))
            custom_max=b.text_input('Máximo (min:seg)',value=saved_source.get('custom_max','1:30'),key='clip_max_'+str(ctx))
        limits_error=None
        try: clip_min,clip_max=clip_limits(preset,custom_min,custom_max)
        except ValueError as e: limits_error=str(e); clip_min,clip_max=30.,90.; st.error(limits_error)
        st.caption('Clips de '+clock(clip_min)+' a '+(clock(clip_max) if clip_max is not None else 'sin máximo')+'. Las duraciones varían dentro del rango elegido; no se generan clips por encima del máximo.')
        title_hint=st.text_input('Título del proyecto (opcional)',value=saved_source.get('title',''),key='project_title_'+str(ctx))
        profile_names=['Ultrarrápido','Rápido','Equilibrado','Calidad alta']
        speed=st.selectbox('Velocidad',profile_names,index=profile_names.index(saved_source.get('speed','Ultrarrápido')),key='speed_'+str(ctx))
        if speed=='Ultrarrápido': st.info('Detecta audio y cambios visuales sin transcribir todo el directo. Elige un clip y genera sus subtítulos en el editor. Menos contexto de conversación; no interpreta lo que ocurre en las imágenes.')
        with st.expander('Más opciones'):
            lang_options=['es','en','auto']
            language=st.selectbox('Idioma',lang_options,index=lang_options.index(saved_source.get('language','es')),key='language_'+str(ctx))
            override_model=st.selectbox('Modelo de transcripción',['Según velocidad','tiny','base','small','medium'],index=['Según velocidad','tiny','base','small','medium'].index(saved_source.get('model_override','Según velocidad')),key='model_override_'+str(ctx))
            device=st.selectbox('Procesador',['auto','cpu','cuda'],index=['auto','cpu','cuda'].index(saved_source.get('device','auto')),key='device_'+str(ctx))
            use_ollama=st.checkbox('Clasificación con Ollama',value=saved_source.get('ollama',False),key='ollama_'+str(ctx))
            ollama_model=st.text_input('Modelo Ollama',value=saved_source.get('ollama_model','qwen3:4b'),key='ollama_model_'+str(ctx))
            st.caption('Los cambios de duración reutilizan la transcripción. Cambiar modelo o idioma puede requerir procesar de nuevo. No hay un segundo panel de análisis.')
    quality_names={'360p · descarga más ligera':360,'720p':720,'1080p · mayor tamaño':1080}
    quality_height=1080
    if mode=='Pegar enlace':
        quality=st.selectbox('Calidad del video que se descargará',list(quality_names),index=2)
        quality_height=quality_names[quality]
        st.caption('360p descarga menos datos; la fuente guardada tendrá esa resolución. Ninguna opción reduce la duración del directo.')
    permission=st.checkbox('Tengo acceso permitido y permiso para procesar y reutilizar este contenido.')
    if st.button('Generar clips',type='primary',disabled=not permission or bool(limits_error) or needs_vod,width='stretch'):
        new_sid=None
        job=progress_jobs.new('Generando clips')
        try:
            if source_end is not None and source_end<=source_start: raise ValueError('El fin del stream debe ser posterior al inicio.')
            with st.status('Preparando tu contenido…',expanded=True) as status:
                if mode=='Pegar enlace':
                    reusable=store.find_import(url.strip(),source_start,source_end,capture_mode,height=quality_height)
                    old_import=reusable[1].get('import',{}) if reusable else {}
                    recent=old_import.get('checked_at',0)>time.time()-300 and old_import.get('expected_duration')
                    if not remote_info and (not recent or saved_source.get('force_refresh')):
                        remote_info=monitored(job,'Comprobando duración actual',inspect_url,url)
                    expected=(source_end-source_start) if source_end is not None else remote_info.get('duration') or old_import.get('expected_duration')
                    if reusable and expected:
                        reusable=store.find_import(url.strip(),source_start,source_end,capture_mode,expected_duration=expected,height=quality_height)
                    live_mode='actual' if capture_mode=='Grabar desde ahora' else 'disponible'
                    if not reusable:
                        status.update(label='Comprobando el enlace…')
                        if not remote_info: remote_info=monitored(job,'Comprobando el enlace',inspect_url,url)
                        if capture_mode=='Grabar desde ahora' and not remote_info.get('live'): raise ValueError('Ese enlace no está emitiendo en directo. Elige Todo lo disponible o inicio–fin.')
                    if reusable:
                        new_sid,import_settings=reusable
                        status.update(label='Fuente ya descargada: reutilizando el archivo…')
                        import_description=import_settings.get('import',{})
                    else:
                        status.update(label='Descargando la fuente. El análisis comienza al terminar la descarga…')
                        dest=monitored(job,'Descargando fuente',import_url,url,ROOT,source_start,source_end,permission,live_mode=live_mode,progress=job.update,height=quality_height)
                        name=title_hint.strip() or remote_info.get('title') or url
                        new_sid=monitored(job,'Registrando archivo',store.register,dest,name,progress=job.update)
                        import_description=dict(url=url.strip(),start=source_start,end=source_end,mode=capture_mode,live=bool(remote_info.get('live')),expected_duration=expected,checked_at=time.time(),height=quality_height)
                    analysis_start=0.; analysis_end=None
                elif mode=='Subir archivo':
                    if upload:
                        temp=ROOT/'temporales'; temp.mkdir(exist_ok=True)
                        p=temp/(uuid.uuid4().hex+Path(upload.name).suffix); p.write_bytes(upload.getbuffer())
                        try: dest=monitored(job,'Importando archivo',import_local,p,ROOT,permission,progress=job.update)
                        finally: p.unlink(missing_ok=True)
                        name=title_hint.strip() or upload.name
                    else:
                        dest=monitored(job,'Importando archivo',import_local,path,ROOT,permission,progress=job.update); name=title_hint.strip() or Path(path.strip().strip('"')).name
                    new_sid=monitored(job,'Registrando archivo',store.register,dest,name,progress=job.update)
                    analysis_start=source_start; analysis_end=source_end; import_description={}
                else:
                    new_sid=sid; analysis_start=source_start-origin; analysis_end=None if source_end is None else source_end-origin; import_description=saved_source.get('import',{})
                options=dict(preset=preset,clip_min=clip_min,clip_max=clip_max,custom_min=custom_min,custom_max=custom_max,speed=speed,language=language,ollama=use_ollama,ollama_model=ollama_model,title=title_hint,capture_mode=capture_mode,capture_start=source_start,capture_end=source_end,url=url if mode=='Pegar enlace' else saved_source.get('url',''),stream_origin=source_start if mode=='Pegar enlace' else saved_source.get('stream_origin',0))
                options.update(dict(last_mode=mode,local_start=analysis_start,local_end=analysis_end,model_override=override_model,device=device)); options['import']=import_description
                store.save_settings(new_sid,options)
                actual_duration=probe(store.source(new_sid)['path'])['duration']
                from cliplivre.sources import incomplete_duration
                expected_available=import_description.get('expected_duration')
                incomplete=incomplete_duration(expected_available,actual_duration)
                import_description['complete']=not incomplete
                options['import']=import_description
                store.save_settings(new_sid,options)
                if incomplete and mode!='Proyecto actual':
                    raise ValueError('Importación incompleta: se esperaba '+clock(expected_available)+' y el archivo disponible dura '+clock(actual_duration)+'. Se conserva este proyecto parcial. Pulsa Actualizar desde el enlace para intentar recuperar el contenido completo; no hay un máximo de cuatro horas.')
                window_length=(analysis_end if analysis_end is not None else actual_duration)-analysis_start
                if window_length<clip_min:
                    raise ValueError('El tramo dura '+clock(window_length)+' y el mínimo elegido es '+clock(clip_min)+'. Elige una duración menor para generar clips.')
                analysis_started=time.monotonic()
                def update(f,m): job.update(stage='Analizando el tramo elegido',done=max(0.,min(1.,f)),total=1,message=m,origin=analysis_started)
                config=Analysis(transcription=speed!='Ultrarrápido',fast_asr=speed in {'Rápido','Ultrarrápido'},model=({'Ultrarrápido':'tiny','Rápido':'tiny','Equilibrado':'small','Calidad alta':'medium'}[speed] if override_model=='Según velocidad' else override_model),device=device,language='' if language=='auto' else language,ollama=use_ollama,ollama_model=ollama_model,min_seconds=clip_min,max_seconds=clip_max,target_seconds=(clip_min+clip_max)/2 if clip_max is not None else max(clip_min,180),duration_variation=True,visual_step=8 if speed in {'Rápido','Ultrarrápido'} else 2,visual_fast=speed in {'Rápido','Ultrarrápido'},source_start=analysis_start,source_end=analysis_end)
                report=monitored(job,'Analizando el tramo elegido',analyze,store,new_sid,config,update,process_progress=job.update)
                job.finish('Clips listos. Intervalo revisado: '+clock(analysis_start)+' → '+clock(analysis_end if analysis_end is not None else actual_duration))
                status.update(label='Clips listos',state='complete')
            st.session_state['pending_project']=new_sid
            st.session_state['pending_mode']='Proyecto actual'
            st.session_state['pending_workflow']='2 · Clips'
            st.session_state['import_warnings']=report['warnings']
            st.session_state['import_notice']='Se usó tu rango '+clock(clip_min)+'–'+(clock(clip_max) if clip_max is not None else 'sin máximo')+'. Revisión de todo el tramo terminado.'
            st.rerun()
        except Exception as e:
            job.fail(e)
            if new_sid and mode!='Proyecto actual':
                st.session_state['pending_project']=new_sid; st.session_state['pending_mode']='Proyecto actual'; st.session_state['pending_error']=str(e); st.rerun()
            st.error(str(e))
    if st.session_state.get('pending_error'): st.error(st.session_state.pop('pending_error'))
    if st.session_state.get('import_notice'): st.success(st.session_state.pop('import_notice'))
    for warning in st.session_state.pop('import_warnings',[]): st.warning(warning)
    gpu_controls()

if sid:
    source=store.source(sid); metadata=probe(source['path'])
    candidates=store.candidates(sid)
    with tabs[1]:
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
        active=store.settings(sid)
        low,high=active.get('clip_min',0),active.get('clip_max')
        if active: st.caption('Resultados del rango '+clock(low)+'–'+(clock(high) if high is not None else 'sin máximo'))
        show_other=st.checkbox('Mostrar clips de otras configuraciones',value=False)
        def in_range(item):
            duration=item['end']-item['start']
            return duration>=low-.01 and (high is None or duration<=high+.01) and item['start']>=active.get('local_start',0)-.01 and (active.get('local_end') is None or item['end']<=active['local_end']+.01)
        items=[x for x in candidates if x['score']>=threshold and x['state'] in states and (show_other or in_range(x))]
        items.sort(key=lambda x:-x['score'] if order=='Puntuación' else x['start'])
        grid=st.columns(2)
        for index,item in enumerate(items):
            with grid[index%2]:
                with st.container(border=True):
                    st.markdown(f"<span class='cl-score'>{item['score']}</span> <span style='color:#aeb8c9'>/ 100 · interés estimado</span>",unsafe_allow_html=True)
                    st.subheader(item['title'])
                    st.caption(f"Duración: {clock(item['end']-item['start'])} · En el directo: {clock(item['start'])} → {clock(item['end'])} · {item['state']}")
                    st.write(item['reason'])
                    if st.button('Ver clip',key='view_button_'+item['id']): st.session_state['view_open_'+item['id']]=True
                    if tabs[1].open and st.session_state.get('view_open_'+item['id']): show_clip(source['path'],item['start'],item['end'])
                    from cliplivre.downloads import source_clip
                    def download_horizontal(path=source['path'],begin=item['start'],finish=item['end'],root=ROOT,jobs=progress_jobs):
                        task=jobs.new('Preparando descarga horizontal')
                        try:
                            data=source_clip(path,begin,finish,root,progress=task.update).read_bytes();task.finish('MP4 horizontal listo para descargar');return data
                        except Exception as e:task.fail(e);raise
                    st.download_button('Descargar clip para CapCut · horizontal',data=download_horizontal,file_name=f"clip_{item['id'][:8]}_horizontal.mp4",mime='video/mp4',key='download_source_'+item['id'],on_click='ignore',width='stretch')
                    st.button('Elegir y editar',key='edit_'+item['id'],on_click=choose_clip,args=(sid,item['id']))
                    a,b=st.columns(2)
                    if a.button('Aceptar',key='accept'+item['id']): store.update(item['id'],state='aceptado'); st.rerun()
                    if b.button('Descartar',key='reject'+item['id']): store.update(item['id'],state='descartado'); st.rerun()
                    with st.expander('Por qué se propuso este clip'):
                        st.write('Gancho sugerido:',item.get('hook',''))
                        st.caption(f"Método: {item['classification']} · muestras visuales: {item['visual_samples']}")
        if not items: st.info('No hay clips de este rango todavía. Vuelve a Fuente y ajustes y pulsa Generar clips. Los clips guardados de otros rangos se conservan.')
    if tabs[2].open:
        with tabs[2]:
            from dataclasses import asdict,replace
            from cliplivre.composition import default_panels,validate_panel
            from cliplivre.controls import parse_clock,clock
            from cliplivre.crop_widget import crop_editor
            from cliplivre.playback import media_server
            import base64
            st.subheader('Editar y exportar')
            eligible=[c for c in candidates if c['state']!='descartado']
            if eligible:
                clip_labels={c['id']:f"Clip {i+1} · {clock(c['end']-c['start'])} · {c['title']}" for i,c in enumerate(eligible)}
                editor_key='editor_clip_'+sid
                if st.session_state.get(editor_key) not in clip_labels: st.session_state[editor_key]=eligible[0]['id']
                cid=st.selectbox('Clip',options=[c['id'] for c in eligible],index=None,format_func=clip_labels.__getitem__,key=editor_key)
                item=next(c for c in eligible if c['id']==cid); saved=item.get('edit_settings',{})
                with st.container(border=True):
                    st.caption('POSICIÓN DEL RECORTE')
                    preset_options=['Vertical','Dúo','Tres cuadros','Foto + clip']
                    layout_key='layout_'+cid
                    if layout_key not in st.session_state: st.session_state[layout_key]=item.get('layout','Vertical')
                    layout=st.radio('Diseño',preset_options,index=None,horizontal=True,key=layout_key,on_change=set_layout,args=(cid,))
                    a,b,c=st.columns([2,1,1]); count_key='panel_count_'+cid
                    expected_count={'Vertical':1,'Dúo':2,'Tres cuadros':3,'Foto + clip':2}[layout]
                    if count_key not in st.session_state: st.session_state[count_key]=expected_count
                    n=a.selectbox('Número de cuadros',[1,2,3],index=None,key=count_key,on_change=count_layout_changed,args=(cid,))
                    b.button('Añadir cuadro',disabled=n==3,on_click=change_panel_count,args=(cid,1),key='add_'+cid)
                    c.button('Quitar último cuadro',disabled=n==1,on_click=change_panel_count,args=(cid,-1),key='remove_'+cid)
                    aspect=st.selectbox('Formato',['9:16','1:1','16:9'],index=['9:16','1:1','16:9'].index(saved.get('aspect','9:16')))
                    crop_area=st.container()
                with st.container(border=True):
                    st.caption('INTERVALO DEL CLIP')
                    a,b=st.columns(2)
                    start_text=a.text_input('Inicio (min:seg)',value=precise_clock(item['start']),key='edit_start_'+cid)
                    end_text=b.text_input('Fin (min:seg)',value=precise_clock(item['end']),key='edit_end_'+cid)
                    try:
                        start=parse_clock(start_text); end=parse_clock(end_text)
                        if not 0<=start<end<=metadata['duration']+.01: raise ValueError('El intervalo debe quedar dentro del video.')
                    except ValueError as e: st.error(str(e)); st.stop()
                    timeline_key=f'timeline_{cid}_{start}_{end}'
                    st.slider('Barra de inicio y fin (min)',min_value=0.,max_value=float(metadata['duration']/60),value=(start/60,end/60),step=.001,key=timeline_key,on_change=sync_clip_timeline,args=(timeline_key,cid))
                    st.caption('Duración: '+clock(end-start)+' · el video original no se modifica.')
                    actual_source=store.settings(sid); configured_min=actual_source.get('clip_min',0); configured_max=actual_source.get('clip_max')
                    if end-start<configured_min-.01 or (configured_max is not None and end-start>configured_max+.01):
                        st.warning('Este cambio manual queda fuera del rango usado para generar. Puedes ajustarlo o conservarlo como edición manual.')
                all_words,audio_context=clip_context(str(store.db),sid,start,end,db_stamp())
                words=[dict(word,start=max(start,word['start']),end=min(end,word['end'])) for word in item.get('edited_words',all_words) if word['start']<end and word['end']>start]
                composition_key=f'composition_{cid}_{layout}_{n}_{aspect}'
                if composition_key not in st.session_state:
                    panels=default_panels(n)
                    if layout=='Foto + clip' and n==2: panels[0]['kind']='image'
                    for panel in panels:
                        d=panel['destination']; output_ratio=({'9:16':9/16,'1:1':1,'16:9':16/9}[aspect])*d[2]/d[3]
                        source_ratio=metadata['width']/metadata['height']
                        rw=min(1.,output_ratio/source_ratio); rh=min(1.,source_ratio/output_ratio)
                        panel['source']=[(1-rw)/2,(1-rh)/2,rw,rh]
                        if panel.get('kind')=='image': panel['source']=[0,0,1,1]; panel['fit']='contain'
                    if item.get('layout','Vertical')==layout and saved.get('panels') and len(saved['panels'])==n: panels=saved['panels']
                    st.session_state[composition_key]=panels
                panels=st.session_state[composition_key]
                photo_path=st.session_state.get('photo_'+cid,saved.get('photo_path'))
                logo_path=st.session_state.get('logo_'+cid,saved.get('logo_path'))
                if layout=='Foto + clip':
                    photo=st.file_uploader('Foto para el cuadro superior',type=['png','jpg','jpeg','webp'],key='photo_upload_'+cid)
                    if photo:
                        photo_path=save_image(photo); st.session_state['photo_'+cid]=photo_path
                    if not photo_path: st.info('Añade una foto para activar Foto + clip.')
                with st.container(border=True):
                    st.caption('TÍTULOS')
                    title=st.text_input('Nombre del clip',value=item['title'],key='title_'+cid)
                    titles_key='titles_'+cid
                    if titles_key not in st.session_state:
                        initial=saved.get('titles') or []
                        if not initial and saved.get('overlay_text'): initial=[dict(id=uuid.uuid4().hex,text=saved['overlay_text'],start=0.,end=end-start,x=saved.get('overlay_x',.5),y=saved.get('overlay_y',.15),size=saved.get('overlay_size',64),color='#'+saved.get('overlay_color','FFFFFF'))]
                        st.session_state[titles_key]=initial
                    a,b=st.columns(2)
                    a.button('＋ Añadir título',on_click=add_title,args=(titles_key,end-start),key='add_title_'+cid)
                    b.button('Quitar último título',disabled=not st.session_state[titles_key],on_click=remove_title,args=(titles_key,),key='remove_title_'+cid)
                    titles=[]
                    for i,track in enumerate(st.session_state[titles_key]):
                        tid=track.get('id',str(i))
                        with st.expander(f'Título {i+1}',expanded=True):
                            text=st.text_input('Texto',value=track.get('text',''),key='tt_'+tid)
                            a,b=st.columns(2)
                            begin=parse_clock(a.text_input('Desde (min:seg)',value=precise_clock(track.get('start',0)),key='ts_'+tid))
                            finish=parse_clock(b.text_input('Hasta (min:seg)',value=precise_clock(min(end-start,track.get('end',end-start))),key='te_'+tid))
                            a,b,c=st.columns(3)
                            tx=a.slider('Horizontal (%)',0,100,round(track.get('x',.5)*100),key='tx_'+tid)/100
                            ty=b.slider('Vertical (%)',0,100,round(track.get('y',.15)*100),key='ty_'+tid)/100
                            size=c.slider('Tamaño',24,120,int(track.get('size',64)),key='tz_'+tid)
                            color=st.color_picker('Color',value=track.get('color','#FFFFFF'),key='tc_'+tid)
                            st.button('Duplicar título',on_click=duplicate_title,args=(titles_key,i),key='duplicate_'+tid)
                            titles.append(dict(id=tid,text=text,start=begin,end=finish,x=tx,y=ty,size=size,color=color))
                    st.session_state[titles_key]=titles
                with st.expander('Logo del canal'):
                    logo=st.file_uploader('Añadir logo',type=['png','jpg','jpeg','webp'],key='logo_upload_'+cid+str(st.session_state.get('logo_revision_'+cid,0)))
                    if logo:
                        logo_path=save_image(logo); st.session_state['logo_'+cid]=logo_path
                    if logo_path:
                        st.image(logo_path,width=80)
                        st.button('Quitar logo',on_click=clear_logo,args=(cid,),key='clear_logo_'+cid)
                with st.expander('Subtítulos opcionales · puedes hacerlos en CapCut',expanded=False):
                    if st.session_state.pop('pending_burn_'+cid,False): st.session_state['burn_'+cid]=True
                    burn=st.checkbox('Mostrar subtítulos',value=False,key='burn_'+cid)
                    if st.button('Generar / actualizar subtítulos',key='generate_subs_'+cid):
                        try:
                            if not words:
                                from cliplivre.media import audio
                                from cliplivre.transcribe import transcribe
                                with st.spinner('Transcribiendo solo este clip…'):
                                    segments,meta=transcribe(audio(source['path'],start,end-start),'tiny','auto',None if actual_source.get('language')=='auto' else actual_source.get('language','es'))
                                words=[dict(w,start=w['start']+start,end=w['end']+start) for segment in segments for w in segment.get('words',[])]
                            if words:
                                item['edited_words']=words; store.update(cid,payload=item)
                                st.session_state['pending_burn_'+cid]=True; st.rerun()
                            else: st.info('No se detectaron palabras. Puedes escribirlas en Corregir texto.')
                        except Exception as e: st.error(str(e))
                    a,b,c=st.columns(3)
                    font=a.selectbox('Fuente',['Arial','Verdana','DejaVu Sans'],index=['Arial','Verdana','DejaVu Sans'].index(saved.get('font','Arial')))
                    sub_color=b.color_picker('Color de palabra activa','#'+saved.get('color','FFFF00'))
                    position=c.selectbox('Posición de subtítulos',['Abajo','Centro','Arriba'],index={2:0,5:1,8:2}[saved.get('subtitle_position',2)])
                    sub_size=st.slider('Tamaño de subtítulos',24,90,saved.get('font_size',54))
                    animated=st.checkbox('Animar subtítulos',value=saved.get('animated',True))
                    with st.expander('Corregir texto y sincronización fina'):
                        st.caption('Marcas de palabra en segundos; los intervalos principales usan min:seg.')
                        edited=st.data_editor(words or [dict(start=start,end=min(end,start+1),text='')],num_rows='dynamic',key='words_'+cid,width='stretch')
                with st.expander('Más ajustes de encuadre y efectos'):
                    resolution=st.selectbox('Resolución base',[1080,720,360],index=[1080,720,360].index(saved.get('resolution',1080)))
                    encoder=st.selectbox('Codificador',['auto','cpu','nvidia'],index=['auto','cpu','nvidia'].index(saved.get('encoder','auto')),format_func=lambda x:{'auto':'Automático: NVIDIA si pasa la prueba','cpu':'CPU','nvidia':'Probar NVIDIA; CPU si falla'}[x])
                    st.caption('Encuadre fijo y zoom desactivado inicialmente. NVENC acelera la codificación cuando funciona; los filtros aún usan CPU.')
                    framing=st.selectbox('Encuadre',['paneles','ajustar','centro','rostros','streamer'],format_func=lambda f:{'paneles':'Cuadros arrastrables','ajustar':'Todo con bandas','centro':'Recortar al centro','rostros':'Seguimiento aproximado de rostros','streamer':'Gameplay + cámara'}[f])
                    cx=st.slider('Centro horizontal',0.,1.,.5); cy=st.slider('Centro vertical',0.,1.,.5)
                    roi=None
                    if framing=='streamer':
                        cols=st.columns(4)
                        roi=tuple(cols[i].number_input(label,0.,1.,float(v),.01,key=f'roi_{cid}_{i}') for i,(label,v) in enumerate(zip(['X cámara','Y cámara','Ancho cámara','Alto cámara'],[0.,0.,.25,.3])))
                    numeric=st.checkbox('Ajustar cuadros por números',value=False)
                    if numeric:
                        for i,panel in enumerate(panels):
                            with st.expander(f'Cuadro {i+1}: números'):
                                for field in ['source','destination']:
                                    cols=st.columns(4); vals=[]
                                    for j,label in enumerate(['X','Y','Ancho','Alto']):
                                        vals.append(cols[j].number_input(field+' '+label,0. if j<2 else .01,.99 if j<2 else 1.,float(panel[field][j]),.01,key=f'num_{composition_key}_{field}_{i}_{j}') )
                                    x,y,w,h=vals; panel[field]=[x,y,min(w,1-x),min(h,1-y)]
                    zoom=st.slider('Zoom suave máximo',1.,1.2,float(saved.get('zoom',1.)),.01)
                    fade=st.checkbox('Fundidos de entrada y salida',value=saved.get('fade',False))
                    reduce=st.checkbox('Reducir silencios (revisar contexto)',value=False)
                with crop_area:
                    from cliplivre.render import dimensions
                    from cliplivre.media import clip_preview
                    preview_end=min(end,start+120)
                    editor_preview=clip_preview(source['path'],start,preview_end,ROOT/'vistas_previas')
                    source_image=cached_frame(str(editor_preview),max(0,min(.2,preview_end-start-.01)),editor_preview.stat().st_mtime_ns)
                    def image_data(path): return 'data:image/png;base64,'+base64.b64encode(Path(path).read_bytes()).decode() if path and Path(path).is_file() else None
                    revision_key='crop_revision_'+composition_key
                    crop=crop_editor(source_image,panels,aspect,video_url=media_server().url(editor_preview),start=0,end=preview_end-start,time_origin=start,configuration=composition_key,words=words,burn=burn,subtitle_color=sub_color,subtitle_size=sub_size,subtitle_position={'Abajo':2,'Centro':5,'Arriba':8}[position],revision=st.session_state.get(revision_key,0),photo=image_data(photo_path) if layout=='Foto + clip' else None,logo=image_data(logo_path),titles=titles,key='crop_'+cid)
                    if crop and crop.get('configuration')==composition_key and crop.get('revision',0)>st.session_state.get(revision_key,0):
                        new_panels=crop.get('panels',[])
                        if len(new_panels)==n:
                            for panel in new_panels: validate_panel(panel)
                            panels=new_panels; st.session_state[composition_key]=panels; st.session_state[revision_key]=crop['revision']
                    if preview_end<end: st.caption('Vista previa de los primeros 2 minutos. La descarga conserva todo el intervalo elegido.')
                    st.caption('Vista interactiva inmediata. Para comprobar cortes, animación y el resultado exacto, usa Vista previa editada.')
                export_speed=st.selectbox('Velocidad de exportación',['Rápida','Equilibrada','Mayor compresión'],index=['ultrafast','veryfast','medium'].index(saved.get('preset','ultrafast')) if saved.get('preset','ultrafast') in ['ultrafast','veryfast','medium'] else 0)
                st.caption('Rápida reduce la espera y genera archivos más grandes. No cambia la resolución elegida.')
                edit=Edit(aspect=aspect,resolution=resolution,framing=framing,center_x=cx,center_y=cy,zoom=zoom,fade=fade,burn=burn,animated=animated,font=font,font_size=sub_size,color=sub_color.lstrip('#'),subtitle_position={'Abajo':2,'Centro':5,'Arriba':8}[position],streamer_roi=roi,panels=panels,photo_path=photo_path if layout=='Foto + clip' else None,logo_path=logo_path,titles=titles,encoder=encoder,preset={'Rápida':'ultrafast','Equilibrada':'veryfast','Mayor compresión':'medium'}[export_speed])
                missing_photo=layout=='Foto + clip' and not photo_path
                if st.button('Guardar revisión y configuración',disabled=missing_photo):
                    try:
                        checked=[]
                        for word in edited:
                            if word['text']:
                                if not start<=float(word['start'])<float(word['end'])<=end: raise ValueError('La palabra debe quedar dentro del clip.')
                                checked.append(dict(start=float(word['start']),end=float(word['end']),text=str(word['text'])))
                        item.update(start=start,end=end,title=title,edited_words=checked,edit_settings=asdict(edit),layout=layout)
                        store.update(cid,payload=item); st.success('Guardado.')
                    except Exception as e: st.error(str(e))
                status=st.empty()
                def make(candidate,settings,preview_mode=False):
                    selected_words=candidate.get('edited_words',words)
                    candidate_audio=clip_context(str(store.db),sid,candidate['start'],candidate['end'],db_stamp())[1] if reduce else []
                    cuts=silent_intervals(candidate_audio,candidate['start'],candidate['end']) if reduce else []
                    fingerprint=hashlib.sha256(json.dumps(dict(source=sid,start=candidate['start'],end=candidate['end'],words=selected_words,edit=asdict(settings),cuts=cuts),sort_keys=True).encode()).hexdigest()
                    manifest=ROOT/'vistas_previas'/('edited_'+fingerprint+'.json'); manifest.parent.mkdir(exist_ok=True)
                    if preview_mode and manifest.exists():
                        output=Path(json.loads(manifest.read_text())['path'])
                        if output.exists(): return output
                    output=render(source['path'],candidate['start'],candidate['end'],selected_words,ROOT/'editados',settings,cuts,lambda m:status.info(m))
                    if preview_mode: manifest.write_text(json.dumps(dict(path=str(output))))
                    return output
                if st.button('Generar vista previa editada',disabled=missing_photo):
                    try:
                        with st.spinner('Generando el resultado exacto del clip…'):
                            result=make(dict(item,start=start,end=end,edited_words=list(edited)),replace(edit,resolution=360,preset='ultrafast'),True)
                        st.session_state['preview'+cid]=str(result)
                    except Exception as e: st.error(str(e))
                if st.session_state.get('preview'+cid): direct_player(st.session_state['preview'+cid])
                from cliplivre.downloads import edited_clip
                download_settings=asdict(replace(edit,burn=False))
                download_cuts=silent_intervals(audio_context,start,end) if reduce else []
                def download_edit(path=source['path'],begin=start,finish=end,root=ROOT,settings=json.dumps(download_settings),cuts=json.dumps(download_cuts),candidate_id=cid,jobs=progress_jobs):
                    task=jobs.new('Preparando descarga editada')
                    try:
                        selected=json.loads(settings)
                        output=edited_clip(path,begin,finish,root,selected,[],json.loads(cuts),progress=task.update)
                        Store(root).export(candidate_id,output,selected)
                        data=output.read_bytes();task.finish('MP4 editado listo para descargar');return data
                    except Exception as e:task.fail(e);raise
                st.download_button('Descargar MP4 editado · sin subtítulos',data=download_edit,file_name=f'clip_{cid[:8]}_editado.mp4',mime='video/mp4',key='download_edit_'+cid,on_click='ignore',type='primary',disabled=missing_photo,width='stretch')
                st.caption('Descarga directa para CapCut. Se prepara al pulsar; conserva audio, cuadros, textos y logo. Sin subtítulos.')
                if st.button('Exportar clip con estos ajustes',disabled=missing_photo,width='stretch'):
                    try:
                        with st.spinner('Exportando…'): result=make(dict(item,start=start,end=end,edited_words=list(edited)),edit)
                        store.export(cid,result,asdict(edit)); st.session_state['export'+cid]=str(result)
                    except Exception as e: st.error(str(e))
                if st.session_state.get('export'+cid):
                    result=Path(st.session_state['export'+cid]); st.success(str(result)); direct_player(str(result))
                    for name in ['editado.mp4','subtitulos.srt','subtitulos.ass','texto.ass','titulos.ass','edicion.json']:
                        p=result.parent/name
                        if p.exists(): st.download_button('Descargar '+name,p.read_bytes(),file_name=name,key=str(p))
                accepted=[c for c in eligible if c['state']=='aceptado']
                if st.button(f'Exportar lote de {len(accepted)} clips aceptados',disabled=not accepted or missing_photo):
                    for candidate in accepted:
                        try:
                            batch_words,_=clip_context(str(store.db),sid,candidate['start'],candidate['end'],db_stamp())
                            result=make(dict(candidate,edited_words=candidate.get('edited_words',batch_words)),edit)
                            store.export(candidate['id'],result,asdict(edit)); st.success(str(result))
                        except Exception as e: st.error(str(e))
            else: st.info('Elige un clip en Clips para editarlo.')

else:
    for tab in tabs[1:]:
        with tab: st.info('Importa un video y selecciona un proyecto en la biblioteca.')
