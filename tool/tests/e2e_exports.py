"""Test E2E « exports & modifications » — DOM Engineering Bike Tool.

Vérifie, via les MÊMES endpoints HTTP que le frontend, que :
  1. CHAQUE export produit une sortie valide et non vide (report, tubes ×5 formats,
     visserie, pivots, lugs, DXF, plan, .bcad) ;
  2. les MODIFICATIONS de paramètres se propagent réellement aux calculs et aux
     exports (la sortie CHANGE quand on change une entrée — pas de valeur figée).

Prérequis : backend en route sur :8000 (cd tool && ./start.sh, ou uvicorn).
Lancer : cd tool && .venv/bin/python tests/e2e_exports.py
"""

import copy
import json
import sys
import urllib.request

BASE = "http://localhost:8000/api"
fails = []


def check(cond, msg):
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        fails.append(msg)
    return cond


def _req(method, path, payload=None, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        body = r.read().decode()
    ctype = r.headers.get("Content-Type", "")
    if raw:
        return body, ctype
    return json.loads(body) if "json" in ctype else body


def GET(p):
    return _req("GET", p)


def POST(p, payload, raw=False):
    return _req("POST", p, payload, raw)


def as_obj(x):
    """Tolère une réponse déjà parsée (Content-Type json) ou une chaîne JSON."""
    return x if isinstance(x, (dict, list)) else json.loads(x)


def patched(bike, section, patch):
    b = copy.deepcopy(bike)
    b[section] = {**b.get(section, {}), **patch}
    return b


# ─── 0. CHARGEMENT ───────────────────────────────────────────────────────────
print("\n=== 0. Design par défaut ===")
bike = GET("/default")
check(isinstance(bike, dict) and "frame" in bike, "GET /default")
bike["name"] = "E2E exports"

# ─── 1. TOUS LES EXPORTS PRODUISENT UNE SORTIE VALIDE ───────────────────────
print("\n=== 1. Exports — sortie valide & non vide ===")

# 1a. Dossier de conception (HTML)
rep, ct = POST("/export/report", {"bike": bike, "designer": "E2E", "revision": "C"}, raw=True)
check("text/html" in ct and rep.startswith("<!doctype html>"), "report : Content-Type HTML")
check(len(rep) > 30000 and rep.count("<svg") >= 2, f"report : substantiel + figures ({len(rep)} o)")
for tok in ("Synthèse", "Cinématique", "Tubes &amp; masses", "Visserie", "EN 17404"):
    check(tok in rep, f"report : section/contenu « {tok} »")

# 1b. Tubes — 5 formats
for fmt, needle in [("csv", "NOMENCLATURE D'ACHAT"), ("summary", "TUBES & LUGS"),
                    ("json", '"tubes"'), ("fab_csv", "Entraxe_mm"),
                    ("fab_summary", "FICHE DE FABRICATION")]:
    out = POST("/export/tubes", {"bike": bike, "fmt": fmt})
    check(isinstance(out, (str, dict)) and (needle in (out if isinstance(out, str) else json.dumps(out))),
          f"export tubes [{fmt}] : contenu attendu")

# 1c. Visserie
for fmt, needle in [("csv", ","), ("summary", "")]:
    out = POST("/export/fasteners", {"bike": bike, "fmt": fmt})
    check(isinstance(out, str) and len(out) > 50, f"export visserie [{fmt}] : non vide")
fjson = POST("/export/fasteners", {"bike": bike, "fmt": "json"})
check(as_obj(fjson).get("items") is not None, "export visserie [json] : parseable")

# 1d. Pivots
pj = POST("/export/pivots", {"bike": bike, "fmt": "json"})
check(as_obj(pj).get("ok") is not None, "export pivots [json] : parseable")
check(len(POST("/export/pivots", {"bike": bike, "fmt": "csv"})) > 30, "export pivots [csv] : non vide")

# 1e. Lugs
lj = POST("/export/lugs", {"bike": bike, "fmt": "json"})
check(as_obj(lj).get("nodes") is not None, "export lugs [json] : nœuds présents")
check("LUG" in POST("/export/lugs", {"bike": bike, "fmt": "summary"}), "export lugs [summary] : non vide")

# 1f. DXF
dxf = POST("/export/dxf", {"bike": bike})
check(isinstance(dxf, str) and dxf.strip().endswith("EOF"), "export DXF : R12 valide (EOF)")

# 1g. Plan technique
plan = POST("/export/drawing", {"bike": bike})
check(isinstance(plan, str) and "<svg" in plan and "</svg>" in plan, "export plan : SVG valide")

# 1h. .bcad Free-safe (écrit disque)
bc = POST("/export/bcad", {"bike": bike, "path": "/tmp/e2e_exports.bcad",
                           "source_path": None, "free_safe": True})
check(bc.get("ok"), "export .bcad : écriture OK")

# 1i. report écrit disque
rf = POST("/export/report", {"bike": bike, "path": "/tmp/e2e_exports_dossier.html"})
check(rf.get("ok") and rf.get("bytes", 0) > 30000, "report : écriture disque OK")

# ─── 2. MODIFICATIONS — propagation aux CALCULS ─────────────────────────────
print("\n=== 2. Modifications → calculs (la sortie change) ===")
calc0 = POST("/calc", bike)

# 2a. Angle de direction → reach & trail changent
b_ha = patched(bike, "frame", {"head_angle": bike["frame"]["head_angle"] - 2.0})
calc1 = POST("/calc", b_ha)
check(abs(calc1["reach"] - calc0["reach"]) > 1.0, "HA −2° → reach change")
check(abs(calc1["trail"] - calc0["trail"]) > 3.0, "HA −2° → trail change")

# 2b. Base arrière (cs) → empattement change
b_cs = patched(bike, "frame", {"cs": bike["frame"]["cs"] + 20.0})
calc2 = POST("/calc", b_cs)
check(abs(calc2["wheelbase"] - calc0["wheelbase"]) > 15.0, "cs +20 → empattement change")

# 2c. Reach répond à FCD
b_fcd = patched(bike, "frame", {"fcd": bike["frame"]["fcd"] + 25.0})
check(POST("/calc", b_fcd)["reach"] - calc0["reach"] > 10.0, "fcd +25 → reach augmente")

# ─── 3. MODIFICATIONS — propagation aux TUBES / MASSES / BOM ────────────────
print("\n=== 3. Modifications → tubes & nomenclature d'achat ===")
t0 = POST("/tubes", {"bike": bike})

# 3a. Paroi plus épaisse → masse augmente
b_wall = patched(bike, "frame", {"down_tube_wall": bike["frame"]["down_tube_wall"] + 1.0})
t_wall = POST("/tubes", {"bike": b_wall})
check(t_wall["total_mass_g"] > t0["total_mass_g"] + 20, "paroi +1 mm → masse tubes augmente")

# 3b. Matériau titane → masse diffère nettement de l'alu
b_ti = patched(bike, "frame", {"frame_material": "titane_3al25v"})
t_ti = POST("/tubes", {"bike": b_ti})
check(abs(t_ti["total_mass_g"] - t0["total_mass_g"]) > 100,
      f"matériau titane → masse change ({t0['total_mass_g']}→{t_ti['total_mass_g']} g)")
check(any("Titane" in g["label"] for g in t_ti["bom"]), "BOM reflète le matériau titane")

# 3c. Carbone → capacité scalaire N/D
b_c = patched(bike, "frame", {"frame_material": "carbone_ud"})
t_c = POST("/tubes", {"bike": b_c})
check(all(t["moment_yield_nm"] == 0 for t in t_c["tubes"]), "carbone → capacité scalaire N/D")

# 3d. Ø tube → barre conseillée (BOM) change
b_od = patched(bike, "frame", {"down_tube_d": bike["frame"]["down_tube_d"] + 4.0})
t_od = POST("/tubes", {"bike": b_od})
check(json.dumps(t_od["bom"]) != json.dumps(t0["bom"]), "Ø tube +4 → BOM change")

# 3e. Test de résistance : moment → FS calculé
t_lc = POST("/tubes", {"bike": bike, "test_moment_nm": 350.0, "test_tube": "down_tube"})
check(t_lc["load_case"] and t_lc["load_case"]["fs"] > 0, "test résistance : FS calculé")

# ─── 4. MODIFICATIONS — cinématique / transmission / batterie ───────────────
print("\n=== 4. Modifications → suspension, transmission, batterie ===")

# 4a. Preset suspension → cinématique différente
k0 = POST("/kinematics", bike)
preset = GET("/suspension/preset/scott_ransom_style")
b_susp = copy.deepcopy(bike)
b_susp["suspension"] = preset
k1 = POST("/kinematics", b_susp)
check(k1["ok"], "preset scott_ransom : cinématique résout")
check(abs(k1["total_travel"] - k0["total_travel"]) > 1 or
      abs(k1["leverage_start"] - k0["leverage_start"]) > 0.05 or
      abs(k1["anti_squat_sag"] - k0["anti_squat_sag"]) > 1,
      "preset suspension → courbes cinématiques changent")

# 4b. Transmission dérailleur ↔ IGH
b_dr = patched(bike, "drivetrain", {"transmission": "derailleur"})
tx_dr = POST("/transmission", b_dr)
b_igh = patched(bike, "drivetrain", {"transmission": "igh", "igh_model": "rohloff_14"})
tx_igh = POST("/transmission", b_igh)
check(tx_dr["kind"] == "derailleur" and tx_igh["kind"] == "igh", "transmission : dérailleur ↔ IGH bascule")
check(tx_igh["max_torque_nm"] > 0, "IGH Rohloff : limite de couple renseignée")

# 4c. Batterie : capacité Wh → autonomie change
b_bat = patched(bike, "battery", {"enabled": True, "capacity_wh": 720.0})
bat1 = POST("/battery", b_bat)
b_bat2 = patched(bike, "battery", {"enabled": True, "capacity_wh": 1100.0})
bat2 = POST("/battery", b_bat2)
check(bat2["est_capacity_wh"] != bat1["est_capacity_wh"] or
      (bat2["autonomy"] and bat1["autonomy"] and
       bat2["autonomy"][0]["km"] != bat1["autonomy"][0]["km"]),
      "batterie : capacité Wh → autonomie/encombrement change")

# ─── 5. MODIFICATION → RENDU (l'aperçu reflète le changement) ───────────────
print("\n=== 5. Modification → rendu SVG (l'aperçu change) ===")
r0 = POST("/render/svg", {"bike": bike, "width": 1400, "height": 750, "show_dims": True})["svg"]
b_seat = patched(bike, "frame", {"seat_angle": bike["frame"]["seat_angle"] - 3.0})
r1 = POST("/render/svg", {"bike": b_seat, "width": 1400, "height": 750, "show_dims": True})["svg"]
check(r0 != r1, "STA −3° → le SVG rendu change")
# toggles de calques modifient le rendu
r_pivots = POST("/render/svg", {"bike": bike, "width": 1400, "height": 750, "show_pivots": True})["svg"]
check(r_pivots != r0, "toggle Pivots → le SVG change")

# ─── 6. MODIFICATION → DOSSIER (le rapport reflète le changement) ───────────
print("\n=== 6. Modification → dossier de conception ===")
rep_ti, _ = POST("/export/report", {"bike": b_ti}, raw=True)
check("Titane" in rep_ti or "titane" in rep_ti, "report : matériau modifié reflété dans le dossier")

# ─── RÉSULTAT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 56)
if fails:
    print(f"ÉCHECS : {len(fails)}")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("✓ EXPORTS & MODIFICATIONS : tout marche")
