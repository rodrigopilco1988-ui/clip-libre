from pathlib import Path
import math


def timestamp(t, ass=False):
    unit=100 if ass else 1000
    n=max(0,round(t*unit)); seconds,frac=divmod(n,unit); minutes,sec=divmod(seconds,60); hour,minute=divmod(minutes,60)
    return f'{hour}:{minute:02}:{sec:02}.{frac:02}' if ass else f'{hour:02}:{minute:02}:{sec:02},{frac:03}'


def map_words(words, intervals):
    result=[]; offset=0.
    for a,b in intervals:
        for w in words:
            start,end=max(a,float(w['start'])),min(b,float(w['end']))
            if end>start:
                result.append(dict(start=offset+start-a,end=offset+end-a,text=str(w['text'])))
        offset+=b-a
    return sorted(result,key=lambda w:w['start'])


def phrases(words, max_words=6):
    group=[]
    for w in words:
        if group and (len(group)>=max_words or w['start']-group[-1]['end']>.7):
            yield group; group=[]
        group.append(w)
    if group: yield group


def ass_escape(text):
    return str(text).replace('\\','／').replace('{','（').replace('}','）').replace('\r',' ').replace('\n',' ')


def write(words, base, width=1080,height=1920,font='Arial',size=54,color='00FFFF',position=2,animated=True):
    if position not in {2,5,8}: raise ValueError('Posición de subtítulos inválida.')
    if len(color)!=6 or any(c not in '0123456789ABCDEFabcdef' for c in color): raise ValueError('Color inválido.')
    if not font.replace(' ','').replace('-','').isalnum(): raise ValueError('Fuente inválida.')
    base=Path(base); base.parent.mkdir(parents=True,exist_ok=True)
    groups=list(phrases(words)); srt=[]; events=[]
    # ASS usa BGR, el selector de UI entrega RGB.
    bgr=color[4:6]+color[2:4]+color[:2]
    for i,g in enumerate(groups,1):
        start,end=g[0]['start'],g[-1]['end']
        text=' '.join(w['text'] for w in g)
        srt.append(f'{i}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n')
        # Eventos por palabra: resaltado exacto con huecos sin resaltar.
        boundaries=sorted({start,end,*[w['start'] for w in g],*[w['end'] for w in g]})
        for a,b in zip(boundaries,boundaries[1:]):
            if b-a<.005: continue
            parts=[]
            for w in g:
                active=w['start']<=a<w['end']
                tag=f'{{\\1c&H{bgr}&}}' if active else '{\\1c&HFFFFFF&}'
                parts.append(tag+ass_escape(w['text']))
            effect='{\\fscx95\\fscy95\\t(0,80,\\fscx100\\fscy100)}' if animated and a==start else ''
            events.append(f'Dialogue: 0,{timestamp(a,True)},{timestamp(b,True)},Default,,0,0,0,,{effect}'+ ' '.join(parts))
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},&H00FFFFFF,&H00{bgr},&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,{position},40,40,{round(height*.1)},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    base.with_suffix('.srt').write_text('\n'.join(srt),encoding='utf-8')
    base.with_suffix('.ass').write_text(header+'\n'.join(events)+'\n',encoding='utf-8')
    return base.with_suffix('.srt'),base.with_suffix('.ass')
