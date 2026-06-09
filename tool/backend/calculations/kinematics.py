"""
Moteur cinématique four-bar (Horst Link) — DOM Engineering Bike Tool

Convention monde : BB = (0,0), x = avant (+), y = haut (+), mm.

Topologie four-bar :
    A = main_pivot        (cadre, sol)        ─┐
    B = horst_pivot       (bout des bases)     │  bielle AB = bases (chainstay)
    C = upper_ss_pivot    (bout du rocker)     │  bielle BC = haubans (coupler)
    D = upper_frame_pivot (cadre, sol)        ─┘  bielle CD = rocker

  • L'axe AR est rigide avec le coupler BC.
  • Le galet (idler) est rigide avec les bases AB.
  • L'amortisseur : point bas sur AB (ou rocker), point haut fixe sur le cadre.

Méthode :
  On pilote la LONGUEUR d'amortisseur de eye-to-eye (topout) jusqu'à
  eye-to-eye − stroke (talon). Pour chaque longueur on résout l'angle des
  bases par bisection, puis le four-bar par intersection de cercles.
  → course roue, ratio de levier, progressivité, belt growth, anti-squat.

Anti-squat (entraînement par courroie) :
  1. IC = centre instantané (intersection des droites (A,B) et (D,C)).
  2. IFC = intersection de la ligne de courroie (brin supérieur) et de la
     droite (axe AR, IC).
  3. Ligne de force = (contact pneu AR, IFC).
  4. AS% = hauteur de la ligne de force à la verticale du contact AV / h_cg.
  À valider dans Linkage avant fabrication.
"""

import math
from ..models.bike import (
    BikeDesign, KinematicsResult, KinematicSample,
)


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _circle_intersections(c0, r0, c1, r1):
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


def _line_intersection(p1, p2, p3, p4):
    """Intersection des droites (p1,p2) et (p3,p4). None si parallèles."""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _rotate_about(p, center, ang):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = p[0] - center[0], p[1] - center[1]
    return (center[0] + c * dx - s * dy, center[1] + s * dx + c * dy)


def _coupler_transform(B0, C0, B, C):
    """Transformation rigide envoyant (B0,C0) sur (B,C). Retourne fn(point)."""
    ang0 = math.atan2(C0[1] - B0[1], C0[0] - B0[0])
    ang1 = math.atan2(C[1] - B[1], C[0] - B[0])
    da = ang1 - ang0
    c, s = math.cos(da), math.sin(da)

    def fn(p):
        dx, dy = p[0] - B0[0], p[1] - B0[1]
        return (B[0] + c * dx - s * dy, B[1] + s * dx + c * dy)
    return fn


def _belt_length(chainring, idler, cog, use_idler):
    """Longueur de brin courroie (centre à centre), avec ou sans galet."""
    if use_idler:
        return _dist(chainring, idler) + _dist(idler, cog)
    return _dist(chainring, cog)


def solve_kinematics(bike: BikeDesign) -> KinematicsResult:
    s = bike.suspension
    f = bike.frame

    if not s.enabled:
        return KinematicsResult(ok=False, message="Cadre rigide (suspension désactivée).")

    # ── Points fixes (cadre) ────────────────────────────────────────────────
    A = (s.main_pivot.x, s.main_pivot.y)
    D = (s.upper_frame_pivot.x, s.upper_frame_pivot.y)
    B0 = (s.horst_pivot.x, s.horst_pivot.y)
    C0 = (s.upper_ss_pivot.x, s.upper_ss_pivot.y)
    shock_up = (s.shock_upper.x, s.shock_upper.y)
    shock_lo0 = (s.shock_lower.x, s.shock_lower.y)
    idler0 = (s.idler.x, s.idler.y)

    # Longueurs de bielles
    L_AB = _dist(A, B0)
    L_BC = _dist(B0, C0)
    L_CD = _dist(D, C0)
    if min(L_AB, L_BC, L_CD) < 1e-3:
        return KinematicsResult(ok=False, message="Pivots dégénérés (longueur nulle).")

    theta0 = math.atan2(B0[1] - A[1], B0[0] - A[0])

    # ── Géométrie roue / sol / transmission ─────────────────────────────────
    wheel_r_r = f.wheel_r / 2.0
    bb_height = wheel_r_r - f.bb_drop
    ground_y = -bb_height
    rear_axle0 = (-math.sqrt(max(f.cs**2 - f.bb_drop**2, 0.0)), f.bb_drop)

    chainring = (0.0, 0.0)  # plateau concentrique au BB
    r_cr = s.chainring_teeth * s.belt_pitch / (2 * math.pi)
    r_cog = s.cog_teeth * s.belt_pitch / (2 * math.pi)

    # ── Résolution du four-bar pour un angle de bases donné ──────────────────
    prev_C = [C0]

    def solve_at_theta(theta):
        B = (A[0] + L_AB * math.cos(theta), A[1] + L_AB * math.sin(theta))
        pts = _circle_intersections(B, L_BC, D, L_CD)
        if not pts:
            return None
        C = min(pts, key=lambda p: _dist(p, prev_C[0]))
        prev_C[0] = C
        return B, C

    def state_at(theta):
        """Retourne (B, C, axle, idler, shock_len) ou None."""
        sol = solve_at_theta(theta)
        if sol is None:
            return None
        B, C = sol
        tf = _coupler_transform(B0, C0, B, C)
        axle = tf(rear_axle0)
        idler = _rotate_about(idler0, A, theta - theta0)
        if s.shock_on_chainstay:
            lo = _rotate_about(shock_lo0, A, theta - theta0)
        else:
            lo = tf(shock_lo0)
        shock_len = _dist(lo, shock_up)
        return B, C, axle, idler, shock_len

    # ── Cadrage de la plage valide (où le four-bar a une solution) ───────────
    # On part du topout (extension max = axe le plus bas) et on comprime
    # (l'axe monte). On pilote par la COURSE ROUE réelle.
    step = math.radians(0.25)
    valid = []  # (theta, axle_y)
    prev_C[0] = C0
    th = theta0
    # Cherche le sens de compression : theta qui fait monter l'axe.
    s_up = state_at(theta0 - step)
    s_dn = state_at(theta0 + step)
    prev_C[0] = C0
    base = state_at(theta0)
    if base is None:
        return KinematicsResult(ok=False, message="Position de référence non résolue.")
    ay0 = base[2][1]
    dir_compress = -1  # par défaut theta diminue pour comprimer
    if s_up and s_dn:
        if s_up[2][1] > ay0 and s_dn[2][1] <= ay0:
            dir_compress = -1
        elif s_dn[2][1] > ay0 and s_up[2][1] <= ay0:
            dir_compress = +1
    elif s_dn and not s_up:
        dir_compress = +1

    # Balaye depuis topout jusqu'au bind ou jusqu'à dépasser la course cible.
    target_travel = s.rear_travel
    prev_C[0] = C0
    th_cur = theta0
    last = state_at(th_cur)
    axle_top = last[2]
    sweep = [(th_cur, last)]
    for _ in range(2000):
        th_cur += dir_compress * step
        st = state_at(th_cur)
        if st is None:
            break
        sweep.append((th_cur, st))
        if st[2][1] - axle_top[1] > target_travel + 5:
            break

    if len(sweep) < 5:
        return KinematicsResult(ok=False, message="Plage de mouvement four-bar trop courte.")

    max_travel_geom = sweep[-1][1][2][1] - axle_top[1]
    travel_cap = min(target_travel, max_travel_geom)

    # ── Métriques continues le long du balayage fin (branche cohérente) ──────
    shock_len_top = sweep[0][1][4]
    belt_top = _belt_length(chainring, sweep[0][1][3], axle_top, s.use_idler)
    curve = []  # (wheel_travel, dict_metrics) — strictement le long de la branche
    for th, st in sweep:
        B, C, axle, idler, shock_len = st
        belt = _belt_length(chainring, idler, axle, s.use_idler)
        curve.append((
            axle[1] - axle_top[1],
            {
                "shock_stroke": shock_len_top - shock_len,
                "wheel_travel": axle[1] - axle_top[1],
                "shock_length": shock_len,
                "belt_growth": belt - belt_top,
                "axle_x": axle[0],
                "axle_y": axle[1],
                "axle_dx": -(axle[0] - axle_top[0]),
                "anti_squat": _anti_squat(
                    A, B, D, C, axle, ground_y,
                    chainring, r_cr, r_cog, s.cog_height, front_axle_x=f.fcd,
                ),
            },
        ))

    def interp_metric(t_target, key):
        prev_t, prev_m = curve[0]
        for cur_t, cur_m in curve[1:]:
            if (prev_t - t_target) * (cur_t - t_target) <= 0 and cur_t != prev_t:
                frac = (t_target - prev_t) / (cur_t - prev_t)
                return prev_m[key] + frac * (cur_m[key] - prev_m[key])
            prev_t, prev_m = cur_t, cur_m
        return curve[-1][1][key]

    # ── Échantillonnage régulier par course roue (interpolé sur la branche) ──
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

    # ── Ratio de levier par différences finies ───────────────────────────────
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
        samples.append(KinematicSample(
            wheel_travel=round(r["wheel_travel"], 2),
            shock_stroke=round(r["shock_stroke"], 2),
            shock_length=round(r["shock_length"], 2),
            leverage=round(lev, 3),
            anti_squat=round(r["anti_squat"], 1),
            belt_growth=round(r["belt_growth"], 2),
            axle_x=round(r["axle_x"], 1),
            axle_y=round(r["axle_y"], 1),
            axle_dx=round(r["axle_dx"], 2),
        ))

    total_travel = samples[-1].wheel_travel
    lr_start = samples[0].leverage
    lr_end = samples[-1].leverage
    progressivity = (lr_start - lr_end) / lr_start * 100 if lr_start else 0.0

    # Sag : fraction de la course roue totale
    sag_travel = total_travel * s.sag_percent / 100.0
    sag_idx = min(range(len(samples)),
                  key=lambda k: abs(samples[k].wheel_travel - sag_travel))
    lr_sag = samples[sag_idx].leverage
    as_sag = samples[sag_idx].anti_squat

    belt_growth_max = max(abs(s_.belt_growth) for s_ in samples)
    axle_rearward = max(s_.axle_dx for s_ in samples)
    shock_used = samples[-1].shock_stroke

    msg = ""
    if travel_cap < target_travel - 1:
        msg = (f"La géométrie ne permet que {travel_cap:.0f} mm de course roue "
               f"(cible {target_travel:.0f} mm) avant blocage du four-bar.")
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
        belt_growth_max=round(belt_growth_max, 2),
        axle_path_rearward=round(axle_rearward, 1),
        shock_stroke_used=round(shock_used, 1),
        shock_stroke_spec=round(s.shock_stroke, 1),
        pivots_world={
            "main": list(A), "horst": list(B0),
            "upper_frame": list(D), "upper_ss": list(C0),
            "shock_lower": list(shock_lo0), "shock_upper": list(shock_up),
            "idler": list(idler0), "rear_axle": list(rear_axle0),
        },
    )


def _anti_squat(A, B, D, C, axle, ground_y, chainring, r_cr, r_cog, cog_height,
                front_axle_x):
    """Anti-squat % (entraînement courroie/chaîne) — voir docstring module."""
    # 1. Centre instantané IC : intersection des droites (A,B) et (D,C)
    ic = _line_intersection(A, B, D, C)
    if ic is None:
        return 0.0
    # 2. Ligne de courroie (brin supérieur tendu) : tangente commune haute
    #    plateau→cog. Pour des rayons proches on prend la tangente parallèle
    #    décalée par la normale orientée VERS LE HAUT (brin moteur en traction).
    dx = axle[0] - chainring[0]
    dy = axle[1] - chainring[1]
    dd = math.hypot(dx, dy)
    if dd < 1e-6:
        return 0.0
    nx, ny = -dy / dd, dx / dd
    if ny < 0:                      # forcer la normale vers le haut (brin supérieur)
        nx, ny = -nx, -ny
    p_cr = (chainring[0] + r_cr * nx, chainring[1] + r_cr * ny)
    p_cog = (axle[0] + r_cog * nx, axle[1] + r_cog * ny)
    # 3. IFC = intersection ligne de courroie & droite (axe AR, IC)
    ifc = _line_intersection(p_cr, p_cog, axle, ic)
    if ifc is None:
        ifc = ic
    # 4. Ligne de force = (contact pneu AR, IFC)
    rear_contact = (axle[0], ground_y)
    # Hauteur de la ligne de force à la verticale du contact AV
    front_contact = (front_axle_x, ground_y)
    # intersection de la ligne de force avec la verticale x = front_axle_x
    fx0, fy0 = rear_contact
    fx1, fy1 = ifc
    if abs(fx1 - fx0) < 1e-6:
        return 0.0
    t = (front_contact[0] - fx0) / (fx1 - fx0)
    h_force = fy0 + t * (fy1 - fy0)  # y au-dessus du sol(=ground_y) ? non, monde
    h_above_ground = h_force - ground_y
    if cog_height <= 0:
        return 0.0
    return h_above_ground / cog_height * 100.0
