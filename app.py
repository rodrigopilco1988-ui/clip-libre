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

tabs=st.tabs(['1 · Crear clips','2 · Configurar análisis','3 · Mis clips','4 · Editor y exportación'])
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
            initial_model=a.selectbox('Calidad de transcripción',['small','tiny','base','medium'])
            initial_language=b.selectbox('Idioma del contenido',['es','en','auto'])
            st.caption('Small ofrece equilibrio. Tiny reduce el tiempo de espera. Se procesa un primer bloque de hasta 50 minutos; puedes continuar desde Configurar análisis.')
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
                        report=analyze(store,new_sid,Analysis(model=initial_model,language='' if initial_language=='auto' else initial_language),initial_progress,max_blocks=1)
                        for warning in report['warnings']: st.warning(warning)
                    status.update(label='Tu proyecto está listo',state='complete')
                st.session_state['pending_project']=new_sid
                st.session_state['import_notice']='Contenido listo. Abre Mis clips para revisar tus propuestas.' if automatic else 'Contenido importado. Abre Configurar análisis para generar tus clips.'
                st.rerun()
            except Exception as e: st.error(str(e))
    if st.session_state.get('import_notice'): st.success(st.session_state.pop('import_notice'))
    st.caption('1. Añade contenido   →   2. Genera clips   →   3. Revisa y edita   →   4. Exporta')

if sid:
    source=store.source(sid); metadata=probe(source['path'])
    with tabs[1]:
        st.subheader('Análisis incremental')
        st.write(f"Duración: {metadata['duration']/60:.1f} min · {metadata['width']} × {metadata['height']}")
        a,b,c=st.columns(3)
        model=a.selectbox('Modelo Whisper',['tiny','base','small','medium'],index=2)
        device=b.selectbox('Procesador',['auto','cpu','cuda'])
        block=c.number_input('Minutos por bloque',min_value=1,max_value=120,value=50)
        language=st.selectbox('Idioma',['es','en','auto'])
        a,b=st.columns(2)
        min_s=a.number_input('Duración mínima propuesta (s)',5,120,12)
        max_s=b.number_input('Duración máxima propuesta (s)',5,180,60)
        use_ollama=st.checkbox('Clasificar con Ollama local (opcional)')
        ollama_model=st.text_input('Modelo Ollama',value='qwen3:4b')
        st.caption('Whisper se descarga y libera antes de usar Ollama. Detén otros modelos GPU para conservar VRAM. Ollama no recibe imágenes; recibe transcripción.')
        max_blocks=st.number_input('Bloques por revisión (0 = todos)',min_value=0,max_value=100,value=1)
        if st.button('Analizar minutos pendientes',type='primary'):
            progress=st.progress(0.); status=st.empty()
            def update(f,m): progress.progress(min(1.,max(0.,f))); status.info(m)
            try:
                report=analyze(store,sid,Analysis(block_minutes=block,model=model,device=device,language='' if language=='auto' else language,ollama=use_ollama,ollama_model=ollama_model,min_seconds=min_s,max_seconds=max_s),update,max_blocks=max_blocks or None)
                st.success(f"Completado: {report['blocks']} bloques nuevos en {report['elapsed_seconds']:.1f} s. RAM muestreada: {report['rss_sampled_mb']:.0f} MB.")
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
                    st.caption(f"{item['start']:.1f}–{item['end']:.1f} s · {item['end']-item['start']:.0f} segundos · {item['state']}")
                    st.write(item['reason'])
                    if st.button('Ver clip',key='view'+item['id']): st.session_state['view'+item['id']]=True
                    if st.session_state.get('view'+item['id']): show_clip(source['path'],item['start'],item['end'])
                    a,b=st.columns(2)
                    if a.button('Aceptar',key='accept'+item['id']): store.update(item['id'],state='aceptado'); st.rerun()
                    if b.button('Descartar',key='reject'+item['id']): store.update(item['id'],state='descartado'); st.rerun()
                    with st.expander('Por qué se propuso este clip'):
                        st.write('Gancho sugerido:',item.get('hook',''))
                        st.caption(f"Método: {item['classification']} · muestras visuales: {item['visual_samples']}")
        if not candidates: st.info('Analiza el video para generar propuestas. No se fuerza un número fijo de clips.')
    with tabs[3]:
        st.subheader('Editor y exportación')
        eligible=[c for c in candidates if c['state']!='descartado']
        if eligible:
            cid=st.selectbox('Clip',options=[c['id'] for c in eligible],format_func=lambda k:next(c['title'] for c in eligible if c['id']==k))
            item=next(c for c in eligible if c['id']==cid)
            show_clip(source['path'],item['start'],item['end'])
            a,b=st.columns(2)
            start=a.number_input('Inicio (segundos)',min_value=0.,max_value=metadata['duration'],value=float(item['start']),key='start'+cid)
            end=b.number_input('Final (segundos)',min_value=0.,max_value=metadata['duration'],value=float(item['end']),key='end'+cid)
            title=st.text_input('Título',value=item['title'],key='title'+cid)
            # Recupera todas las palabras para admitir la ampliación del intervalo.
            with store.connect() as c:
                payloads=[json.loads(r[0]) for r in c.execute('SELECT payload FROM chunks WHERE source=? ORDER BY start',(sid,))]
            all_words=[]; seen=set()
            for p in payloads:
                for seg in p['segments']:
                    for w in seg.get('words',[]):
                        k=(round(w['start'],2),round(w['end'],2))
                        if k not in seen: all_words.append(w); seen.add(k)
            saved=item.get('edited_words')
            words=saved if saved is not None else [w for w in all_words if start<=w['start']<end]
            st.caption('Corrige texto y tiempos absolutos. Añade filas si el modelo no generó palabras.')
            edited=st.data_editor(words or [{'start':float(start),'end':float(min(end,start+1)),'text':''}],num_rows='dynamic',key='words'+cid,use_container_width=True)
            if st.button('Guardar revisión'):
                try:
                    if not 0<=start<end<=metadata['duration']: raise ValueError('Intervalo inválido.')
                    checked=[]
                    for w in edited:
                        if w['text'] and not start<=float(w['start'])<float(w['end'])<=end: raise ValueError('Cada palabra debe estar dentro del clip.')
                        if w['text']: checked.append(dict(start=float(w['start']),end=float(w['end']),text=str(w['text'])))
                    item.update(start=start,end=end,title=title,edited_words=checked)
                    store.update(cid,payload=item); st.success('Revisión guardada.')
                except Exception as e: st.error(str(e))
            template=st.selectbox('Plantilla',['Limpia','Dinámica','Gameplay + cámara'])
            a,b,c=st.columns(3)
            aspect=a.selectbox('Formato',['9:16','1:1','16:9'])
            resolution=b.selectbox('Resolución base',[1080,720,360])
            framing=c.selectbox('Encuadre',['ajustar','centro','rostros','streamer'],index=3 if template=='Gameplay + cámara' else 0)
            st.caption('Rostros: detección y seguimiento aproximado; no identifica personas ni determina el hablante. Cámara: confirma la región antes de exportar.')
            a,b=st.columns(2)
            cx=a.slider('Centro horizontal',0.,1.,.5); cy=b.slider('Centro vertical',0.,1.,.5)
            roi=None
            if framing=='streamer':
                from cliplivre.signals import visual_features
                if st.button('Sugerir región de cámara por rostros'):
                    frames=visual_features(source['path'],start,min(end,start+10),1.)
                    boxes=[r for f in frames for r in f['faces'] if (r[0]<.3 or r[0]>.65) and (r[1]<.3 or r[1]>.6)]
                    if boxes:
                        x,y,w,h=boxes[0]; x=max(0,x-w); y=max(0,y-h*.5); w=min(1-x,w*3); h=min(1-y,h*2.5)
                        st.session_state['roi'+cid]=(x,y,w,h)
                    else: st.warning('No se encontró un rostro en una esquina. Define la cámara manualmente.')
                defaults=st.session_state.get('roi'+cid,(0.,0.,.25,.3))
                cols=st.columns(4)
                roi=tuple(cols[i].number_input(label,0.,1.,float(defaults[i]),.01,key=f'roi{cid}{i}{defaults}') for i,label in enumerate(['X cámara','Y cámara','Ancho cámara','Alto cámara']))
            zoom=st.slider('Zoom suave máximo',1.,1.2,1.08 if template=='Dinámica' else 1.,.01)
            fade=st.checkbox('Fundidos de entrada y salida',value=template=='Dinámica')
            reduce=st.checkbox('Reducir silencios (máximo 0,8 s por pausa; revisar contexto)')
            burn=st.checkbox('Incrustar subtítulos',value=True)
            animated=st.checkbox('Animar subtítulos',value=template=='Dinámica')
            a,b,c=st.columns(3)
            font=a.selectbox('Fuente',['Arial','Verdana','DejaVu Sans'])
            color=b.color_picker('Color de palabra activa','#FFFF00')
            position=c.selectbox('Posición',['Abajo','Centro','Arriba'])
            size=st.slider('Tamaño de fuente (base 1080)',24,90,54)
            edit=Edit(aspect=aspect,resolution=resolution,framing=framing,center_x=cx,center_y=cy,zoom=zoom,fade=fade,burn=burn,animated=animated,font=font,font_size=size,color=color.lstrip('#'),subtitle_position={'Abajo':2,'Centro':5,'Arriba':8}[position],streamer_roi=roi)
            def make(candidate,settings):
                selected_words=candidate.get('edited_words')
                if selected_words is None: selected_words=[w for w in all_words if candidate['start']<=w['start']<candidate['end']]
                cuts=[]
                if reduce:
                    feats=[f for p in payloads for f in p['audio']]
                    cuts=silent_intervals(feats,candidate['start'],candidate['end'])
                return render(source['path'],candidate['start'],candidate['end'],selected_words,ROOT/'editados',settings,cuts,lambda m:status.info(m))
            status=st.empty()
            if st.button('Generar vista previa editada'):
                try:
                    from dataclasses import replace
                    candidate=dict(item,start=start,end=end,edited_words=list(edited))
                    with st.spinner('Renderizando vista previa…'): result=make(candidate,replace(edit,resolution=360,preset='ultrafast'))
                    st.session_state['preview'+cid]=str(result)
                except Exception as e: st.error(str(e))
            if st.session_state.get('preview'+cid): st.video(st.session_state['preview'+cid])
            st.caption('La vista previa es un render real. Si cambias ajustes, genérala de nuevo antes de exportar.')
            if st.button('Exportar clip con estos ajustes',type='primary'):
                try:
                    with st.spinner('Exportando…'): result=make(dict(item,start=start,end=end,edited_words=list(edited)),edit)
                    store.export(cid,result,edit.__dict__); st.session_state['export'+cid]=str(result)
                except Exception as e: st.error(str(e))
            if st.session_state.get('export'+cid):
                result=Path(st.session_state['export'+cid]); st.success(str(result)); st.video(str(result))
                for name in ['editado.mp4','subtitulos.srt','subtitulos.ass','edicion.json']:
                    p=result.parent/name
                    st.download_button('Descargar '+name,p.read_bytes(),file_name=name,key=str(p))
            accepted=[c for c in eligible if c['state']=='aceptado']
            st.caption('Lotes: aplica los ajustes actuales a los clips aceptados; usa las correcciones de palabras guardadas.')
            if st.button(f'Exportar lote de {len(accepted)} clips aceptados',disabled=not accepted):
                for candidate in accepted:
                    try:
                        result=make(candidate,edit); store.export(candidate['id'],result,edit.__dict__); st.success(str(result))
                    except Exception as e: st.error(f"{candidate['title']}: {e}")
        else: st.info('Primero analiza un video y revisa sus candidatos.')
else:
    for tab in tabs[1:]:
        with tab: st.info('Importa un video y selecciona un proyecto en la biblioteca.')
