import cv2
import numpy as np


def audio_features(samples, rate=16000):
    out = []
    for pos in range(0,len(samples),rate):
        part = samples[pos:pos+rate]
        rms = float(np.sqrt(np.mean(part * part))) if len(part) else 0.
        db = float(20*np.log10(max(rms,1e-8)))
        out.append(dict(time=pos/rate, end=(pos+len(part))/rate, db=db,
                        change=abs(db-out[-1]['db']) if out else 0., silence=db < -38))
    return out


def visual_features(path, start, end, step=2.,detect_faces=True,fast=False):
    if fast:
        return fast_visual_features(path,start,end,step)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError('OpenCV no pudo abrir el video.')
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    result, previous = [], None
    try:
        for t in np.arange(start,end,step):
            cap.set(cv2.CAP_PROP_POS_MSEC,float(t*1000))
            ok, frame = cap.read()
            if not ok:
                break
            h,w = frame.shape[:2]
            small = cv2.resize(frame,(320,180))
            gray = cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray],[0],None,[32],[0,256])
            cv2.normalize(hist,hist)
            change = float(cv2.compareHist(previous,hist,cv2.HISTCMP_BHATTACHARYYA)) if previous is not None else 0.
            boxes = detector.detectMultiScale(gray,1.1,4,minSize=(14,14)) if detect_faces else []
            faces = [[float(x/320),float(y/180),float(fw/320),float(fh/180)] for x,y,fw,fh in boxes]
            result.append(dict(time=float(t),scene=change,faces=faces))
            previous=hist
    finally:
        cap.release()
    return result


def silent_intervals(features, start, end, min_duration=1., max_cut=.8):
    """Conserva margen; nunca elimina más de max_cut de un silencio continuo."""
    cuts, begin, finish = [], None, None
    for f in features:
        if f['silence']:
            begin = f['time'] if begin is None else begin
            finish = f['end']
        elif begin is not None:
            if finish-begin >= min_duration:
                a,b=max(start,begin+.2),min(end,begin+.2+min(max_cut,finish-begin-.4))
                if b>a: cuts.append((a,b))
            begin=None
    if begin is not None and finish-begin >= min_duration:
        a,b=max(start,begin+.2),min(end,begin+.2+min(max_cut,finish-begin-.4))
        if b>a: cuts.append((a,b))
    return cuts


def fast_visual_features(path,start,end,step=6.):
    """Muestreo ligero de fotogramas clave; no ejecuta Haar sobre todo el directo."""
    import subprocess
    import tempfile
    frame_bytes=320*180*3
    result=[]; previous=None
    cmd=['ffmpeg','-v','error','-threads','2','-skip_frame','nokey','-ss',str(start),'-i',str(path),
         '-t',str(end-start),'-vf',f'fps=1/{step},scale=320:180', '-an','-pix_fmt','bgr24','-f','rawvideo','pipe:1']
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=errors)
        try:
            while True:
                raw=process.stdout.read(frame_bytes)
                if len(raw)!=frame_bytes: break
                gray=cv2.cvtColor(np.frombuffer(raw,dtype=np.uint8).reshape(180,320,3),cv2.COLOR_BGR2GRAY)
                hist=cv2.calcHist([gray],[0],None,[32],[0,256]); cv2.normalize(hist,hist)
                change=float(cv2.compareHist(previous,hist,cv2.HISTCMP_BHATTACHARYYA)) if previous is not None else 0.
                result.append(dict(time=start+len(result)*step,scene=change,faces=[]))
                previous=hist
            process.wait(timeout=60)
            if process.returncode:
                errors.seek(0); raise RuntimeError(errors.read().decode('utf-8',errors='replace')[-1800:])
        finally:
            if process.poll() is None: process.kill(); process.wait()
            process.stdout.close()
    return result
