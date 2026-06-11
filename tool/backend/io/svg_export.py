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
    # Pneu : anneau noir UNI (pas de sculpture) + liseré BikeCAD
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire:.1f}" fill="{PALETTE["tire"]}" '
             f'stroke="#333333" stroke-width="1.0"/>')
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
    mw, mh = 130.0, 150.0
    mx, my = bb[0] + dt.motor_x, bb[1] + dt.motor_y
    x0, y0 = _pt(mx - mw / 2, my + mh / 2, sx, sy, ox, oy)
    return (f'<rect class="motor" x="{x0:.1f}" y="{y0:.1f}" width="{mw*scale:.1f}" '
            f'height="{mh*scale:.1f}" rx="{18*scale:.1f}" fill="{PALETTE["motor"]}"/>')


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
        # Corps central du lug (boule usinée)
        cxp, cyp = _pt(nx, ny, sx, sy, ox, oy)
        r_hub = (max(bores) / 2 + 7.0) * abs(sx)
        parts.append(f'<circle cx="{cxp:.1f}" cy="{cyp:.1f}" r="{r_hub:.1f}" '
                     f'fill="{metal}" stroke="{PALETTE["lug_edge"]}" stroke-width="0.8"/>')
        # reflet
        parts.append(f'<circle cx="{cxp-r_hub*0.3:.1f}" cy="{cyp-r_hub*0.3:.1f}" '
                     f'r="{r_hub*0.32:.1f}" fill="#e8ebef" opacity="0.5"/>')
    parts.append('</g>')
    return "".join(parts)


def _draw_brakes(bike, calc, sx, sy, ox, oy) -> str:
    """Disques de frein aux deux axes (si freins à disque)."""
    bk = bike.brakes
    if not str(bk.style).startswith("disc"):
        return ""
    parts = []
    for axle, rotor in ((calc.front_axle, bk.rotor_front), (calc.rear_axle, bk.rotor_rear)):
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


def render_svg(bike: BikeDesign, calc: CalcResult,
               width: int = 1400, height: int = 750,
               show_dims: bool = True, fit=None,
               suspension=None, animate_suspension=False, lugs=None,
               show_ground: bool = False, pivots=None) -> str:
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
    paint = PALETTE["frame"]
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

    # === ROUES ===============================================================
    # Dessinées en premier (derrière le cadre). Cassette seulement si dérailleur.
    is_igh = bike.drivetrain.transmission == "igh"
    parts.append(_draw_wheel(ra.x, ra.y, wheel_r_r, sx, sy, ox, oy,
                             cassette=not is_igh, wcfg=bike.wheel_r))
    parts.append(_draw_wheel(fa.x, fa.y, wheel_r_f, sx, sy, ox, oy, wcfg=bike.wheel_f))

    # === MOYEU À VITESSES (IGH : Rohloff / 3X3) — gros corps de moyeu ==========
    if is_igh:
        hcx, hcy, hr = _circle(ra.x, ra.y, 56.0, sx, sy, ox, oy)
        parts.append(f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr:.1f}" fill="{PALETTE["hub"]}" '
                     f'stroke="#222" stroke-width="1.2"/>')
        _, _, hr2 = _circle(ra.x, ra.y, 44.0, sx, sy, ox, oy)
        parts.append(f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr2:.1f}" fill="none" '
                     f'stroke="{_shade(PALETTE["hub"],0.8)}" stroke-width="1.5"/>')
        _, _, hr3 = _circle(ra.x, ra.y, 30.0, sx, sy, ox, oy)
        parts.append(f'<circle cx="{hcx:.1f}" cy="{hcy:.1f}" r="{hr3:.1f}" fill="{_shade(PALETTE["hub"],1.15)}" '
                     f'stroke="#333" stroke-width="0.8"/>')

    # === FREINS (disques) ====================================================
    parts.append(_draw_brakes(bike, calc, sx, sy, ox, oy))

    # === MOTEUR (DERRIÈRE le cadre : les tubes se rejoignent par-dessus au BB) =
    parts.append(_draw_motor(bike, calc, sx, sy, ox, oy, scale_f))

    # === CADRE (technique BikeCAD : remplissages groupés → fillets aux nœuds →
    #     liseré #333 en dernière passe → silhouette « objet peint » sans coutures)
    # bases, haubans, tube de selle, top tube, down tube, tube de direction
    frame_tubes = [
        (bb.x, bb.y, ra.x, ra.y, f.chainstay_d),
        (ra.x, ra.y, stt.x, stt.y, f.seatstay_d),
        (bb.x, bb.y, stt.x, stt.y, f.seat_tube_fd),
        (stt.x, stt.y, ht.x, ht.y, f.top_tube_d),
        (bb.x, bb.y, cr.x, cr.y, f.down_tube_d),
        (cr.x, cr.y, ht.x, ht.y, f.head_tube_d),
    ]
    # Pass 1 : remplissages (dégradé global, pas de stroke) + caps ronds
    for (ax_, ay_, bx_, by_, dia_) in frame_tubes:
        parts.append(_draw_tube(ax_, ay_, bx_, by_, dia_, PALETTE["frame"],
                                sx, sy, ox, oy, scale_f, cap_r=dia_ / 2, fill=FRAME_FILL))
    # Pass 2 : liseré #333 (uniquement les grands côtés)
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

    # Fourche SUSPENDUE ssi débattement > 0 (signal fiable du .bcad) ou double
    # couronne (sinon un BMX, travel=0, héritait d'une fourche télescopique).
    is_susp = (getattr(fk, "travel", 0.0) or 0.0) > 5.0 or getattr(fk, "dual_crown", False)
    fork_part = _PARTS.get("fork_norm")
    if not is_susp:
        # FOURCHE RIGIDE : lame unique (légèrement effilée) de la couronne à l'axe
        parts.append(_draw_tube(cr.x, cr.y, fa.x, fa.y, blade,
                                PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade/2))
        _crown_block(cr)
    elif fork_part and fork_part.get("paths"):
        # SUSPENDUE : forme réelle BikeCAD (sprite normalisé)
        dir_ang = math.degrees(math.atan2(cr.y - fa.y, cr.x - fa.x))
        a2c = math.hypot(cr.x - fa.x, cr.y - fa.y)
        axis_len = fork_part.get("axis_len", 683.0) or 683.0
        fscale = (a2c / (axis_len * 0.74)) if axis_len else 1.0
        parts.append(_draw_sprite("fork_norm", fa.x, fa.y, sx, sy, ox, oy,
                                  scale=fscale, angle_deg=dir_ang - 90.0,
                                  empty_fill=PALETTE["stanchion"], klass="fork"))
    elif fk.dual_crown:
        parts.append(_draw_tube(ht.x, ht.y, cr.x, cr.y, stan,
                                PALETTE["stanchion"], sx, sy, ox, oy, scale_f))
        parts.append(_draw_tube(cr.x, cr.y, fa.x, fa.y, blade,
                                PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade/2))
        _crown_block(ht); _crown_block(cr)
    else:
        mfx = cr.x + (fa.x - cr.x) * 0.42
        mfy = cr.y + (fa.y - cr.y) * 0.42
        parts.append(_draw_tube(cr.x, cr.y, mfx, mfy, stan,
                                PALETTE["stanchion"], sx, sy, ox, oy, scale_f))
        parts.append(_draw_tube(mfx, mfy, fa.x, fa.y, blade,
                                PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade/2))
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

    # === SELLE (profil VTT moderne : coque fine, bec effilé, arrière relevé) ==
    # Nez vers l'avant (+x = droite). Construit en coords monde (y-haut) puis projeté.
    L_sdl = max(250.0, bike.saddle.length)
    H_sdl = max(16.0, min(30.0, bike.saddle.thickness))   # épaisseur de coque
    clampH = 24.0
    # setback = recul de la selle derrière l'axe de tige (réglage tige de selle)
    cxs = sp_end_x + 0.04 * L_sdl - max(0.0, bike.seatpost.setback)
    ty  = sp_end_y + clampH                # ligne d'assise (haut de coque)
    def Wp(x, y):                          # raccourci monde→px
        return f"{W(x, y)[0]:.1f},{W(x, y)[1]:.1f}"
    # Profil supérieur : arrière relevé → creux d'assise → bec relevé
    tailT = (cxs - 0.46 * L_sdl, ty + 0.060 * L_sdl)
    sit   = (cxs - 0.06 * L_sdl, ty)
    noseT = (cxs + 0.56 * L_sdl, ty + 0.045 * L_sdl)
    # Dessous (concave, fin)
    noseB = (cxs + 0.55 * L_sdl, ty + 0.045 * L_sdl - H_sdl * 0.55)
    sitB  = (cxs - 0.04 * L_sdl, ty - H_sdl)
    tailB = (cxs - 0.44 * L_sdl, ty + 0.060 * L_sdl - H_sdl * 0.65)
    shell = (
        f'M {Wp(*tailT)} '
        f'C {Wp(cxs-0.30*L_sdl, ty+0.05*L_sdl)} {Wp(cxs-0.20*L_sdl, ty+0.004*L_sdl)} {Wp(*sit)} '
        f'C {Wp(cxs+0.18*L_sdl, ty-0.004*L_sdl)} {Wp(cxs+0.42*L_sdl, ty+0.055*L_sdl)} {Wp(*noseT)} '
        f'L {Wp(*noseB)} '
        f'C {Wp(cxs+0.20*L_sdl, ty-H_sdl*0.7)} {Wp(cxs+0.05*L_sdl, ty-H_sdl)} {Wp(*sitB)} '
        f'C {Wp(cxs-0.22*L_sdl, ty-H_sdl*0.9)} {Wp(cxs-0.40*L_sdl, ty-0.0*L_sdl)} {Wp(*tailB)} Z'
    )
    parts.append(f'<path d="{shell}" fill="{PALETTE["saddle"]}" stroke="#000" stroke-width="0.8" stroke-linejoin="round"/>')
    # liseré clair sur le dessus (matière/coutures)
    parts.append(
        f'<path d="M {Wp(cxs-0.40*L_sdl, ty+0.045*L_sdl)} '
        f'C {Wp(cxs-0.20*L_sdl, ty+0.01*L_sdl)} {Wp(cxs+0.20*L_sdl, ty+0.005*L_sdl)} {Wp(cxs+0.50*L_sdl, ty+0.04*L_sdl)}" '
        f'stroke="{PALETTE["saddle_hi"]}" stroke-width="1.6" fill="none" opacity="0.65"/>'
    )
    # rails + pince de tige
    rail_y = ty - H_sdl - 4.0
    parts.append(f'<line x1="{Wp(cxs-0.30*L_sdl, rail_y).split(",")[0]}" y1="{Wp(cxs-0.30*L_sdl, rail_y).split(",")[1]}" '
                 f'x2="{Wp(cxs+0.34*L_sdl, rail_y).split(",")[0]}" y2="{Wp(cxs+0.34*L_sdl, rail_y).split(",")[1]}" '
                 f'stroke="{PALETTE["rim_dark"]}" stroke-width="1.6"/>')
    clx, cly = W(sp_end_x, sp_end_y)
    parts.append(f'<rect x="{clx-5:.1f}" y="{cly-2:.1f}" width="10" height="9" rx="2" '
                 f'fill="{PALETTE["seatpost"]}" />')

    # === POTENCE (corps + collier + faceplate) ===============================
    parts.append(_draw_tube(sb.x, sb.y, stip.x, stip.y, 26.0,
                            PALETTE["stem"], sx, sy, ox, oy, scale_f, cap_r=13.0))
    cmx, cmy = W(sb.x, sb.y)
    parts.append(f'<circle cx="{cmx:.1f}" cy="{cmy:.1f}" r="{18*scale_f:.1f}" '
                 f'fill="{PALETTE["stem"]}" stroke="#111" stroke-width="1"/>')

    # === CINTRE (riser MTB : montant + grip vers le pilote) ==================
    rise = max(15.0, bike.handlebar.rise)
    bar_cx, bar_cy = stip.x, stip.y + rise
    grip_len = 95.0 + bike.handlebar.extend
    grip_x = bar_cx - grip_len                 # vers l'arrière (pilote)
    grip_y = bar_cy + 14.0                      # léger sweep/rise
    bw = max(26.0, bike.handlebar.diameter + 4)
    # montant (du collier de potence vers la barre)
    parts.append(_draw_tube(stip.x, stip.y, bar_cx, bar_cy, bw * 0.85,
                            PALETTE["handlebar"], sx, sy, ox, oy, scale_f, cap_r=bw*0.42))
    # grip vers le pilote
    parts.append(_draw_tube(bar_cx, bar_cy, grip_x, grip_y, bw,
                            PALETTE["handlebar"], sx, sy, ox, oy, scale_f, cap_r=bw/2))
    gx, gy = W(grip_x, grip_y)
    parts.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{bw*0.42*scale_f:.1f}" '
                 f'fill="{PALETTE["grip"]}" stroke="#000" stroke-width="0.8"/>')

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

    # === SUSPENSION (overlay pivots/bielles/amorto, animée ou non) ===========
    if suspension:
        frames = suspension if isinstance(suspension, list) else getattr(suspension, "frames", None)
        if frames:
            parts.append(_draw_suspension(frames, wheel_r_r, sx, sy, ox, oy, scale_f,
                                          animate=animate_suspension))

    # === PIVOTS (roulements + axes, coupe) ===================================
    if pivots:
        parts.append(_draw_pivots(pivots, sx, sy, ox, oy))

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
