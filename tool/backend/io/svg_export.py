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
    "tire":       "#191a1d",   # pneu
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
    "bg":         "#ffffff",   # fond blanc (comme BikeCAD)
    "belt":       "#f0a51f",   # courroie / chaîne
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

def _draw_wheel(cx: float, cy: float, r_tire: float, r_rim: float,
                n_spokes: int, sx: float, sy: float, ox: float, oy: float,
                cassette=False) -> str:
    scx, scy, sr_tire = _circle(cx, cy, r_tire, sx, sy, ox, oy)
    _, _, sr_rim = _circle(cx, cy, r_rim, sx, sy, ox, oy)
    _, _, sr_hub = _circle(cx, cy, 26.0, sx, sy, ox, oy)
    _, _, sr_fl  = _circle(cx, cy, 30.0, sx, sy, ox, oy)   # rayon flasque
    tire_w = max(4.0, sr_tire - sr_rim)
    rim_w  = max(2.2, tire_w * 0.34)
    r_bed  = sr_rim - rim_w               # lit de jante (intérieur)

    L = [f'<g class="wheel">']
    # Pneu : bande sombre + sculpture (petits crampons) + flancs
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire:.1f}" fill="{PALETTE["tire"]}"/>')
    n_tread = 72
    for i in range(n_tread):
        a = 2 * math.pi * i / n_tread
        r0, r1 = sr_tire - tire_w * 0.18, sr_tire - tire_w * 0.02
        x0, y0 = scx + r0 * math.cos(a), scy + r0 * math.sin(a)
        x1t, y1t = scx + r1 * math.cos(a), scy + r1 * math.sin(a)
        L.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1t:.1f}" y2="{y1t:.1f}" '
                 f'stroke="{PALETTE["tread"]}" stroke-width="1.4"/>')
    # Ouverture (fond) jusqu'au lit de jante
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r_bed:.1f}" fill="{PALETTE["bg"]}"/>')
    # Rayons (depuis les flasques du moyeu vers le lit de jante), 2 nappes croisées
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes
        hubr = sr_fl
        hx, hy = scx + hubr * math.cos(a + 0.12), scy + hubr * math.sin(a + 0.12)
        rx, ry = scx + r_bed * 0.99 * math.cos(a), scy + r_bed * 0.99 * math.sin(a)
        L.append(f'<line x1="{hx:.1f}" y1="{hy:.1f}" x2="{rx:.1f}" y2="{ry:.1f}" '
                 f'stroke="{PALETTE["spoke"]}" stroke-width="0.8"/>')
    # Jante argent (anneau) + double liseré
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim-rim_w/2:.1f}" fill="none" '
             f'stroke="{PALETTE["rim"]}" stroke-width="{rim_w:.1f}"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim-rim_w*0.1:.1f}" fill="none" '
             f'stroke="{PALETTE["rim_dark"]}" stroke-width="0.8"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{r_bed:.1f}" fill="none" '
             f'stroke="{PALETTE["rim_dark"]}" stroke-width="0.8"/>')
    # Cassette (roue AR) : disques concentriques argentés
    if cassette:
        for k, rr in enumerate((46, 38, 31)):
            _, _, scr = _circle(cx, cy, rr, sx, sy, ox, oy)
            L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{scr:.1f}" fill="none" '
                     f'stroke="{PALETTE["cog_dark"]}" stroke-width="1.4"/>')
    # Moyeu : flasque + corps + axe
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_fl:.1f}" fill="{PALETTE["hub"]}" '
             f'stroke="#222" stroke-width="0.8"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub*0.5:.1f}" fill="#2a2d33"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub*0.18:.1f}" fill="#101114"/>')
    L.append('</g>')
    return "\n".join(L)


_TUBE_ID = [0]   # compteur d'identifiants de dégradés (réinitialisé par render_svg)


def _draw_tube(x1, y1, x2, y2, d, color, sx, sy, ox, oy, scale, cap_r=0.0,
               edge=None, fill=None) -> str:
    """Tube peint. Si `fill` est fourni (ex. dégradé GLOBAL du cadre façon BikeCAD),
    on l'utilise tel quel ; sinon ombrage cylindrique par tube."""
    pts = _tube_polygon(x1, y1, x2, y2, d, sx, sy, ox, oy, scale)
    if not pts:
        return ""
    if fill is not None:
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
    th = max(1.2, r * 0.085)                 # hauteur de dent
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
                       f'stroke="{_shade(fill,0.72)}" stroke-width="{max(2,r*0.13):.1f}" stroke-linecap="round"/>')
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
        fx, fy = lx, -ly                      # Java2D y-bas → y-haut
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

    # Moteur central : enveloppe réelle du carter si disponible (ex. M620),
    # sinon rectangle générique. NB : l'enveloppe est en coords MONDE relatives
    # au BB ; on translate par bb avant projection écran.
    if dt.use_motor:
        motor_svg = _draw_motor_bikecad(dt, calc, sx, sy, ox, oy)
        env = None if motor_svg else motor_envelope_world(dt)
        if motor_svg:
            parts.append(motor_svg)
        elif env is not None:
            pts = " ".join(
                f"{x:.1f},{y:.1f}" for x, y in
                (_pt(bb[0] + ex, bb[1] + ey, sx, sy, ox, oy) for ex, ey in env)
            )
            parts.append(
                f'<polygon class="motor" points="{pts}" '
                f'fill="{PALETTE["motor"]}" opacity="0.85" '
                f'stroke="#1a2530" stroke-width="1.5" />'
            )
        else:
            mw, mh = 130.0, 150.0   # encombrement approximatif d'un mid-drive
            mx, my = bb[0] + dt.motor_x, bb[1] + dt.motor_y
            x0, y0 = _pt(mx - mw / 2, my + mh / 2, sx, sy, ox, oy)
            parts.append(
                f'<rect class="motor" x="{x0:.1f}" y="{y0:.1f}" width="{mw*scale:.1f}" '
                f'height="{mh*scale:.1f}" rx="{18*scale:.1f}" '
                f'fill="{PALETTE["motor"]}" opacity="0.85" />'
            )

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
    wb, wp = 24.0, 13.0                       # largeur au BB / à la pédale
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

    segs = []
    if su.use_idler and dt.drive_type == "belt":
        idler = (su.idler.x, su.idler.y); r_id = su.idler_dia / 2
        segs += tangents(bb, r_cr, idler, r_id)
        segs += tangents(idler, r_id, axle, r_cog)
        icx, icy, isr = _circle(idler[0], idler[1], r_id, sx, sy, ox, oy)
        parts.append(f'<circle cx="{icx:.1f}" cy="{icy:.1f}" r="{isr:.1f}" '
                     f'fill="{PALETTE["cog"]}" opacity="0.7" />')
    else:
        segs += tangents(bb, r_cr, axle, r_cog)

    for a, b in segs:
        ax, ay = _pt(*a, sx, sy, ox, oy); bx2, by2 = _pt(*b, sx, sy, ox, oy)
        parts.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" '
                     f'stroke="{PALETTE["belt"]}" stroke-width="{max(1.5, 4*scale):.1f}" '
                     f'opacity="0.9" />')

    return '<g class="drivetrain">' + "".join(parts) + '</g>'


def _draw_battery(bike, calc, sx, sy, ox, oy) -> str:
    """Pack batterie dans le triangle avant (vert si OK, rouge si débordement)."""
    from ..calculations.battery import battery_polygon_world, compute_battery
    poly = battery_polygon_world(bike, calc)
    if poly is None:
        return ""
    res = compute_battery(bike, calc)
    ok = res.fits_triangle and res.clears_motor and res.clears_tubes
    fill = "#27ae60" if ok else "#c0392b"
    pts = " ".join(f"{x*sx+ox:.1f},{y*sy+oy:.1f}" for (x, y) in poly)
    parts = [f'<g class="battery"><polygon points="{pts}" fill="{fill}" '
             f'fill-opacity="0.45" stroke="{fill}" stroke-width="2" stroke-linejoin="round"/>']
    # Étiquette au centroïde
    cx = sum(p[0] for p in poly) / 4 * sx + ox
    cy = sum(p[1] for p in poly) / 4 * sy + oy
    label = f"{bike.battery.voltage:.0f}V · {bike.battery.capacity_wh:.0f}Wh"
    parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
                 f'dominant-baseline="middle" font-size="13" font-family="sans-serif" '
                 f'font-weight="bold" fill="#fff">{label}</text>')
    parts.append("</g>")
    return "".join(parts)


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
        parts.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr:.1f}" '
                     f'fill="none" stroke="{PALETTE["rotor"]}" stroke-width="1.6" opacity="0.85" />')
        # quelques perçages pour le style
        for i in range(8):
            a = 2 * math.pi * i / 8
            hx, hy = _pt(axle.x + rotor / 2 * 0.8 * math.cos(a),
                         axle.y + rotor / 2 * 0.8 * math.sin(a), sx, sy, ox, oy)
            parts.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="1.6" fill="{PALETTE["rotor"]}" opacity="0.6" />')
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

    # ── Amortisseur : corps + tige + œillets (se comprime) ───────────────────
    up0, lo0 = ref["shock"][1], ref["shock"][0]
    body_len = 0.5 * math.hypot(frames[0]["shock"][0][0] - frames[0]["shock"][1][0],
                                frames[0]["shock"][0][1] - frames[0]["shock"][1][1])

    def body_end(fr):
        up, lo = fr["shock"][1], fr["shock"][0]
        d = math.hypot(lo[0] - up[0], lo[1] - up[1]) or 1.0
        u = ((lo[0] - up[0]) / d, (lo[1] - up[1]) / d)
        return (up[0] + u[0] * body_len, up[1] + u[1] * body_len)
    # tige (fine) : corps→œillet bas ; corps (épais) : œillet haut→corps
    aline(lambda fr: (body_end(fr), fr["shock"][0]), "#cfd6df", 4)      # tige argent
    aline(lambda fr: (fr["shock"][1], body_end(fr)), "#16a085", 11)     # corps amorto
    adot(lambda fr: fr["shock"][0], 5, "#0e6b57")                       # œillet bas (mobile)

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
               suspension=None, animate_suspension=False, lugs=None) -> str:
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

    # ── Bounding box en coords monde ────────────────────────────────────────
    world_min_x = ra.x - wheel_r_r - 40
    world_max_x = fa.x + wheel_r_f + 40
    world_min_y = gl - 20
    world_max_y = max(hbc.y, sdl_mid.y) + 80
    # Étendre la bbox pour inclure le pilote (tête haute)
    if fit is not None and getattr(fit, "ok", False) and fit.head is not None:
        world_max_y = max(world_max_y, fit.head.y + 60)

    world_w = world_max_x - world_min_x
    world_h = world_max_y - world_min_y

    margin = 60
    avail_w = width  - 2 * margin
    avail_h = height - 2 * margin
    scale_f = min(avail_w / world_w, avail_h / world_h)

    # Transformée : SVG_x = x*scale_f + ox, SVG_y = y*(-scale_f) + oy
    sx =  scale_f
    sy = -scale_f   # Y inversé (SVG Y pointe vers le bas)
    ox = margin - world_min_x * sx
    oy = margin - world_max_y * sy   # assure que world_max_y → margin en SVG

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
    # Un SEUL dégradé pour TOUS les tubes : peinture (haut, lumière) → gris foncé
    # (bas, ombre), orienté haut→bas sur la bbox du cadre. Donne l'aspect « objet
    # peint unique » de BikeCAD (vs un dégradé par tube).
    fr_xs = [bb.x, ra.x, stt.x, ht.x, cr.x]
    fr_ys = [bb.y, stt.y, ht.y, cr.y]
    gx1, gy1 = _pt((min(fr_xs)+max(fr_xs))/2, max(fr_ys), sx, sy, ox, oy)  # haut
    gx2, gy2 = _pt((min(fr_xs)+max(fr_xs))/2, min(bb.y, ra.y), sx, sy, ox, oy)  # bas
    paint = PALETTE["frame"]
    parts.append(
        f'<linearGradient id="frameGrad" gradientUnits="userSpaceOnUse" '
        f'x1="{gx1:.1f}" y1="{gy1:.1f}" x2="{gx2:.1f}" y2="{gy2:.1f}">'
        f'<stop offset="0%" stop-color="{_shade(paint,1.25)}"/>'
        f'<stop offset="45%" stop-color="{paint}"/>'
        f'<stop offset="100%" stop-color="#333333"/></linearGradient>'
    )
    FRAME_FILL = "url(#frameGrad)"

    # === SOL =================================================================
    parts.append(
        f'<rect x="0" y="{ground_y:.1f}" width="{width}" height="{height - ground_y:.1f}" '
        f'fill="{PALETTE["ground"]}" opacity="0.35" />'
    )
    parts.append(
        f'<line x1="0" y1="{ground_y:.1f}" x2="{width}" y2="{ground_y:.1f}" '
        f'stroke="#b2bec3" stroke-width="1.5" />'
    )
    # Ombres elliptiques sous les roues
    for (wsx, sr) in [(rear_sx, sr_r), (front_sx, sr_f)]:
        parts.append(
            f'<ellipse cx="{wsx:.0f}" cy="{ground_y + 4:.0f}" '
            f'rx="{sr * 0.6:.0f}" ry="6" fill="#2d3436" opacity="0.12" />'
        )

    # === ROUES ===============================================================
    # Dessinées en premier (derrière le cadre)
    parts.append(_draw_wheel(ra.x, ra.y, wheel_r_r, rim_r_r, n_sp_r, sx, sy, ox, oy, cassette=True))
    parts.append(_draw_wheel(fa.x, fa.y, wheel_r_f, rim_r_f, n_sp_f, sx, sy, ox, oy))

    # === FREINS (disques) ====================================================
    parts.append(_draw_brakes(bike, calc, sx, sy, ox, oy))

    # === BASES (chainstays) ==================================================
    parts.append(_draw_tube(bb.x, bb.y, ra.x, ra.y, f.chainstay_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.chainstay_d/2, fill=FRAME_FILL))

    # === HAUBANS (seatstays) =================================================
    # Relient axe AR au jonction TT/ST
    parts.append(_draw_tube(ra.x, ra.y, stt.x, stt.y, f.seatstay_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.seatstay_d/2, fill=FRAME_FILL))

    # === TUBE DE SELLE ========================================================
    parts.append(_draw_tube(bb.x, bb.y, stt.x, stt.y, f.seat_tube_fd,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.seat_tube_fd/2, fill=FRAME_FILL))

    # === TUBE HORIZONTAL (top tube) ==========================================
    parts.append(_draw_tube(stt.x, stt.y, ht.x, ht.y, f.top_tube_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.top_tube_d/2, fill=FRAME_FILL))

    # === TUBE DIAGONAL (down tube) ===========================================
    parts.append(_draw_tube(bb.x, bb.y, cr.x, cr.y, f.down_tube_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.down_tube_d/2, fill=FRAME_FILL))

    # === TUBE DE DIRECTION ===================================================
    parts.append(_draw_tube(cr.x, cr.y, ht.x, ht.y, f.head_tube_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.head_tube_d/2, fill=FRAME_FILL))

    # === FOURCHE (silhouette UNIQUE, vue de profil — comme BikeCAD) ==========
    hta = math.radians(f.head_angle)
    # direction transversale à l'axe de direction (pour dessiner les couronnes)
    perp_x, perp_y = math.sin(hta), math.cos(hta)
    cw = 60.0                       # largeur de couronne (vue de profil)
    blade = fk.blade_width
    stan  = blade * 0.66            # plongeur plus fin que le fourreau

    def _crown_block(c):
        parts.append(_draw_tube(c.x - perp_x * cw / 2, c.y - perp_y * cw / 2,
                                c.x + perp_x * cw / 2, c.y + perp_y * cw / 2, 24.0,
                                PALETTE["crown"], sx, sy, ox, oy, scale_f, cap_r=12.0))

    if fk.dual_crown:
        # plongeurs (argent) entre couronne haute (ht) et basse (cr)
        parts.append(_draw_tube(ht.x, ht.y, cr.x, cr.y, stan,
                                PALETTE["stanchion"], sx, sy, ox, oy, scale_f))
        # fourreau (noir) de la couronne basse à l'axe
        parts.append(_draw_tube(cr.x, cr.y, fa.x, fa.y, blade,
                                PALETTE["fork_low"], sx, sy, ox, oy, scale_f, cap_r=blade/2))
        _crown_block(ht); _crown_block(cr)
    else:
        # simple couronne : plongeur (haut, argent) + fourreau (bas, noir),
        # split à ~42 % de la longueur couronne→axe.
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

    # === SELLE (silhouette posée sur la tige) ================================
    L_sdl = max(240.0, bike.saddle.length)
    thk = max(28.0, bike.saddle.thickness)
    cx_s = sp_end_x - L_sdl * 0.12          # centre un peu en arrière de la tige
    top = sp_end_y + thk * 0.35             # coque juste au-dessus de la tige
    tail = W(cx_s - L_sdl * 0.46, top)
    tail_dn = W(cx_s - L_sdl * 0.46, top - thk * 0.7)
    nose = W(cx_s + L_sdl * 0.55, top - thk * 0.15)
    midtop = W(cx_s + L_sdl * 0.05, top + thk * 0.25)
    midbot = W(cx_s + L_sdl * 0.05, top - thk * 0.55)
    parts.append(
        f'<path d="M {tail[0]:.0f},{tail[1]:.0f} '
        f'Q {midtop[0]:.0f},{midtop[1]:.0f} {nose[0]:.0f},{nose[1]:.0f} '
        f'Q {midbot[0]:.0f},{midbot[1]:.0f} {tail_dn[0]:.0f},{tail_dn[1]:.0f} Z" '
        f'fill="{PALETTE["saddle"]}" stroke="#000" stroke-width="0.8"/>'
    )
    # reflet sur la coque
    parts.append(
        f'<path d="M {W(cx_s-L_sdl*0.4, top)[0]:.0f},{W(cx_s-L_sdl*0.4, top)[1]:.0f} '
        f'Q {W(cx_s,top+thk*0.18)[0]:.0f},{W(cx_s,top+thk*0.18)[1]:.0f} '
        f'{W(cx_s+L_sdl*0.5,top-thk*0.12)[0]:.0f},{W(cx_s+L_sdl*0.5,top-thk*0.12)[1]:.0f}" '
        f'stroke="{PALETTE["saddle_hi"]}" stroke-width="2" fill="none" opacity="0.7"/>'
    )

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
    parts.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{bw*0.62*scale_f:.1f}" '
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
