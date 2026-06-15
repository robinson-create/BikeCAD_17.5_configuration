"""
Rendu SVG côté latérale — DOM Engineering Bike Tool

Dessine chaque tube comme un polygone rempli (largeur = diamètre réel en mm).
Système de coordonnées : BB = (0,0), X = avant, Y = haut (mm).
Le SVG est généré avec un viewBox qui s'adapte automatiquement au vélo.
"""

import math
from ..models.bike import BikeDesign, CalcResult
from ..calculations.motor import motor_envelope_world


# ─── Palette ──────────────────────────────────────────────────────────────────
# Style BikeCAD : cadre PEINT avec ombrage cylindrique (clair en haut, sombre en
# bas), jonctions lisses, roues détaillées (jante argent + rayons + moyeu), fond
# blanc. Les tubes sont remplis d'un dégradé perpendiculaire (cf. _draw_tube).
PALETTE = {
    "frame":      "#2f7dc4",   # peinture cadre (bleu) — base du dégradé
    "fork_low":   "#1c1f24",   # fourreaux fourche (noir)
    "stanchion":  "#c9ced6",   # plongeurs (chrome/argent)
    "crown":      "#2b2f36",   # couronnes + BB
    "rim":        "#c2c7cf",   # jante (argent)
    "rim_dark":   "#8b9099",
    "tire":       "#0e0f11",   # pneu (noir uni)
    "tread":      "#34373c",   # crampons/sculpture
    "spoke":      "#9298a1",   # rayons
    "hub":        "#7a808a",
    "seatpost":   "#26292f",
    "saddle":     "#141517",   # selle (noir)
    "saddle_hi":  "#3a3d44",
    "stem":       "#1c1f24",
    "handlebar":  "#1c1f24",
    "grip":       "#0f1012",
    "ground":     "#e4e8ee",   # sol
    "dim_line":   "#2f6df0",   # cotes
    "dim_text":   "#2f6df0",
    "dim_bg":     "white",
    "bg":         "#cccccc",   # fond gris BikeCAD (« objet posé sur fond uni »)
    "wheel_gap":  "#cccccc",   # creux de jante (= fond → roue ajourée)
    "belt":       "#101114",   # courroie (noir cranté — vélo DOM Gates)
    "chain":      "#cfd3d8",   # chaîne (acier)
    "cog":        "#aeb4bd",   # plateau / pignon (argent)
    "cog_dark":   "#6c727b",
    "motor":      "#33373d",   # carter moteur
    "rotor":      "#b9c4d2",   # disque de frein (argent)
    "crank":      "#1c1f24",   # manivelle / pédale
    "lug":        "#b9bfc7",   # lug CNC (alu/titane usiné)
    "lug_edge":   "#5d636b",
}


def _shade(hexc: str, factor: float) -> str:
    """Éclaircit (factor>1) ou assombrit (factor<1) une couleur #rrggbb."""
    hexc = hexc.lstrip("#")
    r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
    f = lambda v: max(0, min(255, int(v * factor)))
    return f"#{f(r):02x}{f(g):02x}{f(b):02x}"

# ─── Helpers géométrie ────────────────────────────────────────────────────────

def _tube_polygon(
    x1: float, y1: float,
    x2: float, y2: float,
    d: float,
    sx: float, sy: float,
    ox: float, oy: float,
    scale: float,
) -> str:
    """
    Retourne les points SVG d'un tube (rectangle aligné sur son axe).
    sx, sy, ox, oy : transform monde → SVG  (SVG_x = x*sx + ox, SVG_y = y*sy + oy)
    scale : facteur de mise à l'échelle mm→px (pour d)
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 0.5:
        return ""
    hw = d / 2  # demi-largeur en mm
    nx = -dy / length * hw
    ny =  dx / length * hw

    corners = [
        (x1 + nx, y1 + ny),
        (x1 - nx, y1 - ny),
        (x2 - nx, y2 - ny),
        (x2 + nx, y2 + ny),
    ]
    pts = " ".join(f"{c[0]*sx + ox:.1f},{c[1]*sy + oy:.1f}" for c in corners)
    return pts


def _circle(cx: float, cy: float, r: float, sx: float, sy: float, ox: float, oy: float):
    """Retourne (svg_cx, svg_cy, svg_r) pour un cercle."""
    scx = cx * sx + ox
    scy = cy * sy + oy
    sr  = r * abs(sx)
    return scx, scy, sr


def _pt(x: float, y: float, sx: float, sy: float, ox: float, oy: float):
    return x * sx + ox, y * sy + oy


# ─── Composants visuels ───────────────────────────────────────────────────────

def _draw_wheel(cx: float, cy: float, r_tire: float,
                sx: float, sy: float, ox: float, oy: float,
                cassette=False, wcfg=None) -> str:
    """Roue vue de côté. Les détails (jante depuis BSD+profil, croisement de
    rayons, Ø flasque moyeu, cercle de croisement) viennent du WheelConfig `wcfg`
    → chaque réglage de la roue agit sur l'aperçu."""
    scx, scy, sr_tire = _circle(cx, cy, r_tire, sx, sy, ox, oy)
    # Jante : bord extérieur = BSD/2 + profil de jante (sinon ~0.83·rayon pneu).
    if wcfg is not None:
        rim_mm    = min(r_tire - 3.0, wcfg.bead_seat_dia / 2 + max(0.0, wcfg.rim_depth))
        n_spokes  = max(8, int(wcfg.spokes))
        flange_mm = min(70.0, max(14.0, wcfg.hub_flange_dia_ds / 2))
        cross     = max(0, int(wcfg.cross_pattern))
        circ_mm   = wcfg.spoke_circ_dia
    else:
        rim_mm, n_spokes, flange_mm, cross, circ_mm = r_tire * 0.83, 32, 22.0, 3, 0.0
    _, _, sr_rim = _circle(cx, cy, rim_mm, sx, sy, ox, oy)
    sr_fl  = max(6.0, flange_mm * abs(sx))   # flasque moyeu (Ø réel)
    sr_hub = max(7.0, sr_fl * 0.5)
    tire_w = max(4.0, sr_tire - sr_rim)
    rim_w  = max(2.0, tire_w * 0.14)
    r_bed  = sr_rim - rim_w
    # Rayon d'accroche au lit de jante (cercle de croisement si fourni)
    r_attach = (circ_mm / 2 * abs(sx)) if circ_mm and circ_mm > 0 else r_bed * 0.99
    r_attach = min(r_attach, r_bed * 0.99)
    cross_off = cross * 0.06                 # croisement → décalage tangentiel (rad)

    L = [f'<g class="wheel">']
    # Pneu : carcasse noire + CRAMPONS MTB (couronne de pavés au bord + bande
    # centrale) → lecture « pneu enduro cranté » plutôt qu'un simple anneau lisse.
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire:.1f}" fill="{PALETTE["tire"]}" '
             f'stroke="#2a2d31" stroke-width="1.0"/>')
    knob = max(2.5, tire_w * 0.32)                       # hauteur de crampon
    circ = 2 * math.pi * sr_tire
    n_knob = max(28, int(circ / max(8.0, knob * 2.0)))   # ~1 pavé tous les 2·hauteur
    dash = circ / n_knob
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire - knob*0.45:.1f}" fill="none" '
             f'stroke="{PALETTE["tread"]}" stroke-width="{knob:.1f}" '
             f'stroke-dasharray="{dash*0.55:.1f} {dash*0.45:.1f}"/>')
    # bande centrale (crampons moins hauts, décalés) pour le relief
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire - tire_w*0.5:.1f}" fill="none" '
             f'stroke="{PALETTE["tread"]}" stroke-width="{knob*0.7:.1f}" opacity="0.7" '
             f'stroke-dasharray="{dash*0.4:.1f} {dash*0.9:.1f}"/>')
    # Creux (entre les rayons) = couleur de fond → roue ajourée comme BikeCAD
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r_bed:.1f}" fill="{PALETTE["wheel_gap"]}"/>')
    # Rayons : du flasque (décalé selon le croisement) vers le cercle d'accroche
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes
        sign = 1 if i % 2 == 0 else -1       # 2 nappes alternées
        hx, hy = scx + sr_fl * math.cos(a + sign * cross_off), scy + sr_fl * math.sin(a + sign * cross_off)
        rx, ry = scx + r_attach * math.cos(a), scy + r_attach * math.sin(a)
        L.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{rx:.1f}" y2="{ry:.1f}" '
                 f'stroke="{PALETTE["spoke"]}" stroke-width="0.5"/>')
    # Jante : un seul anneau argent fin
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim-rim_w/2:.1f}" fill="none" '
             f'stroke="{PALETTE["rim"]}" stroke-width="{rim_w:.1f}"/>')
    # Cassette (roue AR, dérailleur) : pile de pignons = anneaux concentriques
    # décroissants (tip de denture par cog), alternés clair/sombre pour le relief.
    if cassette:
        radii = [50, 45, 41, 37, 33, 29, 25, 21, 18]
        # disque de fond (corps de cassette) légèrement teinté
        _, _, sc0 = _circle(cx, cy, radii[0], sx, sy, ox, oy)
        L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sc0:.1f}" fill="{PALETTE["cog"]}" opacity="0.35"/>')
        for i, rr in enumerate(radii):
            _, _, scr = _circle(cx, cy, rr, sx, sy, ox, oy)
            col = PALETTE["cog"] if i % 2 == 0 else PALETTE["cog_dark"]
            L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{scr:.1f}" fill="none" '
                     f'stroke="{col}" stroke-width="2.0"/>')
    # Moyeu : flasque + corps + axe (compact)
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_fl:.1f}" fill="{PALETTE["hub"]}" '
             f'stroke="#222" stroke-width="0.8"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub*0.5:.1f}" fill="#2a2d33"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub*0.18:.1f}" fill="#101114"/>')
    L.append('</g>')
    return "\n".join(L)


_TUBE_ID = [0]   # compteur d'identifiants de dégradés (réinitialisé par render_svg)


def _draw_tube(x1, y1, x2, y2, d, color, sx, sy, ox, oy, scale, cap_r=0.0,
               edge=None, fill=None, outline_only=False) -> str:
    """Tube peint. Si `fill` est fourni (ex. dégradé GLOBAL du cadre façon BikeCAD),
    on l'utilise tel quel ; sinon ombrage cylindrique par tube.

    `outline_only` (cadre) : ne trace QUE les 2 grands côtés (#333) — les bouts sont
    fondus aux jonctions par les cercles de fillet → liseré BikeCAD sans coutures."""
    pts = _tube_polygon(x1, y1, x2, y2, d, sx, sy, ox, oy, scale)
    if not pts:
        return ""
    if fill is not None:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        hw = d / 2
        nx, ny = -dy / L * hw, dx / L * hw
        A = _pt(x1 + nx, y1 + ny, sx, sy, ox, oy)
        B = _pt(x1 - nx, y1 - ny, sx, sy, ox, oy)
        C = _pt(x2 - nx, y2 - ny, sx, sy, ox, oy)
        D = _pt(x2 + nx, y2 + ny, sx, sy, ox, oy)
        if outline_only:
            ec = edge or "#333333"
            return (f'<line x1="{A[0]:.1f}" y1="{A[1]:.1f}" x2="{D[0]:.1f}" y2="{D[1]:.1f}" '
                    f'stroke="{ec}" stroke-width="0.8" stroke-linecap="round"/>'
                    f'<line x1="{B[0]:.1f}" y1="{B[1]:.1f}" x2="{C[0]:.1f}" y2="{C[1]:.1f}" '
                    f'stroke="{ec}" stroke-width="0.8" stroke-linecap="round"/>')
        out = [f'<polygon points="{pts}" fill="{fill}"/>']
        if cap_r > 0:
            r_px = cap_r * abs(sx)
            for (xc, yc) in [(x1, y1), (x2, y2)]:
                cxp, cyp = _pt(xc, yc, sx, sy, ox, oy)
                out.append(f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r_px:.1f}" fill="{fill}"/>')
        return "".join(out)
    # perpendiculaire en coords MONDE, orientée vers le haut (world +y)
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1.0
    px, py = -dy / L, dx / L
    if py < 0:
        px, py = -px, -py
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    top = _pt(mx + px * d / 2, my + py * d / 2, sx, sy, ox, oy)   # bord éclairé
    bot = _pt(mx - px * d / 2, my - py * d / 2, sx, sy, ox, oy)   # bord ombré

    _TUBE_ID[0] += 1
    gid = f"tg{_TUBE_ID[0]}"
    hi   = _shade(color, 1.55)
    base = color
    sh   = _shade(color, 0.55)
    grad = (
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
        f'x1="{top[0]:.1f}" y1="{top[1]:.1f}" x2="{bot[0]:.1f}" y2="{bot[1]:.1f}">'
        f'<stop offset="0%" stop-color="{hi}"/>'
        f'<stop offset="18%" stop-color="{_shade(color,1.25)}"/>'
        f'<stop offset="52%" stop-color="{base}"/>'
        f'<stop offset="100%" stop-color="{sh}"/>'
        f'</linearGradient>'
    )
    stroke = f' stroke="{edge}" stroke-width="0.6"' if edge else ''
    out = [grad, f'<polygon points="{pts}" fill="url(#{gid})"{stroke} stroke-linejoin="round"/>']
    if cap_r > 0:
        r_px = cap_r * abs(sx)
        for (xc, yc) in [(x1, y1), (x2, y2)]:
            cxp, cyp = _pt(xc, yc, sx, sy, ox, oy)
            out.append(f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r_px:.1f}" fill="url(#{gid})"/>')
    return "".join(out)


def _draw_dim(x1, y1, x2, y2, label, sx, sy, ox, oy, offset_px=20, vertical=False) -> str:
    """Dessine une cote avec ligne d'extension et texte."""
    sp1x, sp1y = _pt(x1, y1, sx, sy, ox, oy)
    sp2x, sp2y = _pt(x2, y2, sx, sy, ox, oy)
    mid_x = (sp1x + sp2x) / 2
    mid_y = (sp1y + sp2y) / 2

    if vertical:
        off_x, off_y = -offset_px, 0
    else:
        off_x, off_y = 0, -offset_px

    lx1, ly1 = sp1x + off_x, sp1y + off_y
    lx2, ly2 = sp2x + off_x, sp2y + off_y
    txt_x = mid_x + off_x
    txt_y = mid_y + off_y - 4

    c = PALETTE["dim_line"]
    return (
        f'<line x1="{lx1:.0f}" y1="{ly1:.0f}" x2="{lx2:.0f}" y2="{ly2:.0f}" '
        f'stroke="{c}" stroke-width="1" stroke-dasharray="4,3" />'
        f'<line x1="{sp1x:.0f}" y1="{sp1y:.0f}" x2="{lx1:.0f}" y2="{ly1:.0f}" '
        f'stroke="{c}" stroke-width="0.8" />'
        f'<line x1="{sp2x:.0f}" y1="{sp2y:.0f}" x2="{lx2:.0f}" y2="{ly2:.0f}" '
        f'stroke="{c}" stroke-width="0.8" />'
        f'<text x="{txt_x:.0f}" y="{txt_y:.0f}" '
        f'fill="{PALETTE["dim_text"]}" font-size="11" text-anchor="middle" '
        f'font-family="monospace">{label}</text>'
    )


# ─── Rendu principal ──────────────────────────────────────────────────────────

def _sprocket(cx, cy, r_pitch, teeth, sx, sy, ox, oy,
              fill="#aeb4bd", edge="#6c727b", spider=True) -> str:
    """Plateau/pignon réaliste : silhouette dentée + corps + bras d'araignée."""
    scx, scy = _pt(cx, cy, sx, sy, ox, oy)
    r = max(3.0, r_pitch * abs(sx))
    th = max(1.0, r * 0.045)                 # hauteur de dent (fine, régulière)
    N = max(8, int(teeth))
    pts = []
    for i in range(N):
        a0 = 2 * math.pi * i / N
        am = 2 * math.pi * (i + 0.5) / N
        pts.append(f"{scx + (r+th)*math.cos(a0):.1f},{scy + (r+th)*math.sin(a0):.1f}")
        pts.append(f"{scx + (r-th*0.5)*math.cos(am):.1f},{scy + (r-th*0.5)*math.sin(am):.1f}")
    out = [f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{edge}" stroke-width="0.8"/>']
    # corps + bras d'araignée + axe
    if spider:
        out.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r*0.62:.1f}" fill="{_shade(fill,0.9)}"/>')
        for k in range(5):
            a = 2 * math.pi * k / 5
            ex, ey = scx + r * 0.6 * math.cos(a), scy + r * 0.6 * math.sin(a)
            out.append(f'<line x1="{scx:.1f}" y1="{scy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
                       f'stroke="{_shade(fill,0.72)}" stroke-width="{max(1.5,r*0.07):.1f}" stroke-linecap="round"/>')
    out.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r*0.2:.1f}" fill="{_shade(fill,0.6)}" '
               f'stroke="{edge}" stroke-width="0.6"/>')
    return "".join(out)


import json as _json, os as _os, re as _re
_SHAPES_PATH = _os.path.join(_os.path.dirname(__file__), "..", "..", "refs", "bikecad_shapes.json")
try:
    _BIKECAD_SHAPES = _json.load(open(_SHAPES_PATH, encoding="utf-8"))
except Exception:
    _BIKECAD_SHAPES = {}


_NPAIRS = {"M": 1, "L": 1, "Q": 2, "C": 3, "Z": 0}


def _xform_path(d_local, P):
    """Réécrit un path SVG (M/L/Q/C/Z absolus) en appliquant P(lx,ly)->(px,py)."""
    toks = _re.findall(r'[MLCQZ]|-?\d+\.?\d*', d_local)
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in _NPAIRS:
            cmd = t; i += 1
            if cmd == "Z":
                out.append("Z"); continue
            n = _NPAIRS[cmd]; coords = []
            for k in range(n):
                px, py = P(float(toks[i + 2*k]), float(toks[i + 2*k + 1]))
                coords.append(f"{px:.1f} {py:.1f}")
            i += 2 * n
            out.append(cmd + " ".join(coords))
        else:
            i += 1
    return " ".join(out)


def _draw_motor_bikecad(dt, calc, sx, sy, ox, oy) -> str | None:
    """Carter moteur avec la FORME EXACTE de BikeCAD (extraite de son code,
    basic.bafang / basic.bafangM800), transformée mm (y-bas) → monde (y-haut)."""
    if not dt.motor_key.startswith("bafang"):
        return None
    key = "bafangM800" if "m800" in dt.motor_key else "bafang_gearbox"
    shape = _BIKECAD_SHAPES.get(key)
    if not shape or not shape.get("area", {}).get("d"):
        return None
    ang = math.radians(dt.motor_angle)
    ca, sa = math.cos(ang), math.sin(ang)
    bx, by = calc.bb.x + dt.motor_x, calc.bb.y + dt.motor_y

    def P(lx, ly):
        # PAS de flip Y : la forme getGArea est déjà dans un repère y-haut →
        # flipper la mettait à l'ENVERS (bossages de fixation vers le bas). Vérifié
        # visuellement : sans flip, le carter pointe vers l'avant, les bossages de
        # fixation vers le HAUT (vers le tube diagonal), ailettes vers l'avant.
        fx, fy = lx, ly
        wx = bx + fx * ca - fy * sa
        wy = by + fx * sa + fy * ca
        return wx * sx + ox, wy * sy + oy

    d = _xform_path(shape["area"]["d"], P)
    base = PALETTE["motor"]
    grad = (f'<linearGradient id="motorg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{_shade(base,1.5)}"/>'
            f'<stop offset="55%" stop-color="{base}"/>'
            f'<stop offset="100%" stop-color="{_shade(base,0.55)}"/></linearGradient>')
    out = [grad, f'<g class="motor">',
           f'<path d="{d}" fill="url(#motorg)" fill-rule="evenodd" '
           f'stroke="#10151c" stroke-width="1.4"/>']
    # lignes de détail (logo/usinage) par-dessus, en plus clair
    det = shape.get("detail", {}).get("d") if isinstance(shape.get("detail"), dict) else None
    if det:
        out.append(f'<path d="{_xform_path(det, P)}" fill="none" '
                   f'stroke="{_shade(base,1.7)}" stroke-width="0.8" opacity="0.5"/>')
    out.append("</g>")
    return "".join(out)


_PARTS_DIR = _os.path.join(_os.path.dirname(__file__), "..", "..", "refs", "bikecad_parts")


def _load_part(name):
    try:
        return _json.load(open(_os.path.join(_PARTS_DIR, name + ".json"), encoding="utf-8"))
    except Exception:
        return None


# Sprites de formes RÉELLES extraites des exports BikeCAD (paths en mm, y-haut,
# ancre à l'origine). Voir tool/scripts/svg_part_tool.py + tool/refs/bikecad_parts/.
# Les sprites *_norm = ré-orientés (PCA) en repère canonique (cf. normalize_parts.py) :
# fork/rear_shock = axe vertical ancre basse ; battery = axe horizontal ancre centre.
_PART_NAMES = ("fork", "rear_shock", "derailleur", "belt", "battery",
               "fork_norm", "rear_shock_norm", "battery_norm")
_PARTS = {n: _load_part(n) for n in _PART_NAMES}


def _draw_sprite(name, ax, ay, sx, sy, ox, oy, *, scale=1.0, angle_deg=0.0,
                 mirror=False, fill_override=None, stroke_override=None,
                 empty_fill="#9aa0a8", opacity=1.0, klass="sprite") -> str:
    """Place un sprite BikeCAD dans le monde.

    Le sprite est une liste de paths en mm (y vers le haut), ancre à l'origine.
    ax,ay = position MONDE de l'ancre ; scale = facteur de taille ;
    angle_deg = rotation (sens trigo, repère monde y-haut) ; mirror = miroir
    horizontal local. Les couleurs d'origine BikeCAD sont conservées.

    Cas des fills : un fill explicite (rgb/black…) est gardé ; `fill=""` = forme
    DEVANT être pleine mais dont BikeCAD avait omis la couleur (héritée) → on
    applique `empty_fill` ; `fill="none"` = simple contour (garde son stroke).
    """
    part = _PARTS.get(name)
    if not part or not part.get("paths"):
        return ""
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    mx = -1.0 if mirror else 1.0

    def P(lx, ly):
        lx2 = lx * scale * mx
        ly2 = ly * scale
        wx = ax + lx2 * ca - ly2 * sa
        wy = ay + lx2 * sa + ly2 * ca
        return wx * sx + ox, wy * sy + oy

    out = [f'<g class="{klass}" opacity="{opacity}">']
    for sp in part["paths"]:
        d = _xform_path(sp["d"], P)
        f0 = (sp.get("fill") or "").strip()
        if fill_override:
            fill = fill_override
        elif f0 == "":
            fill = empty_fill
        else:
            fill = f0                      # "none" ou couleur explicite
        stroke = stroke_override if stroke_override else (sp.get("stroke") or "none")
        if not stroke:
            stroke = "none"
        sw = 0.7 if stroke != "none" else 0.0
        out.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
                   f'stroke-width="{sw}" stroke-linejoin="round"/>')
    out.append("</g>")
    return "".join(out)


# ── Contours RÉELS de composants (vues de côté, recherche web) ───────────────
# Points normalisés (x,y) ∈ [0,1]², x=+avant/droite, y=+haut. Tracés d'après des
# dessins techniques / vues de profil de pièces réelles (Specialized Power /
# Fizik Terra, Shimano XT 4-pistons, Bafang M620 manuel BF-DM-C-MM G510).
def _parse_outline(s):
    return [tuple(float(v) for v in p.split(",")) for p in s.split(";") if p.strip()]

_OUTLINE_SADDLE = _parse_outline(
    "0.02,0.62; 0.06,0.78; 0.12,0.86; 0.20,0.90; 0.30,0.86; 0.42,0.80; 0.55,0.76; "
    "0.68,0.74; 0.80,0.72; 0.90,0.70; 0.96,0.67; 1.00,0.60; 0.99,0.53; 0.95,0.50; "
    "0.88,0.51; 0.80,0.52; 0.70,0.53; 0.62,0.50; 0.58,0.42; 0.55,0.34; 0.53,0.30; "
    "0.49,0.30; 0.46,0.36; 0.44,0.44; 0.40,0.49; 0.30,0.50; 0.20,0.51; 0.12,0.52; "
    "0.06,0.55; 0.02,0.62")
# Étrier 4-pistons : corps qui enjambe la piste + 2 oreilles post-mount.
_OUTLINE_CALIPER = _parse_outline(
    "0.50,0.06; 0.60,0.06; 0.66,0.10; 0.70,0.18; 0.72,0.30; 0.74,0.40; 0.82,0.42; "
    "0.92,0.44; 0.97,0.48; 0.99,0.55; 0.97,0.62; 0.92,0.66; 0.82,0.68; 0.74,0.70; "
    "0.72,0.82; 0.68,0.90; 0.60,0.95; 0.50,0.96; 0.40,0.95; 0.33,0.90; 0.29,0.82; "
    "0.27,0.70; 0.18,0.68; 0.08,0.66; 0.03,0.62; 0.01,0.55; 0.03,0.48; 0.08,0.44; "
    "0.18,0.42; 0.27,0.40; 0.29,0.30; 0.32,0.18; 0.37,0.10; 0.43,0.06; 0.50,0.06")
# Carter Bafang M620 (galet ovoïde 234×140, manuel G510). BB ≈ (0.27,0.42).
_OUTLINE_M620 = _parse_outline(
    "0.747,0.965; 0.500,1.000; 0.390,0.965; 0.308,0.930; 0.199,0.948; 0.089,0.878; "
    "0.014,0.739; 0.000,0.565; 0.034,0.383; 0.116,0.191; 0.253,0.070; 0.418,0.009; "
    "0.582,0.000; 0.719,0.043; 0.842,0.122; 0.932,0.209; 0.979,0.348; 1.000,0.522; "
    "0.986,0.696; 0.932,0.835; 0.863,0.922")


def _norm_path(points, anchor_world, w, h, anchor_n=(0.0, 0.0), angle_deg=0.0,
               *, sx, sy, ox, oy, close=True):
    """Mappe un contour normalisé (0..1) en coords écran : place `anchor_n` du
    contour sur `anchor_world` (monde), échelle (w,h) en mm, rotation angle_deg
    (CCW, repère monde y-haut). Renvoie un `d` SVG."""
    a = math.radians(angle_deg)
    ca, sa_ = math.cos(a), math.sin(a)
    axw, ayw = anchor_world
    anx, any_ = anchor_n
    d = []
    for i, (nx, ny) in enumerate(points):
        lx = (nx - anx) * w
        ly = (ny - any_) * h
        wx = axw + lx * ca - ly * sa_
        wy = ayw + lx * sa_ + ly * ca
        px, py = _pt(wx, wy, sx, sy, ox, oy)
        d.append(f"{'M' if i == 0 else 'L'} {px:.1f} {py:.1f}")
    if close:
        d.append("Z")
    return " ".join(d)


def _draw_motor(bike, calc, sx, sy, ox, oy, scale) -> str:
    """Carter moteur central, dessiné DERRIÈRE le cadre (les tubes se rejoignent
    par-dessus, au BB — le moteur est la jonction d'un mid-drive). Forme exacte
    BikeCAD si dispo, sinon enveloppe carter, sinon rectangle générique."""
    dt = bike.drivetrain
    if not dt.use_motor:
        return ""
    bb = (calc.bb.x, calc.bb.y)
    motor_svg = _draw_motor_bikecad(dt, calc, sx, sy, ox, oy)
    if motor_svg:
        return motor_svg
    env = motor_envelope_world(dt)
    if env is not None:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in
                       (_pt(bb[0] + ex, bb[1] + ey, sx, sy, ox, oy) for ex, ey in env))
        return (f'<polygon class="motor" points="{pts}" fill="{PALETTE["motor"]}" '
                f'stroke="#1a2530" stroke-width="1.5"/>')
    # Fallback : CONTOUR RÉEL du carter M620 (manuel, 234×140 ; BB ≈ norm (0.27,0.42)).
    anchor = (bb[0] + dt.motor_x, bb[1] + dt.motor_y)
    d = _norm_path(_OUTLINE_M620, anchor, -234.0, 140.0, anchor_n=(0.27, 0.42),
                   sx=sx, sy=sy, ox=ox, oy=oy)   # w<0 : x=0 du contour = avant (+x monde)
    return (f'<path class="motor" d="{d}" fill="{PALETTE["motor"]}" '
            f'stroke="#1a2530" stroke-width="1.5" stroke-linejoin="round"/>')


def _draw_motor_mount(bike, calc, sx, sy, ox, oy, scale) -> str:
    """Interface de FIXATION du moteur au cadre (3 points M8, manuel Bafang M620) :
    bossages + boulons aux 3 ancrages + brides reliant le carter aux tubes, pour
    qu'on voie que le moteur est tenu par le cadre (et non posé dans le vide)."""
    dt = bike.drivetrain
    if not dt.use_motor or dt.motor_key == "none":
        return ""
    bbx, bby = calc.bb.x, calc.bb.y
    # 3 points de fixation relatifs au BB (avant-haut vers down tube, avant-bas,
    # arrière vers tube de selle / base) — d'après l'agencement M620.
    pts = [(58.0, 46.0), (66.0, -20.0), (-70.0, 30.0)]
    # cibles cadre (vers quel tube la bride pointe)
    tgt = [(calc.crown.x, calc.crown.y), (bbx + 90, bby - 6), (calc.seat_tube_top.x, calc.seat_tube_top.y)]
    out = ['<g class="motor-mount">']
    for (mx, my), (tx, ty) in zip(pts, tgt):
        wx, wy = bbx + mx, bby + my
        # bride : court tronçon métal du carter vers le tube le plus proche
        dx, dy = tx - wx, ty - wy
        L = math.hypot(dx, dy) or 1.0
        ex, ey = wx + dx / L * 26.0, wy + dy / L * 26.0
        out.append(_draw_tube(wx, wy, ex, ey, 18.0, _shade(PALETTE["motor"], 1.5),
                              sx, sy, ox, oy, scale, cap_r=9.0))
        # bossage + boulon M8 (tête hex)
        cx, cy = _pt(wx, wy, sx, sy, ox, oy)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{8.5*scale:.1f}" '
                   f'fill="{_shade(PALETTE["motor"],1.35)}" stroke="#10161c" stroke-width="1"/>')
        r = 5.2 * scale
        hexp = " ".join(f"{cx + r*math.cos(math.pi/6 + math.pi*k/3):.1f},"
                        f"{cy + r*math.sin(math.pi/6 + math.pi*k/3):.1f}" for k in range(6))
        out.append(f'<polygon points="{hexp}" fill="#2c3137" stroke="#10161c" stroke-width="0.7"/>')
    out.append('</g>')
    return "".join(out)


def _draw_drivetrain(bike, calc, sx, sy, ox, oy, scale) -> str:
    """Plateau, pignon AR, courroie/chaîne (+ galet), moteur central, manivelle."""
    dt = bike.drivetrain
    su = bike.suspension
    parts = []

    bb = (calc.bb.x, calc.bb.y)
    axle = (calc.rear_axle.x, calc.rear_axle.y)

    # Rayons plateau / pignon depuis dentures (pas courroie ou ~12.7 chaîne)
    pitch = dt.belt_pitch if dt.drive_type == "belt" else 12.7
    r_cr = su.chainring_teeth * pitch / (2 * math.pi)
    r_cog = su.cog_teeth * pitch / (2 * math.pi)

    # NB : le MOTEUR n'est PLUS dessiné ici — il est rendu AVANT le cadre (derrière
    # les tubes) via _draw_motor(), pour que les tubes se rejoignent visiblement au
    # BB (le moteur EST la jonction sur un mid-drive). Voir render_svg.

    # Plateau (chainring denté) au BB + pignon AR — dessinés AVANT la manivelle
    parts.append(_sprocket(bb[0], bb[1], r_cr, su.chainring_teeth, sx, sy, ox, oy,
                           fill=PALETTE["cog"], edge=PALETTE["cog_dark"]))
    parts.append(_sprocket(axle[0], axle[1], r_cog, su.cog_teeth, sx, sy, ox, oy,
                           fill=PALETTE["cog"], edge=PALETTE["cog_dark"], spider=False))

    # Manivelle profilée (polygone effilé BB→pédale) + axe + pédale
    crank_len = bike.cranks.crank_length
    pe = (bb[0] + crank_len * 0.5, bb[1] - crank_len * 0.87)   # bout de manivelle
    dx, dy = pe[0] - bb[0], pe[1] - bb[1]
    dl = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / dl, dx / dl
    wb = max(14.0, bike.cranks.arm_thickness * 1.7)   # largeur manivelle (réglage)
    wp = max(9.0, wb * 0.55)                            # largeur à la pédale
    quad = [(bb[0] + nx*wb/2, bb[1] + ny*wb/2), (pe[0] + nx*wp/2, pe[1] + ny*wp/2),
            (pe[0] - nx*wp/2, pe[1] - ny*wp/2), (bb[0] - nx*wb/2, bb[1] - ny*wb/2)]
    qpts = " ".join(f"{p[0]*sx+ox:.1f},{p[1]*sy+oy:.1f}" for p in quad)
    parts.append(f'<polygon points="{qpts}" fill="{PALETTE["crank"]}" stroke="#000" stroke-width="0.6"/>')
    # boss de manivelle au BB
    bcx, bcy = _pt(*bb, sx, sy, ox, oy)
    parts.append(f'<circle cx="{bcx:.1f}" cy="{bcy:.1f}" r="{16*scale:.1f}" fill="{PALETTE["crank"]}" '
                 f'stroke="#000" stroke-width="0.6"/>')
    # pédale (corps + axe)
    pl = max(80.0, bike.pedals.length)
    pth = max(14.0, bike.pedals.thickness)
    pcx, pcy = _pt(pe[0], pe[1], sx, sy, ox, oy)
    parts.append(f'<rect class="pedals" x="{pcx-pl/2*scale:.1f}" y="{pcy-pth/2*scale:.1f}" '
                 f'width="{pl*scale:.1f}" height="{pth*scale:.1f}" rx="{3*scale:.1f}" '
                 f'fill="#101114" stroke="#000" stroke-width="0.6"/>')

    # Courroie : brins tangents (haut tendu + bas), via galet si présent
    def tangents(c0, r0, c1, r1):
        dx, dy = c1[0]-c0[0], c1[1]-c0[1]
        d = math.hypot(dx, dy)
        if d < 1e-6: return []
        nx, ny = -dy/d, dx/d
        return [((c0[0]+s*r0*nx, c0[1]+s*r0*ny), (c1[0]+s*r1*nx, c1[1]+s*r1*ny)) for s in (+1, -1)]

    # Le galet de renvoi n'a de sens (et ne dévie le brin) que pour un single-pivot
    # HAUT (high_pivot_idler). Sur un four-bar classique, on route en direct
    # BB→pignon (sinon le galet crée un coude parasite sous le pédalier).
    segs = []
    use_idler = su.use_idler and dt.drive_type == "belt" and su.linkage_type == "high_pivot_idler"
    if use_idler:
        idler = (su.idler.x, su.idler.y); r_id = su.idler_dia / 2
        segs += tangents(bb, r_cr, idler, r_id)
        segs += tangents(idler, r_id, axle, r_cog)
        icx, icy, isr = _circle(idler[0], idler[1], r_id, sx, sy, ox, oy)
        parts.append(f'<circle cx="{icx:.1f}" cy="{icy:.1f}" r="{isr:.1f}" '
                     f'fill="{PALETTE["cog"]}" stroke="{PALETTE["cog_dark"]}" stroke-width="1"/>')
    else:
        segs += tangents(bb, r_cr, axle, r_cog)

    # Brin = BANDE épaisse texturée (jamais un fil) : courroie noire crantée (Gates)
    # ou chaîne grise à rouleaux. Couleur/texture selon dt.drive_type.
    is_belt = dt.drive_type == "belt"
    strand_col = PALETTE["belt"] if is_belt else PALETTE["chain"]
    w_mm = (dt.belt_width if is_belt else 7.5)
    w_px = max(3.0, w_mm * abs(sx))
    for a, b in segs:
        ax, ay = _pt(*a, sx, sy, ox, oy); bx2, by2 = _pt(*b, sx, sy, ox, oy)
        seg_len = math.hypot(bx2 - ax, by2 - ay)
        if seg_len < 1:
            continue
        ux, uy = (bx2 - ax) / seg_len, (by2 - ay) / seg_len
        px, py = -uy, ux
        # bande principale
        parts.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" '
                     f'stroke="{strand_col}" stroke-width="{w_px:.1f}" stroke-linecap="butt"/>')
        step = max(4.0, pitch * abs(sx))
        n = int(seg_len / step)
        if is_belt:
            # dents Gates : stries transversales fines plus claires
            for k in range(n + 1):
                t = k * step
                mxk, myk = ax + ux * t, ay + uy * t
                parts.append(f'<line x1="{mxk-px*w_px*0.46:.1f}" y1="{myk-py*w_px*0.46:.1f}" '
                             f'x2="{mxk+px*w_px*0.46:.1f}" y2="{myk+py*w_px*0.46:.1f}" '
                             f'stroke="#3a4048" stroke-width="1.0"/>')
        else:
            # chaîne : 2 plaques sombres + rouleaux clairs
            for s in (+1, -1):
                parts.append(f'<line x1="{ax+px*s*w_px*0.42:.1f}" y1="{ay+py*s*w_px*0.42:.1f}" '
                             f'x2="{bx2+px*s*w_px*0.42:.1f}" y2="{by2+py*s*w_px*0.42:.1f}" '
                             f'stroke="#333333" stroke-width="0.6"/>')
            for k in range(n + 1):
                t = k * step
                mxk, myk = ax + ux * t, ay + uy * t
                parts.append(f'<circle cx="{mxk:.1f}" cy="{myk:.1f}" r="{w_px*0.26:.1f}" '
                             f'fill="#aab0b8" stroke="#333333" stroke-width="0.4"/>')

    return '<g class="drivetrain">' + "".join(parts) + '</g>'


def _draw_battery(bike, calc, sx, sy, ox, oy) -> str:
    """Pack batterie dans le tube diagonal : forme RÉELLE BikeCAD (sprite normalisé)
    placée le long du tube, + liseré vert (OK) / rouge (débordement) = indicateur de fit."""
    from ..calculations.battery import battery_polygon_world, compute_battery
    poly = battery_polygon_world(bike, calc)
    if poly is None:
        return ""
    res = compute_battery(bike, calc)
    ok = res.fits_triangle and res.clears_motor and res.clears_tubes
    edge = "#27ae60" if ok else "#c0392b"

    parts = ['<g class="battery">']
    part = _PARTS.get("battery_norm")
    pts = " ".join(f"{x*sx+ox:.1f},{y*sy+oy:.1f}" for (x, y) in poly)
    if ok and part and part.get("paths"):
        # FIT OK → pack réel (sprite) + liseré vert
        p0, p1 = poly[0], poly[1]
        axis_ang = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        along = math.hypot(p1[0] - p0[0], p1[1] - p0[1])  # = bat.length
        cx = sum(p[0] for p in poly) / 4
        cy = sum(p[1] for p in poly) / 4
        norm_len = part.get("size", [424.7, 110])[0] or 424.7
        bscale = along / norm_len if norm_len else 1.0
        parts.append(_draw_sprite("battery_norm", cx, cy, sx, sy, ox, oy,
                                  scale=bscale, angle_deg=axis_ang, klass="battery"))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="{edge}" '
                     f'stroke-width="2.5" stroke-linejoin="round" opacity="0.9"/>')
        # Étiquette V·Wh au centroïde
        cxl = sum(p[0] for p in poly) / 4 * sx + ox
        cyl = sum(p[1] for p in poly) / 4 * sy + oy
        label = f"{bike.battery.voltage:.0f}V · {bike.battery.capacity_wh:.0f}Wh"
        parts.append(f'<text x="{cxl:.1f}" y="{cyl:.1f}" text-anchor="middle" '
                     f'dominant-baseline="middle" font-size="12" font-family="sans-serif" '
                     f'font-weight="bold" fill="#fff" stroke="#000" stroke-width="0.4" '
                     f'paint-order="stroke">{label}</text>')
    else:
        # NE TIENT PAS → on ne plaque PAS un gros pack noir hors cadre : juste un
        # contour rouge pointillé (= « batterie trop grande pour ce cadre »),
        # le détail du fit est dans le panneau Batterie.
        parts.append(f'<polygon points="{pts}" fill="none" stroke="#c0392b" '
                     f'stroke-width="2" stroke-dasharray="7 5" stroke-linejoin="round" opacity="0.75"/>')
    parts.append("</g>")
    return "".join(parts)


def _draw_pivots(pres, sx, sy, ox, oy) -> str:
    """Hardware des pivots : coupe roulement (logement + bague ext + billes + axe)
    à chaque point de pivot. `pres` = PivotResult (compute_pivots)."""
    if not pres or not getattr(pres, "ok", False):
        return ""
    out = ['<g class="pivots">']
    for p in pres.pivots:
        cx, cy = _pt(p.x, p.y, sx, sy, ox, oy)
        r_house = max(5.0, p.housing_od / 2 * abs(sx))
        r_od    = max(4.0, p.od / 2 * abs(sx))
        r_bore  = max(1.6, p.bore / 2 * abs(sx))
        is_bush = p.bearing.startswith("bushing")
        race = "#b9874a" if is_bush else "#8b9099"   # bague bronze vs roulement acier
        # logement usiné dans le lug
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_house:.1f}" '
                   f'fill="#e7eaef" stroke="#5d636b" stroke-width="1"/>')
        # bague extérieure
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_od:.1f}" fill="none" '
                   f'stroke="{race}" stroke-width="{max(1.5, (r_od-r_bore)*0.32):.1f}"/>')
        # billes (roulement) — 8 petites billes entre alésage et OD
        if not is_bush and r_od - r_bore > 4:
            rb = (r_od + r_bore) / 2
            for i in range(8):
                a = 2 * math.pi * i / 8
                bx, by = cx + rb * math.cos(a), cy + rb * math.sin(a)
                out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{(r_od-r_bore)*0.22:.1f}" '
                           f'fill="#d6dae0" stroke="#5d636b" stroke-width="0.4"/>')
        # alésage + axe
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_bore:.1f}" '
                   f'fill="#33373d" stroke="#1a1d22" stroke-width="0.6"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_bore*0.42:.1f}" fill="#0e1013"/>')
    out.append('</g>')
    return "".join(out)


# Couleur par catégorie de visserie (cohérent avec le panneau Visserie)
_FAST_CAT_COL = {
    "Cockpit":       "#2980b9",
    "Tige de selle": "#8e44ad",
    "Freins":        "#c0392b",
    "Roues":         "#16a085",
    "Transmission":  "#d35400",
    "Moteur":        "#2c3e50",
    "Suspension":    "#e67e22",
    "Divers":        "#7f8c8d",
}


def _bolt_glyph(cx: float, cy: float, r: float, col: str, drive: str) -> str:
    """Tête de vis : empreinte étoile (Torx) ou hexagone (BTR/hex)."""
    d = drive.lower()
    out = [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{col}" '
           f'stroke="#0d0f12" stroke-width="0.9"/>']
    if "torx" in d or "étoile" in d or "etoile" in d:
        pts = []
        for i in range(12):
            rr = r * 0.60 if i % 2 == 0 else r * 0.28
            a = math.pi * i / 6
            pts.append(f"{cx + rr*math.cos(a):.1f},{cy + rr*math.sin(a):.1f}")
        out.append(f'<polygon points="{" ".join(pts)}" fill="#0e1013"/>')
    else:
        pts = [f"{cx + r*0.55*math.cos(math.pi/6 + math.pi*i/3):.1f},"
               f"{cy + r*0.55*math.sin(math.pi/6 + math.pi*i/3):.1f}" for i in range(6)]
        out.append(f'<polygon points="{" ".join(pts)}" fill="#0e1013"/>')
    return "".join(out)


def _draw_fasteners(fres, sx, sy, ox, oy) -> str:
    """Repère chaque point de vis/boulon (tête colorée par catégorie + empreinte
    Torx/hex, quantité × N). `fres` = FastenerResult (compute_fasteners)."""
    if not fres or not getattr(fres, "ok", False):
        return ""
    # Regrouper les glyphes au même point (BB, axe…) pour les décaler en étoile.
    groups: dict = {}
    for it in fres.items:
        groups.setdefault((round(it.x), round(it.y)), []).append(it)
    out = ['<g class="fasteners">']
    for (_gx, _gy), its in groups.items():
        n = len(its)
        for i, it in enumerate(its):
            cx, cy = _pt(it.x, it.y, sx, sy, ox, oy)
            if n > 1:
                a = 2 * math.pi * i / n
                cx += 12 * math.cos(a)
                cy += 12 * math.sin(a)
            col = _FAST_CAT_COL.get(it.category, "#7f8c8d")
            out.append(_bolt_glyph(cx, cy, 6.0, col, it.drive))
            if it.qty > 1:
                out.append(f'<text x="{cx + 7.5:.1f}" y="{cy - 5:.1f}" font-size="9" '
                           f'font-family="sans-serif" font-weight="bold" fill="#111" '
                           f'stroke="#fff" stroke-width="0.5" paint-order="stroke">×{it.qty}</text>')
    # Légende compacte (catégories présentes) en haut à gauche
    cats: list = []
    for it in fres.items:
        if it.category not in cats:
            cats.append(it.category)
    ly = 64
    out.append(f'<rect x="10" y="{ly-14}" width="146" height="{len(cats)*16+10}" rx="5" '
               f'fill="#ffffff" stroke="#c5ccd6" stroke-width="1" opacity="0.92"/>')
    out.append(f'<text x="18" y="{ly}" font-size="10" font-family="sans-serif" '
               f'font-weight="bold" fill="#333">Visserie</text>')
    for c in cats:
        ly += 16
        out.append(f'<circle cx="24" cy="{ly-3:.0f}" r="5" fill="{_FAST_CAT_COL.get(c,"#7f8c8d")}" '
                   f'stroke="#0d0f12" stroke-width="0.8"/>')
        out.append(f'<text x="34" y="{ly:.0f}" font-size="10" font-family="sans-serif" '
                   f'fill="#333">{c}</text>')
    out.append('</g>')
    return "".join(out)


def _draw_dropout(rear_axle, bb, adjust_mm, method, sx, sy, ox, oy) -> str:
    """Patte arrière RÉGLABLE pour tendre la courroie : glissière le long de la
    base (axe AR → BB), de longueur `adjust_mm`, avec l'axe en bout et une cote ↔."""
    if adjust_mm <= 0.1:
        return ""
    ax, ay = rear_axle
    # Direction de la base (axe AR → BB) normalisée
    dx, dy = bb[0] - ax, bb[1] - ay
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    # Extrémités de la glissière (l'axe coulisse de adjust_mm vers l'avant)
    x0, y0 = ax, ay                       # position détendue (arrière)
    x1, y1 = ax + ux * adjust_mm, ay + uy * adjust_mm   # position tendue (avant)
    sx0, sy0 = _pt(x0, y0, sx, sy, ox, oy)
    sx1, sy1 = _pt(x1, y1, sx, sy, ox, oy)
    r_axle = max(4.0, 6.0 * abs(sx))      # rayon visuel de l'axe (~12mm)
    # Perpendiculaire pour l'épaisseur de la lumière
    px, py = -uy, ux
    half = r_axle * 0.7
    out = ['<g class="dropout">']
    # corps de la patte (lumière oblongue)
    p_sx, p_sy = px * half, -py * half
    poly = (f'{sx0 + p_sx:.1f},{sy0 + p_sy:.1f} {sx1 + p_sx:.1f},{sy1 + p_sy:.1f} '
            f'{sx1 - p_sx:.1f},{sy1 - p_sy:.1f} {sx0 - p_sx:.1f},{sy0 - p_sy:.1f}')
    out.append(f'<polygon points="{poly}" fill="#cfd4da" stroke="#5d636b" stroke-width="1.2"/>')
    # rails de la glissière
    out.append(f'<line x1="{sx0 + p_sx:.1f}" y1="{sy0 + p_sy:.1f}" x2="{sx1 + p_sx:.1f}" '
               f'y2="{sy1 + p_sy:.1f}" stroke="#5d636b" stroke-width="0.8"/>')
    out.append(f'<line x1="{sx0 - p_sx:.1f}" y1="{sy0 - p_sy:.1f}" x2="{sx1 - p_sx:.1f}" '
               f'y2="{sy1 - p_sy:.1f}" stroke="#5d636b" stroke-width="0.8"/>')
    # axe (à mi-course, position de réglage)
    mx, my = (sx0 + sx1) / 2, (sy0 + sy1) / 2
    out.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{r_axle:.1f}" fill="#33373d" '
               f'stroke="#0e1013" stroke-width="1"/>')
    out.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{r_axle*0.4:.1f}" fill="#0e1013"/>')
    # trait de réglage (course de tension) + cote
    out.append(f'<line x1="{sx0:.1f}" y1="{sy0 - r_axle - 4:.1f}" x2="{sx1:.1f}" '
               f'y2="{sy1 - r_axle - 4:.1f}" stroke="#e8851a" stroke-width="1.4"/>')
    label = {"sliding_dropout": "patte coulissante", "eccentric_bb": "BB excentrique",
             "eccentric_pivot": "pivot excentrique"}.get(method, method)
    out.append(f'<text x="{(sx0+sx1)/2:.1f}" y="{(sy0+sy1)/2 - r_axle - 9:.1f}" '
               f'font-size="9" font-family="sans-serif" fill="#e8851a" '
               f'text-anchor="middle">↔ {adjust_mm:.0f}mm ({label})</text>')
    out.append('</g>')
    return "".join(out)


def _draw_lugs(nodes, sx, sy, ox, oy, scale) -> str:
    """Lugs CNC aux jonctions : manchon (collar) le long de chaque douille +
    corps central usiné. Montre la construction lug-and-bond du cadre."""
    if not nodes:
        return ""
    metal = PALETTE["lug"]
    parts = ['<g class="lugs">']
    for n in nodes:
        nx, ny = n.x, n.y
        bores = [s.bore_dia for s in n.sockets] or [40.0]
        # Manchons : chaque douille = tube métal le long de son axe (longueur = insertion)
        for s in n.sockets:
            a = math.radians(s.axis_deg)
            ex = nx + math.cos(a) * s.depth
            ey = ny + math.sin(a) * s.depth
            parts.append(_draw_tube(nx, ny, ex, ey, s.bore_dia + 6.0, metal,
                                    sx, sy, ox, oy, scale, cap_r=(s.bore_dia + 6.0) / 2))
        # Corps central du lug (boule usinée) — padding réduit pour ne pas noyer le nœud
        cxp, cyp = _pt(nx, ny, sx, sy, ox, oy)
        r_hub = (max(bores) / 2 + 4.0) * abs(sx)
        parts.append(f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r_hub:.1f}" '
                     f'fill="{metal}" stroke="{PALETTE["lug_edge"]}" stroke-width="0.8"/>')
        # reflet
        parts.append(f'<circle cx="{cxp-r_hub*0.3:.1f}" cy="{cyp-r_hub*0.3:.1f}" '
                     f'r="{r_hub*0.32:.1f}" fill="#e8ebef" opacity="0.5"/>')
    parts.append('</g>')
    return "".join(parts)


def _draw_brakes(bike, calc, sx, sy, ox, oy, which="both") -> str:
    """Disques de frein (rotors) aux deux axes. Les étriers sont dessinés
    séparément (_draw_calipers), PAR-DESSUS la fourche/le cadre, pour rester visibles.
    `which` (both|front|rear) → ne dessine qu'un disque (utile pour grouper l'AR sous
    l'animation de suspension et l'AV sous la compression de fourche)."""
    bk = bike.brakes
    if not str(bk.style).startswith("disc"):
        return ""
    rotors = {"front": (calc.front_axle, bk.rotor_front),
              "rear":  (calc.rear_axle,  bk.rotor_rear)}
    sel = (["front", "rear"] if which == "both" else [which])
    parts = []
    for axle, rotor in (rotors[k] for k in sel):
        scx, scy, sr = _circle(axle.x, axle.y, rotor / 2, sx, sy, ox, oy)
        # disque plein argent (piste de freinage) + anneau intérieur (zone ajourée)
        parts.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr:.1f}" '
                     f'fill="{PALETTE["rotor"]}" stroke="{PALETTE["rim_dark"]}" '
                     f'stroke-width="1.0" opacity="0.92" />')
        parts.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr*0.74:.1f}" '
                     f'fill="none" stroke="{_shade(PALETTE["rotor"],0.8)}" stroke-width="1.0" opacity="0.8" />')
        # perçages de la piste
        for i in range(10):
            a = 2 * math.pi * i / 10
            hx, hy = _pt(axle.x + rotor / 2 * 0.87 * math.cos(a),
                         axle.y + rotor / 2 * 0.87 * math.sin(a), sx, sy, ox, oy)
            parts.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="2.0" fill="{PALETTE["bg"]}" '
                         f'stroke="{PALETTE["rim_dark"]}" stroke-width="0.4" />')
        # araignée centrale (carrier) sombre
        parts.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr*0.34:.1f}" '
                     f'fill="{_shade(PALETTE["rotor"],0.7)}" stroke="{PALETTE["rim_dark"]}" stroke-width="0.6" />')
    return '<g class="brakes">' + "".join(parts) + '</g>'


def _draw_calipers(bike, calc, sx, sy, ox, oy, which="both") -> str:
    """Étriers 4-pistons (CONTOUR RÉEL) enjambant la périphérie du disque, dessinés
    PAR-DESSUS la fourche/le cadre. AV = posé au bord arrière du fourreau (visible) ;
    AR = près du hauban/de la base. Oreilles post-mount + 2 vis M6.
    `which` (both|front|rear) → un seul étrier (l'AR suit la rotation du bras,
    l'AV suit la compression de fourche)."""
    bk = bike.brakes
    if not str(bk.style).startswith("disc"):
        return ""
    # angle (math, repère monde y-haut) sur la périphérie du disque.
    caliper_phi = {"front": math.radians(158.0), "rear": math.radians(48.0)}
    calipers = {"front": (calc.front_axle, bk.rotor_front),
                "rear":  (calc.rear_axle,  bk.rotor_rear)}
    sel = (["front", "rear"] if which == "both" else [which])
    parts = []
    for which in sel:
        axle, rotor = calipers[which]
        phi = caliper_phi[which]
        cw_box, ch_box = 60.0, 66.0          # mm (tangentiel × radial)
        rr = rotor / 2.0
        anchor = (axle.x + rr * math.cos(phi), axle.y + rr * math.sin(phi))
        cal_d = _norm_path(_OUTLINE_CALIPER, anchor, cw_box, ch_box,
                           anchor_n=(0.50, 0.78), angle_deg=math.degrees(phi) - 90.0,
                           sx=sx, sy=sy, ox=ox, oy=oy)
        parts.append(f'<path d="{cal_d}" fill="{PALETTE["crank"]}" stroke="#0a0c0f" '
                     f'stroke-width="1.0" stroke-linejoin="round"/>')
        # 2 vis post-mount (oreilles tangentielles)
        for tn in (0.03, 0.97):
            bx = anchor[0] + (tn - 0.50) * cw_box * math.cos(phi - math.pi/2) \
                 + (0.55 - 0.78) * ch_box * math.cos(phi)
            by = anchor[1] + (tn - 0.50) * cw_box * math.sin(phi - math.pi/2) \
                 + (0.55 - 0.78) * ch_box * math.sin(phi)
            bpx, bpy = _pt(bx, by, sx, sy, ox, oy)
            parts.append(f'<circle cx="{bpx:.1f}" cy="{bpy:.1f}" r="3.0" fill="#15181c" '
                         f'stroke="#0a0c0f" stroke-width="0.5"/>')
    return '<g class="calipers">' + "".join(parts) + '</g>'


def _draw_rider(fit, sx, sy, ox, oy) -> str:
    """Squelette du pilote (plan sagittal) : segments + articulations + tête."""
    def P(kp):
        return None if kp is None else (kp.x * sx + ox, kp.y * sy + oy)

    hip = P(fit.hip); knee = P(fit.knee); pedal = P(fit.pedal)
    sho = P(fit.shoulder); elb = P(fit.elbow); hand = P(fit.hand); head = P(fit.head)

    col = "#d63031"      # rouge silhouette
    seg = []
    def line(a, b, w=5):
        if a and b:
            seg.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                       f'x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" '
                       f'stroke-width="{w}" stroke-linecap="round" opacity="0.85"/>')
    # Jambe
    line(hip, knee); line(knee, pedal)
    # Torse + bras
    line(hip, sho, 7); line(sho, elb); line(elb, hand)
    # Tête
    if head and sho:
        hr = math.hypot(head[0] - sho[0], head[1] - sho[1]) * 0.45
        seg.append(f'<circle cx="{head[0]:.1f}" cy="{head[1]:.1f}" r="{hr:.1f}" '
                   f'fill="none" stroke="{col}" stroke-width="4" opacity="0.85"/>')
    # Articulations
    for j in (hip, knee, sho, elb):
        if j:
            seg.append(f'<circle cx="{j[0]:.1f}" cy="{j[1]:.1f}" r="4.5" '
                       f'fill="{col}" opacity="0.9"/>')
    return '<g class="rider">' + "".join(seg) + '</g>'


def _draw_suspension(frames, wheel_r_r, sx, sy, ox, oy, scale,
                     animate=False, period=4.0) -> str:
    """Overlay CLAIR de la biellette : bielles colorées épaisses, amortisseur
    (corps + tige + œillets) qui se comprime, pivots marqués, jante AR mobile.

    `frames` = KinematicsResult.frames. Statique → frame de sag. Animé → SMIL.
    """
    if not frames:
        return ""

    def P(pt):
        return (pt[0] * sx + ox, pt[1] * sy + oy)

    def vals(seq):
        full = list(seq) + list(reversed(seq[:-1]))
        return ";".join(f"{v:.1f}" for v in full)

    anim_simple = f'<animate attributeName="{{a}}" values="{{v}}" dur="{period}s" repeatCount="indefinite"/>'

    sag_i = min(range(len(frames)),
                key=lambda i: abs(frames[i]["travel"] - frames[-1]["travel"] * 0.3))
    ref = frames[sag_i]
    n_links = len(ref["links"])
    LINK_COL = (["#e67e22"] if n_links == 1
                else ["#e67e22", "#2e86de", "#8e44ad", "#16a085"])[:n_links]
    parts = ['<g class="suspension">']

    def aline(getter, color, w):
        """Ligne animée (ou statique au sag) : getter(frame)->((x1,y1),(x2,y2))."""
        if animate:
            a1 = [P(getter(fr)[0]) for fr in frames]
            a2 = [P(getter(fr)[1]) for fr in frames]
            parts.append(
                f'<line stroke="{color}" stroke-width="{w}" stroke-linecap="round" opacity="0.95">'
                + anim_simple.format(a="x1", v=vals([p[0] for p in a1]))
                + anim_simple.format(a="y1", v=vals([p[1] for p in a1]))
                + anim_simple.format(a="x2", v=vals([p[0] for p in a2]))
                + anim_simple.format(a="y2", v=vals([p[1] for p in a2])) + '</line>')
        else:
            p1, p2 = P(getter(ref)[0]), P(getter(ref)[1])
            parts.append(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" '
                         f'stroke="{color}" stroke-width="{w}" stroke-linecap="round" opacity="0.95"/>')

    def adot(getter, r, fill, stroke="#fff", sw=2.0):
        if animate:
            pts = [P(getter(fr)) for fr in frames]
            parts.append(f'<circle r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}">'
                         + anim_simple.format(a="cx", v=vals([p[0] for p in pts]))
                         + anim_simple.format(a="cy", v=vals([p[1] for p in pts])) + '</circle>')
        else:
            p = P(getter(ref))
            parts.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r}" fill="{fill}" '
                         f'stroke="{stroke}" stroke-width="{sw}"/>')

    # ── Jante AR mobile (anneau accent, lisible) + axe ───────────────────────
    rim = wheel_r_r * 0.84 * abs(sx)
    if animate:
        pts = [P(fr["axle"]) for fr in frames]
        parts.append(f'<circle r="{rim:.1f}" fill="none" stroke="#e84393" stroke-width="3" opacity="0.55">'
                     + anim_simple.format(a="cx", v=vals([p[0] for p in pts]))
                     + anim_simple.format(a="cy", v=vals([p[1] for p in pts])) + '</circle>')
    else:
        a = P(ref["axle"])
        parts.append(f'<circle cx="{a[0]:.1f}" cy="{a[1]:.1f}" r="{rim:.1f}" '
                     f'fill="none" stroke="#e84393" stroke-width="3" opacity="0.55"/>')

    # ── Bielles colorées (chainstay/seatstay/rocker) ─────────────────────────
    for li in range(n_links):
        aline(lambda fr, li=li: fr["links"][li], LINK_COL[li], 6)

    # ── Amortisseur ──────────────────────────────────────────────────────────
    up0, lo0 = ref["shock"][1], ref["shock"][0]   # œillet haut (fixe) / bas (mobile)
    shock_part = _PARTS.get("rear_shock_norm")
    if (not animate) and shock_part and shock_part.get("paths"):
        # Vue statique : FORME RÉELLE BikeCAD, ancrée à l'œillet bas, axe vers le haut.
        sang = math.degrees(math.atan2(up0[1] - lo0[1], up0[0] - lo0[0]))
        eye = math.hypot(up0[0] - lo0[0], up0[1] - lo0[1])
        ax_len = shock_part.get("axis_len", 182.0) or 182.0
        parts.append(_draw_sprite("rear_shock_norm", lo0[0], lo0[1], sx, sy, ox, oy,
                                  scale=eye / ax_len, angle_deg=sang - 90.0,
                                  empty_fill="#8a929c", klass="shock"))
        adot(lambda fr: fr["shock"][0], 4, "#0e6b57")                  # œillet bas
        adot(lambda fr: fr["shock"][1], 4, "#0e6b57")                  # œillet haut
    else:
        # Animation : glyphe paramétrique (corps fixe + tige coulissante = compression).
        body_len = 0.5 * math.hypot(frames[0]["shock"][0][0] - frames[0]["shock"][1][0],
                                    frames[0]["shock"][0][1] - frames[0]["shock"][1][1])

        def body_end(fr):
            up, lo = fr["shock"][1], fr["shock"][0]
            d = math.hypot(lo[0] - up[0], lo[1] - up[1]) or 1.0
            u = ((lo[0] - up[0]) / d, (lo[1] - up[1]) / d)
            return (up[0] + u[0] * body_len, up[1] + u[1] * body_len)
        aline(lambda fr: (body_end(fr), fr["shock"][0]), "#cfd6df", 4)   # tige argent
        aline(lambda fr: (fr["shock"][1], body_end(fr)), "#16a085", 11)  # corps amorto
        adot(lambda fr: fr["shock"][0], 5, "#0e6b57")                    # œillet bas (mobile)

    # ── Galet (si présent) ───────────────────────────────────────────────────
    if ref.get("idler"):
        adot(lambda fr: fr["idler"], 5, "#16a085")

    # ── Pivots MOBILES (extrémités des bielles, hors pivots-cadre) ───────────
    # début link0 = main (fixe), fin dernier link = cadre (fixe) ; les autres bougent
    for li in range(n_links):
        # extrémité « fin » de chaque bielle (sauf la dernière = pivot cadre)
        if li < n_links - 1:
            adot(lambda fr, li=li: fr["links"][li][1], 6, "#c0392b")

    # ── Pivots FIXES au cadre (carrés blancs cerclés) ────────────────────────
    f0 = frames[0]
    fixed = [f0["links"][0][0], f0["shock"][1]]
    if n_links >= 3:
        fixed.append(f0["links"][2][1])
    for fp in fixed:
        p = P(fp)
        parts.append(f'<rect x="{p[0]-5:.1f}" y="{p[1]-5:.1f}" width="10" height="10" '
                     f'fill="#1b2330" stroke="#fff" stroke-width="2"/>')

    parts.append("</g>")
    return "".join(parts)


def _draw_susp_analysis(frames, sx, sy, ox, oy) -> str:
    """Overlay d'ANALYSE propre (toggle Suspension, hors animation) : trajectoire
    de l'axe AR à travers la course + repères topout/bottom-out. Pas de bielles
    debug ni de carrés — le linkage réaliste est déjà dessiné en statique."""
    if not frames or len(frames) < 2:
        return ""
    pts = [_pt(fr["axle"][0], fr["axle"][1], sx, sy, ox, oy) for fr in frames if "axle" in fr]
    if len(pts) < 2:
        return ""
    d = "M " + " L ".join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts)
    out = [f'<path d="{d}" fill="none" stroke="#e84393" stroke-width="2.6" '
           f'stroke-dasharray="2 3" opacity="0.9"/>']
    for p, col, lbl in ((pts[0], "#0e6b57", "topout"), (pts[-1], "#c0392b", "fond")):
        out.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="4" fill="{col}" '
                   f'stroke="#fff" stroke-width="1"/>')
    out.append(f'<text x="{pts[-1][0]+6:.1f}" y="{pts[-1][1]:.1f}" font-size="11" '
               f'font-family="sans-serif" fill="#c0392b">trajectoire d\'axe</text>')
    return '<g class="susp-analysis">' + "".join(out) + '</g>'


def _draw_shock(lo, up, sx, sy, ox, oy, scale) -> str:
    """Amortisseur à air RÉALISTE le long de l'axe lo→up (œillet bas → haut) :
    œillet + tige argent + bonbonne (air can) + bague de sag + œillet haut +
    petite molette. Lisible comme un vrai amorto quelle que soit l'orientation."""
    L = math.hypot(up[0] - lo[0], up[1] - lo[1]) or 1.0
    ux, uy = (up[0] - lo[0]) / L, (up[1] - lo[1]) / L      # axe (vers le haut)
    px, py = -uy, ux                                       # perpendiculaire
    def at(t, off=0.0):
        return (lo[0] + ux * L * t + px * off, lo[1] + uy * L * t + py * off)
    out = []
    # tige (damper shaft) : fine, argent, depuis l'œillet bas (t=0) jusque dans le corps.
    s0, s1 = at(0.0), at(0.45)
    out.append(_draw_tube(s0[0], s0[1], s1[0], s1[1], 12.0, "#c7ccd3",
                          sx, sy, ox, oy, scale, cap_r=6.0))
    # corps / bonbonne air (air can) : gros cylindre jusqu'à l'œillet haut (t=1).
    b0, b1 = at(0.38), at(1.0)
    out.append(_draw_tube(b0[0], b0[1], b1[0], b1[1], 40.0, "#3b4047",
                          sx, sy, ox, oy, scale, cap_r=20.0))
    # reflet sur la bonbonne
    h0, h1 = at(0.46, 9.0), at(0.94, 9.0)
    out.append(_draw_tube(h0[0], h0[1], h1[0], h1[1], 6.0, "#5b626b",
                          sx, sy, ox, oy, scale, cap_r=3.0))
    # bague de sag (o-ring) sur la tige exposée
    rcx, rcy = _pt(*at(0.28), sx, sy, ox, oy)
    out.append(f'<circle cx="{rcx:.1f}" cy="{rcy:.1f}" r="{8.5*scale:.1f}" fill="none" '
               f'stroke="#e74c3c" stroke-width="{2.4*scale:.1f}"/>')
    # molette de réglage (détente) en tête, décalée
    kcx, kcy = _pt(*at(0.88, 13.0), sx, sy, ox, oy)
    out.append(f'<circle cx="{kcx:.1f}" cy="{kcy:.1f}" r="{6.0*scale:.1f}" fill="#1d6fa5" '
               f'stroke="#10324a" stroke-width="0.8"/>')
    # œillets bas/haut (anneaux DU)
    for pt in (lo, up):
        ex, ey = _pt(*pt, sx, sy, ox, oy)
        out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{9.0*scale:.1f}" fill="#2b2f35" '
                   f'stroke="#14171b" stroke-width="1.1"/>')
        out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{4.0*scale:.1f}" fill="#0e1013"/>')
    return "".join(out)


def _draw_gusset(root, tip, sx, sy, ox, oy, scale,
                 w_root=30.0, w_tip=13.0, fill=None, edge=None) -> str:
    """Gousset/clevis SOLIDE (bracket coulé) d'un membre (root, large) vers un
    œillet (tip, étroit) : polygone effilé → lecture « patte boulonnée », jamais
    un fil flottant. Utilisé pour ancrer un œillet d'amortisseur hors-membre."""
    fill = fill or PALETTE["lug"]
    edge = edge or PALETTE["lug_edge"]
    dx, dy = tip[0] - root[0], tip[1] - root[1]
    L = math.hypot(dx, dy) or 1.0
    px, py = -dy / L, dx / L          # perpendiculaire (monde)
    quad = [(root[0] + px * w_root / 2, root[1] + py * w_root / 2),
            (tip[0]  + px * w_tip  / 2, tip[1]  + py * w_tip  / 2),
            (tip[0]  - px * w_tip  / 2, tip[1]  - py * w_tip  / 2),
            (root[0] - px * w_root / 2, root[1] - py * w_root / 2)]
    pts = " ".join(f"{x*sx+ox:.1f},{y*sy+oy:.1f}" for x, y in quad)
    return (f'<polygon points="{pts}" fill="{fill}" stroke="{edge}" '
            f'stroke-width="1" stroke-linejoin="round"/>')


def _draw_susp_links_static(bike, calc, sx, sy, ox, oy, scale) -> str:
    """Rendu RÉALISTE (non-debug) de l'arrière suspendu en position topout :
    biellette (rocker) en plaque métal + amortisseur paramétrique + axes de pivot.
    Les bras (base/hauban) sont dessinés comme tubes de cadre dans render_svg.

    ROBUSTESSE : l'amortisseur et ses œillets sont TOUJOURS reliés à un membre
    porteur par un gousset solide (jamais flottant), et on ne dessine pas de patte
    REDONDANTE quand l'œillet est déjà l'extrémité d'un membre (hauban high-pivot,
    bras de biellette four-bar)."""
    su = bike.suspension
    topo = su.linkage_type
    A  = (su.main_pivot.x, su.main_pivot.y)
    C  = (su.upper_ss_pivot.x, su.upper_ss_pivot.y)
    D  = (su.upper_frame_pivot.x, su.upper_frame_pivot.y)
    B  = (su.horst_pivot.x, su.horst_pivot.y)
    lo = (su.shock_lower.x, su.shock_lower.y)
    up = (su.shock_upper.x, su.shock_upper.y)

    def W(p):
        return _pt(p[0], p[1], sx, sy, ox, oy)

    out = ['<g class="rear-susp">']

    # ── Biellette / rocker = bellcrank COMPACT : bras métal du pivot cadre (D)
    # vers le pivot hauban (C) [+ vers l'œillet d'amorto si montage sur biellette].
    # (PAS un grand triangle vers l'ancrage fixe d'amorto — c'était le « slab ».)
    is_four_bar = str(topo).startswith("four_bar")
    mount = getattr(su, "shock_mount", "auto")
    if mount == "auto":
        mount = "chainstay" if su.shock_on_chainstay else "coupler"
    if is_four_bar:
        # Biellette (rocker) : bras du pivot cadre (D) vers le pivot hauban (C) et,
        # si l'amorto est sur la biellette, vers l'œillet bas (lo) → lo PORTÉ.
        rocker_ends = [C] + ([lo] if mount == "rocker" else [])
        for e in rocker_ends:
            out.append(_draw_tube(D[0], D[1], e[0], e[1], 20.0, PALETTE["lug"],
                                  sx, sy, ox, oy, scale, cap_r=10.0))
        dcx, dcy = W(D)                                   # moyeu central de la biellette
        out.append(f'<circle cx="{dcx:.1f}" cy="{dcy:.1f}" r="{13.0*scale:.1f}" '
                   f'fill="{PALETTE["lug"]}" stroke="{PALETTE["lug_edge"]}" stroke-width="1"/>')

    def _proj(p, a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]; L2 = dx*dx + dy*dy or 1.0
        t = max(0.0, min(1.0, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / L2))
        return (a[0]+t*dx, a[1]+t*dy)
    bb = (calc.bb.x, calc.bb.y)
    axle = (calc.rear_axle.x, calc.rear_axle.y)

    # ── Œillet FIXE (up) : gousset SOLIDE vers le tube le plus proche (selle/diagonal)
    # → amorto boulonné au cadre, jamais en l'air.
    cands = [_proj(up, bb, (calc.seat_tube_top.x, calc.seat_tube_top.y)),
             _proj(up, bb, (calc.crown.x, calc.crown.y))]
    anc = min(cands, key=lambda q: (q[0]-up[0])**2 + (q[1]-up[1])**2)
    if math.hypot(anc[0]-up[0], anc[1]-up[1]) > 6:
        out.append(_draw_gusset(anc, up, sx, sy, ox, oy, scale, w_root=32.0, w_tip=15.0))

    # ── Œillet MOBILE (lo) : NE PAS dessiner de patte redondante quand lo est DÉJÀ
    # l'extrémité d'un membre porteur — hauban high-pivot (axe→lo, dessiné par
    # render_svg) ou bras de biellette four-bar (D→lo ci-dessus). Sinon (amorto sur
    # base/coupler), gousset solide vers le membre porteur le plus proche.
    lo_carried = (not is_four_bar) or (mount == "rocker")
    if not lo_carried:
        arms = [(A, axle), (axle, C)]                     # base / hauban
        lo_anc = min((_proj(lo, a, b) for a, b in arms),
                     key=lambda q: (q[0]-lo[0])**2 + (q[1]-lo[1])**2)
        if math.hypot(lo_anc[0]-lo[0], lo_anc[1]-lo[1]) > 6:
            out.append(_draw_gusset(lo_anc, lo, sx, sy, ox, oy, scale, w_root=28.0, w_tip=14.0))

    # ── Amortisseur paramétrique (air can + tige + œillets) lo → up ─────────
    out.append(f'<g class="shock">{_draw_shock(lo, up, sx, sy, ox, oy, scale)}</g>')

    # ── Axes de pivot (alésage sombre cerclé acier) — UNIQUEMENT les pivots de la
    # topologie active (sinon dots parasites C/D non utilisés sur un single-pivot).
    if is_four_bar:
        pivots = [A, B, C, D]
    else:                                   # high_pivot single-pivot : pivot + galet
        pivots = [A] + ([(su.idler.x, su.idler.y)] if getattr(su, "use_idler", False) else [])
    for p in pivots:
        cx, cy = W(p)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="#8b9099" '
                   f'stroke="#3a3f46" stroke-width="1.4"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.4" fill="#23272d"/>')
    # œillets d'amortisseur
    for p in (lo, up):
        cx, cy = W(p)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="#3a3f46" '
                   f'stroke="#1a1d22" stroke-width="1"/>')

    out.append('</g>')
    return "".join(out)


def render_svg(bike: BikeDesign, calc: CalcResult,
               width: int = 1400, height: int = 750,
               show_dims: bool = True, fit=None,
               suspension=None, animate_suspension=False, lugs=None,
               show_ground: bool = False, pivots=None, fasteners=None) -> str:
    _TUBE_ID[0] = 0
    f = bike.frame
    fk = bike.fork

    wheel_r_r = f.wheel_r / 2
    wheel_r_f = f.wheel_f / 2
    rim_r_r   = bike.wheel_r.effective_rim_dia / 2
    rim_r_f   = bike.wheel_f.effective_rim_dia / 2
    n_sp_r    = bike.wheel_r.spokes
    n_sp_f    = bike.wheel_f.spokes

    ra  = calc.rear_axle
    fa  = calc.front_axle
    cr  = calc.crown
    ht  = calc.ht_top
    stt = calc.seat_tube_top
    sb  = calc.stem_base
    stip= calc.stem_tip
    hbc = calc.handlebar_center
    sdl_tip = calc.saddle_tip
    sdl_mid = calc.saddle_mid
    bb  = calc.bb
    gl  = calc.ground_level  # Y sol en coords monde

    # ── Bounding box en coords monde (cadrage plein-cadre façon BikeCAD) ──────
    world_min_x = ra.x - wheel_r_r - 12
    world_max_x = fa.x + wheel_r_f + 12
    world_min_y = gl - 8
    world_max_y = max(hbc.y, sdl_mid.y) + 30
    # Étendre la bbox pour inclure le pilote (tête haute)
    if fit is not None and getattr(fit, "ok", False) and fit.head is not None:
        world_max_y = max(world_max_y, fit.head.y + 40)

    world_w = world_max_x - world_min_x
    world_h = world_max_y - world_min_y

    margin = 18
    avail_w = width  - 2 * margin
    avail_h = height - 2 * margin
    scale_f = min(avail_w / world_w, avail_h / world_h)

    # Transformée : SVG_x = x*scale_f + ox, SVG_y = y*(-scale_f) + oy
    sx =  scale_f
    sy = -scale_f   # Y inversé (SVG Y pointe vers le bas)
    # Recentrage dans le canvas (sinon liseré asymétrique quand les ratios diffèrent)
    ox = (width  - world_w * scale_f) / 2 - world_min_x * sx
    oy = (height - world_h * scale_f) / 2 - world_max_y * sy

    # ── Sol ─────────────────────────────────────────────────────────────────
    gsy = gl * sy + oy
    ground_y = gsy

    # ── Ombres roues ────────────────────────────────────────────────────────
    rear_sx,  rear_sy  = _pt(ra.x, gl, sx, sy, ox, oy)
    front_sx, front_sy = _pt(fa.x, gl, sx, sy, ox, oy)
    sr_r = wheel_r_r * scale_f
    sr_f = wheel_r_f * scale_f

    parts: list[str] = []

    # === FOND ================================================================
    parts.append(f'<rect width="{width}" height="{height}" fill="{PALETTE["bg"]}" />')

    # === DÉGRADÉ GLOBAL DU CADRE (technique BikeCAD) =========================
    # Un SEUL dégradé userSpaceOnUse pour TOUS les tubes : 2 stops LINÉAIRES
    # (peinture pure → #333) comme BikeCAD. Axe incliné ~73° (légèrement vers
    # l'avant) et ALLONGÉ d'une hauteur de cadre sous le bas → le BB est à ~50 %
    # du mélange (la base reste saturée, pas lavée en gris).
    fr_xs = [bb.x, ra.x, stt.x, ht.x, cr.x]
    fr_ys = [bb.y, stt.y, ht.y, cr.y]
    cx_g = (min(fr_xs) + max(fr_xs)) / 2
    top_y = max(fr_ys)
    bot_frame = min(bb.y, ra.y)
    frame_h = max(1.0, top_y - bot_frame)
    gx1, gy1 = _pt(cx_g - 0.12 * frame_h, top_y, sx, sy, ox, oy)              # haut-arrière
    gx2, gy2 = _pt(cx_g + 0.42 * frame_h, bot_frame - frame_h, sx, sy, ox, oy)  # bas-avant, prolongé
    # Peinture du cadre : couleur LUE du .bcad si présente (fidélité BikeCAD), sinon le bleu DOM.
    paint = getattr(bike.frame, "color", None) or PALETTE["frame"]
    parts.append(
        f'<linearGradient id="frameGrad" gradientUnits="userSpaceOnUse" '
        f'x1="{gx1:.1f}" y1="{gy1:.1f}" x2="{gx2:.1f}" y2="{gy2:.1f}">'
        f'<stop offset="0%" stop-color="{paint}"/>'
        f'<stop offset="100%" stop-color="#333333"/></linearGradient>'
    )
    FRAME_FILL = "url(#frameGrad)"

    # === SOL (désactivé par défaut — absent des exports BikeCAD) =============
    if show_ground:
        parts.append(
            f'<rect x="0" y="{ground_y:.1f}" width="{width}" height="{height - ground_y:.1f}" '
            f'fill="{PALETTE["ground"]}" opacity="0.35" />'
        )
        parts.append(
            f'<line x1="0" y1="{ground_y:.1f}" x2="{width}" y2="{ground_y:.1f}" '
            f'stroke="#b2bec3" stroke-width="1.5" />'
        )
        for (wsx, sr) in [(rear_sx, sr_r), (front_sx, sr_f)]:
            parts.append(
                f'<ellipse cx="{wsx:.0f}" cy="{ground_y + 4:.0f}" '
                f'rx="{sr * 0.6:.0f}" ry="6" fill="#2d3436" opacity="0.12" />'
            )

    # === ANIMATION FOURCHE : si on anime, la fourche se COMPRIME (l'axe AV + les
    # fourreaux + la roue AV remontent le long de l'axe de direction, synchronisé
    # avec l'arrière sur la même période 4 s). On l'applique via un animateTransform
    # injecté dans les groupes roue AV + fourreaux (z-order préservé).
    fork_anim = ""
    if animate_suspension and (getattr(fk, "travel", 0.0) or 0.0) > 5.0:
        dux, duy = cr.x - fa.x, cr.y - fa.y
        dl = math.hypot(dux, duy) or 1.0
        comp = min((fk.travel or 60.0), 60.0)          # compression visible (mm)
        fx0, fy0 = _pt(fa.x, fa.y, sx, sy, ox, oy)
        fx1, fy1 = _pt(fa.x + dux/dl*comp, fa.y + duy/dl*comp, sx, sy, ox, oy)
        fork_anim = (f'<animateTransform attributeName="transform" type="translate" '
                     f'values="0 0;{fx1-fx0:.1f} {fy1-fy0:.1f};0 0" keyTimes="0;0.5;1" '
                     f'dur="4s" repeatCount="indefinite"/>')

    # === ANIMATION TRAIN ARRIÈRE : le bras oscillant + la roue AR + le disque/étrier
    # AR + le moyeu pivotent RIGIDEMENT autour du pivot principal (exact pour un
    # single-pivot ; très proche pour un four-bar). L'angle par image est lu sur la
    # position RÉELLE de l'axe AR (frames) → la roue suit sa vraie trajectoire. On
    # l'injecte (animateTransform rotate) dans chaque groupe arrière, même période
    # 4 s que la fourche → tout bouge en phase.
    su = bike.suspension
    full_susp = su.enabled and str(su.linkage_type) in (
        "four_bar_horst", "high_pivot_idler", "four_bar_generic")
    susp_frames = None
    if suspension:
        susp_frames = suspension if isinstance(suspension, list) else getattr(suspension, "frames", None)
    rear_anim = ""
    if animate_suspension and full_susp and susp_frames and len(susp_frames) > 1:
        Mx, My = su.main_pivot.x, su.main_pivot.y
        msx, msy = _pt(Mx, My, sx, sy, ox, oy)
        # Angle (monde) de l'axe AR p/r au pivot, DÉROULÉ (unwrap) pour éviter le saut
        # de ±360° quand atan2 traverse ±180° (sinon la roue ferait un tour complet).
        raw = []
        prev = None
        for fr in susp_frames:
            axp = fr["axle"]
            ang = math.degrees(math.atan2(axp[1] - My, axp[0] - Mx))
            if prev is not None:
                while ang - prev > 180.0:  ang -= 360.0
                while ang - prev < -180.0: ang += 360.0
            prev = ang
            raw.append(ang)
        base_ang = raw[0]
        seq = [-(a - base_ang) for a in raw]             # SVG : Y inversé → angle opposé
        full = seq + list(reversed(seq[:-1]))            # aller-retour (boucle fluide)
        vstr = ";".join(f"{d:.2f} {msx:.1f} {msy:.1f}" for d in full)
        rear_anim = (f'<animateTransform attributeName="transform" type="rotate" '
                     f'values="{vstr}" dur="4s" repeatCount="indefinite"/>')

    def _rear_group(svg: str) -> str:
        """Enveloppe un fragment dans le groupe animé du train arrière (no-op hors anim)."""
        return f'<g class="rear-anim">{rear_anim}{svg}</g>' if rear_anim else svg

    # === ROUES ===============================================================
    # Dessinées en premier (derrière le cadre). Cassette seulement si dérailleur.
    # La roue AR est groupée sous l'animation du train arrière (rotation pivot).
    is_igh = bike.drivetrain.transmission == "igh"
    rw_svg = _draw_wheel(ra.x, ra.y, wheel_r_r, sx, sy, ox, oy,
                         cassette=not is_igh, wcfg=bike.wheel_r)
    parts.append(_rear_group(rw_svg))
    fw_svg = _draw_wheel(fa.x, fa.y, wheel_r_f, sx, sy, ox, oy, wcfg=bike.wheel_f)
    parts.append(f'<g class="fork-anim">{fork_anim}{fw_svg}</g>' if fork_anim else fw_svg)

    # === MOYEU À VITESSES (IGH : Rohloff / 3X3) — gros corps de moyeu ==========
    if is_igh:
        hcx, hcy, hr = _circle(ra.x, ra.y, 56.0, sx, sy, ox, oy)
        hub_parts = [f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr:.1f}" fill="{PALETTE["hub"]}" '
                     f'stroke="#222" stroke-width="1.2"/>']
        _, _, hr2 = _circle(ra.x, ra.y, 44.0, sx, sy, ox, oy)
        hub_parts.append(f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr2:.1f}" fill="none" '
                         f'stroke="{_shade(PALETTE["hub"],0.8)}" stroke-width="1.5"/>')
        _, _, hr3 = _circle(ra.x, ra.y, 30.0, sx, sy, ox, oy)
        hub_parts.append(f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr3:.1f}" fill="{_shade(PALETTE["hub"],1.15)}" '
                         f'stroke="#333" stroke-width="0.8"/>')
        parts.append(_rear_group("".join(hub_parts)))

    # === FREINS (disques) ====================================================
    # AR groupé sous l'animation du bras ; AV sous la compression de fourche.
    if rear_anim or fork_anim:
        parts.append(_rear_group(_draw_brakes(bike, calc, sx, sy, ox, oy, which="rear")))
        fb = _draw_brakes(bike, calc, sx, sy, ox, oy, which="front")
        parts.append(f'<g class="fork-anim">{fork_anim}{fb}</g>' if fork_anim else fb)
    else:
        parts.append(_draw_brakes(bike, calc, sx, sy, ox, oy))

    # === MOTEUR (DERRIÈRE le cadre : les tubes se rejoignent par-dessus au BB) =
    parts.append(_draw_motor(bike, calc, sx, sy, ox, oy, scale_f))

    # === CADRE (technique BikeCAD : remplissages groupés → fillets aux nœuds →
    #     liseré #333 en dernière passe → silhouette « objet peint » sans coutures)
    # bases, haubans, tube de selle, top tube, down tube, tube de direction.
    # TOUT-SUSPENDU : l'arrière devient un bras oscillant (pivote au main_pivot) +
    # hauban → biellette, au lieu du triangle arrière rigide d'un hardtail.
    # (su / full_susp déjà calculés plus haut pour l'animation du train arrière)
    if full_susp:
        A_piv = (su.main_pivot.x, su.main_pivot.y)        # pivot principal (cadre)
        # SINGLE-PIVOT haut : le bras oscillant est RIGIDE et remonte jusqu'à l'œillet
        # bas d'amortisseur (la base porte l'amorto) → le hauban va à shock_lower, et
        # l'œillet est SUR le tube. FOUR-BAR : le hauban va au pivot biellette (upper_ss).
        is_hp = str(su.linkage_type) == "high_pivot_idler"
        # Bras oscillant MASSIF (pièce moulée) : base plus épaisse + hauban renforcé.
        cs_d = max(46.0, f.chainstay_d * 1.4)
        ss_d = max(32.0, f.seatstay_d * 1.5)
        if is_hp:
            # SINGLE-PIVOT haut : le bras oscillant est RIGIDE (A→axe) et remonte vers
            # l'œillet bas d'amortisseur (la base porte l'amorto).
            top_pt = (su.shock_lower.x, su.shock_lower.y)
            rear_tubes = [
                (A_piv[0], A_piv[1], ra.x, ra.y, cs_d),       # bras oscillant
                (ra.x, ra.y, top_pt[0], top_pt[1], ss_d),     # hauban → mont. amorto
            ]
        else:
            # FOUR-BAR (Horst) — suivre EXACTEMENT la topologie du solveur (four_bar.py) :
            # chainstay A→B (horst), coupler/hauban B→C (upper_ss). L'axe AR est rigide
            # avec le coupler BC, en retrait de B → patte dropout B→axe qui PORTE la roue.
            # (Avant : base A→axe + hauban axe→C ignoraient le pivot horst B → B flottait
            #  et les tubes ne coïncidaient pas avec la cinématique.)
            B_piv = (su.horst_pivot.x, su.horst_pivot.y)
            C_piv = (su.upper_ss_pivot.x, su.upper_ss_pivot.y)
            drop_d = max(30.0, ss_d * 0.8)
            rear_tubes = [
                (A_piv[0], A_piv[1], B_piv[0], B_piv[1], cs_d),   # chainstay (base)
                (B_piv[0], B_piv[1], C_piv[0], C_piv[1], ss_d),   # coupler (hauban)
                (B_piv[0], B_piv[1], ra.x, ra.y, drop_d),         # patte dropout → axe
            ]
    else:
        rear_tubes = [
            (bb.x, bb.y, ra.x, ra.y, f.chainstay_d),
            (ra.x, ra.y, stt.x, stt.y, f.seatstay_d),
        ]
    front_tubes = [
        (bb.x, bb.y, stt.x, stt.y, f.seat_tube_fd),
        (stt.x, stt.y, ht.x, ht.y, f.top_tube_d),
        (bb.x, bb.y, cr.x, cr.y, f.down_tube_d),
        (cr.x, cr.y, ht.x, ht.y, f.head_tube_d),
    ]

    def _tube_passes(tubes):
        """Remplissage (dégradé) puis liseré #333 sur une liste de tubes → fragment SVG."""
        seg = []
        for (ax_, ay_, bx_, by_, dia_) in tubes:
            seg.append(_draw_tube(ax_, ay_, bx_, by_, dia_, PALETTE["frame"],
                                  sx, sy, ox, oy, scale_f, cap_r=dia_ / 2, fill=FRAME_FILL))
        for (ax_, ay_, bx_, by_, dia_) in tubes:
            seg.append(_draw_tube(ax_, ay_, bx_, by_, dia_, PALETTE["frame"],
                                  sx, sy, ox, oy, scale_f, fill=FRAME_FILL,
                                  edge="#333333", outline_only=True))
        return "".join(seg)

    if rear_anim:
        # Bras oscillant DANS le groupe animé (pivote) ; triangle avant statique.
        parts.append(_rear_group(_tube_passes(rear_tubes)))
        parts.append(_tube_passes(front_tubes))
    else:
        # Comportement d'origine : passes entrelacées rear+front (z-order historique).
        frame_tubes = rear_tubes + front_tubes
        for (ax_, ay_, bx_, by_, dia_) in frame_tubes:
            parts.append(_draw_tube(ax_, ay_, bx_, by_, dia_, PALETTE["frame"],
                                    sx, sy, ox, oy, scale_f, cap_r=dia_ / 2, fill=FRAME_FILL))
        for (ax_, ay_, bx_, by_, dia_) in frame_tubes:
            parts.append(_draw_tube(ax_, ay_, bx_, by_, dia_, PALETTE["frame"],
                                    sx, sy, ox, oy, scale_f, fill=FRAME_FILL,
                                    edge="#333333", outline_only=True))
    # Pass 3 : cercles de fillet aux nœuds EN DERNIER (même fill, sans stroke) →
    # masque les croisements de liseré internes et fond les jonctions (façon BikeCAD)
    for (nx_, ny_), dd in [((bb.x, bb.y), f.down_tube_d), ((stt.x, stt.y), f.top_tube_d),
                           ((ht.x, ht.y), f.head_tube_d), ((cr.x, cr.y), f.head_tube_d)]:
        ncx, ncy, _ = _circle(nx_, ny_, dd / 2, sx, sy, ox, oy)
        parts.append(f'<circle cx="{ncx:.1f}" cy="{ncy:.1f}" r="{dd/2*abs(sx):.1f}" fill="{FRAME_FILL}"/>')

    # === SUSPENSION ARRIÈRE (amortisseur + biellette + pivots, RÉALISTE) =====
    # Rendu réaliste statique (position topout) SAUF en animation (où le linkage
    # bouge). L'overlay d'analyse `suspension` n'ajoute qu'une trajectoire d'axe
    # PROPRE (pas de bielles debug ni de carrés blancs).
    if full_susp and not animate_suspension:
        parts.append(_draw_susp_links_static(bike, calc, sx, sy, ox, oy, scale_f))

    # === FIXATION MOTEUR (bossages + boulons M8 vers le cadre) ===============
    parts.append(_draw_motor_mount(bike, calc, sx, sy, ox, oy, scale_f))

    # === FOURCHE ============================================================
    # Forme RÉELLE BikeCAD (sprite normalisé) si dispo, sinon silhouette tubulaire.
    hta = math.radians(f.head_angle)
    perp_x, perp_y = math.sin(hta), math.cos(hta)
    cw = 60.0
    blade = fk.blade_width
    stan  = blade * 0.66

    def _crown_block(c):
        parts.append(_draw_tube(c.x - perp_x * cw / 2, c.y - perp_y * cw / 2,
                                c.x + perp_x * cw / 2, c.y + perp_y * cw / 2, 24.0,
                                PALETTE["crown"], sx, sy, ox, oy, scale_f, cap_r=12.0))

    # Fourche SUSPENDUE ssi débattement > 0 ou double couronne. Rendu PARAMÉTRIQUE
    # aux BONNES proportions (plongeur argent COURT en haut ~32 %, fourreaux noirs
    # LONGS en bas ~68 % — comme une vraie fourche), pas le sprite (qui rendait un
    # long plongeur blanc inversé).
    is_susp = (getattr(fk, "travel", 0.0) or 0.0) > 5.0 or getattr(fk, "dual_crown", False)
    if not is_susp:
        # FOURCHE RIGIDE : lame unique (légèrement effilée) de la couronne à l'axe
        parts.append(_draw_tube(cr.x, cr.y, fa.x, fa.y, blade,
                                PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade/2))
        _crown_block(cr)
    else:
        # plongeur (stanchion) argent COURT : du haut vers ~22 % de l'A2C (le reste
        # est couvert par les fourreaux) ; fourreaux (lowers) noirs : 22 %→axe (plus gros).
        top = ht if fk.dual_crown else cr
        mfx = cr.x + (fa.x - cr.x) * 0.22
        mfy = cr.y + (fa.y - cr.y) * 0.22
        parts.append(_draw_tube(top.x, top.y, mfx, mfy, stan,
                                PALETTE["stanchion"], sx, sy, ox, oy, scale_f, cap_r=stan/2))
        # fourreaux + axe : COMPRESSIBLES (remontent avec la roue AV en animation)
        lowers = _draw_tube(mfx, mfy, fa.x, fa.y, blade * 1.12,
                            PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade*0.56)
        parts.append(f'<g class="fork-anim">{fork_anim}{lowers}</g>' if fork_anim else lowers)
        if fk.dual_crown:
            _crown_block(ht)
        _crown_block(cr)

    # === BB shell =============================================================
    bb_svgx, bb_svgy, bb_svgr = _circle(bb.x, bb.y, f.bb_shell_d / 2, sx, sy, ox, oy)
    parts.append(
        f'<circle cx="{bb_svgx:.1f}" cy="{bb_svgy:.1f}" r="{bb_svgr:.1f}" '
        f'fill="{PALETTE["crown"]}" />'
    )

    # Helper monde → SVG (px)
    def W(x, y):
        return (x * sx + ox, y * sy + oy)

    # === TIGE DE SELLE ========================================================
    sta = math.radians(f.seat_angle)
    std_x = -math.cos(sta); std_y = math.sin(sta)
    sp_end_x = stt.x + bike.seatpost.exposed * std_x
    sp_end_y = stt.y + bike.seatpost.exposed * std_y
    parts.append(_draw_tube(stt.x, stt.y, sp_end_x, sp_end_y, bike.seatpost.diameter,
                            PALETTE["seatpost"], sx, sy, ox, oy, scale_f, cap_r=bike.seatpost.diameter/2))

    # === SELLE (CONTOUR RÉEL e-MTB court : nez fin, queue relevée) ============
    # Profil réel (Specialized Power / Fizik Terra). Boîte normalisée : x=0 queue
    # (arrière), x=1 nez (avant, +x monde) ; pince de tige ≈ (0.50, 0.31).
    L_sdl = max(240.0, bike.saddle.length)
    H_box = L_sdl * 0.34
    tilt = -(getattr(bike.saddle, "angle", 0.0) or 0.0)   # nez bas → angle négatif
    setback = max(0.0, bike.seatpost.setback)
    clamp_w = (sp_end_x - setback, sp_end_y + 16.0)       # ancrage = pince sur la tige

    def _sdlpt(nx, ny):                                   # boîte selle → écran
        a = math.radians(tilt); ca = math.cos(a); sn = math.sin(a)
        lx = (nx - 0.50) * L_sdl; ly = (ny - 0.31) * H_box
        return _pt(clamp_w[0] + lx*ca - ly*sn, clamp_w[1] + lx*sn + ly*ca, sx, sy, ox, oy)

    sdl_d = _norm_path(_OUTLINE_SADDLE, clamp_w, L_sdl, H_box, anchor_n=(0.50, 0.31),
                       angle_deg=tilt, sx=sx, sy=sy, ox=ox, oy=oy)
    parts.append(f'<path d="{sdl_d}" fill="{PALETTE["saddle"]}" stroke="#000" '
                 f'stroke-width="0.9" stroke-linejoin="round"/>')
    # liseré clair (matière) sur le dessus
    hi = _norm_path([(0.10, 0.81), (0.32, 0.83), (0.55, 0.75), (0.80, 0.71), (0.95, 0.665)],
                    clamp_w, L_sdl, H_box, anchor_n=(0.50, 0.31), angle_deg=tilt,
                    sx=sx, sy=sy, ox=ox, oy=oy, close=False)
    parts.append(f'<path d="{hi}" stroke="{PALETTE["saddle_hi"]}" stroke-width="1.6" '
                 f'fill="none" opacity="0.55"/>')
    # rails (saillie sous la coque) + pince de tige
    r0 = _sdlpt(0.34, 0.255); r1 = _sdlpt(0.60, 0.245)
    parts.append(f'<line x1="{r0[0]:.1f}" y1="{r0[1]:.1f}" x2="{r1[0]:.1f}" y2="{r1[1]:.1f}" '
                 f'stroke="{PALETTE["rim_dark"]}" stroke-width="2.2"/>')
    clx, cly = W(sp_end_x, sp_end_y)
    parts.append(f'<rect x="{clx-5:.1f}" y="{cly-3:.1f}" width="10" height="11" rx="2" '
                 f'fill="{PALETTE["seatpost"]}"/>')

    # === POTENCE + CINTRE (poste de pilotage) =================================
    # Recherche : en vue de côté le backsweep (8°) projette le grip ~50 mm en
    # ARRIÈRE du collier (pas une longue barre) ; le grip se voit en MOIGNON.
    st = bike.stem
    st_ang = math.radians(f.head_angle)
    ux, uy = -math.cos(st_ang), math.sin(st_ang)        # axe de direction (haut-arrière)
    steerer_exp = max(0.0, getattr(st, "steerer_exposed", 0.0))
    if steerer_exp > 5:
        parts.append(_draw_tube(ht.x, ht.y, ht.x + ux * steerer_exp, ht.y + uy * steerer_exp,
                                28.6, PALETTE["stem"], sx, sy, ox, oy, scale_f, cap_r=14.0))
    # Corps de potence : du steerer (sb) au serrage cintre (stip), tube propre et fin
    parts.append(_draw_tube(sb.x, sb.y, stip.x, stip.y, 26.0,
                            PALETTE["stem"], sx, sy, ox, oy, scale_f, cap_r=13.0))
    # Faceplate (serrage cintre) — petit bloc rond
    coll_d = max(25.0, getattr(st, "collar_diameter", 31.8))
    fcx, fcy = W(stip.x, stip.y)
    parts.append(f'<circle cx="{fcx:.1f}" cy="{fcy:.1f}" r="{coll_d*0.5*scale_f:.1f}" '
                 f'fill="{_shade(PALETTE["stem"],1.25)}" stroke="#111" stroke-width="0.8"/>')

    # === CINTRE riser (vue de côté : montant VERTICAL court + barre ~horizontale) ===
    # En profil un riser plat se voit : un petit montant (le rise) puis le grip qui
    # part vers le PILOTE (arrière), quasi à plat — surtout PAS une barre à 45°.
    rise = max(0.0, bike.handlebar.rise)
    bw = max(22.0, bike.handlebar.diameter - 2.0)
    half_w = max(280.0, getattr(bike.handlebar, "width", 780.0) / 2.0)
    top_x, top_y = stip.x, stip.y + rise                 # haut du montant (rise)
    if rise > 3:                                         # montant vertical court
        parts.append(_draw_tube(stip.x, stip.y, top_x, top_y, bw, PALETTE["handlebar"],
                                sx, sy, ox, oy, scale_f, cap_r=bw/2))
    back = half_w * math.sin(math.radians(8.0))          # recul (backsweep projeté)
    lift = 10.0 + half_w * math.sin(math.radians(5.0)) * 0.35   # léger up (barre ~ à plat)
    bx, by = top_x - back, top_y + lift                  # début du grip
    parts.append(_draw_tube(top_x, top_y, bx, by, bw, PALETTE["handlebar"],
                            sx, sy, ox, oy, scale_f, cap_r=bw/2))
    # grip caoutchouc : moignon vers le pilote (quasi horizontal)
    gw = bw + 7.0
    parts.append(_draw_tube(bx, by, bx - 34.0, by + 4.0, gw, PALETTE["grip"],
                            sx, sy, ox, oy, scale_f, cap_r=gw/2))

    # === ÉTRIERS DE FREIN (par-dessus la fourche/le cadre, donc visibles) ====
    # AR sur le bras (groupe animé) ; AV sur le fourreau (compression de fourche).
    if rear_anim or fork_anim:
        parts.append(_rear_group(_draw_calipers(bike, calc, sx, sy, ox, oy, which="rear")))
        fc = _draw_calipers(bike, calc, sx, sy, ox, oy, which="front")
        parts.append(f'<g class="fork-anim">{fork_anim}{fc}</g>' if fork_anim else fc)
    else:
        parts.append(_draw_calipers(bike, calc, sx, sy, ox, oy))

    # === COTES (dimensions) ==================================================
    if show_dims:
        dim_parts: list[str] = []

        # Reach (BB → haut HT horizontal)
        dim_parts.append(_draw_dim(
            bb.x, ht.y, ht.x, ht.y,
            f"Reach {calc.reach:.0f}mm",
            sx, sy, ox, oy, offset_px=-28
        ))
        # Stack (BB → haut HT vertical)
        dim_parts.append(_draw_dim(
            ht.x, bb.y, ht.x, ht.y,
            f"Stack {calc.stack:.0f}mm",
            sx, sy, ox, oy, offset_px=32, vertical=True
        ))
        # Wheelbase
        dim_parts.append(_draw_dim(
            ra.x, gl - 15, fa.x, gl - 15,
            f"WB {calc.wheelbase:.0f}mm",
            sx, sy, ox, oy, offset_px=22
        ))
        # BB height
        dim_parts.append(_draw_dim(
            bb.x, gl, bb.x, bb.y,
            f"BB ↑{calc.bb_height:.0f}mm",
            sx, sy, ox, oy, offset_px=-30, vertical=True
        ))

        # Encadré inférieur : Trail, Chainstay
        info_y = height - 30
        info_items = [
            f"Trail {calc.trail:.0f}mm",
            f"Trail@sag {calc.trail_sag:.0f}mm",
            f"CS {f.cs:.0f}mm",
            f"FCD {f.fcd:.0f}mm",
            f"TT {calc.tt_effective:.0f}mm",
        ]
        x_start = 20
        for item in info_items:
            dim_parts.append(
                f'<text x="{x_start}" y="{info_y}" '
                f'font-size="11" font-family="monospace" fill="{PALETTE["dim_text"]}">'
                f'{item}</text>'
            )
            x_start += 170

        parts.extend(dim_parts)

    # === TRANSMISSION (plateau, courroie, moteur, manivelle) =================
    parts.append(_draw_drivetrain(bike, calc, sx, sy, ox, oy, scale_f))

    # === DÉRAILLEUR ARRIÈRE (forme réelle BikeCAD, sous l'axe AR) =============
    # Uniquement en transmission par dérailleur (IGH/courroie = pas de dérailleur).
    if bike.drivetrain.transmission == "derailleur" and bike.drivetrain.drive_type != "belt":
        parts.append(_draw_sprite("derailleur", ra.x, ra.y, sx, sy, ox, oy,
                                  scale=1.0, klass="derailleur"))

    # === LUGS (jonctions CNC lug-and-bond) ===================================
    if lugs:
        parts.append(_draw_lugs(lugs, sx, sy, ox, oy, scale_f))

    # === BATTERIE (pack dans le triangle avant) ==============================
    if bike.battery.enabled:
        parts.append(_draw_battery(bike, calc, sx, sy, ox, oy))

    # === SUSPENSION (overlay) : animation OU analyse propre (trajectoire d'axe) =
    if suspension:
        frames = suspension if isinstance(suspension, list) else getattr(suspension, "frames", None)
        if frames:
            if animate_suspension:
                parts.append(_draw_suspension(frames, wheel_r_r, sx, sy, ox, oy, scale_f,
                                              animate=True))
            else:
                parts.append(_draw_susp_analysis(frames, sx, sy, ox, oy))

    # === PIVOTS (roulements + axes, coupe) ===================================
    if pivots:
        parts.append(_draw_pivots(pivots, sx, sy, ox, oy))

    # === VISSERIE (chaque point de vis/boulon + type) ========================
    if fasteners:
        parts.append(_draw_fasteners(fasteners, sx, sy, ox, oy))

    # === PATTE RÉGLABLE (tension courroie) ===================================
    if bike.drivetrain.drive_type == "belt" and bike.suspension.dropout_adjust_mm > 0:
        parts.append(_draw_dropout(
            (calc.rear_axle.x, calc.rear_axle.y), (0.0, 0.0),
            bike.suspension.dropout_adjust_mm, bike.suspension.belt_tension_method,
            sx, sy, ox, oy))

    # === PILOTE (squelette de fit) ===========================================
    if fit is not None and getattr(fit, "ok", False):
        parts.append(_draw_rider(fit, sx, sy, ox, oy))

    # === TITRE ================================================================
    parts.append(
        f'<text x="16" y="24" font-size="14" font-family="sans-serif" '
        f'font-weight="bold" fill="#2d3436">{bike.name}</text>'
    )

    svg_body = "\n".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'{svg_body}\n'
        f'</svg>'
    )
