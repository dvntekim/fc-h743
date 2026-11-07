"""plot copper of every net on given layers in a box, highlighting nets of interest"""
import json, sys, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import LineString
g=json.load(open(sys.argv[1])); x0,y0,x1,y1=map(float,sys.argv[2:6]); layers=sys.argv[6].split(","); hi=sys.argv[7].split(","); out=sys.argv[8]
fig,axs=plt.subplots(1,len(layers),figsize=(6*len(layers),6))
if len(layers)==1: axs=[axs]
for ax,l in zip(axs,layers):
    for z in g['zones']:
        if z['l']==l:
            for o,h in z['polys']:
                xs,ys=zip(*o); ax.fill(xs,ys,color=('#ffcc66' if z['net'] in hi else '#dddddd'),lw=0)
    for t in g['tracks']:
        if t['l']==l:
            c='red' if t['net'] in hi else ('#88aa88' if t['net']=='GND' else '#5577cc')
            ax.plot([t['x1'],t['x2']],[t['y1'],t['y2']],color=c,lw=max(0.6,t['w']*12),solid_capstyle='round')
    for p in g['pads']:
        if p['l']==l:
            for o,h in p['polys']:
                xs,ys=zip(*o); ax.fill(xs,ys,color=('red' if p['net'] in hi else '#999999'),alpha=0.8,lw=0)
            if x0<p['x']<x1 and y0<p['y']<y1 and p['pad'] in ('1',): ax.text(p['x'],p['y'],p['ref'],fontsize=6)
    for v in g['vias']:
        ax.add_patch(plt.Circle((v['x'],v['y']),v['d']/2,color=('darkred' if v['net'] in hi else 'k')))
    ax.set_xlim(x0,x1); ax.set_ylim(y1,y0); ax.set_aspect('equal'); ax.set_title(l); ax.grid(alpha=0.3)
fig.savefig(out,dpi=90,bbox_inches='tight')
