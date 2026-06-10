"""Plan technique d'ingénierie (blueprint vectoriel) — DOM Engineering Bike Tool.

Sortie SVG « bureau d'études » : vue de profil filaire (axes centraux), cotation
complète (longueurs + angles), repère d'axes XY au BB, VISSERIE / AXES annotés
(axe AV/AR, pédalier, jeu de direction, pivots, amortisseur), repérage des LUGS,
table de coordonnées des points clés, et cartouche (projet, dessinateur, date,
échelle, unités). Vectoriel → ouvrable dans Illustrator / Inkscape / CAO, et
convertible en PDF pour diffusion.

Repère monde : BB=(0,0), x avant +, y haut +, mm.
"""

import math
from ..models.bike import BikeDesign, CalcResult

INK = "#1b2330"        # traits principaux
THIN = "#5b6573"       # traits fins / centerlines
DIM = "#1f6feb"        # cotes
FAST = "#c0392b"       # visserie / axes
LUGC = "#0a7d52"       # lugs
PAPER = "#ffffff"
GRID = "#eef2f7"


def _fit(pts, W, H, pad_l, pad_r, pad_t, pad_b):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    ww = (maxx - minx) or 1; hh = (maxy - miny) or 1
    s = min((W - pad_l - pad_r) / ww, (H - pad_t - pad_b) / hh)
    ox = pad_l - minx * s
    oy = pad_t + maxy * s          # y monde haut → svg bas
    return s, ox, oy


def render_drawing_svg(bike: BikeDesign, calc: CalcResult, nodes=None,
                       project="eMTB DOM Engineering", designer="Robinson Joubert",
                       date="", scale_note="") -> str:
    f = bike.frame
    s_ = bike.suspension
    W, H = 1700, 1150
    # marges (cartouche en bas à droite, table en haut à gauche)
    pad_l, pad_r, pad_t, pad_b = 70, 60, 120, 220

    # points clés monde
    bb = (calc.bb.x, calc.bb.y)
    ra = (calc.rear_axle.x, calc.rear_axle.y)
    fa = (calc.front_axle.x, calc.front_axle.y)
    cr = (calc.crown.x, calc.crown.y)
    ht = (calc.ht_top.x, calc.ht_top.y)
    st = (calc.seat_tube_top.x, calc.seat_tube_top.y)
    gl = calc.ground_level
    allpts = [bb, ra, fa, cr, ht, st, (0, gl), (fa[0], fa[1] + f.wheel_f / 2)]
    s, ox, oy = _fit(allpts, W, H, pad_l, pad_r, pad_t, pad_b)

    def P(p):
        return (p[0] * s + ox, p[1] * (-s) + oy)

    e = []  # éléments svg
    # arrière-plan + cadre + grille légère
    e.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
    for gx in range(0, W, 50):
        e.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{H}" stroke="{GRID}" stroke-width="1"/>')
    for gy in range(0, H, 50):
        e.append(f'<line x1="0" y1="{gy}" x2="{W}" y2="{gy}" stroke="{GRID}" stroke-width="1"/>')
    e.append(f'<rect x="14" y="14" width="{W-28}" height="{H-28}" fill="none" '
             f'stroke="{INK}" stroke-width="2"/>')

    # ── Roues (contour pneu + jante, filaire) ────────────────────────────────
    for axle, dia, bsd in ((ra, f.wheel_r, bike.wheel_r.bead_seat_dia),
                           (fa, f.wheel_f, bike.wheel_f.bead_seat_dia)):
        c = P(axle)
        e.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{dia/2*s:.1f}" '
                 f'fill="none" stroke="{THIN}" stroke-width="1.4"/>')
        e.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{bsd/2*s:.1f}" '
                 f'fill="none" stroke="{THIN}" stroke-width="1" stroke-dasharray="2,3"/>')

    # ── Sol ──────────────────────────────────────────────────────────────────
    gy = P((0, gl))[1]
    e.append(f'<line x1="40" y1="{gy:.1f}" x2="{W-40}" y2="{gy:.1f}" '
             f'stroke="{THIN}" stroke-width="1" stroke-dasharray="10,4"/>')

    # ── Centerlines des tubes (axe à axe) ────────────────────────────────────
    centerlines = [(bb, ra), (bb, st), (st, ht), (bb, cr), (cr, ht), (ra, st),
                   (cr, fa)]
    for a, b in centerlines:
        pa, pb = P(a), P(b)
        e.append(f'<line x1="{pa[0]:.1f}" y1="{pa[1]:.1f}" x2="{pb[0]:.1f}" y2="{pb[1]:.1f}" '
                 f'stroke="{INK}" stroke-width="2" stroke-linecap="round"/>')

    # ── Repère d'axes XY au BB ───────────────────────────────────────────────
    obb = P(bb)
    e.append(f'<circle cx="{obb[0]:.1f}" cy="{obb[1]:.1f}" r="4" fill="{INK}"/>')
    e.append(f'<line x1="{obb[0]:.1f}" y1="{obb[1]:.1f}" x2="{obb[0]+90:.1f}" y2="{obb[1]:.1f}" '
             f'stroke="{INK}" stroke-width="1.5" marker-end="url(#arrow)"/>')
    e.append(f'<line x1="{obb[0]:.1f}" y1="{obb[1]:.1f}" x2="{obb[0]:.1f}" y2="{obb[1]-90:.1f}" '
             f'stroke="{INK}" stroke-width="1.5" marker-end="url(#arrow)"/>')
    e.append(f'<text x="{obb[0]+96:.0f}" y="{obb[1]+4:.0f}" font-size="13" fill="{INK}" font-family="monospace">X</text>')
    e.append(f'<text x="{obb[0]-4:.0f}" y="{obb[1]-96:.0f}" font-size="13" fill="{INK}" font-family="monospace">Y</text>')
    e.append(f'<text x="{obb[0]+8:.0f}" y="{obb[1]+18:.0f}" font-size="11" fill="{INK}" font-family="monospace">BB (0,0)</text>')

    # ── Cotes linéaires ──────────────────────────────────────────────────────
    def dim_h(x1, x2, yworld, label, above=True, off=34):
        p1 = P((x1, yworld)); p2 = P((x2, yworld))
        yy = min(p1[1], p2[1]) - off if above else max(p1[1], p2[1]) + off
        e.append(f'<line x1="{p1[0]:.1f}" y1="{yy:.1f}" x2="{p2[0]:.1f}" y2="{yy:.1f}" '
                 f'stroke="{DIM}" stroke-width="1" marker-start="url(#dim)" marker-end="url(#dim)"/>')
        for px in (p1, p2):
            e.append(f'<line x1="{px[0]:.1f}" y1="{px[1]:.1f}" x2="{px[0]:.1f}" y2="{yy:.1f}" '
                     f'stroke="{DIM}" stroke-width="0.6" stroke-dasharray="3,2"/>')
        e.append(f'<text x="{(p1[0]+p2[0])/2:.0f}" y="{yy-5:.0f}" fill="{DIM}" font-size="12" '
                 f'text-anchor="middle" font-family="monospace">{label}</text>')

    def dim_v(yworld1, yworld2, xworld, label, left=True, off=40):
        p1 = P((xworld, yworld1)); p2 = P((xworld, yworld2))
        xx = min(p1[0], p2[0]) - off if left else max(p1[0], p2[0]) + off
        e.append(f'<line x1="{xx:.1f}" y1="{p1[1]:.1f}" x2="{xx:.1f}" y2="{p2[1]:.1f}" '
                 f'stroke="{DIM}" stroke-width="1" marker-start="url(#dim)" marker-end="url(#dim)"/>')
        for px in (p1, p2):
            e.append(f'<line x1="{px[0]:.1f}" y1="{px[1]:.1f}" x2="{xx:.1f}" y2="{px[1]:.1f}" '
                     f'stroke="{DIM}" stroke-width="0.6" stroke-dasharray="3,2"/>')
        e.append(f'<text x="{xx-6:.0f}" y="{(p1[1]+p2[1])/2:.0f}" fill="{DIM}" font-size="12" '
                 f'text-anchor="middle" font-family="monospace" '
                 f'transform="rotate(-90 {xx-6:.0f} {(p1[1]+p2[1])/2:.0f})">{label}</text>')

    dim_h(ra[0], fa[0], gl, f"Empattement {calc.wheelbase:.0f}", above=False, off=70)
    dim_h(bb[0], ht[0], ht[1], f"Reach {calc.reach:.0f}", above=True, off=30)
    dim_h(bb[0], fa[0], gl, f"FCD {f.fcd:.0f}", above=False, off=120)
    dim_v(bb[1], ht[1], ht[0], f"Stack {calc.stack:.0f}", left=False, off=44)
    dim_v(gl, bb[1], bb[0], f"BB {calc.bb_height:.0f}", left=True, off=40)

    # ── Cotes angulaires (HTA, STA) avec arc ─────────────────────────────────
    def dim_angle(vertex, ang_deg, label, r=58):
        v = P(vertex)
        a0 = 0.0                      # horizontale (réf)
        a1 = math.radians(ang_deg)
        # arc en coords svg (y inversé → angles négatifs)
        x0, y0 = v[0] + r, v[1]
        x1 = v[0] + r * math.cos(a1); y1 = v[1] - r * math.sin(a1)
        e.append(f'<path d="M {x0:.1f},{y0:.1f} A {r},{r} 0 0 0 {x1:.1f},{y1:.1f}" '
                 f'fill="none" stroke="{DIM}" stroke-width="1"/>')
        e.append(f'<text x="{v[0]+r+6:.0f}" y="{v[1]-r*0.4:.0f}" fill="{DIM}" font-size="12" '
                 f'font-family="monospace">{label}</text>')
    dim_angle(cr, f.head_angle, f"HTA {f.head_angle:.1f}°")
    dim_angle(bb, f.seat_angle, f"STA {f.seat_angle:.1f}°")

    # ── VISSERIE / AXES ──────────────────────────────────────────────────────
    fa_dia = 20 if bike.fork.dual_crown else 15
    fasteners = [
        (ra, 12, "Axe AR Ø12 (148×12)"),
        (fa, fa_dia, f"Axe AV Ø{fa_dia} (110×{fa_dia})"),
        (bb, 24, "Axe pédalier (BB)"),
        (ht, 28, "JDD haut"),
        (cr, 28, "JDD bas"),
    ]
    if s_.enabled:
        fasteners += [
            ((s_.main_pivot.x, s_.main_pivot.y), 15, "Pivot principal M15"),
            ((s_.shock_lower.x, s_.shock_lower.y), 8, "Œillet amorto bas M8"),
            ((s_.shock_upper.x, s_.shock_upper.y), 8, "Œillet amorto haut M8"),
        ]
        if s_.linkage_type == "four_bar_horst":
            fasteners += [
                ((s_.horst_pivot.x, s_.horst_pivot.y), 12, "Pivot Horst M12"),
                ((s_.upper_frame_pivot.x, s_.upper_frame_pivot.y), 12, "Pivot rocker/cadre M12"),
                ((s_.upper_ss_pivot.x, s_.upper_ss_pivot.y), 12, "Pivot rocker/hauban M12"),
            ]
        if s_.use_idler:
            fasteners += [((s_.idler.x, s_.idler.y), 10, "Axe galet M10")]

    for (pt, dia, label) in fasteners:
        c = P(pt)
        rr = max(4.0, dia / 2 * s)
        e.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{rr:.1f}" '
                 f'fill="none" stroke="{FAST}" stroke-width="1.5"/>')
        # croix de centre
        e.append(f'<line x1="{c[0]-rr-4:.1f}" y1="{c[1]:.1f}" x2="{c[0]+rr+4:.1f}" y2="{c[1]:.1f}" '
                 f'stroke="{FAST}" stroke-width="0.8"/>')
        e.append(f'<line x1="{c[0]:.1f}" y1="{c[1]-rr-4:.1f}" x2="{c[0]:.1f}" y2="{c[1]+rr+4:.1f}" '
                 f'stroke="{FAST}" stroke-width="0.8"/>')
        # leader + étiquette
        lx, ly = c[0] + 16, c[1] - 16
        e.append(f'<line x1="{c[0]:.1f}" y1="{c[1]:.1f}" x2="{lx:.1f}" y2="{ly:.1f}" stroke="{FAST}" stroke-width="0.6"/>')
        e.append(f'<text x="{lx+2:.0f}" y="{ly:.0f}" fill="{FAST}" font-size="9.5" font-family="monospace">{label}</text>')

    # ── LUGS (jonctions à coller) ────────────────────────────────────────────
    if nodes:
        for n in nodes:
            c = P((n.x, n.y))
            e.append(f'<rect x="{c[0]-9:.1f}" y="{c[1]-9:.1f}" width="18" height="18" '
                     f'fill="none" stroke="{LUGC}" stroke-width="1.4" transform="rotate(45 {c[0]:.1f} {c[1]:.1f})"/>')
            e.append(f'<text x="{c[0]+12:.0f}" y="{c[1]+16:.0f}" fill="{LUGC}" font-size="9.5" '
                     f'font-family="monospace">LUG {n.name} ({len(n.sockets)} d.)</text>')

    # ── Table de coordonnées (haut-gauche) ───────────────────────────────────
    rows = [("BB", *bb), ("Axe AR", *ra), ("Axe AV", *fa), ("Couronne", *cr),
            ("Haut HT", *ht), ("Haut TS", *st)]
    if s_.enabled:
        rows += [("Pivot principal", s_.main_pivot.x, s_.main_pivot.y),
                 ("Amorto bas", s_.shock_lower.x, s_.shock_lower.y),
                 ("Amorto haut", s_.shock_upper.x, s_.shock_upper.y)]
    tx, ty = 30, 40
    e.append(f'<rect x="{tx-6}" y="{ty-22}" width="270" height="{26+len(rows)*16}" '
             f'fill="#ffffff" stroke="{INK}" stroke-width="1"/>')
    e.append(f'<text x="{tx}" y="{ty-6}" font-size="12" font-weight="bold" fill="{INK}" '
             f'font-family="monospace">POINTS CLÉS (mm, BB origine)</text>')
    for i, (nm, x, y) in enumerate(rows):
        yy = ty + 12 + i * 16
        e.append(f'<text x="{tx}" y="{yy}" font-size="10.5" fill="{INK}" font-family="monospace">'
                 f'{nm:<16}{x:>7.1f} ; {y:>7.1f}</text>')

    # ── Cartouche (bas-droite) ───────────────────────────────────────────────
    bw, bh = 520, 150
    bx, by = W - bw - 22, H - bh - 22
    e.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
    e.append(f'<line x1="{bx}" y1="{by+34}" x2="{bx+bw}" y2="{by+34}" stroke="{INK}" stroke-width="1"/>')
    e.append(f'<line x1="{bx+bw*0.62:.0f}" y1="{by}" x2="{bx+bw*0.62:.0f}" y2="{by+bh}" stroke="{INK}" stroke-width="1"/>')
    e.append(f'<text x="{bx+12}" y="{by+23}" font-size="15" font-weight="bold" fill="{INK}" font-family="sans-serif">DOM ENGINEERING — {project}</text>')
    specs = [f"Dessinateur : {designer}", f"Date : {date}", f"Échelle : {scale_note or f'1:{1/s*1000:.0f} (mm)'}",
             "Unités : mm — Repère BB (0,0)",
             f"HTA {f.head_angle:.1f}°  STA {f.seat_angle:.1f}°  CS {f.cs:.0f}  BBdrop {f.bb_drop:.0f}"]
    for i, line in enumerate(specs):
        e.append(f'<text x="{bx+12}" y="{by+54+i*20}" font-size="12" fill="{INK}" font-family="monospace">{line}</text>')
    geo = [f"Reach   {calc.reach:.0f} mm", f"Stack   {calc.stack:.0f} mm",
           f"Empat.  {calc.wheelbase:.0f} mm", f"Trail   {calc.trail:.0f} mm",
           f"BB haut {calc.bb_height:.0f} mm"]
    for i, line in enumerate(geo):
        e.append(f'<text x="{bx+bw*0.62+12:.0f}" y="{by+54+i*20}" font-size="12" fill="{INK}" font-family="monospace">{line}</text>')

    # légende couleurs
    lx0, ly0 = bx, by - 26
    e.append(f'<text x="{lx0}" y="{ly0}" font-size="10.5" font-family="monospace">'
             f'<tspan fill="{DIM}">■ cotes</tspan>  '
             f'<tspan fill="{FAST}">■ visserie/axes</tspan>  '
             f'<tspan fill="{LUGC}">◆ lugs</tspan></text>')

    defs = (
        '<defs>'
        '<marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">'
        f'<path d="M0,0 L9,4.5 L0,9 z" fill="{INK}"/></marker>'
        '<marker id="dim" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">'
        f'<path d="M0,5 L10,2 L10,8 z" fill="{DIM}"/></marker>'
        '</defs>'
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{defs}{"".join(e)}</svg>')
