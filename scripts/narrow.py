"""narrow.py NET LAYER x y R width : set tracks of NET on LAYER whose midpoint is within R mm of (x,y) to width"""
import pcbnew,sys,math
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
net,lay=sys.argv[1],sys.argv[2]; x0,y0,R,w=map(float,sys.argv[3:7]); lid=b.GetLayerID(lay); n=0
for t in b.GetTracks():
    if t.GetClass()!="PCB_VIA" and t.GetNetname()==net and t.GetLayer()==lid:
        cx,cy=mm((t.GetStart().x+t.GetEnd().x)/2),mm((t.GetStart().y+t.GetEnd().y)/2)
        if math.dist((cx,cy),(x0,y0))<R and mm(t.GetWidth())>w: t.SetWidth(pcbnew.FromMM(w)); n+=1
pcbnew.SaveBoard("kicad/fc.kicad_pcb",b); print("narrowed",n)
