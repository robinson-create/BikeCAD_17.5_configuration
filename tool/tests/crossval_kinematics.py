"""CROSS-VALIDATION de la cinématique vs la VRAIE librairie de référence.

Oracle : `mark-bak/bikinematicsolver` (la réf citée dans CLAUDE.md), exécutée
indépendamment sur une géométrie IDENTIQUE à notre four-bar Horst par défaut, puis
ses courbes (levier, chemin d'axe, anti-squat) capturées en GOLDEN ci-dessous.

Méthode de la réf (bike.py + kinematic_solver_scipy_min.py, étudiée en détail) :
  • points TYPÉS (ground / linkage / rear_wheel / front_wheel / bottom_bracket) + liens rigides ;
  • boucle cinématique détectée par plus court chemin entre 2 « ground » ;
  • résolution par FERMETURE DE BOUCLE (min ‖Σ L·[cosθ,sinθ]‖) à chaque angle d'entrée ;
  • levier = |d(course roue)/d(longueur amortisseur)| ; anti-squat = IC + tangente de
    chaîne (IFC) projetée du contact pneu AR (INSTANTANÉ = axe − rayon) vers l'axe AV.
Notre `calculations/layouts/` implémente exactement cette méthode (cf. common.py).

Reproduire l'oracle :
  python3 -m venv /tmp/bikv && /tmp/bikv/bin/pip install "numpy>=2.1" "scipy>=1.14" \
      dijkstar && /tmp/bikv/bin/pip install --no-deps bikinematicsolver==0.0.5
  (patcher 3 incompat. numpy-2 : float(np.ravel(x)[0]) lignes 117/118/214, et
   x=np.ravel(loop_ls[1:mid-1]) ligne 148 du solver) ; voir /tmp/crossval.py.

Lancer : cd tool && PYTHONPATH=. .venv/bin/python tests/crossval_kinematics.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.bike import BikeDesign
from backend.calculations.kinematics import solve_kinematics

# Courbe GOLDEN produite par la VRAIE librairie bikinematicsolver sur la géométrie
# four-bar Horst par défaut (sans galet, pas de courroie 12.7 mm pour matcher la
# chaîne hard-codée de la réf). Colonnes : (course_mm, levier, |Δaxe_x|_mm, AS%).
GOLDEN_BIKINEMATICSOLVER = [
    (0.0, 2.882, 0.0, 109.1), (19.4, 2.911, 1.27, 84.6), (38.8, 2.911, 1.38, 70.6),
    (58.2, 2.897, 0.46, 60.2), (77.6, 2.875, 1.43, 51.6), (97.0, 2.849, 4.29, 43.9),
    (116.4, 2.82, 8.11, 36.8), (135.8, 2.787, 12.91, 29.8), (155.2, 2.753, 18.72, 23.1),
    (160.0, 2.747, 20.34, 21.4),
]

# Tolérances : la cinématique est INDICATIVE ; on exige néanmoins une équivalence
# serrée avec l'oracle (le solveur et la métrologie doivent coïncider).
TOL_LEV, TOL_AXLE, TOL_AS = 0.02, 0.6, 1.5

_fail = [0]
def check(cond, label, detail=""):
    print(f"  {'✓' if cond else '✗'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    if not cond:
        _fail[0] += 1


def our_curve():
    b = BikeDesign(); s = b.suspension
    s.use_idler = False          # chainline plateau→pignon (pas de galet) = même que l'oracle
    s.belt_pitch = 12.7          # la réf hard-code un pas de 12.7 mm pour le pcd
    k = solve_kinematics(b)
    ax0 = k.samples[0].axle_x
    return [(x.wheel_travel, x.leverage, abs(x.axle_x - ax0), x.anti_squat) for x in k.samples]


def interp(curve, t, col):
    for j in range(1, len(curve)):
        a, bb = curve[j - 1], curve[j]
        if (a[0] - t) * (bb[0] - t) <= 0 and bb[0] != a[0]:
            f = (t - a[0]) / (bb[0] - a[0])
            return a[col] + f * (bb[col] - a[col])
    return curve[-1][col]


print("=== CROSS-VALIDATION cinématique vs bikinematicsolver (mark-bak) ===")
ours = our_curve()
print(f"  (notre four-bar : {len(ours)} échantillons, course {ours[-1][0]:.0f} mm)")
max_lev = max_axle = max_as = 0.0
for t, lev_ref, axle_ref, as_ref in GOLDEN_BIKINEMATICSOLVER:
    lev = interp(ours, t, 1); axle = interp(ours, t, 2); a_s = interp(ours, t, 3)
    max_lev = max(max_lev, abs(lev - lev_ref))
    max_axle = max(max_axle, abs(axle - axle_ref))
    max_as = max(max_as, abs(a_s - as_ref))

check(max_lev <= TOL_LEV, f"levier ≡ oracle (max |Δ| = {max_lev:.3f} ≤ {TOL_LEV})", f"{max_lev:.3f}")
check(max_axle <= TOL_AXLE, f"chemin d'axe ≡ oracle (max |Δ| = {max_axle:.2f} mm ≤ {TOL_AXLE})", f"{max_axle:.2f}")
check(max_as <= TOL_AS, f"anti-squat ≡ oracle (max |Δ| = {max_as:.2f} % ≤ {TOL_AS})", f"{max_as:.2f}")

# ── 2e CAS : vélo de SÉRIE (Vitus Sommet) tracé dans bikinematicsolver ───────
# Géométrie réelle (pivots convertis px→mm) + amortisseur sur BIELLETTE (rocker),
# comme la majorité des enduros modernes. Golden = vraie librairie sur ce vélo.
import math
GOLDEN_VITUS = [
    (0.0, 3.343, 0.0, 99.7), (14.6, 3.252, 0.88, 94.4), (29.1, 3.149, 1.22, 89.6),
    (43.6, 3.048, 1.03, 85.2), (58.2, 2.95, 0.31, 81.1), (72.7, 2.856, 0.91, 77.1),
    (87.3, 2.767, 2.66, 73.3), (101.8, 2.683, 4.91, 69.5), (116.4, 2.605, 7.7, 65.9),
    (130.9, 2.534, 11.02, 62.4), (145.4, 2.47, 14.87, 58.9), (160.0, 2.42, 19.28, 55.4),
]
VITUS = dict(A=(-8.0, 46.8), B=(-382.7, 13.5), C=(-78.9, 261.7), D=(26.8, 250.2),
             shock_lo=(73.6, 295.7), shock_up=(52.2, 91.0),
             rear_axle=(-445.5, 21.9), front_axle=(809.5, 28.1))


def vitus_curve():
    b = BikeDesign(); f = b.frame; s = b.suspension
    f.bb_drop = VITUS['rear_axle'][1]; f.cs = math.hypot(*VITUS['rear_axle'])
    f.fcd = VITUS['front_axle'][0]; f.wheel_r = f.wheel_f = 736.6
    s.linkage_type = "four_bar_horst"; s.use_idler = False; s.belt_pitch = 12.7
    s.chainring_teeth = 30; s.cog_teeth = 52; s.cog_height = 1100.0; s.rear_travel = 160.0
    s.main_pivot.x, s.main_pivot.y = VITUS['A']; s.horst_pivot.x, s.horst_pivot.y = VITUS['B']
    s.upper_ss_pivot.x, s.upper_ss_pivot.y = VITUS['C']; s.upper_frame_pivot.x, s.upper_frame_pivot.y = VITUS['D']
    s.shock_mount = "rocker"                       # amortisseur sur la biellette (enduro moderne)
    s.shock_lower.x, s.shock_lower.y = VITUS['shock_lo']
    s.shock_upper.x, s.shock_upper.y = VITUS['shock_up']
    k = solve_kinematics(b); ax0 = k.samples[0].axle_x
    return [(x.wheel_travel, x.leverage, abs(x.axle_x - ax0), x.anti_squat) for x in k.samples]


print("\n=== CROSS-VALIDATION sur un vélo de SÉRIE : Vitus Sommet (enduro) ===")
vc = vitus_curve()
mlev = max(abs(interp(vc, t, 1) - lv) for t, lv, _, _ in GOLDEN_VITUS)
max2 = max(abs(interp(vc, t, 2) - ax) for t, _, ax, _ in GOLDEN_VITUS)
mas2 = max(abs(interp(vc, t, 3) - a) for t, _, _, a in GOLDEN_VITUS)
check(mlev <= TOL_LEV, f"levier ≡ oracle (amorto rocker) (max |Δ| = {mlev:.3f})", f"{mlev:.3f}")
check(max2 <= TOL_AXLE, f"chemin d'axe ≡ oracle (max |Δ| = {max2:.2f} mm)", f"{max2:.2f}")
check(mas2 <= TOL_AS, f"anti-squat ≡ oracle (max |Δ| = {mas2:.2f} %)", f"{mas2:.2f}")

print("\n" + "=" * 50)
if _fail[0] == 0:
    print("✓ CROSS-VALIDATION : notre cinématique ≡ bikinematicsolver (synthétique + vélo de série)")
else:
    print(f"ÉCHECS : {_fail[0]}")
    sys.exit(1)
