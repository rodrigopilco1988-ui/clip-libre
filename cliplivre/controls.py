"""Unidades y límites compartidos por la pantalla inicial y el backend."""
import math

PRESETS={
    '30–90 s · variado':(30.,90.),
    '15–30 s · variado':(15.,30.),
    '1–3 min · variado':(60.,180.),
    '3–5 min · variado':(180.,300.),
    '1 minuto exacto':(60.,60.),
    'Personalizado':None,
    'Sin máximo':(30.,None),
}


def parse_clock(value):
    parts=str(value).strip().split(':')
    if len(parts) not in {2,3}: raise ValueError('Usa min:seg: 0:30 son 30 segundos; 1:30 es un minuto y medio.')
    try: numbers=[float(p) for p in parts]
    except ValueError as e: raise ValueError('El tiempo debe tener formato min:seg o h:min:seg.') from e
    if any(not math.isfinite(n) or n<0 for n in numbers) or any(n>=60 for n in numbers[1:]):
        raise ValueError('Los segundos deben estar entre 00 y 59.')
    return sum(n*60**i for i,n in enumerate(reversed(numbers)))


def clock(seconds):
    total=max(0,round(seconds)); hours,remainder=divmod(total,3600); minutes,secs=divmod(remainder,60)
    return f'{hours}:{minutes:02}:{secs:02}' if hours else f'{minutes}:{secs:02}'


def clip_limits(preset,minimum='0:30',maximum='1:30'):
    values=PRESETS[preset] if preset!='Personalizado' else (parse_clock(minimum),parse_clock(maximum))
    low,high=values
    if low<=0 or (high is not None and high<low): raise ValueError('La duración máxima debe ser igual o mayor que la mínima.')
    return low,high
