"""Dossier de conception — rapport HTML agrégé, transmissible aux ingénieurs.

Rassemble en UN seul document auto-suffisant (imprimable → PDF par le navigateur)
tout ce que l'outil sait du vélo à partir d'une géométrie VALIDÉE :
  géométrie · plan technique · cinématique · tubes & masses · nomenclature d'achat ·
  jonctions de lugs · pivots (roulements/axes) · visserie · motorisation/batterie/
  transmission · fit pilote · conformité (rappels normatifs) · garde-fous.

Pur Python + chaînes HTML (aucune dépendance lourde — cohérent avec le dépôt).
Les SVG (vue de profil + plan coté) sont intégrés inline pour un fichier unique.
"""

import html
from datetime import date as _date

from ..calculations.geometry import calculate
from ..calculations.kinematics import solve_kinematics
from ..calculations.fit import compute_fit
from ..calculations.battery import compute_battery
from ..calculations.transmission import compute_transmission
from ..calculations.pivots import compute_pivots
from ..calculations.fasteners import compute_fasteners
from ..calculations.tubes import compute_tubes
from ..lugs.joint_model import build_joints
from .svg_export import render_svg
from .drawing_export import render_drawing_svg


def _esc(v):
    return html.escape(str(v))


def _fmt(v, unit="", nd=1):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "oui" if v else "non"
    if isinstance(v, (int, float)):
        s = f"{v:.{nd}f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
        return f"{s}{(' ' + unit) if unit else ''}"
    return _esc(v)


def _verdict(ok, ok_txt="conforme", no_txt="à revoir"):
    cls = "ok" if ok else "no"
    return f'<span class="badge {cls}">{ok_txt if ok else no_txt}</span>'


def _kv_table(rows):
    """rows = [(label, value), …] ; saute les valeurs None."""
    body = "".join(
        f"<tr><th>{_esc(lbl)}</th><td>{val}</td></tr>"
        for lbl, val in rows if val is not None
    )
    return f'<table class="kv">{body}</table>'


def _section(num, title, body, note=None):
    n = f'<span class="snum">{num}</span>' if num else ""
    nt = f'<p class="snote">{note}</p>' if note else ""
    return f'<section><h2>{n}{_esc(title)}</h2>{body}{nt}</section>'


# ── Sections ────────────────────────────────────────────────────────────────

def _sec_synthese(bike, calc, kin, tubes):
    rows = [
        ("Modèle", _esc(bike.name or "—")),
        ("Reach", _fmt(calc.reach, "mm")),
        ("Stack", _fmt(calc.stack, "mm")),
        ("Empattement", _fmt(calc.wheelbase, "mm")),
        ("Angle de direction", _fmt(bike.frame.head_angle, "°")),
        ("Angle de selle effectif", _fmt(calc.effective_sta, "°")),
        ("Hauteur de BB", _fmt(calc.bb_height, "mm")),
        ("Chasse (trail)", _fmt(calc.trail, "mm")),
        ("Masse tubes (cadre nu)", _fmt(tubes.total_mass_g, "g", 0)),
    ]
    if kin and kin.ok:
        rows += [
            ("Débattement roue AR", _fmt(kin.total_travel, "mm")),
            ("Ratio de levier (début→fin)", f"{_fmt(kin.leverage_start)} → {_fmt(kin.leverage_end)}"),
            ("Progressivité", _fmt(kin.progressivity, "%")),
            ("Anti-squat au sag", _fmt(kin.anti_squat_sag, "%")),
        ]
    return _section("1", "Synthèse", _kv_table(rows))


def _sec_geometrie(bike, calc, drawing_svg):
    rows = [
        ("Reach / Stack", f"{_fmt(calc.reach,'mm')} / {_fmt(calc.stack,'mm')}"),
        ("Empattement", _fmt(calc.wheelbase, "mm")),
        ("Front-center", _fmt(calc.front_center, "mm")),
        ("Tube horizontal effectif", _fmt(calc.tt_effective, "mm")),
        ("Enjambement (standover)", _fmt(calc.standover, "mm")),
        ("Angle de direction", _fmt(bike.frame.head_angle, "°")),
        ("Angle de selle (réel / effectif)", f"{_fmt(bike.frame.seat_angle,'°')} / {_fmt(calc.effective_sta,'°')}"),
        ("Base arrière (chainstay)", _fmt(bike.frame.cs, "mm")),
        ("Chasse statique / au sag", f"{_fmt(calc.trail,'mm')} / {_fmt(calc.trail_sag,'mm')}"),
        ("Angle direction au sag", _fmt(calc.head_angle_sag, "°")),
        ("Wheel flop", _fmt(calc.wheel_flop)),
    ]
    body = _kv_table(rows) + f'<div class="fig">{drawing_svg}<figcaption>Plan technique coté (axes, visserie, lugs, cartouche).</figcaption></div>'
    return _section("2", "Géométrie", body)


def _sec_cinematique(kin):
    if not kin or not kin.ok:
        return _section("3", "Cinématique de suspension",
                        '<p class="muted">Suspension désactivée ou non résolue sur ce modèle.</p>')
    rows = [
        ("Débattement roue total", _fmt(kin.total_travel, "mm")),
        ("Course amortisseur (utilisée / spec)", f"{_fmt(kin.shock_stroke_used,'mm')} / {_fmt(kin.shock_stroke_spec,'mm')}"),
        ("Levier début / sag / fin", f"{_fmt(kin.leverage_start)} / {_fmt(kin.leverage_sag)} / {_fmt(kin.leverage_end)}"),
        ("Progressivité", _fmt(kin.progressivity, "%")),
        ("Anti-squat au sag", _fmt(kin.anti_squat_sag, "%")),
        ("Anti-rise au sag", _fmt(kin.anti_rise_sag, "%")),
        ("Pedal kickback max", _fmt(kin.pedal_kickback_max, "°")),
        ("Croissance courroie max", _fmt(kin.belt_growth_max, "mm")),
        ("Recul d'axe max", _fmt(kin.axle_path_rearward, "mm")),
        ("Dégagement carter moteur", _verdict(kin.motor_clearance_ok, "dégagé", "collision")),
    ]
    if kin.motor_collisions:
        rows.append(("Collisions", _esc(", ".join(kin.motor_collisions))))
    note = ("Cinématique <strong>INDICATIVE</strong> — à valider dans Linkage (bureau d'études) "
            "avant fabrication. Méthode anti-squat cross-validée vs bikinematicsolver.")
    return _section("3", "Cinématique de suspension", _kv_table(rows), note)


def _sec_tubes(tubes, nodes):
    head = ("<tr><th>Tube</th><th>Ø ext</th><th>Ø int</th><th>paroi</th><th>L (mm)</th>"
            "<th>matériau</th><th>A mm²</th><th>Z mm³</th><th>masse</th></tr>")
    body = "".join(
        f"<tr><td class='l'>{_esc(t.label)}</td><td>{_fmt(t.od)}</td><td>{_fmt(t.id)}</td>"
        f"<td>{_fmt(t.wall,'',2)}</td><td>{_fmt(t.length)}</td><td class='l'>{_esc(t.material)}</td>"
        f"<td>{_fmt(t.area_mm2)}</td><td>{_fmt(t.modulus_mm3)}</td><td>{_fmt(t.mass_g,'g',0)}</td></tr>"
        for t in tubes.tubes
    )
    tbl = f'<table class="grid"><thead>{head}</thead><tbody>{body}</tbody></table>'

    # nomenclature d'achat
    bhead = "<tr><th>Spec</th><th>Membres</th><th>Nb</th><th>Long. totale</th><th>Barre conseillée</th><th>Masse</th></tr>"
    bbody = "".join(
        f"<tr><td class='l'>{_esc(b.get('stock_label'))}</td><td class='l'>{_esc('; '.join(b.get('members',[])))}</td>"
        f"<td>{b.get('count')}</td><td>{_fmt(b.get('total_length_mm'),'mm')}</td>"
        f"<td>{_fmt(b.get('stock_length_mm'),'mm',0)}</td><td>{_fmt(b.get('total_mass_g'),'g',0)}</td></tr>"
        for b in tubes.bom
    )
    bom = f'<h3>Nomenclature d\'achat</h3><table class="grid"><thead>{bhead}</thead><tbody>{bbody}</tbody></table>'

    summary = (f'<p>Masse tubes (cadre nu) : <strong>{_fmt(tubes.total_mass_g,"g",0)}</strong> · '
               f'adhésif {_esc(tubes.adhesive)} (τ_adm {_fmt(tubes.bond_tau_adm,"MPa")}).</p>')
    note = ("Propriétés de section + pré-dimensionnement <strong>1er ordre</strong>. "
            "Fatigue / impact / durée de vie = bureau d'études (ISO 4210-6, EN 17404).")
    return _section("4", "Tubes & masses", summary + tbl + bom, note)


def _sec_lugs(nodes):
    if not nodes:
        return ""
    blocks = []
    for n in nodes:
        socks = "".join(
            f"<tr><td class='l'>{_esc(s.member)}</td><td>{_fmt(s.axis_deg,'°',2)}</td>"
            f"<td>Ø{_fmt(s.bore_dia)}</td><td>{_fmt(s.depth,'mm')}</td>"
            f"<td>{'3D' if s.out_of_plane else '—'}</td></tr>"
            for s in n.sockets
        )
        angs = "".join(f"<li>{_esc(k.replace('|',' / '))} = {_fmt(a,'°',2)}</li>" for k, a in n.angles.items())
        blocks.append(
            f"<h3>Lug « {_esc(n.name)} » @ ({_fmt(n.x)}, {_fmt(n.y)}) mm</h3>"
            f'<table class="grid"><thead><tr><th>douille</th><th>axe</th><th>alésage</th>'
            f"<th>emmanchement</th><th>plan</th></tr></thead><tbody>{socks}</tbody></table>"
            + (f"<ul class='angs'>{angs}</ul>" if angs else "")
        )
    note = "Manchons CNC paramétriques (table de conception SolidWorks via export Lugs)."
    return _section("5", "Jonctions de lugs", "".join(blocks), note)


def _sec_pivots(piv):
    if not piv or not piv.ok or not piv.pivots:
        return ""
    head = ("<tr><th>Pivot</th><th>rôle</th><th>roulement</th><th>alésage</th><th>OD×l</th>"
            "<th>qté</th><th>logement</th><th>axe</th><th>boulon</th></tr>")
    body = "".join(
        f"<tr><td class='l'>{_esc(p.name)}</td><td class='l'>{_esc(p.role)}</td><td class='l'>{_esc(p.bearing)}</td>"
        f"<td>{_fmt(p.bore)}</td><td>{_fmt(p.od)}×{_fmt(p.width)}</td><td>{p.qty}</td>"
        f"<td>Ø{_fmt(p.housing_od)}</td><td>Ø{_fmt(p.axle_dia)}</td><td class='l'>{_esc(p.bolt)}</td></tr>"
        for p in piv.pivots
    )
    tbl = f'<table class="grid"><thead>{head}</thead><tbody>{body}</tbody></table>'
    note = (f"Topologie {_esc(piv.topology)} · couple de pivot {_fmt(piv.torque_nm,'N·m')}. "
            "Sélection GÉOMÉTRIQUE — charges/fatigue = bureau d'études.")
    return _section("6", "Pivots (roulements & axes)", tbl, note)


def _sec_fasteners(fast):
    if not fast or not fast.ok or not fast.items:
        return ""
    # regroupé par catégorie
    cats = {}
    for it in fast.items:
        cats.setdefault(it.category, []).append(it)
    blocks = []
    for cat, items in cats.items():
        rows = "".join(
            f"<tr><td class='l'>{_esc(it.name)}</td><td>{_esc(it.size)}</td><td>{_esc(it.drive)}</td>"
            f"<td>{it.qty}</td><td>{_esc(it.torque_nm)}</td></tr>"
            for it in items
        )
        blocks.append(
            f"<h3>{_esc(cat)}</h3><table class='grid'><thead><tr><th>point</th><th>taille</th>"
            f"<th>empreinte</th><th>qté</th><th>couple (N·m)</th></tr></thead><tbody>{rows}</tbody></table>"
        )
    note = "Couples de RÉFÉRENCE (specs constructeurs) — prioriser toujours la valeur gravée sur la pièce."
    return _section("7", "Visserie & couples", "".join(blocks), note)


def _sec_moto(bike, battery, tx):
    blocks = []
    rows = [
        ("Type de transmission", _esc(tx.kind) if tx else "—"),
        ("Désignation", _esc(tx.label) if tx and tx.label else None),
        ("Vitesses / étendue", f"{tx.gears} / {_fmt(tx.range_pct,'%')}" if tx else None),
        ("Rapport primaire (plateau/pignon)", _fmt(tx.primary_ratio, "", 2) if tx else None),
        ("Couple entrée moyeu / limite", f"{_fmt(tx.hub_input_nm,'N·m')} / {_fmt(tx.max_torque_nm,'N·m')} {_verdict(tx.torque_ok)}" if tx else None),
    ]
    if tx and tx.belt:
        rows += [
            ("Courroie (dents Gates)", _fmt(tx.belt_teeth, "", 0)),
            ("Entraxe courroie", _fmt(tx.belt_center_mm, "mm")),
            ("Tension (méthode / réglage)", f"{_esc(tx.belt_tension_method)} · {_fmt(tx.dropout_adjust_mm,'mm')} {_verdict(tx.belt_tension_ok)}"),
        ]
    blocks.append("<h3>Transmission</h3>" + _kv_table(rows))

    if battery and battery.enabled:
        brows = [
            ("Capacité estimée", _fmt(battery.est_capacity_wh, "Wh", 0)),
            ("Capacité", _fmt(battery.capacity_ah, "Ah")),
            ("Volume pack", _fmt(battery.volume_l, "L")),
            ("Intégration triangle", _verdict(battery.fits_triangle)),
            ("Dégagement moteur / tubes", f"{_verdict(battery.clears_motor)} / {_verdict(battery.clears_tubes)}"),
            ("Courant nominal / crête", f"{_fmt(battery.nominal_current_a,'A')} / {_fmt(battery.peak_current_a,'A')}"),
        ]
        for a in (battery.autonomy or []):
            brows.append((f"Autonomie {a.get('mode','')}", f"{_fmt(a.get('km'),'km',0)} ({_fmt(a.get('whkm'),'Wh/km',0)})"))
        blocks.append("<h3>Batterie & autonomie</h3>" + _kv_table(brows))
    return _section("8", "Motorisation, batterie & transmission", "".join(blocks))


def _sec_fit(fit):
    if not fit or not fit.ok:
        return ""
    rows = [
        ("Hauteur de selle", _fmt(fit.saddle_height, "mm")),
        ("Reach selle→cintre", _fmt(fit.saddle_to_bar_reach, "mm")),
        ("Drop selle→cintre", _fmt(fit.saddle_to_bar_drop, "mm")),
        ("Extension de jambe", _fmt(fit.leg_extension_pct, "%")),
        ("Angle genou (PMB)", _fmt(fit.knee_angle_bdc, "°")),
        ("Angle hanche (PMH)", _fmt(fit.hip_angle_tdc, "°")),
        ("Angle dos", _fmt(fit.back_angle, "°")),
        ("KOPS", _fmt(fit.kops_offset, "mm")),
    ]
    return _section("9", "Fit pilote", _kv_table(rows))


def _sec_conformite():
    body = (
        "<ul class='conf'>"
        "<li><strong>EN 15194</strong> — EPAC : assistance ≤ 25 km/h, ≤ 250 W. "
        "Au-delà ⇒ N'EST PAS un EPAC (S-pedelec L1e / cyclomoteur L1e-B / moto L3e).</li>"
        "<li><strong>EN 17404</strong> — EPAC VTT (eMTB). <em>Exclut la catégorie 5 (DH/extrême).</em></li>"
        "<li><strong>ISO 4210-6:2023</strong> — méthodes d'essai cadre/fourche : impacts masse "
        "tombante, fatigue (100 000 cycles). Critères → ISO 4210-2.</li>"
        "<li><strong>ASTM F2043 / EFBE Tri-Test</strong> — conditions d'usage 1–5.</li>"
        "</ul>"
        "<p class='warn'>⚠ Engin motorisé haute performance, organe de sécurité. Le présent "
        "dossier est un <strong>pré-dimensionnement de conception</strong>. La validation "
        "STRUCTURELLE / FATIGUE / IMPACT et la cinématique finale relèvent d'un "
        "<strong>bureau d'études qualifié</strong>.</p>"
    )
    return _section("10", "Conformité & garde-fous", body)


# ── Document ──────────────────────────────────────────────────────────────────

def build_report_html(bike, designer="Robinson Joubert", date_iso="", company="DOM Engineering",
                      revision="A") -> str:
    """Construit le dossier de conception HTML complet (auto-suffisant)."""
    date_iso = date_iso or _date.today().isoformat()
    calc = calculate(bike)

    kin = solve_kinematics(bike) if getattr(bike.suspension, "enabled", False) else None
    try:
        tubes = compute_tubes(bike, calc)
    except Exception:
        tubes = None
    nodes = build_joints(bike, calc)
    piv = compute_pivots(bike) if getattr(bike.suspension, "enabled", False) else None
    try:
        fast = compute_fasteners(bike, calc)
    except Exception:
        fast = None
    try:
        tx = compute_transmission(bike)
    except Exception:
        tx = None
    battery = compute_battery(bike, calc) if getattr(bike.battery, "enabled", False) else None
    fit = compute_fit(bike, calc) if getattr(bike, "rider", None) else None

    drawing_svg = render_drawing_svg(bike, calc, nodes, project=bike.name or "Vélo",
                                     designer=designer, date=date_iso)
    side_svg = render_svg(bike, calc, 1100, 620, True, None,
                          suspension=(kin.frames if kin and kin.ok else None))

    secs = []
    if tubes:
        secs.append(_sec_synthese(bike, calc, kin, tubes))
    secs.append(_sec_geometrie(bike, calc, drawing_svg))
    secs.append(_sec_cinematique(kin))
    if tubes:
        secs.append(_sec_tubes(tubes, nodes))
    secs.append(_sec_lugs(nodes))
    secs.append(_sec_pivots(piv))
    secs.append(_sec_fasteners(fast))
    secs.append(_sec_moto(bike, battery, tx))
    secs.append(_sec_fit(fit))
    secs.append(_sec_conformite())
    body = "".join(s for s in secs if s)

    fig_side = f'<div class="fig">{side_svg}<figcaption>Vue de profil — rendu de l\'outil.</figcaption></div>'

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>Dossier de conception — {_esc(bike.name or 'Vélo')}</title>
<style>{_CSS}</style></head>
<body>
<header class="cover">
  <div class="brand">{_esc(company)}</div>
  <h1>Dossier de conception</h1>
  <div class="model">{_esc(bike.name or 'Vélo')}</div>
  <table class="meta">
    <tr><th>Dessinateur</th><td>{_esc(designer)}</td><th>Date</th><td>{_esc(date_iso)}</td></tr>
    <tr><th>Révision</th><td>{_esc(revision)}</td><th>Unités</th><td>mm · °  ·  repère BB (x avant +, y haut +)</td></tr>
  </table>
  {fig_side}
  <p class="cover-note">Document destiné aux ingénieurs en conception. Synthèse des paramètres
  géométriques, cinématiques et de fabrication issus d'une géométrie validée dans l'outil DOM.
  Pré-dimensionnement — la validation structurelle relève du bureau d'études.</p>
</header>
{body}
<footer>{_esc(company)} · {_esc(bike.name or 'Vélo')} · rév. {_esc(revision)} · {_esc(date_iso)} —
généré par DOM Engineering Bike Tool. Imprimer → PDF pour diffusion.</footer>
</body></html>"""


_CSS = """
:root{--ink:#1b2330;--mut:#5b6573;--line:#dde3ec;--accent:#2563eb;--brand:#e8851a;
--ok:#16a34a;--no:#dc2626;--warn:#b45309;}
*{box-sizing:border-box;}
body{font-family:'Inter',system-ui,Arial,sans-serif;color:var(--ink);margin:0;
background:#f4f6f9;font-size:13px;line-height:1.5;}
.cover,section{max-width:980px;margin:0 auto;background:#fff;padding:26px 34px;
border:1px solid var(--line);border-radius:8px;margin-top:16px;}
.cover{text-align:center;padding-top:34px;}
.brand{color:var(--brand);font-weight:800;letter-spacing:.06em;text-transform:uppercase;font-size:.8rem;}
.cover h1{font-size:2rem;margin:6px 0 2px;}
.model{font-size:1.15rem;color:var(--accent);font-weight:700;margin-bottom:16px;}
.meta{margin:0 auto 14px;border-collapse:collapse;font-size:.85rem;}
.meta th{background:#f7f8fa;color:var(--mut);text-align:left;padding:5px 10px;border:1px solid var(--line);font-weight:600;}
.meta td{padding:5px 10px;border:1px solid var(--line);}
.cover-note{color:var(--mut);font-size:.82rem;max-width:640px;margin:8px auto 0;}
h2{font-size:1.05rem;border-bottom:2px solid var(--line);padding-bottom:6px;margin:0 0 14px;}
h3{font-size:.92rem;color:var(--accent);margin:16px 0 6px;}
.snum{display:inline-block;background:var(--accent);color:#fff;border-radius:5px;
padding:1px 8px;margin-right:9px;font-size:.85rem;}
table{width:100%;border-collapse:collapse;font-size:.82rem;margin:4px 0;}
table.kv th{width:46%;text-align:left;color:var(--mut);font-weight:600;background:#f9fafb;}
table.kv th,table.kv td{border:1px solid var(--line);padding:5px 9px;}
table.grid th{background:#f3f5f9;color:var(--mut);border:1px solid var(--line);padding:5px 7px;text-align:right;}
table.grid td{border:1px solid var(--line);padding:4px 7px;text-align:right;}
table.grid td.l,table.grid th:first-child{text-align:left;}
.badge{display:inline-block;border-radius:999px;padding:1px 9px;font-size:.74rem;font-weight:700;}
.badge.ok{background:#e7f6ec;color:var(--ok);}
.badge.no{background:#fdeceb;color:var(--no);}
.fig{margin:16px 0;text-align:center;border:1px solid var(--line);border-radius:6px;padding:10px;background:#fbfcfd;}
.fig svg{max-width:100%;height:auto;}
figcaption{color:var(--mut);font-size:.76rem;margin-top:6px;}
.snote{color:var(--mut);font-size:.78rem;border-left:3px solid var(--brand);padding:4px 10px;margin-top:12px;background:#fffaf3;}
.muted{color:var(--mut);}
ul.angs{columns:2;font-size:.8rem;color:var(--mut);margin:6px 0;padding-left:18px;}
ul.conf{font-size:.84rem;padding-left:18px;}
.warn{background:#fffaf3;border:1px solid #f0d9b5;border-radius:6px;padding:9px 12px;color:var(--warn);margin-top:12px;}
footer{max-width:980px;margin:18px auto 30px;color:var(--mut);font-size:.74rem;text-align:center;padding:0 34px;}
@media print{body{background:#fff;}.cover,section{border:none;border-radius:0;margin:0;
max-width:none;page-break-inside:avoid;}section{padding-top:10px;}footer{position:fixed;bottom:0;}}
"""
