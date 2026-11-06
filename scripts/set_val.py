import pcbnew,sys
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); ref,val,lcsc=sys.argv[1:4]
f=b.FindFootprintByReference(ref); old=f.GetValue(); f.SetValue(val)
for k in ("LCSC","LCSC Part","JLCPCB"):
    if f.HasFieldByName(k): f.GetFieldByName(k).SetText(lcsc); print("field",k)
pcbnew.SaveBoard("kicad/fc.kicad_pcb",b); print(ref,old,"->",val,lcsc)
