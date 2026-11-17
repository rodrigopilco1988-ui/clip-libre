from pathlib import Path
from dataclasses import dataclass, asdict
import json
import math
import uuid
from functools import lru_cache
from .media import probe, run
from .subtitles import map_words, write, overlay
from .composition import geometry,validate_panel
from .signals import visual_features


@lru_cache(maxsize=1)
def filter_file_option():
    # FFmpeg reciente eliminó -filter_complex_script; -/filter_complex carga
    # el argumento desde archivo y evita el límite de línea de comandos de Windows.
    help_text = run(['ffmpeg', '-hide_banner', '-h', 'full'], timeout=30)
    return '-filter_complex_script' if b'-filter_complex_script' in help_text else '-/filter_complex'

@dataclass
class Edit:
    aspect: str = '9:16'
    resolution: int = 1080
    framing: str = 'ajustar'
    center_x: float = .5
    center_y: float = .5
    zoom: float = 1.0
    fade: bool = False
    burn: bool = True
    animated: bool = True
    font: str = 'Arial'
    font_size: int = 54
    color: str = 'FFFF00'
    subtitle_position: int = 2
    preset: str = 'veryfast'
    streamer_roi: tuple | None = None
    panels: list | None = None
    overlay_text: str = ''
    overlay_size: int = 64
    overlay_color: str = 'FFFFFF'
    overlay_x: float = .5
    overlay_y: float = .15
    photo_path: str | None = None
    logo_path: str | None = None
    titles: list | None = None
    encoder: str = 'auto'


def retained(start,end,cuts):
    if not 0<=start<end: raise ValueError('Inicio y final inválidos.')
    cursor=start; out=[]
    for a,b in sorted(cuts):
        a,b=max(start,a),min(end,b)
        if b<=cursor: continue
        if a>cursor: out.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<end: out.append((cursor,end))
    if not out: raise ValueError('Los cortes eliminarían todo el clip.')
    return out


def dimensions(aspect,resolution):
    if aspect not in {'9:16','1:1','16:9'} or resolution not in {360,720,1080}:
        raise ValueError('Formato o resolución no admitidos.')
    if aspect=='9:16': return resolution,round(resolution*16/9)//2*2
    if aspect=='1:1': return resolution,resolution
    return round(resolution*16/9)//2*2,resolution


def face_track(frames,intervals):
    """Centro estable: ignora temblores pequeños y limita desplazamiento por segundo."""
    points=[(0.,.5)]; offset=0.; last=.5; previous_time=0.
    for a,b in intervals:
        for f in frames:
            if a<=f['time']<b and f['faces']:
                t=offset+f['time']-a
                face=min(f['faces'],key=lambda r:abs(r[0]+r[2]/2-last))
                target=face[0]+face[2]/2
                delta=target-last
                if abs(delta)>.035:
                    step=.025*min(2.,max(0.,t-previous_time))
                    last+=max(-step,min(step,delta*.3))
                if t>points[-1][0]: points.append((t,last))
                previous_time=t
        offset+=b-a
    return points


def face_expression(frames,intervals,width):
    points=face_track(frames,intervals)
    points=points[:120]
    if not points: return '(iw-ow)/2'
    expr=str(round(points[-1][1],4))
    for (t,x),(t2,x2) in reversed(list(zip(points,points[1:]))):
        if t2<=t: continue
        expr=f'if(lt(t,{t2:.3f}),{x:.4f}+({x2-x:.4f})*clip((t-{t:.3f})/{t2-t:.3f},0,1),{expr})'
    return f'max(0,min(iw-ow,iw*({expr})-ow/2))'


def render(path,start,end,words,output_root,edit=None,cuts=(),progress=lambda _:None):
    edit=edit or Edit(); info=probe(path)
    if end>info['duration']+.1: raise ValueError('El final excede la duración del video.')
    if not 1<=edit.zoom<=1.2: raise ValueError('El zoom debe estar entre 1 y 1,2.')
    if not 0<=edit.center_x<=1 or not 0<=edit.center_y<=1: raise ValueError('Centro fuera de rango.')
    if edit.framing not in {'ajustar','centro','rostros','streamer','paneles'}: raise ValueError('Encuadre inválido.')
    intervals=retained(start,end,cuts)
    w,h=dimensions(edit.aspect,edit.resolution)
    target=Path(output_root).resolve()/('clip_'+uuid.uuid4().hex[:12]); target.mkdir(parents=True)
    # Filtros ASS usan ruta relativa segura; funciona también con unidades C: en Windows.
    relative_words=map_words(words,intervals)
    srt,ass=write(relative_words,target/'subtitulos',w,h,edit.font,round(edit.font_size*w/1080),edit.color,edit.subtitle_position,edit.animated)
    graph=[]
    for i,(a,b) in enumerate(intervals):
        graph.append(f'[0:v]trim=start={a-start:.6f}:end={b-start:.6f},setpts=PTS-STARTPTS[v{i}]')
        if info['audio']: graph.append(f'[0:a]atrim=start={a-start:.6f}:end={b-start:.6f},asetpts=PTS-STARTPTS[a{i}]')
    inputs=''.join(f'[v{i}]'+(f'[a{i}]' if info['audio'] else '') for i in range(len(intervals)))
    graph.append(inputs+f'concat=n={len(intervals)}:v=1:a={int(info["audio"])}[joined]'+('[sound]' if info['audio'] else ''))
    frame='[joined]'
    if edit.framing=='paneles':
        panels=edit.panels
        if not panels or not 1<=len(panels)<=3: raise ValueError('Elige entre uno y tres cuadros.')
        single=len(panels)==1 and panels[0].get('kind')!='image' and geometry(panels[0],w,h)==(0,0,w,h)
        if single:
            panel=panels[0]; validate_panel(panel)
            sx,sy,sw,sh=panel['source']
            fit=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}' if panel.get('fit','cover')=='cover' else f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2'
            graph.append(f'{frame}crop=iw*{sw}:ih*{sh}:iw*{sx}:ih*{sy},{fit},setsar=1[framed]')
        else:
            video_panels=[i for i,p in enumerate(panels) if p.get('kind')!='image']
            graph.append(frame+f'split={len(video_panels)+1}[canvas_source]'+''.join(f'[panel{i}]' for i in video_panels))
            graph.append(f'[canvas_source]scale={w}:{h},drawbox=color=black:t=fill,setsar=1[canvas0]')
            for i,panel in enumerate(panels):
                validate_panel(panel)
                sx,sy,sw,sh=panel['source']; dx,dy,dw,dh=geometry(panel,w,h)
                if panel.get('fit','cover')=='cover': fit=f'scale={dw}:{dh}:force_original_aspect_ratio=increase,crop={dw}:{dh}'
                else: fit=f'scale={dw}:{dh}:force_original_aspect_ratio=decrease,pad={dw}:{dh}:(ow-iw)/2:(oh-ih)/2'
                panel_input='[1:v]' if panel.get('kind')=='image' else f'[panel{i}]'
                if panel.get('kind')=='image' and not edit.photo_path: raise ValueError('Añade una foto para Foto + clip.')
                graph.append(f'{panel_input}crop=iw*{sw}:ih*{sh}:iw*{sx}:ih*{sy},{fit},setsar=1[layer{i}]')
                graph.append(f'[canvas{i}][layer{i}]overlay=x={dx}:y={dy}:shortest=1[canvas{i+1}]')
            graph.append(f'[canvas{len(panels)}]null[framed]')
    elif edit.framing=='streamer':
        roi=edit.streamer_roi
        if not roi or len(roi)!=4 or any(not 0<=v<=1 for v in roi) or roi[2]<=0 or roi[3]<=0 or roi[0]+roi[2]>1 or roi[1]+roi[3]>1:
            raise ValueError('Define una región válida para la cámara (x, y, ancho, alto).')
        x,y,rw,rh=roi; top=(h//3)//2*2; bottom=h-top
        graph.append(f'{frame}split=2[game][cam]')
        graph.append(f'[cam]crop=iw*{rw}:ih*{rh}:iw*{x}:ih*{y},scale={w}:{top}:force_original_aspect_ratio=increase,crop={w}:{top}[camera]')
        graph.append(f'[game]scale={w}:{bottom}:force_original_aspect_ratio=decrease,pad={w}:{bottom}:(ow-iw)/2:(oh-ih)/2[gameplay]')
        graph.append('[camera][gameplay]vstack=inputs=2[framed]')
    elif edit.framing=='ajustar':
        graph.append(f'{frame}scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[framed]')
    else:
        x=f'(iw-ow)*{edit.center_x}'; y=f'(ih-oh)*{edit.center_y}'
        if edit.framing=='rostros':
            progress('Muestreando rostros para el encuadre…')
            frames=visual_features(path,start,end,step=.8)
            if not any(f['faces'] for f in frames):
                progress('Sin rostros detectados: se usará el centro configurado.')
            else: x=face_expression(frames,intervals,w)
        graph.append(f"{frame}scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:x='{x}':y='{y}'[framed]")
    filters=['setsar=1','fps=30']
    if edit.zoom>1:
        # Zoom oscilante suave con centro estable, sin generación de imágenes.
        filters.append(f"zoompan=z='1+{edit.zoom-1:.4f}*(1-cos(on/90))/2':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps=30")
    duration=sum(b-a for a,b in intervals)
    if edit.fade: filters.extend(['fade=t=in:st=0:d=0.2',f'fade=t=out:st={max(0,duration-.2):.4f}:d=0.2'])
    if edit.burn and relative_words: filters.append('ass=subtitulos.ass')
    if edit.overlay_text.strip():
        overlay(edit.overlay_text,target/'texto.ass',duration,w,h,edit.font,round(edit.overlay_size*w/1080),edit.overlay_color,edit.overlay_x,edit.overlay_y)
        filters.append('ass=texto.ass')
    if edit.titles:
        from .subtitles import titles_ass
        titles_ass(edit.titles,target/'titulos.ass',duration,w,h,edit.font)
        filters.append('ass=titulos.ass')
    graph.append('[framed]'+','.join(filters)+('[before_logo]' if edit.logo_path else '[final]'))
    if edit.logo_path:
        logo_index=2 if edit.photo_path else 1
        graph.append(f'[{logo_index}:v]scale={max(2,round(w*.17)//2*2)}:-2[logo]')
        graph.append('[before_logo][logo]overlay=x=W*0.79:y=H*0.03:shortest=1[final]')
    script=target/'filters.txt'; script.write_text(';\n'.join(graph),encoding='utf-8')
    cmd=['ffmpeg','-v','error','-y','-threads','2','-ss',str(start),'-t',str(end-start),'-i',str(Path(path).resolve())]
    if edit.photo_path: cmd+=['-loop','1','-i',str(Path(edit.photo_path).resolve())]
    if edit.logo_path: cmd+=['-loop','1','-i',str(Path(edit.logo_path).resolve())]
    cmd+=['-filter_complex_threads','1',filter_file_option(),str(script),'-map','[final]']
    if info['audio']: cmd+=['-map','[sound]','-c:a','aac','-b:a','160k']
    from .encoding import choose_encoder,encoder_options
    encoder=choose_encoder(edit.encoder)
    base_cmd=list(cmd)
    ending=['-pix_fmt','yuv420p','-movflags','+faststart',str(target/'editado.mp4')]
    cmd=base_cmd+encoder_options(encoder,edit.preset)+ending
    progress('Exportando con NVIDIA NVENC…' if encoder=='h264_nvenc' else 'Exportando en CPU con FFmpeg…')
    # Cambiar cwd global rompería otros trabajos; subprocess aislado.
    import subprocess
    try:
        p=subprocess.run(cmd,cwd=target,capture_output=True,timeout=max(7200,int(duration*8+600)))
        if p.returncode and encoder=='h264_nvenc':
            progress('NVENC no pudo exportar este clip; reintentando en CPU…')
            (target/'editado.mp4').unlink(missing_ok=True)
            encoder='libx264'
            p=subprocess.run(base_cmd+encoder_options(encoder,edit.preset)+ending,cwd=target,capture_output=True,timeout=max(7200,int(duration*8+600)))
        if p.returncode: raise RuntimeError(p.stderr.decode('utf-8',errors='replace')[-3500:])
    except Exception:
        (target/'editado.mp4').unlink(missing_ok=True)
        raise
    (target/'edicion.json').write_text(json.dumps(dict(edit=asdict(edit),intervals=intervals,source=str(path),encoder_used=encoder),ensure_ascii=False,indent=2),encoding='utf-8')
    progress('Exportación terminada.')
    return target/'editado.mp4'
