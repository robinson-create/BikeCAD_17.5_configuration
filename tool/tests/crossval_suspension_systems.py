"""CROSS-VALIDATION MULTI-SYSTÈMES : prouve que notre four-bar général (+ high_pivot)
reproduit DIFFÉRENTS systèmes de suspension, pas seulement le Horst du Vitus.

Pour chaque système, même géométrie passée à NOTRE outil et à la VRAIE librairie
`mark-bak/bikinematicsolver` (exécutée séparément). Golden = sortie de la librairie
(course 0→150 mm) : (course_mm, |Δaxe|_mm, anti-squat%).

Systèmes (le solveur de réf annonce couvrir « single-pivot ou 4-barres à pivots
placés différemment, >80% des suspensions ») :
  • Horst Link (FSR) — pivot AR sur la base devant l'axe ;
  • Split-Pivot (Devinci) — pivot AR ~concentrique à l'axe ;
  • DW-Link / twin-link (DW/VPP) — 2 biellettes courtes, AS NON-monotone ;
  • Single-Pivot — high_pivot (vérifié solvable + plausible ; réf instable sur single-piv).

Lancer : cd tool && PYTHONPATH=. .venv/bin/python tests/crossval_suspension_systems.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.models.bike import BikeDesign
from backend.calculations.kinematics import solve_kinematics

AXLE = (-445.5, 21.9); FAXLE = (809.5, 28.1)
TOL_AS, TOL_AXLE = 1.5, 0.6

SYSTEMS = {
    "Horst Link (FSR)": dict(
        A=(-8.0, 46.8), B=(-382.7, 13.5), C=(-78.9, 261.7), D=(26.8, 250.2),
        shock_lo=(73.6, 295.7), shock_up=(52.2, 91.0), mount="rocker",
        golden=[(0.0, 0.0, 99.7), (18.2, 1.01, 93.2), (36.4, 1.19, 87.4), (54.5, 0.55, 82.1),
                (72.7, 0.9, 77.1), (90.9, 3.16, 72.3), (109.1, 6.23, 67.8), (127.3, 10.12, 63.3),
                (145.4, 14.85, 58.9)]),
    "Split-Pivot (Devinci)": dict(
        A=(-8.0, 46.8), B=(-437.5, 27.9), C=(-120.0, 250.0), D=(26.8, 250.2),
        shock_lo=(73.6, 295.7), shock_up=(52.2, 91.0), mount="rocker",
        golden=[(0.0, 0.0, 82.2), (18.2, 0.45, 79.0), (36.4, 0.16, 75.6), (54.5, 0.88, 72.2),
                (72.7, 2.68, 68.8), (90.9, 5.23, 65.3), (109.1, 8.57, 61.8), (127.3, 12.7, 58.2),
                (145.4, 17.65, 54.6)]),
    "DW-Link / twin-link": dict(
        A=(48.0, 35.0), B=(8.0, 28.0), C=(18.0, 168.0), D=(58.0, 150.0),
        shock_lo=(12.0, 120.0), shock_up=(75.0, 330.0), mount="coupler",
        golden=[(0.0, 0.0, 93.9), (18.2, 0.6, 76.0), (36.4, 0.07, 61.1), (54.5, 1.74, 50.6),
                (72.7, 4.38, 45.2), (90.9, 7.79, 45.0), (109.1, 11.79, 48.8), (127.3, 16.28, 55.0),
                (145.4, 21.2, 61.7)]),
}

_fail = [0]
def check(cond, label, detail=""):
    print(f"  {'✓' if cond else '✗'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        _fail[0] += 1


def our_curve(g):
    b = BikeDesign(); f = b.frame; s = b.suspension
    f.bb_drop = AXLE[1]; f.cs = math.hypot(*AXLE); f.fcd = FAXLE[0]; f.wheel_r = f.wheel_f = 736.6
    s.linkage_type = "four_bar_horst"; s.use_idler = False; s.belt_pitch = 12.7
    s.chainring_teeth = 30; s.cog_teeth = 52; s.cog_height = 1100.0; s.rear_travel = 150.0
    s.main_pivot.x, s.main_pivot.y = g['A']; s.horst_pivot.x, s.horst_pivot.y = g['B']
    s.upper_ss_pivot.x, s.upper_ss_pivot.y = g['C']; s.upper_frame_pivot.x, s.upper_frame_pivot.y = g['D']
    s.shock_mount = g['mount']
    s.shock_lower.x, s.shock_lower.y = g['shock_lo']; s.shock_upper.x, s.shock_upper.y = g['shock_up']
    k = solve_kinematics(b)
    if not k.ok:
        return None
    ax0 = k.samples[0].axle_x
    return [(x.wheel_travel, abs(x.axle_x - ax0), x.anti_squat) for x in k.samples]


def interp(curve, t, col):
    for j in range(1, len(curve)):
        a, b = curve[j-1], curve[j]
        if (a[0]-t)*(b[0]-t) <= 0 and b[0] != a[0]:
            f = (t-a[0])/(b[0]-a[0]); return a[col]+f*(b[col]-a[col])
    return curve[-1][col]


print("=== CROSS-VALIDATION multi-systèmes vs bikinematicsolver ===")
for name, g in SYSTEMS.items():
    oc = our_curve(g)
    if oc is None:
        check(False, f"{name} : résout"); continue
    tmax = oc[-1][0]
    mas = max(abs(interp(oc, t, 2) - a) for t, _, a in g['golden'] if t <= tmax)
    max_ = max(abs(interp(oc, t, 1) - x) for t, x, _ in g['golden'] if t <= tmax)
    ok = mas <= TOL_AS and max_ <= TOL_AXLE
    check(ok, f"{name:24} ≡ oracle (AS Δ={mas:.2f}% · axe Δ={max_:.2f}mm)", f"AS {mas:.2f} axe {max_:.2f}")

# Single-pivot (high_pivot) : la réf est instable sur single-piv → on vérifie
# seulement que NOTRE outil le résout avec des valeurs plausibles.
b = BikeDesign(); f = b.frame; s = b.suspension
f.bb_drop = AXLE[1]; f.cs = math.hypot(*AXLE); f.fcd = FAXLE[0]; f.wheel_r = f.wheel_f = 736.6
s.linkage_type = "high_pivot_idler"; s.use_idler = False; s.rear_travel = 150.0
s.main_pivot.x, s.main_pivot.y = (45.0, 100.0)
s.shock_lower.x, s.shock_lower.y = (-110.0, 70.0); s.shock_upper.x, s.shock_upper.y = (-30.0, 300.0)
k = solve_kinematics(b)
check(k.ok and 1.5 < k.leverage_start < 5 and 80 < k.samples[0].anti_squat < 200,
      f"Single-Pivot (high_pivot)  résout + plausible (lev {k.leverage_start:.2f}, AS {k.samples[0].anti_squat:.0f}%)")

print("\n" + "=" * 50)
if _fail[0] == 0:
    print("✓ Notre four-bar GÉNÉRAL reproduit Horst / Split-Pivot / DW-Link ≡ référence (+ Single-Pivot)")
else:
    print(f"ÉCHECS : {_fail[0]}")
    sys.exit(1)
