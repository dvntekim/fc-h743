import pcbnew, sys
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb")
pads=sys.argv[1:]
for rp in pads:
    r,n=rp.split(":")
    f=b.FindFootprintByReference(r)
    for p in f.Pads():
        if p.GetNumber()==n:
            p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL); print("solid",rp,p.GetNetname())
filler=pcbnew.ZONE_FILLER(b); b.BuildConnectivity(); filler.Fill(b.Zones())
pcbnew.SaveBoard("kicad/fc.kicad_pcb",b)
