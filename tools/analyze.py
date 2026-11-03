"""Read extracted LUTs; compare original lookup and offline smoothing candidates."""
from pathlib import Path
from paths import BUILD, TOOLS, ASSETS, PAKS, REPAK, UASSET, ASSEMBLER
import math,struct,json,random,hashlib
ROOT=BUILD/'colour';ROOT.mkdir(parents=True,exist_ok=True)
OUT=BUILD/'reports/lut'
NAMES=('StandardColor','OtherWorldLUT','Wincolor','StandardColor_OtherWorld')
def table(name):
    p=ASSETS/'QueensDomain/Content/UI/LUTs'/f'{name}.uexp'
    raw=p.read_bytes();start=raw.index(b'PF_B8G8R8A8\0')+len(b'PF_B8G8R8A8\0')+32
    d=raw[start:start+16384]
    return [tuple(d[i+c]/255 for c in (2,1,0)) for i in range(0,len(d),4)]
def tex(t,r,g,b):return t[g*256+b*16+r]
def evaluate(t,rgb,mode):
    q=[min(15,max(0,c*15)) for c in rgb]
    if mode=='original':return tex(t,math.floor(q[0]+.5),math.floor(q[1]+.5),math.floor(q[2]))
    if mode=='shifted':q[2]=max(0,q[2]-.5)
    if mode=='endpoint':q[2]=max(0,q[2]-.5) if q[2]<=14.5 else 2*q[2]-15
    lo=[math.floor(c) for c in q];hi=[min(15,c+1) for c in lo];f=[q[i]-lo[i] for i in range(3)]
    out=[0.,0.,0.]
    for b in range(2):
        for g in range(2):
            for r in range(2):
                w=(f[0] if r else 1-f[0])*(f[1] if g else 1-f[1])*(f[2] if b else 1-f[2])
                v=tex(t,hi[0] if r else lo[0],hi[1] if g else lo[1],hi[2] if b else lo[2])
                for c in range(3):out[c]+=w*v[c]
    return out
MODES=('original','smooth','shifted','endpoint')
