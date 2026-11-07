"""Remove GND stitching vias closer than GAP mm (edge to edge) to the 4 mm mounting holes."""
import pcbnew, math, sys
GAP=float(sys.argv[1]) if len(sys.argv)>1 else 1.0
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
holes=[(mm(p.GetX()),mm(p.GetY()),mm(p.GetDrillSize().x)) for f in b.GetFootprints() if f.GetReference().startswith("H") for p in f.Pads() if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH]
n=0
for v in [t for t in b.GetTracks() if t.GetClass()=="PCB_VIA" and t.GetNetname()=="GND"]:
    x,y=mm(v.GetX()),mm(v.GetY())
    for hx,hy,d in holes:
        if math.dist((x,y),(hx,hy))-d/2-mm(v.GetDrillValue())/2 < GAP:
            # only free-standing stitching vias: no track ends on them
            if not any(t.GetClass()!="PCB_VIA" and t.GetNetname()=="GND" and (t.GetStart()==v.GetPosition() or t.GetEnd()==v.GetPosition()) for t in b.GetTracks()):
                b.Delete(v); n+=1; print("removed", round(x,2), round(y,2))
            break
filler=pcbnew.ZONE_FILLER(b); b.BuildConnectivity(); filler.Fill(b.Zones())
pcbnew.SaveBoard("kicad/fc.kicad_pcb",b); print("removed",n)
