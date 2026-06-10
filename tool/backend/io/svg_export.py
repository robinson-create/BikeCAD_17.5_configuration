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
# Look « catalogue moderne » : cadre ardoise foncé avec liseré, fourche métal,
# fond clair neutre. Contours sur chaque pièce pour la lisibilité.
PALETTE = {
    "frame":      "#2b3442",   # tubes cadre
    "frame_edge": "#161c25",   # liseré tubes
    "fork":       "#6b7686",   # fourche (métal)
    "fork_edge":  "#3f4754",
    "crown":      "#3a4452",   # couronnes + BB
    "wheel_rim":  "#3a4049",   # jante
    "rim_hi":     "#5b6470",   # reflet jante
    "tire":       "#1b1e22",   # pneu
    "spoke":      "#aeb6c0",   # rayons (clairs = visibles)
    "hub":        "#4a525d",
    "seatpost":   "#3a4452",
    "saddle":     "#15181d",   # selle (noir)
    "saddle_hi":  "#2c323b",
    "stem":       "#2f3845",
    "handlebar":  "#22272e",
    "grip":       "#1b1e22",
    "ground":     "#d6dde6",   # sol
    "dim_line":   "#2f6df0",   # cotes
    "dim_text":   "#2f6df0",
    "dim_bg":     "white",
    "bg":         "#eef1f6",   # fond
    "belt":       "#f0a51f",   # courroie / chaîne
    "belt_edge":  "#b87a10",
    "cog":        "#3a4452",   # plateau / pignon
    "motor":      "#3d4757",   # carter moteur
    "motor_edge": "#262d38",
    "crank":      "#262d38",   # manivelle
    "rotor":      "#9fc2e8",   # disque de frein
}

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
                n_spokes: int, sx: float, sy: float, ox: float, oy: float) -> str:
    scx, scy, sr_tire = _circle(cx, cy, r_tire, sx, sy, ox, oy)
    _, _, sr_rim = _circle(cx, cy, r_rim, sx, sy, ox, oy)
    _, _, sr_hub = _circle(cx, cy, 22.0, sx, sy, ox, oy)
    tire_w = max(3.0, sr_tire - sr_rim)          # épaisseur pneu
    rim_w  = max(2.5, tire_w * 0.45)             # épaisseur jante

    L = [f'<g class="wheel">']
    # Pneu (anneau sombre) + flanc subtil
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire:.1f}" fill="{PALETTE["tire"]}"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_tire-tire_w/2:.1f}" '
             f'fill="none" stroke="#2a2e34" stroke-width="1"/>')
    # Ouverture (fond) entre jante et moyeu
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim:.1f}" fill="{PALETTE["bg"]}"/>')
    # Rayons (mid-grey, visibles sur fond clair)
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes
        rx, ry = _pt(cx + r_rim * 0.97 * math.cos(a), cy + r_rim * 0.97 * math.sin(a), sx, sy, ox, oy)
        L.append(f'<line x1="{scx:.1f}" y1="{scy:.1f}" x2="{rx:.1f}" y2="{ry:.1f}" '
                 f'stroke="{PALETTE["spoke"]}" stroke-width="0.7"/>')
    # Jante (anneau) + reflet
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim:.1f}" fill="none" '
             f'stroke="{PALETTE["wheel_rim"]}" stroke-width="{rim_w:.1f}"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_rim-rim_w*0.35:.1f}" fill="none" '
             f'stroke="{PALETTE["rim_hi"]}" stroke-width="1" opacity="0.6"/>')
    # Moyeu
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub:.1f}" fill="{PALETTE["hub"]}" '
             f'stroke="#222" stroke-width="1"/>')
    L.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr_hub*0.35:.1f}" fill="#222"/>')
    L.append('</g>')
    return "\n".join(L)


def _draw_tube(x1, y1, x2, y2, d, color, sx, sy, ox, oy, scale, cap_r=0.0,
               edge="rgba(0,0,0,0.38)") -> str:
    """Tube = polygone rempli + liseré sombre (lisibilité) + chapeaux arrondis."""
    pts = _tube_polygon(x1, y1, x2, y2, d, sx, sy, ox, oy, scale)
    if not pts:
        return ""
    ew = max(0.8, d * scale * 0.06)
    lines = [f'<polygon points="{pts}" fill="{color}" stroke="{edge}" '
             f'stroke-width="{ew:.1f}" stroke-linejoin="round"/>']
    if cap_r > 0:
        r_px = cap_r * abs(sx)
        for (xc, yc) in [(x1, y1), (x2, y2)]:
            sc_x, sc_y = _pt(xc, yc, sx, sy, ox, oy)
            lines.append(f'<circle cx="{sc_x:.1f}" cy="{sc_y:.1f}" r="{r_px:.1f}" '
                         f'fill="{color}"/>')
    return "\n".join(lines)


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
        env = motor_envelope_world(dt)
        if env is not None:
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

    # Manivelle (vers le bas-avant) + axe
    bx, by = _pt(*bb, sx, sy, ox, oy)
    crank_len = bike.cranks.crank_length
    pedal_w = bb[0] + crank_len * 0.5
    pedal_h = bb[1] - crank_len * 0.87
    cex, cey = _pt(pedal_w, pedal_h, sx, sy, ox, oy)
    parts.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{cex:.1f}" y2="{cey:.1f}" '
                 f'stroke="{PALETTE["crank"]}" stroke-width="{max(3, 12*scale):.1f}" stroke-linecap="round" />')
    # Pédale (plateforme, vue de côté ≈ longueur fore/aft)
    pl = bike.pedals.length
    pt_th = max(2.5, bike.pedals.thickness * scale)
    px0, py0 = _pt(pedal_w - pl / 2, pedal_h, sx, sy, ox, oy)
    parts.append(f'<rect class="pedals" x="{px0:.1f}" y="{py0 - pt_th/2:.1f}" width="{pl*scale:.1f}" '
                 f'height="{pt_th:.1f}" rx="2" fill="{PALETTE["crank"]}" />')

    # Plateau et pignon
    for c, r in ((bb, r_cr), (axle, r_cog)):
        scx, scy, sr = _circle(c[0], c[1], r, sx, sy, ox, oy)
        parts.append(f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr:.1f}" '
                     f'fill="none" stroke="{PALETTE["cog"]}" stroke-width="2.5" />')

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
    """Overlay biellette de suspension (pivots, bielles, amortisseur, galet, roue AR).

    `frames` = liste KinematicsResult.frames (géométrie monde par pas de course).
    Statique → dessine la frame de sag (~30 %). Animé → SMIL ping-pong topout↔talon.
    """
    if not frames:
        return ""

    def P(pt):
        return (pt[0] * sx + ox, pt[1] * sy + oy)

    def vals(seq):
        # ping-pong : aller + retour (sans dupliquer les extrémités)
        full = list(seq) + list(reversed(seq[:-1]))
        return ";".join(f"{v:.1f}" for v in full)

    acc = "#e84393"   # rose accent (pivots/bielles mobiles)
    sh  = "#00b894"   # amortisseur
    parts = ['<g class="suspension">']
    anim = (f'<animate attributeName="{{a}}" values="{{v}}" '
            f'dur="{period}s" repeatCount="indefinite" />')

    # Frame de référence pour l'affichage statique : ~sag (30 %)
    sag_i = max(range(len(frames)), key=lambda i: 0) if False else \
            min(range(len(frames)), key=lambda i: abs(frames[i]["travel"] -
                (frames[-1]["travel"] * 0.3)))
    ref = frames[sag_i]

    n_links = len(ref["links"])
    # ── Bielles ──────────────────────────────────────────────────────────────
    for li in range(n_links):
        if animate:
            x1 = [P(fr["links"][li][0])[0] for fr in frames]
            y1 = [P(fr["links"][li][0])[1] for fr in frames]
            x2 = [P(fr["links"][li][1])[0] for fr in frames]
            y2 = [P(fr["links"][li][1])[1] for fr in frames]
            parts.append(
                f'<line stroke="{acc}" stroke-width="4" stroke-linecap="round" opacity="0.9">'
                + anim.format(a="x1", v=vals(x1)) + anim.format(a="y1", v=vals(y1))
                + anim.format(a="x2", v=vals(x2)) + anim.format(a="y2", v=vals(y2))
                + '</line>')
        else:
            a, b = P(ref["links"][li][0]), P(ref["links"][li][1])
            parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                         f'stroke="{acc}" stroke-width="4" stroke-linecap="round" opacity="0.9"/>')

    # ── Amortisseur ──────────────────────────────────────────────────────────
    if animate:
        sx1 = [P(fr["shock"][0])[0] for fr in frames]; sy1 = [P(fr["shock"][0])[1] for fr in frames]
        sx2 = [P(fr["shock"][1])[0] for fr in frames]; sy2 = [P(fr["shock"][1])[1] for fr in frames]
        parts.append(
            f'<line stroke="{sh}" stroke-width="7" stroke-linecap="round" opacity="0.85">'
            + anim.format(a="x1", v=vals(sx1)) + anim.format(a="y1", v=vals(sy1))
            + anim.format(a="x2", v=vals(sx2)) + anim.format(a="y2", v=vals(sy2)) + '</line>')
    else:
        a, b = P(ref["shock"][0]), P(ref["shock"][1])
        parts.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                     f'stroke="{sh}" stroke-width="7" stroke-linecap="round" opacity="0.85"/>')

    # ── Roue arrière fantôme (cercle) + axe ──────────────────────────────────
    rr = wheel_r_r * abs(sx)
    if animate:
        cxs = [P(fr["axle"])[0] for fr in frames]; cys = [P(fr["axle"])[1] for fr in frames]
        parts.append(
            f'<circle r="{rr:.1f}" fill="none" stroke="{acc}" stroke-width="2" opacity="0.5">'
            + anim.format(a="cx", v=vals(cxs)) + anim.format(a="cy", v=vals(cys)) + '</circle>')
        parts.append(
            f'<circle r="6" fill="{acc}">'
            + anim.format(a="cx", v=vals(cxs)) + anim.format(a="cy", v=vals(cys)) + '</circle>')
    else:
        ax = P(ref["axle"])
        parts.append(f'<circle cx="{ax[0]:.1f}" cy="{ax[1]:.1f}" r="{rr:.1f}" '
                     f'fill="none" stroke="{acc}" stroke-width="2" opacity="0.5"/>')
        parts.append(f'<circle cx="{ax[0]:.1f}" cy="{ax[1]:.1f}" r="6" fill="{acc}"/>')

    # ── Galet (si présent) ────────────────────────────────────────────────────
    if ref.get("idler"):
        if animate and all(fr.get("idler") for fr in frames):
            ixs = [P(fr["idler"])[0] for fr in frames]; iys = [P(fr["idler"])[1] for fr in frames]
            parts.append(f'<circle r="5" fill="{sh}" opacity="0.9">'
                         + anim.format(a="cx", v=vals(ixs)) + anim.format(a="cy", v=vals(iys)) + '</circle>')
        else:
            ip = P(ref["idler"])
            parts.append(f'<circle cx="{ip[0]:.1f}" cy="{ip[1]:.1f}" r="5" fill="{sh}" opacity="0.9"/>')

    # ── Pivots fixes (cadre) : premiers points des bielles à la frame topout ──
    fixed = []
    f0 = frames[0]
    fixed.append(f0["links"][0][0])                 # main pivot (début 1re bielle)
    if n_links >= 3:
        fixed.append(f0["links"][2][1])             # rocker/cadre (fin 3e bielle)
    fixed.append(f0["shock"][1])                     # amorto haut (cadre)
    for fp in fixed:
        sp = P(fp)
        parts.append(f'<circle cx="{sp[0]:.1f}" cy="{sp[1]:.1f}" r="5" '
                     f'fill="#2d3436" stroke="#fff" stroke-width="1.5"/>')

    parts.append("</g>")
    return "".join(parts)


def render_svg(bike: BikeDesign, calc: CalcResult,
               width: int = 1400, height: int = 750,
               show_dims: bool = True, fit=None,
               suspension=None, animate_suspension=False) -> str:
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
    parts.append(_draw_wheel(ra.x, ra.y, wheel_r_r, rim_r_r, n_sp_r, sx, sy, ox, oy))
    parts.append(_draw_wheel(fa.x, fa.y, wheel_r_f, rim_r_f, n_sp_f, sx, sy, ox, oy))

    # === FREINS (disques) ====================================================
    parts.append(_draw_brakes(bike, calc, sx, sy, ox, oy))

    # === BASES (chainstays) ==================================================
    parts.append(_draw_tube(bb.x, bb.y, ra.x, ra.y, f.chainstay_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.chainstay_d/2))

    # === HAUBANS (seatstays) =================================================
    # Relient axe AR au jonction TT/ST
    parts.append(_draw_tube(ra.x, ra.y, stt.x, stt.y, f.seatstay_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.seatstay_d/2))

    # === TUBE DE SELLE ========================================================
    parts.append(_draw_tube(bb.x, bb.y, stt.x, stt.y, f.seat_tube_fd,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.seat_tube_fd/2))

    # === TUBE HORIZONTAL (top tube) ==========================================
    parts.append(_draw_tube(stt.x, stt.y, ht.x, ht.y, f.top_tube_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.top_tube_d/2))

    # === TUBE DIAGONAL (down tube) ===========================================
    parts.append(_draw_tube(bb.x, bb.y, cr.x, cr.y, f.down_tube_d,
                            PALETTE["frame"], sx, sy, ox, oy, scale_f, cap_r=f.down_tube_d/2))

    # === TUBE DE DIRECTION ===================================================
    parts.append(_draw_tube(cr.x, cr.y, ht.x, ht.y, f.head_tube_d,
                            PALETTE["crown"], sx, sy, ox, oy, scale_f, cap_r=f.head_tube_d/2))

    # === FOURCHE =============================================================
    hta = math.radians(f.head_angle)
    # Décalage latéral des tubes de fourche (±40mm)
    fork_offset_lateral = 35.0
    nfx =  math.sin(hta) * fork_offset_lateral
    nfy = -math.cos(hta) * fork_offset_lateral

    if fk.dual_crown:
        # Couronne basse (crown) → axe AV : deux jambes
        for sign in [+1, -1]:
            lx1 = cr.x + sign * nfx
            ly1 = cr.y + sign * nfy
            lx2 = fa.x + sign * nfx * 0.5
            ly2 = fa.y + sign * nfy * 0.5
            parts.append(_draw_tube(lx1, ly1, lx2, ly2, fk.blade_width,
                                    PALETTE["fork"], sx, sy, ox, oy, scale_f))
        # Axe avant (cross bar basse couronne)
        parts.append(_draw_tube(cr.x - nfx, cr.y - nfy,
                                cr.x + nfx, cr.y + nfy, 20.0,
                                PALETTE["crown"], sx, sy, ox, oy, scale_f))
        # Tubes plongeurs (stanchions) : couronne haute → couronne basse
        upper_crown_x = ht.x
        upper_crown_y = ht.y
        for sign in [+1, -1]:
            sx1 = upper_crown_x + sign * nfx * 0.4
            sy1 = upper_crown_y + sign * nfy * 0.4
            sx2 = cr.x + sign * nfx
            sy2 = cr.y + sign * nfy
            parts.append(_draw_tube(sx1, sy1, sx2, sy2, fk.blade_width * 0.7,
                                    PALETTE["fork"], sx, sy, ox, oy, scale_f))
        # Couronne haute (cross bar)
        parts.append(_draw_tube(ht.x - nfx * 0.4, ht.y - nfy * 0.4,
                                ht.x + nfx * 0.4, ht.y + nfy * 0.4, 20.0,
                                PALETTE["crown"], sx, sy, ox, oy, scale_f))
    else:
        # Fourche simple couronne
        for sign in [+1, -1]:
            lx1 = cr.x + sign * nfx
            ly1 = cr.y + sign * nfy
            lx2 = fa.x + sign * nfx * 0.5
            ly2 = fa.y
            parts.append(_draw_tube(lx1, ly1, lx2, ly2, fk.blade_width,
                                    PALETTE["fork"], sx, sy, ox, oy, scale_f))
        parts.append(_draw_tube(cr.x - nfx, cr.y - nfy,
                                cr.x + nfx, cr.y + nfy, 18.0,
                                PALETTE["crown"], sx, sy, ox, oy, scale_f))

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
