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

# ─── RÉSULTAT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
if fails:
    print(f"ÉCHECS : {len(fails)}")
    for f in fails[:30]:
        print("  -", f)
    sys.exit(1)
print("✓ TOUS LES TESTS E2E PASSENT")
