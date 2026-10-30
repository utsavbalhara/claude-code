import sys
import numpy as np, scipy.io.wavfile as w, scipy.signal as s
from scipy.ndimage import median_filter, binary_dilation
sr,x=w.read(sys.argv[1]); x=x.astype(np.float64)/32768
# siren region mask (seconds) from pass on original
def region(x):
    f,t,Z=s.stft(x,sr,nperseg=2048,noverlap=1792); M=np.abs(Z); b=(f>760)&(f<1420)
    sub=M[b]; prom=20*np.log10(sub.max(0)/(np.median(sub,0)+1e-9)); lev=20*np.log10(sub.max(0)+1e-12)
    a=median_filter(((prom>18)&(lev>-45)).astype(float),9)>0.5
    a=binary_dilation(a,iterations=int(1.0*sr/256))
    return lambda tt: np.interp(tt,t,a.astype(float))>0.5
inreg=region(x)
def one_pass(x,N,H,ws,atten,thr):
    f,t,Z=s.stft(x,sr,nperseg=N,noverlap=N-H); M=np.abs(Z); df=f[1]
    band=np.where((f>760)&(f<1420))[0]; sub=M[band]; bi=band[sub.argmax(0)]; J=np.arange(len(bi))
    a,b,c=[np.log(M[bi+d,J]+1e-12) for d in (-1,0,1)]
    f0=(bi+np.clip(0.5*(a-c)/(a-2*b+c+1e-12),-1,1))*df
    f0=np.nan_to_num(f0,nan=1000.0)
    prom=20*np.log10(sub.max(0)/(np.median(sub,0)+1e-9)+1e-12)
    act=(median_filter((prom>thr).astype(float),size=5)>0.5)&inreg(t)
    G=np.ones_like(M)
    for j in np.where(act)[0]:
        rate=abs(f0[min(j+1,len(f0)-1)]-f0[max(j-1,0)])/2/(H/sr)
        for k in range(1,9):
            fc=k*f0[j]
            if fc>sr/2-500: break
            # refine harmonic centre by local peak search
            sr_hw=max(2,int(0.03*fc/df)); ci=int(round(fc/df))
            win=M[max(ci-sr_hw,1):ci+sr_hw+1,j]; ci=max(ci-sr_hw,1)+win.argmax()
            hw=min(ws*(30+k*rate*(N/sr)*0.5+8*k),35+25*k)
            lo=max(int(ci-hw/df),1); hi=int(ci+hw/df)+1
            ring=np.r_[M[max(lo-14,0):lo-3,j],M[hi+3:hi+14,j]]
            fl=np.median(ring); seg=M[lo:hi+1,j]
            if seg.max()<2.0*fl: continue
            g=np.minimum(1,atten*fl/(seg+1e-12))
            G[lo:hi+1,j]=np.minimum(G[lo:hi+1,j],g)
    _,y=s.istft(Z*G,sr,nperseg=N,noverlap=N-H)
    return y[:len(x)]
y=one_pass(x,2048,256,1.1,0.8,15)
y=one_pass(y,1024,128,1.3,0.8,10)
y=one_pass(y,4096,512,1.0,0.8,10)
y=one_pass(y,2048,256,1.2,0.8,8)
w.write(sys.argv[2],sr,(np.clip(y,-1,1)*32767).astype(np.int16))
f2,t2,Z2=s.stft(y,sr,nperseg=4096,noverlap=3072); M2=np.abs(Z2); bb=(f2>780)&(f2<1400)
fx,tx,Zx=s.stft(x,sr,nperseg=4096,noverlap=3072); Mx=np.abs(Zx)
for a in [5,30,60,90,150]:
    idx=(t2>=a)&(t2<a+5); m=M2[bb][:,idx]
    print(a,"s prom:",round(20*np.log10(np.median(m.max(0)/np.median(m,0))),1)," band reduction:",round(10*np.log10((Mx[bb][:,idx]**2).sum()/(m**2).sum()),1)," total reduction:",round(10*np.log10((Mx[:,idx]**2).sum()/(M2[:,idx]**2).sum()),1))
