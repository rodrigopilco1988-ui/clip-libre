"""Progreso medido, seguro entre trabajadores y la interfaz."""
import time
import math
from threading import RLock

class Progress:
    def __init__(self,title='Procesando',clock=time.monotonic):
        self.clock=clock;self.lock=RLock();self.started=clock();self.phase_started=self.started
        self.stage=title;self.message='';self.done=None;self.total=None;self.speed=None;self.eta=None
        self.status='pendiente';self.updated=self.started;self.finished=None;self.phase_key=None
    def start(self,stage,message=''):
        with self.lock:
            self.stage=stage;self.message=message;self.phase_started=self.clock();self.updated=self.phase_started
            self.done=self.total=self.speed=self.eta=None;self.status='procesando';self.finished=None
    def update(self,event=None,**values):
        data=dict(event or {},**values)
        with self.lock:
            stage=data.get('stage')
            key=data.get('phase_key')
            if (stage and stage!=self.stage) or (key is not None and key!=self.phase_key):self.start(stage or self.stage)
            if key is not None:self.phase_key=key
            if data.get('origin') is not None:self.phase_started=float(data['origin'])
            self.status='procesando';now=self.clock()
            if data.get('message') is not None:self.message=str(data['message'])
            if data.get('done') is not None:self.done=max(0,float(data['done']))
            if data.get('total') is not None:self.total=max(0,float(data['total']))
            if data.get('speed') is not None:self.speed=max(0,float(data['speed']))
            eta=data.get('eta')
            if eta is not None and math.isfinite(float(eta)) and float(eta)>=0:self.eta=float(eta);self.updated=now
            elif self.done and self.total and self.done<self.total:
                elapsed=now-self.phase_started
                if self.speed and self.speed>0:self.eta=(self.total-self.done)/self.speed;self.updated=now
                elif elapsed>=1 and self.done/self.total>=.01:self.eta=elapsed*(self.total-self.done)/self.done;self.updated=now
    def finish(self,message='Terminado'):
        with self.lock:self.status='completado';self.message=message;self.eta=0;self.finished=self.clock()
    def fail(self,error):
        with self.lock:self.status='error';self.message=str(error);self.eta=None;self.finished=self.clock()
    def snapshot(self):
        with self.lock:
            now=self.clock();fraction=min(1,self.done/self.total) if self.done is not None and self.total and self.total>0 else None
            eta=max(0,self.eta-(now-self.updated)) if self.eta is not None else None
            if self.status!='completado' and eta==0:eta=None
            return dict(stage=self.stage,message=self.message,status=self.status,fraction=fraction,elapsed=max(0,(self.finished if self.finished is not None else now)-self.started),phase_elapsed=max(0,(self.finished if self.finished is not None else now)-self.phase_started),eta=eta,speed=self.speed)

class Jobs:
    def __init__(self):self.lock=RLock();self.items=[]
    def new(self,title):
        with self.lock:
            job=Progress(title);job.start(title);self.items.append(job);self.items=[j for j in self.items if j.status=='procesando']+[j for j in self.items if j.status!='procesando'][-6:];return job
    def recent(self):
        with self.lock:return [j.snapshot() for j in self.items if j.status=='procesando']+[j.snapshot() for j in self.items if j.status!='procesando'][-2:]
