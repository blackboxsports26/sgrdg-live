"""Findet in jedem Bild des Momo-Videos die Hände (grüne Hautflächen ohne Kopf, Füße und Panzer). Siehe make_fists.py."""
import cv2, numpy as np, pickle, sys, time, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from handdet import analyze
SRC=os.environ.get('MOMO_SRC','momo-original.mp4')
cap=cv2.VideoCapture(SRC); N=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps=cap.get(cv2.CAP_PROP_FPS)
frames=[]; t0=time.time()
for i in range(N):
    ok,f=cap.read()
    if not ok: break
    r=analyze(f); lab=r['lab']; hl=[]
    for h in r['hands']:
        m=np.isin(lab,h['ids']).astype(np.uint8)
        ok2,png=cv2.imencode('.png',m*255)
        cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        (_,_),(rw,rh),_=cv2.minAreaRect(max(cs,key=cv2.contourArea))
        hl.append(dict(c=h['c'],w=h['w'],u=h['u'],L=h['L'],area=h['area'],asp=float(max(rw,rh)/max(min(rw,rh),1)),mask=png.tobytes()))
    hc=None
    if r['info']['head'] is not None:
        yy,xx=np.where(lab==r['info']['head']); hc=[float(xx.mean()),float(yy.mean())]
    frames.append(dict(hands=hl,head=hc))
    if i%60==0: print(i,f"{time.time()-t0:.0f}s",flush=True)
pickle.dump(dict(frames=frames,fps=fps,N=len(frames)),open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'dets.pkl'),'wb'))
print('fertig',len(frames),'Bilder',sum(len(f['hands']) for f in frames),'Hand-Erkennungen')
