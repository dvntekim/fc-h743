"""Route one explicit pad-to-pad connection with the local router.
Usage: python3 route_pair.py NET REF:PAD REF:PAD [width]"""
import sys, os
net, A, C = sys.argv[1:4]
w = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
sys.argv = [sys.argv[0], os.path.join(os.path.dirname(os.path.abspath(__file__)), "drc_last.json")]
import fix_route as fr, pcbnew
def pad(rc):
    if "," in rc:   # x,y of a via: reachable on every signal layer
        x, y = map(float, rc.split(","))
        return (x, y), list(fr.SIG)
    r, n = rc.split(":")
    p = next(p for p in fr.b.FindFootprintByReference(r).Pads() if p.GetNumber() == n)
    q = p.GetPosition()
    return (fr.tomm(q.x), fr.tomm(q.y)), [l for l in fr.SIG if p.IsOnLayer(l)]
a, al = pad(A); c, cl = pad(C)
nc = fr.b.FindNet(net).GetNetCode()
for ww in (w, 0.2, 0.15):
    pts = fr.route(nc, a, al, c, cl, ww)
    if pts:
        print("routed", net, A, C, "w", ww, "vias", fr.emit(nc, pts, ww)); break
else:
    print("FAIL", net, A, C)
pcbnew.SaveBoard(fr.PCB, fr.b)
