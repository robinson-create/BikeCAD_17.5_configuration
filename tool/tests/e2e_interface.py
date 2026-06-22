"""Test E2E « parcours interface » — DOM Engineering Bike Tool.

Reproduit ce que fait le frontend Svelte : mêmes endpoints HTTP, même séquence
(GET /api/default → on règle les specs du projet comme via les panneaux →
/api/render/svg avec tous les calques → kinematics / fit / battery → catalogue →
exports). Vérifie le FONCTIONNEL (valeurs, codes) ET le GRAPHIQUE (composants
présents, rien hors-canvas, pas de NaN, cotes cohérentes).

Prérequis : backend en route sur :8000  (cd tool && ./start.sh, ou uvicorn).
Lancer : cd tool && .venv/bin/python tests/e2e_interface.py
"""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

BASE = "http://localhost:8000/api"
W, H = 1400, 750
fails = []


def check(cond, msg):
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        fails.append(msg)
    return cond


def _req(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
    ctype = r.headers.get("Content-Type", "")
    return json.loads(body) if "json" in ctype else body


def GET(path):  return _req("GET", path)
def POST(path, payload):  return _req("POST", path, payload)


# ── Specs du projet (eMTB DOM Engineering) ───────────────────────────────────
PROJECT = {
    "frame": {"head_angle": 64.0, "seat_angle": 78.0, "cs": 435.0, "bb_drop": 30.0,
              "fcd": 820.0, "seat_tube": 423.0, "head_tube": 125.0,
              "wheel_f": 736.0, "wheel_r": 736.0},
    "fork":  {"travel": 160.0, "sag": 40.0, "a2c": 570.8, "offset": 44.0, "dual_crown": True},
    "drivetrain": {"drive_type": "belt", "motor_key": "bafang_m620", "use_motor": True},
    # mount_offset 140 : pousse le pack en haut du tube diagonal pour dégager le
    # gros carter M620 (collision sous ~120 mm — contrainte d'intégration réelle).
    "battery": {"enabled": True, "voltage": 52.0, "capacity_wh": 960.0,
                "length": 380.0, "height": 90.0, "mount_offset": 140.0},
    "suspension": {"enabled": True, "linkage_type": "four_bar_horst", "rear_travel": 160.0},
}

RIDER = {"inseam": 810, "lower_leg": 380, "upper_leg": 430, "torso_length": 580,
         "upper_arm": 300, "lower_arm": 260, "shoulder_width": 410, "shoe_length": 270,
         "pelvis_thickness": 200, "knee_thickness": 90, "ankle_thickness": 65,
         "elbow_thickness": 70, "arm_thickness": 80, "forehead_to_back": 200,
         "shoulder_to_jaw": 220, "hip_angle": 0, "knee_angle": 0, "torso_angle": 0,
         "shoulder_angle": 0, "elbow_angle": 0, "shoulder_roll": 0}


def svg_bounds_ok(svg, tol=0.06):
    """Aucune coordonnée hors du canvas (tolérance), XML valide, pas de NaN/Inf."""
    if re.search(r"\b(nan|inf|infinity)\b", svg, re.I):
        return False, "NaN/Inf dans le SVG"
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as e:
        return False, f"XML invalide: {e}"
    bad = 0
    for el in root.iter():
        for a in ("x", "y", "cx", "cy", "x1", "y1", "x2", "y2"):
            v = el.get(a)
            if v is None:
                continue
            try:
                f = float(v)
            except ValueError:
                continue
            lim = W if a in ("x", "cx", "x1", "x2") else H
            if f < -tol * lim or f > (1 + tol) * lim:
                bad += 1
    return bad == 0, f"{bad} coords hors-canvas"


# ─── 1. CHARGEMENT INITIAL (comme onMount) ───────────────────────────────────
print("\n=== 1. /api/default (chargement initial de l'interface) ===")
bike = GET("/default")
check(isinstance(bike, dict) and "frame" in bike, "design par défaut chargé")

# ─── 2. SAISIE DES SPECS PROJET (comme les panneaux) ─────────────────────────
print("\n=== 2. Saisie des specs projet (panneaux) ===")
for section, patch in PROJECT.items():
    bike[section] = {**bike.get(section, {}), **patch}
bike["rider"] = RIDER
bike["name"] = "eMTB DOM Engineering (E2E)"
check(bike["frame"]["head_angle"] == 64.0 and bike["drivetrain"]["motor_key"] == "bafang_m620",
      "specs appliquées au design")

# ─── 3. RENDU COMPLET (render/svg, tous calques) ─────────────────────────────
print("\n=== 3. Rendu graphique (tous calques activés) ===")
r = POST("/render/svg", {"bike": bike, "width": W, "height": H,
                         "show_dims": True, "show_rider": True,
                         "show_suspension": True, "animate_suspension": True})
svg = r["svg"]; calc = r["calc"]
check(len(svg) > 5000, f"SVG généré ({len(svg)} o)")
ok_b, why = svg_bounds_ok(svg)
check(ok_b, f"graphique : rien hors-canvas, XML valide, sans NaN ({why})")

# Présence de TOUS les composants graphiques
import importlib.util as _ilu, pathlib as _pl
_spec = _ilu.spec_from_file_location(
    "svg_palette", _pl.Path(__file__).resolve().parents[1] / "backend/io/svg_export.py")
# import léger de la PALETTE sans démarrer tout le backend
try:
    from backend.io.svg_export import PALETTE
except Exception:
    PALETTE = {"fork_low": "#1c1f24", "belt": "#f0a51f", "motor": "#33373d", "dim_line": "#2f6df0"}

COMPONENTS = {
    "cadre (tubes)": "<polygon", "roues": 'class="wheel"', "fourche": PALETTE["fork_low"],
    "transmission": 'class="drivetrain"', "courroie": PALETTE["belt"], "moteur": PALETTE["motor"],
    "freins": 'class="brakes"', "pédales": 'class="pedals"',
    "batterie": 'class="battery"', "suspension": 'class="suspension"',
    "pilote": 'class="rider"', "animation": "<animate", "cotes": PALETTE["dim_line"],
}
for name, token in COMPONENTS.items():
    check(token in svg, f"composant affiché : {name}")

# ─── 4. GÉOMÉTRIE vs CIBLES PROJET ───────────────────────────────────────────
print("\n=== 4. Géométrie vs cibles projet ===")
check(470 <= calc["reach"] <= 500, f"reach {calc['reach']} ≈ cible 480 mm")
check(580 <= calc["stack"] <= 645, f"stack {calc['stack']} mm plausible")
check(110 <= calc["trail"] <= 150, f"trail {calc['trail']} mm plausible")
check(1200 <= calc["wheelbase"] <= 1320, f"empattement {calc['wheelbase']} mm")
check(76 <= calc["effective_sta"] <= 80, f"STA effectif {calc['effective_sta']}°")
# roues au sol
check(abs((calc["rear_axle"]["y"] - bike["frame"]["wheel_r"]/2) - calc["ground_level"]) < 0.6,
      "roue AR au sol (cohérence verticale)")

# ─── 5. CINÉMATIQUE ──────────────────────────────────────────────────────────
print("\n=== 5. Cinématique ===")
kin = POST("/kinematics", bike)
check(kin["ok"], f"cinématique résolue ({kin['message'][:60]})")
check(150 <= kin["total_travel"] <= 170, f"course roue {kin['total_travel']} mm ≈ 160")
check(len(kin["frames"]) >= 10, f"frames d'animation ({len(kin['frames'])})")

# ─── 6. FIT PILOTE ───────────────────────────────────────────────────────────
print("\n=== 6. Fit pilote ===")
fit = POST("/fit", bike)
check(fit["ok"] and fit["saddle_height"] > 0, f"fit OK (selle {fit['saddle_height']} mm)")
check(fit["knee_angle_bdc"] is not None, "angle de genou calculé")

# ─── 7. BATTERIE 52V dans le triangle avant ──────────────────────────────────
print("\n=== 7. Batterie 52V ===")
bat = POST("/battery", bike)
check(bat["ok"] and bat["enabled"], "batterie calculée")
check(bat["fits_triangle"], f"batterie 52V tient dans le triangle ({bat['notes']})")
check(bat["clears_motor"], "batterie dégage le carter M620")

# ─── 8. CATALOGUE : appliquer une vraie fourche ──────────────────────────────
print("\n=== 8. Catalogue (appliquer une fourche réelle) ===")
forks = GET("/catalog/fork")
fox = next((f for f in forks if "140" in f["name"] and "Fox" in f["name"]), forks[1])
patch = POST(f"/catalog/fork/load", {"file": fox["file"]})
check("fork" in patch and patch["fork"]["a2c"] > 0,
      f"fourche catalogue chargée : {fox['name']} (A2C {patch['fork']['a2c']})")
bike["fork"] = {**bike["fork"], **patch["fork"]}
r2 = POST("/render/svg", {"bike": bike, "width": W, "height": H, "show_dims": True})
check(svg_bounds_ok(r2["svg"])[0], "re-rendu après fourche catalogue : graphique OK")

# ─── 9. EXPORTS (DXF, .bcad Free-safe, lugs) ─────────────────────────────────
print("\n=== 9. Exports ===")
dxf = POST("/export/dxf", {"bike": bike})
check(isinstance(dxf, str) and dxf.strip().endswith("EOF"), "export DXF (R12) valide")
bc = POST("/export/bcad", {"bike": bike, "path": "/tmp/e2e_iface.bcad",
                           "source_path": None, "free_safe": True})
check(bc.get("ok"), "export .bcad Free-safe OK")
lugs = POST("/export/lugs", {"bike": bike, "fmt": "summary"})
check("LUG BB" in lugs, "export lugs (résumé) OK")

# ─── 9b. LIVRABLES INGÉNIERIE (dossier de conception + export tubes) ──────────
print("\n=== 9b. Dossier de conception + export tubes ===")
# Export tubes : nomenclature d'achat dans le CSV standard
tcsv = POST("/export/tubes", {"bike": bike, "fmt": "csv"})
check("NOMENCLATURE D'ACHAT" in tcsv, "export tubes CSV : nomenclature d'achat intégrée")
# Fiche de fabrication (tubes ↔ jonctions de lugs)
tfab = POST("/export/tubes", {"bike": bike, "fmt": "fab_summary"})
check("FICHE DE FABRICATION" in tfab and "ANGLES DE LUG" in tfab, "export tubes : fiche de fabrication")
tfabc = POST("/export/tubes", {"bike": bike, "fmt": "fab_csv"})
check(tfabc.splitlines()[0].startswith("Membre,Label,Spec,Entraxe_mm"), "export tubes fab CSV : en-tête")
# Dossier de conception (HTML agrégé)
rep = POST("/export/report", {"bike": bike, "designer": "E2E", "revision": "B"})
check(rep.startswith("<!doctype html>") and "Dossier de conception" in rep, "dossier : HTML auto-suffisant")
check(rep.count("<svg") >= 2 and "Cinématique" in rep, "dossier : figures + sections agrégées")
check("EN 17404" in rep and "bureau d'études" in rep, "dossier : rappels normatifs + garde-fou")
# Écriture disque via path
repf = POST("/export/report", {"bike": bike, "path": "/tmp/e2e_iface_dossier.html"})
check(repf.get("ok") and repf.get("bytes", 0) > 30000, "dossier : écriture disque OK")

# ─── 10. PRESET VÉLO COMPLET (menu Modèle) ───────────────────────────────────
print("\n=== 10. Preset vélo complet (menu Modèle) ===")
bikes = GET("/catalog/bike")
mtb = next((b for b in bikes if b["name"] == "MTB"), bikes[0])
full = POST("/catalog/bike/load", {"file": mtb["file"]})
check("__full__" in full and "frame" in full["__full__"], f"preset complet « {mtb['name']} » chargé")
r3 = POST("/render/svg", {"bike": full["__full__"], "width": W, "height": H, "show_dims": True})
check(svg_bounds_ok(r3["svg"])[0], "rendu du preset vélo : graphique OK")

# ─── RÉSULTAT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 56)
if fails:
    print(f"ÉCHECS : {len(fails)}")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("✓ PARCOURS INTERFACE COMPLET : tout marche, graphiquement OK")
