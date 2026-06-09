"""Topologie four-bar (Horst Link).

    A = main_pivot        (cadre, sol)        ─┐
    B = horst_pivot       (bout des bases)     │  bielle AB = bases (chainstay)
    C = upper_ss_pivot    (bout du rocker)     │  bielle BC = haubans (coupler)
    D = upper_frame_pivot (cadre, sol)        ─┘  bielle CD = rocker

  • L'axe AR est rigide avec le coupler BC.
  • Le galet (idler) est rigide avec les bases AB.
  • L'amortisseur : point bas sur AB (ou rocker), point haut fixe sur le cadre.

On pilote la position en faisant tourner les bases (angle theta) depuis la
position de référence (topout) vers la compression, et on résout le four-bar
par intersection de cercles à chaque pas. La métrologie (levier, AS, belt
growth, kickback, échantillonnage) est dans `common.build_result`.
"""

import math
from . import common
from ...models.bike import BikeDesign, KinematicsResult


def solve_four_bar(bike: BikeDesign):
    """Retourne (states, pivots_world) ou un KinematicsResult d'échec."""
    s = bike.suspension
    f = bike.frame

    # ── Points fixes (cadre) ────────────────────────────────────────────────
    A = (s.main_pivot.x, s.main_pivot.y)
    D = (s.upper_frame_pivot.x, s.upper_frame_pivot.y)
    B0 = (s.horst_pivot.x, s.horst_pivot.y)
    C0 = (s.upper_ss_pivot.x, s.upper_ss_pivot.y)
    shock_up = (s.shock_upper.x, s.shock_upper.y)
    shock_lo0 = (s.shock_lower.x, s.shock_lower.y)
    idler0 = (s.idler.x, s.idler.y)

    L_AB = common.dist(A, B0)
    L_BC = common.dist(B0, C0)
    L_CD = common.dist(D, C0)
    if min(L_AB, L_BC, L_CD) < 1e-3:
        return KinematicsResult(ok=False, message="Pivots dégénérés (longueur nulle).")

    theta0 = math.atan2(B0[1] - A[1], B0[0] - A[0])

    # ── Géométrie roue / sol / transmission ─────────────────────────────────
    wheel_r_r = f.wheel_r / 2.0
    bb_height = wheel_r_r - f.bb_drop
    ground_y = -bb_height
    rear_axle0 = (-math.sqrt(max(f.cs ** 2 - f.bb_drop ** 2, 0.0)), f.bb_drop)

    chainring = (0.0, 0.0)
    r_cr = s.chainring_teeth * s.belt_pitch / (2 * math.pi)
    r_cog = s.cog_teeth * s.belt_pitch / (2 * math.pi)
    r_idler = s.idler_dia / 2.0

    prev_C = [C0]

    def solve_at_theta(theta):
        B = (A[0] + L_AB * math.cos(theta), A[1] + L_AB * math.sin(theta))
        pts = common.circle_intersections(B, L_BC, D, L_CD)
        if not pts:
            return None
        C = min(pts, key=lambda p: common.dist(p, prev_C[0]))
        prev_C[0] = C
        return B, C

    def state_at(theta):
        """Retourne (B, C, axle, idler, shock_len) ou None."""
        sol = solve_at_theta(theta)
        if sol is None:
            return None
        B, C = sol
        tf = common.coupler_transform(B0, C0, B, C)
        axle = tf(rear_axle0)
        idler = common.rotate_about(idler0, A, theta - theta0)
        if s.shock_on_chainstay:
            lo = common.rotate_about(shock_lo0, A, theta - theta0)
        else:
            lo = tf(shock_lo0)
        shock_len = common.dist(lo, shock_up)
        return B, C, axle, idler, shock_len, lo

    # ── Cadrage du sens de compression ───────────────────────────────────────
    step = math.radians(0.25)
    prev_C[0] = C0
    s_up = state_at(theta0 - step)
    s_dn = state_at(theta0 + step)
    prev_C[0] = C0
    base = state_at(theta0)
    if base is None:
        return KinematicsResult(ok=False, message="Position de référence non résolue.")
    ay0 = base[2][1]
    dir_compress = -1
    if s_up and s_dn:
        if s_up[2][1] > ay0 and s_dn[2][1] <= ay0:
            dir_compress = -1
        elif s_dn[2][1] > ay0 and s_up[2][1] <= ay0:
            dir_compress = +1
    elif s_dn and not s_up:
        dir_compress = +1

    # ── Balayage topout → compression ────────────────────────────────────────
    target_travel = s.rear_travel
    prev_C[0] = C0
    th_cur = theta0
    last = state_at(th_cur)
    axle_top = last[2]
    sweep = [last]
    for _ in range(2000):
        th_cur += dir_compress * step
        st = state_at(th_cur)
        if st is None:
            break
        sweep.append(st)
        if st[2][1] - axle_top[1] > target_travel + 5:
            break

    if len(sweep) < 5:
        return KinematicsResult(ok=False, message="Plage de mouvement four-bar trop courte.")

    # ── États : axle / idler / shock_len / anti_squat (IC du four-bar) ───────
    states = []
    for B, C, axle, idler, shock_len, lo in sweep:
        ic = common.line_intersection(A, B, D, C)
        # Brin moteur = dernier segment de courroie : galet→pignon si galet
        # dans le trajet, sinon plateau→pignon (cf. BiKinematics chainline[-2:]).
        drive_pt = idler if s.use_idler else chainring
        r_drive = r_idler if s.use_idler else r_cr
        as_pct = common.anti_squat(
            ic, axle, ground_y, drive_pt, r_drive, r_cog, s.cog_height,
            front_axle_x=f.fcd,
        )
        states.append({
            "axle": axle, "idler": idler,
            "shock_len": shock_len, "anti_squat": as_pct,
            "draw": {
                "links": [[list(A), list(B)], [list(B), list(C)], [list(C), list(D)]],
                "shock": [list(lo), list(shock_up)],
                "axle": list(axle),
                "idler": list(idler) if s.use_idler else None,
            },
        })

    pivots_world = {
        "main": list(A), "horst": list(B0),
        "upper_frame": list(D), "upper_ss": list(C0),
        "shock_lower": list(shock_lo0), "shock_upper": list(shock_up),
        "idler": list(idler0), "rear_axle": list(rear_axle0),
    }
    return states, pivots_world
