"""Copy rev A's routing of the BMI088 nets (the part sits where it sat in rev A) into the rev B board."""
import pcbnew
A = pcbnew.LoadBoard("/tmp/revA.kicad_pcb"); b = pcbnew.LoadBoard("kicad/fc.kicad_pcb")
NETS = ["SPI2_SCK", "SPI2_MOSI", "SPI2_MISO", "BMI_ACC_CS", "BMI_GYRO_CS", "BMI_ACC_DRDY", "BMI_GYRO_DRDY"]
for t in list(b.GetTracks()):
    if t.GetNetname() in NETS: b.Delete(t)
n = 0
for t in A.GetTracks():
    if t.GetNetname() not in NETS: continue
    ni = b.FindNet(t.GetNetname())
    if t.GetClass() == "PCB_VIA":
        v = pcbnew.PCB_VIA(b); v.SetPosition(t.GetPosition()); v.SetWidth(t.GetWidth(pcbnew.F_Cu)); v.SetDrill(t.GetDrillValue())
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(ni); b.Add(v)
    else:
        c = pcbnew.PCB_TRACK(b); c.SetStart(t.GetStart()); c.SetEnd(t.GetEnd()); c.SetWidth(t.GetWidth()); c.SetLayer(t.GetLayer()); c.SetNet(ni); b.Add(c)
    n += 1
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("restored", n)
