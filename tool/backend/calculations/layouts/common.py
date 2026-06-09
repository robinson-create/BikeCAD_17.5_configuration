"""Primitives géométriques + assemblage du résultat cinématique partagé.

Convention monde : BB = (0,0), x = avant (+), y = haut (+), mm.

Tout ce qui est INDÉPENDANT de la topologie vit ici :
  - helpers géométriques (distances, intersections, rotations, transfo rigide) ;
  - `anti_squat()` paramétrable par centre instantané + brin moteur ;
  - `build_result()` : échantillonnage régulier par course roue, ratio de levier
    par différences finies, belt growth, pedal kickback, synthèse + verdicts.

Les modules de topologie (`four_bar`, `high_pivot`, …) ne font QUE produire la
liste ordonnée d'états ; toute la métrologie est ici → un seul endroit à
maintenir et à valider.
"""

import math
from ...models.bike import BikeDesign, KinematicsResult, KinematicSample


# ── Primitives géométriques ────────────────────────────────────────────────

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def circle_intersections(c0, r0, c1, r1):
    """Points d'intersection de deux cercles. Retourne [] si aucun."""
    x0, y0 = c0
    x1, y1 = c1
    d = math.hypot(x1 - x0, y1 - y0)
    if d == 0 or d > r0 + r1 or d < abs(r0 - r1):
        return []
    a = (r0 ** 2 - r1 ** 2 + d ** 2) / (2 * d)
    h2 = r0 ** 2 - a ** 2
    if h2 < 0:
        h2 = 0.0
    h = math.sqrt(h2)
    xm = x0 + a * (x1 - x0) / d
    ym = y0 + a * (y1 - y0) / d
    rx = -(y1 - y0) * (h / d)
    ry = (x1 - x0) * (h / d)
    return [(xm + rx, ym + ry), (xm - rx, ym - ry)]


def line_intersection(p1, p2, p3, p4):
    """Intersection des droites (p1,p2) et (p3,p4). None si parallèles."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def rotate_about(p, center, ang):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = p[0] - center[0], p[1] - center[1]
    return (center[0] + c * dx - s * dy, center[1] + s * dx + c * dy)


def coupler_transform(B0, C0, B, C):
    """Transformation rigide envoyant (B0,C0) sur (B,C). Retourne fn(point)."""
    ang0 = math.atan2(C0[1] - B0[1], C0[0] - B0[0])
    ang1 = math.atan2(C[1] - B[1], C[0] - B[0])
    da = ang1 - ang0
    c, s = math.cos(da), math.sin(da)

    def fn(p):
        dx, dy = p[0] - B0[0], p[1] - B0[1]
        return (B[0] + c * dx - s * dy, B[1] + s * dx + c * dy)
    return fn


def belt_length(chainring, idler, cog, use_idler):
    """Longueur de brin courroie (centre à centre), avec ou sans galet."""
    if use_idler:
        return dist(chainring, idler) + dist(idler, cog)
    return dist(chainring, cog)


def anti_squat(ic, axle, ground_y, drive_pt, r_drive, r_cog, cog_height,
               front_axle_x):
    """Anti-squat % par la méthode du centre instantané + ligne motrice.

    Paramétrable par :
      - `ic`       : centre instantané de la roue AR p/r au cadre (point) ;
      - `drive_pt` : centre de la poulie qui tend le brin moteur vers le pignon
                     (plateau BB, ou galet sur un montage à idler) ;
      - `r_drive`  : rayon de cette poulie ;
      - `r_cog`    : rayon du pignon AR.

    Construction : brin moteur = tangente supérieure (drive_pt → cog) ; IFC =
    intersection (brin moteur) ∩ (axe AR, IC) ; ligne de force = (contact pneu
    AR, IFC) ; AS% = hauteur de cette ligne à la verticale du contact AV / h_cg.
    INDICATIVE — à valider dans Linkage avant fabrication.
    """
    if ic is None:
        return 0.0
    dx = axle[0] - drive_pt[0]
    dy = axle[1] - drive_pt[1]
    dd = math.hypot(dx, dy)
    if dd < 1e-6:
        return 0.0
    nx, ny = -dy / dd, dx / dd
    if ny < 0:                      # forcer la normale vers le haut (brin supérieur)
        nx, ny = -nx, -ny
    p_drive = (drive_pt[0] + r_drive * nx, drive_pt[1] + r_drive * ny)
    p_cog = (axle[0] + r_cog * nx, axle[1] + r_cog * ny)
    ifc = line_intersection(p_drive, p_cog, axle, ic)
    if ifc is None:
        ifc = ic
    rear_contact = (axle[0], ground_y)
    fx0, fy0 = rear_contact
    fx1, fy1 = ifc
    if abs(fx1 - fx0) < 1e-6:
        return 0.0
    t = (front_axle_x - fx0) / (fx1 - fx0)
    h_force = fy0 + t * (fy1 - fy0)
    h_above_ground = h_force - ground_y
    if cog_height <= 0:
        return 0.0
    return h_above_ground / cog_height * 100.0


# ── Assemblage du résultat ───────────────────────────────────────────────────

def build_result(bike: BikeDesign, states: list,
                 pivots_world: dict | None = None) -> KinematicsResult:
    """Transforme un balayage d'états (topout → compression) en KinematicsResult.

    `states[0]` est la position de référence (topout). Chaque état porte
    axle / idler / shock_len / anti_squat (cf. layouts/__init__). `pivots_world`
    (positions des pivots pour le schéma) est propre à la topologie : le layout
    le fournit.
    """
    s = bike.suspension
    f = bike.frame

    if len(states) < 5:
        return KinematicsResult(ok=False, message="Plage de mouvement trop courte.")

    # Transmission (plateau concentrique au BB)
    chainring = (0.0, 0.0)
    r_cr = s.chainring_teeth * s.belt_pitch / (2 * math.pi)

    axle_top = states[0]["axle"]
    shock_len_top = states[0]["shock_len"]
    belt_top = belt_length(chainring, states[0]["idler"], axle_top, s.use_idler)

    # Courbe continue le long de la branche cohérente
    curve = []  # (wheel_travel, metrics)
    for st in states:
        axle = st["axle"]; idler = st["idler"]; shock_len = st["shock_len"]
        belt = belt_length(chainring, idler, axle, s.use_idler)
        wt = axle[1] - axle_top[1]
        curve.append((wt, {
            "shock_stroke": shock_len_top - shock_len,
            "wheel_travel": wt,
            "shock_length": shock_len,
            "belt_growth": belt - belt_top,
            "axle_x": axle[0],
            "axle_y": axle[1],
            "axle_dx": -(axle[0] - axle_top[0]),
            "anti_squat": st["anti_squat"],
        }))

    max_travel_geom = curve[-1][0]
    travel_cap = min(s.rear_travel, max_travel_geom)

    def interp_metric(t_target, key):
        prev_t, prev_m = curve[0]
        for cur_t, cur_m in curve[1:]:
            if (prev_t - t_target) * (cur_t - t_target) <= 0 and cur_t != prev_t:
                frac = (t_target - prev_t) / (cur_t - prev_t)
                return prev_m[key] + frac * (cur_m[key] - prev_m[key])
            prev_t, prev_m = cur_t, cur_m
        return curve[-1][1][key]

    # Échantillonnage régulier par course roue
    N = max(5, s.samples)
    raw = []
    for i in range(N + 1):
        t_target = travel_cap * i / N
        raw.append({k: interp_metric(t_target, k) for k in (
            "shock_stroke", "wheel_travel", "shock_length", "belt_growth",
            "axle_x", "axle_y", "axle_dx", "anti_squat",
        )})

    if len(raw) < 3:
        return KinematicsResult(ok=False, message="Échantillonnage insuffisant.")

    # Ratio de levier par différences finies + pedal kickback
    samples = []
    for i, r in enumerate(raw):
        if i == 0:
            j0, j1 = 0, 1
        elif i == len(raw) - 1:
            j0, j1 = len(raw) - 2, len(raw) - 1
        else:
            j0, j1 = i - 1, i + 1
        dws = raw[j1]["wheel_travel"] - raw[j0]["wheel_travel"]
        dss = raw[j1]["shock_stroke"] - raw[j0]["shock_stroke"]
        lev = dws / dss if abs(dss) > 1e-6 else 0.0
        # Pedal kickback : la courroie s'allonge de belt_growth ; plateau au BB
        # bloqué (moteur/cliquets) → la manivelle recule de Δ/r_plateau (rad).
        kick = math.degrees(r["belt_growth"] / r_cr) if r_cr > 1e-6 else 0.0
        samples.append(KinematicSample(
            wheel_travel=round(r["wheel_travel"], 2),
            shock_stroke=round(r["shock_stroke"], 2),
            shock_length=round(r["shock_length"], 2),
            leverage=round(lev, 3),
            anti_squat=round(r["anti_squat"], 1),
            pedal_kickback=round(kick, 2),
            belt_growth=round(r["belt_growth"], 2),
            axle_x=round(r["axle_x"], 1),
            axle_y=round(r["axle_y"], 1),
            axle_dx=round(r["axle_dx"], 2),
        ))

    total_travel = samples[-1].wheel_travel
    lr_start = samples[0].leverage
    lr_end = samples[-1].leverage
    progressivity = (lr_start - lr_end) / lr_start * 100 if lr_start else 0.0

    sag_travel = total_travel * s.sag_percent / 100.0
    sag_idx = min(range(len(samples)),
                  key=lambda k: abs(samples[k].wheel_travel - sag_travel))
    lr_sag = samples[sag_idx].leverage
    as_sag = samples[sag_idx].anti_squat

    belt_growth_max = max(abs(s_.belt_growth) for s_ in samples)
    pedal_kickback_max = max(abs(s_.pedal_kickback) for s_ in samples)
    axle_rearward = max(s_.axle_dx for s_ in samples)
    shock_used = samples[-1].shock_stroke

    msg = ""
    if travel_cap < s.rear_travel - 1:
        msg = (f"La géométrie ne permet que {travel_cap:.0f} mm de course roue "
               f"(cible {s.rear_travel:.0f} mm) avant blocage du mécanisme.")
    if shock_used > s.shock_stroke + 1:
        extra = (f"Course amortisseur requise {shock_used:.0f} mm > "
                 f"course spécifiée {s.shock_stroke:.0f} mm — revoir les ancrages.")
        msg = (msg + " " + extra).strip()

    return KinematicsResult(
        ok=True,
        message=msg,
        samples=samples,
        total_travel=round(total_travel, 1),
        leverage_start=round(lr_start, 3),
        leverage_end=round(lr_end, 3),
        leverage_sag=round(lr_sag, 3),
        progressivity=round(progressivity, 1),
        anti_squat_sag=round(as_sag, 1),
        pedal_kickback_max=round(pedal_kickback_max, 2),
        belt_growth_max=round(belt_growth_max, 2),
        axle_path_rearward=round(axle_rearward, 1),
        shock_stroke_used=round(shock_used, 1),
        shock_stroke_spec=round(s.shock_stroke, 1),
        pivots_world=pivots_world or {},
    )
