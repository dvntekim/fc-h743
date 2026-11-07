import pcbnew, math, sys
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
x0,y0,R=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA":
        d=math.dist((mm(t.GetX()),mm(t.GetY())),(x0,y0))
        if d<R: print("via",t.GetNetname(),"(%.2f,%.2f)"%(mm(t.GetX()),mm(t.GetY())),"d=%.2f"%d, "%.2f/%.2f"%(mm(t.GetWidth(pcbnew.F_Cu)),mm(t.GetDrillValue())))
    else:
        s,e=t.GetStart(),t.GetEnd()
        # distance point-segment
        ax,ay,bx,by=mm(s.x),mm(s.y),mm(e.x),mm(e.y)
        dx,dy=bx-ax,by-ay; L=dx*dx+dy*dy
        u=0 if L==0 else max(0,min(1,((x0-ax)*dx+(y0-ay)*dy)/L))
        d=math.dist((ax+u*dx,ay+u*dy),(x0,y0))
        if d<R: print("trk",b.GetLayerName(t.GetLayer()),t.GetNetname(),"w%.2f"%mm(t.GetWidth()),"(%.2f,%.2f)-(%.2f,%.2f)"%(ax,ay,bx,by),"d=%.2f"%d)
for f in b.GetFootprints():
    for p in f.Pads():
        d=math.dist((mm(p.GetX()),mm(p.GetY())),(x0,y0))
        if d<R: print("pad",f.GetReference()+"."+p.GetNumber(),p.GetNetname(),"B" if f.IsFlipped() else "F","(%.2f,%.2f)"%(mm(p.GetX()),mm(p.GetY())),"d=%.2f"%d)
for z in b.Zones():
    if z.GetIsRuleArea(): 
        if z.HitTestForCorner if False else True:
            bb=z.GetBoundingBox()
            if mm(bb.GetLeft())-R<x0<mm(bb.GetRight())+R and mm(bb.GetTop())-R<y0<mm(bb.GetBottom())+R:
                print("keepout",z.GetZoneName(),[b.GetLayerName(l) for l in z.GetLayerSet().Seq()], "bbox",mm(bb.GetLeft()),mm(bb.GetTop()),mm(bb.GetRight()),mm(bb.GetBottom()))
