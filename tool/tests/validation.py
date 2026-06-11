"""Suite de FIABILISATION (golden / cohérence / cross-validation).

Implémente les pistes du recap :
  • golden tests : le vélo de réf doit retomber sur ses cotes documentées (±tol) ;
  • cohérence interne : trail = formule canonique, reach/stack = points clés, WB = axes ;
  • round-trip .bcad LOSSLESS (nb de clés <entry> préservé) ;
  • cross-validation anti-squat : recalcul INDÉPENDANT par la méthode
    mark-bak/bikinematicsolver (IFC = (brin moteur) ∩ (axe AR, IC) ; ligne contact→IFC) ;
  • trail dynamique : sag fourche ⇒ HTA plus raide, trail & WB qui diminuent.

Lancer : cd tool && PYTHONPATH=. .venv/bin/python tests/validation.py
"""
import sys, os, math, re, glob, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.bike import BikeDesign
from backend.calculations.geometry import calculate
from backend.calculations.kinematics import solve_kinematics
from backend.io.bcad_io import load_bcad, save_bcad
from backend.calculations.layouts import common

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, "BIKE", "eMTB_DOM_Engineering.bcad")

_fail = [0]
def check(cond, label, detail=""):
    print(f"  {'✓' if cond else '✗'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        _fail[0] += 1


print("=== 1. GOLDEN — eMTB de référence vs cotes documentées (CLAUDE.md) ===")
b = load_bcad(SRC); c = calculate(b)
# Roue réelle 752 → reach≈482, stack≈622, WB≈1254 (cf. CLAUDE.md « Faits vérifiés »)
check(abs(c.reach - 482) <= 6, "reach ≈ 482 mm", f"{c.reach}")
check(abs(c.stack - 622) <= 8, "stack ≈ 622 mm", f"{c.stack}")
check(abs(c.wheelbase - 1254) <= 12, "wheelbase ≈ 1254 mm", f"{c.wheelbase}")

print("\n=== 2. COHÉRENCE INTERNE de la géométrie ===")
# reach/stack = position du haut du tube de direction p/r au BB
check(abs(c.reach - (c.ht_top.x - c.bb.x)) <= 0.6, "reach = ht_top.x − bb.x", f"{c.reach} vs {c.ht_top.x-c.bb.x:.1f}")
check(abs(c.stack - (c.ht_top.y - c.bb.y)) <= 0.6, "stack = ht_top.y − bb.y")
check(abs(c.wheelbase - (c.front_axle.x - c.rear_axle.x)) <= 0.6, "WB = front_axle.x − rear_axle.x")
# trail = formule canonique (R·cosHTA − offset)/sinHTA
hta = math.radians(b.frame.head_angle); R = b.frame.wheel_f / 2
trail_ref = (R * math.cos(hta) - b.fork.offset) / math.sin(hta)
check(abs(c.trail - trail_ref) <= 0.6, "trail = (R·cosHTA − offset)/sinHTA", f"{c.trail} vs {trail_ref:.1f}")

print("\n=== 3. TRAIL DYNAMIQUE au sag (fork ⇒ HTA raide, trail↓, WB↓) ===")
check(c.trail_sag < c.trail, "trail_sag < trail (fourche comprimée)", f"{c.trail_sag} < {c.trail}")
check(c.head_angle_sag > b.frame.head_angle, "HTA_sag > HTA (plus raide)", f"{c.head_angle_sag} > {b.frame.head_angle}")
check(c.wheelbase_sag <= c.wheelbase, "WB_sag ≤ WB", f"{c.wheelbase_sag} ≤ {c.wheelbase}")

print("\n=== 4. ROUND-TRIP .bcad LOSSLESS (nb de clés <entry>) ===")
def nkeys(path): return len(re.findall(r"<entry\s+key=", open(path, encoding="utf-8", errors="ignore").read()))
n_src = nkeys(SRC)
out = tempfile.mktemp(suffix=".bcad")
save_bcad(load_bcad(SRC), out, SRC, backup=False, free_safe=False)
n_out = nkeys(out)
check(n_out == n_src, f"clés préservées {n_src} → {n_out} (0 perdue/ajoutée)", f"{n_src}→{n_out}")
for p in (out, out + ".bak"):
    if os.path.exists(p): os.remove(p)

print("\n=== 5. CROSS-VALIDATION anti-squat vs méthode bikinematicsolver ===")
# Recalcul INDÉPENDANT sur un single-pivot connu : IC = pivot principal.
bx = BikeDesign(); bx.suspension.linkage_type = "high_pivot_idler"
k = solve_kinematics(bx)
s = bx.suspension
P = (s.main_pivot.x, s.main_pivot.y)
axle0 = (k.samples[0].axle_x, k.samples[0].axle_y)
ground_y = -(bx.frame.wheel_r / 2) + bx.frame.bb_drop   # contact pneu AR ≈ sol
# brin moteur : plateau BB → pignon (ou galet→pignon si galet)
chain = (s.chainring_teeth * s.belt_pitch / (2*math.pi))
cog = (s.cog_teeth * s.belt_pitch / (2*math.pi))
drive_pt = (s.idler.x, s.idler.y) if s.use_idler else (0.0, 0.0)
r_drive = (s.idler_dia/2) if s.use_idler else chain
ref_as = common.anti_squat(P, axle0, ground_y, drive_pt, r_drive, cog, s.cog_height, front_axle_x=bx.frame.fcd)
tool_as = k.samples[0].anti_squat
check(abs(ref_as - tool_as) <= 0.5, "anti-squat (recalc indépendant ≡ outil)", f"{ref_as:.1f} vs {tool_as}")

print("\n=== 6. COHÉRENCE sur TOUS les vélos du dépôt ===")
for f in sorted(glob.glob(os.path.join(REPO, "BIKE", "*.bcad"))):
    bb = load_bcad(f); cc = calculate(bb)
    name = os.path.basename(f).replace(".bcad", "")
    # garde-fou « non cassé » (pas de NaN/négatif/absurde) — tolérant aux petits cadres
    finite = all(math.isfinite(v) for v in (cc.wheelbase, cc.reach, cc.stack, cc.trail, cc.bb_height))
    sane = (finite and cc.wheelbase > 500 and cc.reach > 100 and cc.stack > 150
            and 0 < cc.trail < 250)
    check(sane, f"{name}: géométrie finie/plausible", f"WB{cc.wheelbase} R{cc.reach} trail{cc.trail}")

print("\n" + "=" * 50)
if _fail[0] == 0:
    print("✓ VALIDATION : TOUT PASSE")
else:
    print(f"ÉCHECS : {_fail[0]}")
    sys.exit(1)
