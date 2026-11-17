from pathlib import Path
import base64
import streamlit.components.v1 as components

_component=components.declare_component('clip_libre_crop_v7',path=str(Path(__file__).parent/'assets'/'crop_editor'))


def crop_editor(image,panels,aspect='9:16',text='',text_color='#ffffff',text_size=64,text_x=.5,text_y=.15,video_url=None,start=0,end=None,words=None,burn=True,subtitle_color="#FFFF00",subtitle_size=54,subtitle_position=2,revision=0,configuration=None,time_origin=0,photo=None,logo=None,titles=None,key=None):
    return _component(image='data:image/png;base64,'+base64.b64encode(image).decode(),panels=panels,aspect=aspect,
                      text=text,text_color=text_color,text_size=text_size,text_x=text_x,text_y=text_y,video_url=video_url,start=start,end=end,words=words or [],burn=burn,subtitle_color=subtitle_color,subtitle_size=subtitle_size,subtitle_position=subtitle_position,revision=revision,configuration=configuration,time_origin=time_origin,photo=photo,logo=logo,titles=titles or [],default=None,key=key)
