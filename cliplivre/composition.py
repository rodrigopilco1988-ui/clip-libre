"""Composición editable compartida por guía estática y render FFmpeg."""
from io import BytesIO
from PIL import Image,ImageOps,ImageDraw,ImageFont


def default_panels(count=1,columns=False):
    if count not in {1,2,3}: raise ValueError('Elige uno, dos o tres cuadros.')
    return [dict(source=[0.,0.,1.,1.],destination=[i/count,0.,1/count,1.] if columns else [0.,i/count,1.,1/count],fit='cover') for i in range(count)]


def validate_panel(panel):
    for key in ['source','destination']:
        values=panel[key]
        if len(values)!=4 or any(not 0<=float(v)<=1 for v in values): raise ValueError('El cuadro está fuera del lienzo.')
        x,y,w,h=values
        if w<=0 or h<=0 or x+w>1.001 or y+h>1.001: raise ValueError('El cuadro debe quedar dentro del lienzo y tener tamaño positivo.')
    if panel.get('fit','cover') not in {'cover','contain'}: raise ValueError('Ajuste de cuadro inválido.')


def geometry(panel,w,h):
    validate_panel(panel)
    x,y,pw,ph=panel['destination']
    left=round(x*w/2)*2; top=round(y*h/2)*2
    right=min(w,round((x+pw)*w/2)*2); bottom=min(h,round((y+ph)*h/2)*2)
    return left,top,max(2,right-left),max(2,bottom-top)


def guide(image_bytes,panels,w=360,h=640,text='',text_x=.5,text_y=.15,text_color='FFFFFF',text_size=54):
    image=Image.open(BytesIO(image_bytes)).convert('RGB')
    canvas=Image.new('RGB',(w,h),'black')
    for panel in panels:
        validate_panel(panel)
        x,y,pw,ph=panel['source']; iw,ih=image.size
        crop=image.crop((int(x*iw),int(y*ih),max(int((x+pw)*iw),int(x*iw)+1),max(int((y+ph)*ih),int(y*ih)+1)))
        dx,dy,dw,dh=geometry(panel,w,h)
        if panel.get('fit','cover')=='cover': layer=ImageOps.fit(crop,(dw,dh))
        else: layer=ImageOps.pad(crop,(dw,dh),color='black')
        canvas.paste(layer,(dx,dy))
    if text:
        try: font=ImageFont.truetype('arial.ttf',max(10,round(text_size*w/1080)))
        except OSError:
            try: font=ImageFont.truetype('DejaVuSans.ttf',max(10,round(text_size*w/1080)))
            except OSError: font=ImageFont.load_default()
        ImageDraw.Draw(canvas).multiline_text((w*text_x,h*text_y),text,font=font,fill='#'+text_color,anchor='mm',align='center',stroke_width=1,stroke_fill='black')
    result=BytesIO(); canvas.save(result,format='PNG')
    return result.getvalue()
