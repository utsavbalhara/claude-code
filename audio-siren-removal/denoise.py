import sys
import numpy as np, scipy.io.wavfile as w, noisereduce as nr
sr,y=w.read(sys.argv[1]); y=y.astype(np.float32)/32768
amount=float(sys.argv[3]) if len(sys.argv)>3 else 0.6
# stationary reduction of hiss, using quietest 2s as profile
win=sr*2; e=[np.mean(y[i:i+win]**2) for i in range(0,len(y)-win,sr)]; i0=int(np.argmin(e))*sr
z=nr.reduce_noise(y=y,sr=sr,y_noise=y[i0:i0+win],stationary=True,prop_decrease=amount,n_fft=2048)
w.write(sys.argv[2],sr,(np.clip(z,-1,1)*32767).astype(np.int16))
