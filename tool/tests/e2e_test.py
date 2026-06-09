"""
Test E2E — DOM Engineering Bike Tool
1. Sweep de TOUS les champs : muter chaque champ → calc/render/kinematics/fit sans crash.
2. Cohérence géométrique (superposition des blocs).
3. Présence graphique de chaque composant dans le SVG.

Lancer : cd tool && PYTHONPATH=. .venv/bin/python tests/e2e_test.py
"""
import math
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy

from backend.models.bike import BikeDesign, RiderConfig
from backend.calculations.geometry import calculate
from backend.calculations.kinematics import solve_kinematics
from backend.calculations.fit import compute_fit
from backend.io.svg_export import render_svg
from backend.io.dxf_export import export_dxf
from backend.io.bcad_io import load_bcad, save_bcad

SRC = "/Users/theodorelecointe/BikeCAD_17.5_configuration/BIKE/eMTB_DOM_Engineering.bcad"

fails = []
def check(cond, msg):
    if not cond:
        fails.append(msg)
        print(f"  ✗ {msg}")
    return cond


def svg_finite(svg: str) -> bool:
    low = svg.lower()
    if "nan" in low or "inf" in low:
        return False
    try:
        ET.fromstring(svg)
    except ET.ParseError:
        return False
    return True


def run_pipeline(bike: BikeDesign, with_rider=True):
    """Exécute tout le pipeline, retourne (ok, svg)."""
    calc = calculate(bike)
    fit = compute_fit(bike, calc) if bike.rider else None
    svg = render_svg(bike, calc, 1400, 750, True, fit)
    solve_kinematics(bike)
    export_dxf(bike, calc)
    return calc, svg


# ─── 1. SWEEP DE TOUS LES CHAMPS ────────────────────────────────────────────
print("\n=== 1. SWEEP DE TOUS LES CHAMPS ===")
base = load_bcad(SRC)
base.rider = RiderConfig()
base_dict = base.model_dump()

def mutate(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value * 1.1 + 1.0
    return value  # str/None inchangés

n_fields = 0
n_ok = 0
def sweep(section_name, section_dict):
    global n_fields, n_ok
    for key, val in section_dict.items():
        if isinstance(val, dict):  # pivot {x,y}
            for sub in val:
                if isinstance(val[sub], (int, float)) and not isinstance(val[sub], bool):
                    d = deepcopy(base_dict)
                    d[section_name][key][sub] = mutate(val[sub])
                    _try(d, f"{section_name}.{key}.{sub}")
            continue
        if isinstance(val, (int, float, bool)):
            n_fields += 1
            d = deepcopy(base_dict)
            d[section_name][key] = mutate(val)
            _try(d, f"{section_name}.{key}")

def _try(d, label):
    global n_ok
    try:
        bike = BikeDesign(**d)
        calc, svg = run_pipeline(bike)
        if not svg_finite(svg):
            fails.append(f"SVG invalide après modif {label}")
            print(f"  ✗ SVG invalide: {label}")
            return
        n_ok += 1
    except Exception as exc:
        fails.append(f"CRASH sur {label}: {exc}")
        print(f"  ✗ CRASH {label}: {exc}")

for sec in base_dict:
    if isinstance(base_dict[sec], dict):
        sweep(sec, base_dict[sec])
print(f"  {n_ok} champs mutés sans erreur (sur ~{n_fields} scalaires + pivots)")

# ─── 2. COHÉRENCE GÉOMÉTRIQUE (superposition des blocs) ─────────────────────
print("\n=== 2. COHÉRENCE GÉOMÉTRIQUE ===")
bike = load_bcad(SRC)
calc = calculate(bike)
wr_r = bike.frame.wheel_r / 2
wr_f = bike.frame.wheel_f / 2

# Les roues touchent le sol
check(abs((calc.rear_axle.y - wr_r) - calc.ground_level) < 0.5,
      f"roue AR au sol (axe_y {calc.rear_axle.y} - r {wr_r} = {calc.rear_axle.y-wr_r} vs sol {calc.ground_level})")
check(abs((calc.front_axle.y - wr_f) - calc.ground_level) < 0.5,
      "roue AV au sol")
# Axe AR derrière le BB, axe AV devant
check(calc.rear_axle.x < 0 < calc.front_axle.x, "axes de part et d'autre du BB")
# Empattement = distance entre axes
check(abs(calc.wheelbase - (calc.front_axle.x - calc.rear_axle.x)) < 0.5, "empattement cohérent")
# Le tube de direction relie crown → ht_top, longueur ≈ head_tube (+ext)
ht_len = math.hypot(calc.ht_top.x - calc.crown.x, calc.ht_top.y - calc.crown.y)
exp = bike.frame.head_tube + bike.frame.head_tube_upper_ext + bike.frame.head_tube_lower_ext
check(abs(ht_len - exp) < 1.0, f"longueur tube direction {ht_len:.1f} ≈ {exp:.1f}")
# Reach/stack = position ht_top
check(abs(calc.reach - calc.ht_top.x) < 0.5 and abs(calc.stack - calc.ht_top.y) < 0.5,
      "reach/stack = position haut tube direction")
# Stem tip devant et au-dessus du BB ; selle derrière le BB
check(calc.stem_tip.x > 0 and calc.handlebar_center.y > calc.bb.y, "cintre devant/au-dessus du BB")
check(calc.saddle_mid.x < calc.ht_top.x, "selle en arrière du cintre")
# Pas de coordonnées aberrantes
for name in ("reach","stack","trail","wheelbase","bb_height"):
    v = getattr(calc, name)
    check(math.isfinite(v) and 0 < abs(v) < 5000, f"{name} dans une plage saine ({v})")

# ─── 3. PRÉSENCE GRAPHIQUE DE CHAQUE COMPOSANT ──────────────────────────────
print("\n=== 3. PRÉSENCE GRAPHIQUE DES COMPOSANTS ===")
bike = load_bcad(SRC)
bike.rider = RiderConfig()
calc = calculate(bike)
fit = compute_fit(bike, calc)
svg = render_svg(bike, calc, 1400, 750, True, fit)

components = {
    "fond":          'fill="#f8f9fa"',
    "transmission":  'class="drivetrain"',
    "pilote":        'class="rider"',
    "courroie":      '#e8851a',          # couleur belt
    "moteur":        '#34495e',
    "roues (tire)":  '#1e1e1e',
    "fourche":       '#16213e',
    "couronne/BB":   '#0f3460',
    "cotes":         '#0984e3',
    "titre":         bike.name,
    "freins/disques":'class="brakes"',
    "pédales":       'class="pedals"',
}
for label, token in components.items():
    check(token in svg, f"composant présent : {label}")

# ─── 4. CINÉMATIQUE — TOPOLOGIES ────────────────────────────────────────────
print("\n=== 4. CINÉMATIQUE — TOPOLOGIES ===")

# 4a. Four-bar (défaut) résolu + verdicts cohérents
b = load_bcad(SRC)
b.suspension.linkage_type = "four_bar_horst"
r = solve_kinematics(b)
check(r.ok, f"four-bar résolu ({r.message})")
check(abs(r.total_travel - b.suspension.rear_travel) <= 10, "four-bar : course ≈ cible")
check(len(r.samples) >= 5, "four-bar : échantillons présents")
# pedal kickback cohérent avec belt growth : kick = deg(belt/r_plateau)
r_cr = b.suspension.chainring_teeth * b.suspension.belt_pitch / (2 * math.pi)
for smp in r.samples:
    exp = math.degrees(smp.belt_growth / r_cr)
    if abs(exp - smp.pedal_kickback) > 0.05:
        check(False, f"kickback incohérent: {smp.pedal_kickback} vs {exp:.2f}")
        break

# 4b. High-pivot single-idler résolu
b = load_bcad(SRC)
s = b.suspension
s.linkage_type = "high_pivot_idler"
s.main_pivot.x, s.main_pivot.y = -20.0, 110.0     # pivot haut
s.idler.x, s.idler.y = -10.0, 90.0                # galet proche du pivot
s.shock_lower.x, s.shock_lower.y = -120.0, 20.0
s.shock_upper.x, s.shock_upper.y = -10.0, 200.0
r = solve_kinematics(b)
check(r.ok, f"high-pivot résolu ({r.message})")
check(abs(r.total_travel - s.rear_travel) <= 10, "high-pivot : course ≈ cible")
check(r.axle_path_rearward > 0, f"high-pivot : axe recule (rearward {r.axle_path_rearward})")

# 4c. Invariant high-pivot : galet AU pivot → belt growth ≈ 0 et kickback ≈ 0
s.idler.x, s.idler.y = s.main_pivot.x, s.main_pivot.y
r0 = solve_kinematics(b)
check(r0.belt_growth_max < 0.05, f"galet=pivot → belt growth nul ({r0.belt_growth_max})")
check(r0.pedal_kickback_max < 0.05, f"galet=pivot → kickback nul ({r0.pedal_kickback_max})")

# 4d. Dispatch : topologie inconnue → échec propre (pas de crash)
b2 = load_bcad(SRC)
b2.suspension.__dict__["linkage_type"] = "inexistant"  # bypass validation pydantic
r = solve_kinematics(b2)
check(not r.ok, "topologie inconnue → ok=False sans crash")

# 4e. Suspension désactivée → échec propre
b3 = load_bcad(SRC)
b3.suspension.enabled = False
r = solve_kinematics(b3)
check(not r.ok, "suspension désactivée → ok=False")

# ─── 5. ENVELOPPE MOTEUR M620 + DÉGAGEMENT ──────────────────────────────────
print("\n=== 5. ENVELOPPE MOTEUR M620 + DÉGAGEMENT ===")
from backend.calculations.motor import motor_envelope_world, point_in_polygon
from backend.presets import high_pivot_m620

# 5a. Enveloppe disponible pour le M620, absente sinon
b = load_bcad(SRC)
b.drivetrain.motor_key = "bafang_m620"
b.drivetrain.use_motor = True
env = motor_envelope_world(b.drivetrain)
check(env is not None and len(env) >= 6, "enveloppe M620 générée")
check(point_in_polygon((0.0, 0.0), env), "BB (origine) dans le carter M620")
check(not point_in_polygon((0.0, 300.0), env), "point très haut hors carter")

b.drivetrain.motor_key = "bafang_mm520"
check(motor_envelope_world(b.drivetrain) is None, "pas d'enveloppe pour MM520 (fallback rect)")

# 5b. Preset high-pivot M620 : résout ET dégage le carter
b = load_bcad(SRC)
b.drivetrain.motor_key = "bafang_m620"
b.suspension = high_pivot_m620()
r = solve_kinematics(b)
check(r.ok, f"preset high-pivot M620 résout ({r.message})")
check(r.motor_clearance_ok, f"preset dégage le carter (collisions: {r.motor_collisions})")

# 5c. Pivot délibérément DANS le carter → collision détectée
b.suspension.main_pivot.x = 60.0
b.suspension.main_pivot.y = 0.0     # au cœur du carter M620
r = solve_kinematics(b)
check(not r.motor_clearance_ok and "pivot principal" in r.motor_collisions,
      f"pivot dans le carter → collision signalée ({r.motor_collisions})")

# 5d. Le SVG dessine bien le polygone du carter (class="motor")
b = load_bcad(SRC)
b.drivetrain.motor_key = "bafang_m620"
calc = calculate(b)
svg = render_svg(b, calc, 1400, 750, True, None)
check('class="motor"' in svg and "polygon" in svg, "carter M620 dessiné en polygone dans le SVG")
check(svg_finite(svg), "SVG carter M620 valide")

# ─── 6. SOLVEUR GÉNÉRIQUE PAR CONTRAINTES ───────────────────────────────────
print("\n=== 6. SOLVEUR GÉNÉRIQUE (Newton-Raphson) ===")
b = load_bcad(SRC)
b.suspension.linkage_type = "four_bar_horst"
rh = solve_kinematics(b)
b.suspension.linkage_type = "four_bar_generic"
rg = solve_kinematics(b)
check(rg.ok, f"solveur générique résout ({rg.message})")
check(len(rh.samples) == len(rg.samples), "même nombre d'échantillons")
maxd = 0.0
for a, c in zip(rh.samples, rg.samples):
    for key in ("wheel_travel", "shock_stroke", "leverage", "anti_squat",
                "belt_growth", "axle_x", "axle_y"):
        maxd = max(maxd, abs(getattr(a, key) - getattr(c, key)))
check(maxd < 1e-3, f"générique ≡ hardcodé four-bar (écart max {maxd:.2e})")

# Le noyau de contraintes : test unitaire d'un triangle rigide trivial
from backend.calculations.layouts.generic import solve_constraints
import math as _m
pts = {"P": [0.0, 0.0], "Q": [10.0, 0.0], "R": [3.0, 3.0]}
# R contraint à distance 5 de P et 5 de Q → doit converger vers (5, ±?) ; 5/5/10 colinéaire
pts2 = {"P": [0.0, 0.0], "Q": [6.0, 0.0], "R": [2.0, 2.0]}
ok = solve_constraints(pts2, ["R"], [("P", "R", 5.0), ("Q", "R", 5.0)], [])
dPR = _m.hypot(pts2["R"][0], pts2["R"][1])
dQR = _m.hypot(pts2["R"][0] - 6, pts2["R"][1])
check(ok and abs(dPR - 5) < 1e-6 and abs(dQR - 5) < 1e-6,
      f"noyau contraintes : R à 5/5 de P/Q (got {dPR:.4f}/{dQR:.4f})")

# ─── 7. MODE LUGS — JONCTIONS TUBE↔LUG ──────────────────────────────────────
print("\n=== 7. MODE LUGS ===")
from backend.lugs.joint_model import build_joints
from backend.lugs import export_cad as lx
from backend.lugs.miter import miter_angle, saddle_depth

b = load_bcad(SRC)
calc = calculate(b)
nodes = build_joints(b, calc)
names = {n.name for n in nodes}
check(names == {"head_top", "head_bottom", "bb", "seat_cluster", "dropout"},
      f"5 nœuds-lugs attendus (got {names})")

bb_node = next(n for n in nodes if n.name == "bb")
check(len(bb_node.sockets) == 3, "lug BB : 3 douilles (down/seat/chainstay)")
# Tous les alésages > Ø tube (jeu de collage) et profondeurs > 0
for n in nodes:
    for s in n.sockets:
        check(s.bore_dia > s.tube_od and s.depth > 0,
              f"{n.name}/{s.member}: bore>{s.tube_od} & depth>0")

# Angle seat tube ↔ down tube au BB : doit être plausible (~50–80°)
ang = bb_node.angles.get("down_tube|seat_tube")
check(ang is not None and 40 < ang < 110, f"angle BB down|seat plausible ({ang}°)")

# Le triangle arrière (bases/haubans) marqué hors-plan
cs_oop = any(s.out_of_plane for n in nodes for s in n.sockets if s.member in ("chainstay", "seatstay"))
check(cs_oop, "bases/haubans marqués out_of_plane (triangle fendu 3D)")

# Exports valides
import json as _json
js = lx.to_json(nodes)
check(_json.loads(js)["nodes"], "export JSON parseable")
csv = lx.to_design_table_csv(nodes)
check(csv.startswith("Parameter,Value,Unit") and "bb_seat_tube_axis" in csv, "export CSV SolidWorks")
summ = lx.to_summary(nodes)
check("LUG BB" in summ, "résumé lisible")

# Utilitaires miter
check(abs(miter_angle(0, 90) - 45.0) < 1e-6, "miter 0/90 = 45°")
check(saddle_depth(30, 40) > 0, "saddle depth positive")

# ─── RÉSULTAT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
if fails:
    print(f"ÉCHECS : {len(fails)}")
    for f in fails[:30]:
        print("  -", f)
    sys.exit(1)
print("✓ TOUS LES TESTS E2E PASSENT")
