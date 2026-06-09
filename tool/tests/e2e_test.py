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


_NONFINITE = __import__("re").compile(r"\b(nan|inf|-inf|infinity)\b", __import__("re").I)

def svg_finite(svg: str) -> bool:
    # tokens isolés seulement (évite le faux positif "domi-nan-t" / "baseline")
    if _NONFINITE.search(svg):
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
    "batterie":      'class="battery"',
}
for label, token in components.items():
    check(token in svg, f"composant présent : {label}")

# 3c. Batterie 52V dans le triangle avant : fit + collisions
print("  -- batterie 52V triangle avant --")
from backend.calculations.battery import compute_battery
bk = load_bcad(SRC); cc = calculate(bk)
br = compute_battery(bk, cc)
check(br.ok and br.enabled, "batterie : calcul OK")
check(br.fits_triangle, f"batterie défaut tient dans le triangle ({br.notes})")
check(br.est_capacity_wh > 0 and br.volume_l > 0, "batterie : volume/capacité estimés")
# pack volontairement trop gros → doit être détecté hors triangle
bk.battery.length = 520; bk.battery.height = 140
br2 = compute_battery(bk, cc)
check(not br2.fits_triangle, "batterie surdimensionnée détectée hors triangle")
# désactivée → pas de polygone, ok
bk.battery.enabled = False
check(compute_battery(bk, cc).enabled is False, "batterie désactivable")

# 3b. Overlay suspension (statique + animé) sur la vue 2D, pour les 3 topologies
print("  -- overlay/animation suspension --")
for lt, setup in [
    ("four_bar_horst", lambda s: None),
    ("four_bar_generic", lambda s: None),
    ("high_pivot_idler", lambda s: (
        setattr(s.main_pivot, "x", -20.0), setattr(s.main_pivot, "y", 110.0),
        setattr(s.idler, "x", -10.0), setattr(s.idler, "y", 90.0),
        setattr(s.shock_lower, "x", -120.0), setattr(s.shock_lower, "y", 20.0),
        setattr(s.shock_upper, "x", -10.0), setattr(s.shock_upper, "y", 200.0))),
]:
    bk = load_bcad(SRC); bk.suspension.linkage_type = lt; setup(bk.suspension)
    cc = calculate(bk); kk = solve_kinematics(bk)
    check(kk.ok and len(kk.frames) >= 10, f"{lt}: frames d'animation produites ({len(kk.frames)})")
    svg_st = render_svg(bk, cc, 1400, 750, True, None, suspension=kk.frames, animate_suspension=False)
    svg_an = render_svg(bk, cc, 1400, 750, True, None, suspension=kk.frames, animate_suspension=True)
    check('class="suspension"' in svg_st, f"{lt}: overlay suspension statique présent")
    check('<animate' in svg_an and svg_finite(svg_an), f"{lt}: animation SMIL valide")
    # cohérence frames : course croissante de 0 à ~cible
    tr = [fr["travel"] for fr in kk.frames]
    check(tr[0] == 0.0 and tr[-1] > tr[0], f"{lt}: course frames 0 → {tr[-1]}")

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

# 7b. Export .bcad : intégrité + Free-safe (courroie → chaîne sans crash) ────
print("  -- export .bcad / Free-safe --")
def _kv(p):
    return {e.get("key"): (e.text or "") for e in ET.parse(p).findall(".//entry")}
b = load_bcad(SRC)
check(b.drivetrain.drive_type == "belt", "modèle interne = courroie")
orig_keys = set(_kv(SRC))
# Export full (Pro) : garde la courroie =2, round-trip lossless
save_bcad(b, "/tmp/e2e_pro.bcad", source_path=SRC, backup=False, free_safe=False)
pro = _kv("/tmp/e2e_pro.bcad")
check(pro.get("BELTorCHAIN") == "2", "export full : BELTorCHAIN=2 (courroie)")
check(set(pro) == orig_keys, "export full : 0 clé perdue/ajoutée")
# Export Free-safe : rétrograde en chaîne =1 (ne crashe pas BikeCAD Free)
save_bcad(b, "/tmp/e2e_free.bcad", source_path=SRC, backup=False, free_safe=True)
free = _kv("/tmp/e2e_free.bcad")
check(free.get("BELTorCHAIN") == "1", "export Free-safe : BELTorCHAIN=1 (chaîne)")
check(set(free) == orig_keys, "export Free-safe : 0 clé perdue/ajoutée")
check(_kv(SRC).get("BELTorCHAIN") == "2", "fichier principal inchangé (=2)")

# ─── 8. BIBLIOTHÈQUE — SAUVE/IMPORT/EXPORT TOUS COMPOSANTS ──────────────────
print("\n=== 8. BIBLIOTHÈQUE (round-trip tous composants) ===")
from backend import library as lib
from backend.presets import high_pivot_m620

SECTIONS = ["frame", "fork", "headtube", "headset", "stem", "handlebar",
            "saddle", "seatpost", "cranks", "wheel_f", "wheel_r", "pedals",
            "brakes", "drivetrain", "suspension"]

# Design non trivial : suspension high-pivot + selle A→N + moteur M620 + rider
b = load_bcad(SRC)
b.suspension = high_pivot_m620()
b.drivetrain.motor_key = "bafang_m620"
b.saddle.a = 12.3; b.saddle.n = 4.5; b.saddle.angle = -2.0
b.stem.x = 7.0; b.stem.y = -3.0
b.seatpost.exposed = 173.0
b.rider = RiderConfig()
b.name = "E2E Test Lossless"

# Sauvegarde + rechargement bibliothèque
path = lib.save_bike(b, b.name)
check(path.exists() and path.suffix == ".json", f"vélo sauvegardé ({path.name})")
reloaded = lib.load_bike(path.name)

# Tous les composants identiques au round-trip
orig = b.model_dump()
back = reloaded.model_dump()
for sec in SECTIONS:
    check(orig[sec] == back[sec], f"composant '{sec}' préservé (lossless)")
check(orig["name"] == back["name"], "nom préservé")
check(orig["rider"] == back["rider"], "rider préservé")
# Points sensibles que le .bcad PERD mais que la biblio conserve
check(back["suspension"]["linkage_type"] == "high_pivot_idler", "suspension topologie préservée")
check(abs(back["suspension"]["main_pivot"]["y"] - b.suspension.main_pivot.y) < 1e-9, "pivots suspension préservés")
check(abs(back["saddle"]["a"] - 12.3) < 1e-9, "selle A préservée")
check(abs(back["stem"]["x"] - 7.0) < 1e-9, "offset potence X préservé")
check(abs(back["seatpost"]["exposed"] - 173.0) < 1e-9, "tige selle exposée préservée")

# La bibliothèque liste le vélo
listed = lib.list_bikes()
check(any(x["name"] == "E2E Test Lossless" for x in listed), "vélo listé en bibliothèque")

# Anti path-traversal
try:
    lib.load_bike("../../../etc/passwd")
    check(False, "path-traversal bloqué")
except Exception:
    check(True, "path-traversal bloqué (chemin hors biblio refusé)")

# Documenté : le .bcad PERD la suspension (d'où la biblio JSON)
import tempfile as _tf
tmp_bcad = _tf.mktemp(suffix=".bcad")
save_bcad(b, tmp_bcad, source_path=SRC, backup=False)
via_bcad = load_bcad(tmp_bcad)
check(via_bcad.suspension.linkage_type == "four_bar_horst",
      "(attendu) .bcad NE conserve PAS la suspension → défaut au reload")

# Nettoyage du fichier de test bibliothèque
path.unlink(missing_ok=True)

# ─── 9. ASSISTANT — OUTILS PILOTANT LE VÉLO (sans clé API) ───────────────────
print("\n=== 9. ASSISTANT (logique outils) ===")
from backend import assistant as ASSIST

b = load_bcad(SRC)
data = b.model_dump()
acts = []
# 9a. set_parameters : champ valide, pivot, champ invalide rejeté
out = ASSIST._exec_tool("set_parameters", {"edits": [
    {"section": "frame", "field": "head_angle", "value": 63.5},
    {"section": "suspension", "field": "main_pivot", "axis": "y", "value": 95.0},
    {"section": "frame", "field": "champ_bidon", "value": 1},
]}, data, acts)
check(abs(data["frame"]["head_angle"] - 63.5) < 1e-9, "assistant: édite head_angle")
check(abs(data["suspension"]["main_pivot"]["y"] - 95.0) < 1e-9, "assistant: édite un pivot {x,y}")
check("champ inconnu" in out, "assistant: champ invalide rejeté proprement")
check("frame.head_angle=63.5" in acts, "assistant: action journalisée")

# 9b. apply_preset
ASSIST._exec_tool("apply_preset", {"name": "high_pivot_m620"}, data, acts)
check(data["suspension"]["linkage_type"] == "high_pivot_idler", "assistant: preset applique la topologie")
check(data["drivetrain"]["motor_key"] == "bafang_m620", "assistant: preset bascule le moteur M620")

# 9c. get_state contient géométrie + cinématique
state = ASSIST._exec_tool("get_state", {}, data, acts)
check("reach=" in state and "anti_squat_sag" in state, "assistant: get_state résume géométrie+cinématique")

# 9d. outils bien définis (schémas)
names = {t["name"] for t in ASSIST.TOOLS}
check({"set_parameters", "apply_preset", "get_state", "list_library",
       "save_bike", "load_bike"} <= names, f"assistant: outils de base présents ({names})")
for t in ASSIST.TOOLS:
    check("input_schema" in t and t["input_schema"]["type"] == "object",
          f"assistant: schéma valide pour {t['name']}")

# 9e. system prompt mentionne le garde-fou structurel
sp = ASSIST._system_prompt(ASSIST._state_summary(data))
check("structurelle" in sp and "bureau d'études" in sp, "assistant: garde-fou structurel dans le system prompt")

# ─── 10. ANALYSE (sag / compression / axes) + BANQUE DE CONNAISSANCES ───────
print("\n=== 10. ANALYSE + KNOWLEDGE ===")
from backend.calculations import analysis as AN
from backend import knowledge as KN

b = load_bcad(SRC)
# 10a. compute_sag : raideur → sag, et cible → raideur requise (cohérence inverse)
s1 = AN.compute_sag(b, spring_rate_n_per_mm=500)
check(s1["ok"] and s1["wheel_sag_mm"] > 0 and 0 < s1["sag_pct"] < 100, f"sag depuis raideur ({s1.get('sag_pct')}%)")
s2 = AN.compute_sag(b, target_sag_pct=30)
req = s2["required_spring_rate_N_per_mm"]
check(req and req > 0, f"raideur requise pour 30% ({req} N/mm)")
# vérif inverse : appliquer la raideur requise redonne ~30%
s3 = AN.compute_sag(b, spring_rate_n_per_mm=req)
check(abs(s3["sag_pct"] - 30) < 0.5, f"inverse sag cohérent ({s3['sag_pct']}% ≈ 30)")
check(s1["rear_wheel_load_N"] > 0 and s1["shock_force_N"] > s1["rear_wheel_load_N"],
      "charges : force amorto = force roue × LR > force roue")

# 10b. compression_state : sag, %, mm bornés ; métriques présentes
cs = AN.compression_state(b, at_sag=True)
check(cs["ok"] and abs(cs["travel_pct"] - b.suspension.sag_percent) < 0.5, "compression au sag")
for key in ("leverage", "anti_squat_pct", "belt_growth_mm", "pedal_kickback_deg", "axle", "axle_rearward_mm"):
    check(key in cs, f"compression_state contient {key}")
check(AN.compression_state(b, at_mm=99999)["wheel_travel_mm"] <= cs["total_travel_mm"], "compression bornée à la course max")

# 10c. wheel_axles : axes + chemin d'axe
ax = AN.wheel_axles(b)
check(ax["rear_axle"][0] < 0 < ax["front_axle"][0], "axes de part et d'autre du BB")
check(abs(ax["wheelbase"] - (ax["front_axle"][0] - ax["rear_axle"][0])) < 0.5, "empattement = AV-AR")
check(len(ax.get("rear_axle_path", [])) >= 5, "chemin d'axe AR échantillonné")

# 10d. banque de connaissances : récupération pertinente + catalogue pièces du dépôt
hits = KN.search("couple moteur M620 chain line", 3)
check(hits and hits[0]["title"].startswith("Moteur Bafang M620"), f"knowledge: M620 top-hit ({hits[0]['title'] if hits else None})")
check(KN.search("manivelle crank", 3), "knowledge: trouve les manivelles")
parts = [e for e in KN.entries() if e["id"].startswith("parts-")]
check(any("manivelles" in e["title"] for e in parts), "catalogue pièces scanné depuis le dépôt (CRANKS)")
check(KN.search("zzzznotaword", 2) == [], "knowledge: requête sans match → vide")

# 10e. assistant expose les nouveaux outils + les exécute
from backend import assistant as ASSIST
names = {t["name"] for t in ASSIST.TOOLS}
for t in ("compute_sag", "compression_state", "wheel_axles", "search_knowledge"):
    check(t in names, f"assistant: outil {t} exposé")
d2 = b.model_dump(); a2 = []
import json as _j
sag_out = _j.loads(ASSIST._exec_tool("compute_sag", {"target_sag_pct": 28}, d2, a2))
check(sag_out["ok"] and sag_out["required_spring_rate_N_per_mm"] > 0, "assistant: compute_sag exécute")
kn_out = ASSIST._exec_tool("search_knowledge", {"query": "courroie gates belt growth"}, d2, a2)
check("Gates" in kn_out or "courroie" in kn_out.lower(), "assistant: search_knowledge exécute")

# ─── RÉSULTAT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
if fails:
    print(f"ÉCHECS : {len(fails)}")
    for f in fails[:30]:
        print("  -", f)
    sys.exit(1)
print("✓ TOUS LES TESTS E2E PASSENT")
