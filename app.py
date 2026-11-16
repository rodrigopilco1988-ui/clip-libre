from pathlib import Path
import json
import uuid
import os
import streamlit as st
from cliplivre.store import Store
from cliplivre.sources import import_local,import_url,EXTENSIONS
from cliplivre.pipeline import Analysis,analyze
from cliplivre.render import Edit,render
from cliplivre.media import probe,preview
from cliplivre.signals import silent_intervals

ROOT=Path(os.environ.get('CLIP_LIBRE_DATA',str(Path(__file__).resolve().parent/'data')))
st.set_page_config(page_title='Clip Libre',page_icon='🎞️',layout='wide')
store=Store(ROOT)
st.title('Clip Libre')
st.caption('Video largo → momentos revisables → clips editados. Procesamiento local; tú decides qué compartir.')

with st.sidebar:
    st.header('Tu biblioteca')
    sources=store.sources()
    sid=st.selectbox('Proyecto',options=[s['id'] for s in sources],format_func=lambda k:next(s['name'] for s in sources if s['id']==k)) if sources else None
    st.caption('Originales y exportaciones se guardan separados dentro de data/.')
    st.caption('Los modelos se descargan la primera vez. Después pueden trabajar sin conexión.')
    with st.expander('Historial de trabajos'):
        with store.connect() as c:
            rows=[dict(r) for r in c.execute('SELECT state,message,updated FROM jobs ORDER BY updated DESC LIMIT 15')]
        for row in rows: st.write(row)

tabs=st.tabs(['1 · Importar','2 · Analizar','3 · Revisar','4 · Editar y exportar'])
with tabs[0]:
    st.subheader('Añade tu video')
    permission=st.checkbox('Tengo acceso permitido y permiso para procesar y reutilizar este contenido.')
    mode=st.radio('Fuente',['Archivo local','Enlace público'],horizontal=True)
    if mode=='Archivo local':
        st.caption('Para videos largos, pega la ruta de Windows. Evita cargar gigabytes en el navegador.')
        path=st.text_input('Ruta al archivo',placeholder=r'C:\Videos\grabacion.mkv')
        upload=st.file_uploader('O selecciona un archivo (máximo 200 MB)',type=[x[1:] for x in sorted(EXTENSIONS)])
        if st.button('Crear proyecto',disabled=not permission):
            try:
                if upload:
                    temp=ROOT/'temporales'; temp.mkdir(exist_ok=True)
                    p=temp/(uuid.uuid4().hex+Path(upload.name).suffix)
                    p.write_bytes(upload.getbuffer())
                    try: dest=import_local(p,ROOT,permission)
                    finally: p.unlink(missing_ok=True)
                    name=upload.name
                else:
                    dest=import_local(path,ROOT,permission); name=Path(path).name
                store.register(dest,name); st.success('Video importado. Selecciónalo en la biblioteca.'); st.rerun()
            except Exception as e: st.error(str(e))
    else:
        st.warning('YouTube/Twitch: integración experimental. No validada con directos reales. No usa cookies ni evita restricciones. El historial de un directo puede no estar disponible.')
        url=st.text_input('Enlace HTTPS')
        a,b=st.columns(2)
        remote_start=a.number_input('Desde el segundo',min_value=0,value=0)
        remote_end=b.number_input('Hasta el segundo',min_value=1,value=300)
        if st.button('Recuperar tramo permitido',disabled=not permission):
            try:
                with st.spinner('Recuperando segmento finito…'):
                    dest=import_url(url,ROOT,remote_start,remote_end,permission)
                store.register(dest,f'{url} [{remote_start}–{remote_end}s]'); st.rerun()
            except Exception as e: st.error(str(e))

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
        st.subheader('Candidatos para revisar')
        st.caption('La puntuación estima interés; no garantiza viralidad. Los títulos y motivos de IA requieren comprobarse en el video.')
        a,b,c=st.columns(3)
        threshold=a.slider('Puntuación mínima',0,100,0)
        states=b.multiselect('Estados',['pendiente','aceptado','descartado'],default=['pendiente','aceptado'])
        order=c.selectbox('Ordenar por',['Puntuación','Inicio'])
        items=[x for x in candidates if x['score']>=threshold and x['state'] in states]
        items.sort(key=lambda x:-x['score'] if order=='Puntuación' else x['start'])
        for item in items:
            with st.expander(f"{item['score']}/100 · {item['title']} · {item['start']:.1f}–{item['end']:.1f} s · {item['state']}"):
                st.write(item['reason']); st.caption(f"Método: {item['classification']} · muestras visuales: {item['visual_samples']}")
                st.write('Gancho sugerido:',item.get('hook',''))
                st.video(source['path'],start_time=item['start'],end_time=item['end'])
                a,b=st.columns(2)
                if a.button('Aceptar',key='accept'+item['id']): store.update(item['id'],state='aceptado'); st.rerun()
                if b.button('Descartar',key='reject'+item['id']): store.update(item['id'],state='descartado'); st.rerun()
        if not candidates: st.info('Analiza el video para generar propuestas. No se fuerza un número fijo de clips.')
    with tabs[3]:
        st.subheader('Editor y exportación')
        eligible=[c for c in candidates if c['state']!='descartado']
        if eligible:
            cid=st.selectbox('Clip',options=[c['id'] for c in eligible],format_func=lambda k:next(c['title'] for c in eligible if c['id']==k))
            item=next(c for c in eligible if c['id']==cid)
            st.video(source['path'],start_time=item['start'],end_time=item['end'])
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
