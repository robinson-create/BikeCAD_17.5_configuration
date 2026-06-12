"""Solveur cinématique GÉNÉRIQUE par contraintes (planar, pur Python).

Esprit open-kinematics, mais sans numpy/scipy : un mécanisme plan est un
ensemble de points (certains fixes au cadre, d'autres libres) reliés par des
liaisons rigides (contraintes de distance). Le mécanisme a 1 DDL ; on ajoute UNE
contrainte motrice (driver) → système déterminé, résolu par Newton-Raphson à
chaque pas de course.

Pourquoi générique : ajouter une topologie (6-bar, amortisseur piloté par une
biellette intermédiaire, galet sur un lien mobile…) = ajouter des points et des
contraintes de distance, SANS écrire de nouvelle trigonométrie. La version
intersection-de-cercles de `four_bar.py` ne sait faire que le 4-bar ; ici le
même noyau résout n'importe quel assemblage de liens rigides.

Validation : `solve_four_bar_generic` reproduit `four_bar.solve_four_bar` à la
tolérance machine (voir tests/e2e_test.py section 6).
"""

import math
from . import common
from ...models.bike import BikeDesign, KinematicsResult


# ── Algèbre linéaire dense minimale (petits systèmes) ───────────────────────

def _solve_linear(A, b):
    """Résout A x = b par élimination de Gauss avec pivot partiel. None si singulier."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            return None
        M[col], M[piv] = M[piv], M[col]
        pv = M[col][col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / pv
            if f != 0.0:
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


# ── Newton-Raphson sur contraintes de distance + résidus moteur ─────────────

def solve_constraints(points, free, links, extra_residuals,
                      max_iter=60, tol=1e-11):
    """Résout les positions des points `free` (noms) satisfaisant :
      - `links` : liste (nameA, nameB, longueur) → |A-B| = longueur ;
      - `extra_residuals` : liste de fn(points)->float (contraintes motrices),
        annulées à la solution.

    `points` : dict nom -> [x, y] (modifié en place ; warm-start = état courant).
    Le nombre total de contraintes doit égaler 2*len(free). Retourne True/False.
    """
    idx = {name: k for k, name in enumerate(free)}
    n = 2 * len(free)

    def residuals():
        res = []
        for a, b, L in links:
            pa, pb = points[a], points[b]
            res.append(math.hypot(pa[0] - pb[0], pa[1] - pb[1]) - L)
        for fn in extra_residuals:
            res.append(fn(points))
        return res

    if len(links) + len(extra_residuals) != n:
        raise ValueError(
            f"Système mal posé : {len(links)+len(extra_residuals)} contraintes "
            f"pour {n} inconnues.")

    for _ in range(max_iter):
        r = residuals()
        if max(abs(v) for v in r) < tol:
            return True
        # Jacobien par différences finies (colonnes = coords libres)
        J = [[0.0] * n for _ in range(n)]
        for name in free:
            for axis in (0, 1):
                col = 2 * idx[name] + axis
                h = 1e-7 * (1.0 + abs(points[name][axis]))
                points[name][axis] += h
                rp = residuals()
                points[name][axis] -= h
                for row in range(n):
                    J[row][col] = (rp[row] - r[row]) / h
        dx = _solve_linear(J, [-v for v in r])
        if dx is None:
            return False
        for name in free:
            points[name][0] += dx[2 * idx[name]]
            points[name][1] += dx[2 * idx[name] + 1]
    return max(abs(v) for v in residuals()) < 1e-6


# ── Layout : four-bar résolu par le noyau générique ─────────────────────────

def solve_four_bar_generic(bike: BikeDesign):
    """4-bar (Horst) résolu par contraintes — démontre/valide le noyau générique.
    Retourne (states, pivots_world) ou un KinematicsResult d'échec."""
    s = bike.suspension
    f = bike.frame

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

    wheel_r_r = f.wheel_r / 2.0
    ground_y = -(wheel_r_r - f.bb_drop)
    rear_axle0 = (-math.sqrt(max(f.cs ** 2 - f.bb_drop ** 2, 0.0)), f.bb_drop)

    chainring = (0.0, 0.0)
    r_cr = s.chainring_teeth * s.belt_pitch / (2 * math.pi)
    r_cog = s.cog_teeth * s.belt_pitch / (2 * math.pi)
    r_idler = s.idler_dia / 2.0

    # Points : A, D fixes (cadre) ; B, C libres. Liaisons rigides AB, BC, CD.
    # Driver : angle de (A→B) imposé = theta (résidu = composante perpendiculaire).
    links = [("A", "B", L_AB), ("B", "C", L_BC), ("C", "D", L_CD)]

    def state_at(points, theta):
        def angle_res(p):
            bx, by = p["B"]
            return (bx - A[0]) * math.sin(theta) - (by - A[1]) * math.cos(theta)
        ok = solve_constraints(points, ["B", "C"], links, [angle_res])
        if not ok:
            return None
        B = tuple(points["B"]); C = tuple(points["C"])
        tf = common.coupler_transform(B0, C0, B, C)
        axle = tf(rear_axle0)
        idler = common.rotate_about(idler0, A, theta - theta0)
        if s.shock_on_chainstay:
            lo = common.rotate_about(shock_lo0, A, theta - theta0)
        else:
            lo = tf(shock_lo0)
        shock_len = common.dist(lo, shock_up)
        ic = common.line_intersection(A, B, D, C)
        return B, C, axle, idler, shock_len, ic, lo

    # Sens de compression (theta qui fait monter l'axe)
    step = math.radians(0.25)
    pts = {"A": list(A), "B": list(B0), "C": list(C0), "D": list(D)}
    base = state_at(pts, theta0)
    if base is None:
        return KinematicsResult(ok=False, message="Position de référence non résolue.")
    ay0 = base[2][1]
    pts_up = {"A": list(A), "B": list(B0), "C": list(C0), "D": list(D)}
    up = state_at(pts_up, theta0 - step)
    dir_compress = -1 if (up and up[2][1] > ay0) else +1

    # Balayage topout → compression (warm-start continu)
    target_travel = s.rear_travel
    pts = {"A": list(A), "B": list(B0), "C": list(C0), "D": list(D)}
    first = state_at(pts, theta0)
    axle_top = first[2]
    sweep = [first]
    th = theta0
    for _ in range(2000):
        th += dir_compress * step
        st = state_at(pts, th)
        if st is None:
            break
        sweep.append(st)
        if st[2][1] - axle_top[1] > target_travel + 5:
            break

    if len(sweep) < 5:
        return KinematicsResult(ok=False, message="Plage de mouvement trop courte.")

    states = []
    for B, C, axle, idler, shock_len, ic, lo in sweep:
        drive_pt = idler if s.use_idler else chainring
        r_drive = r_idler if s.use_idler else r_cr
        as_pct = common.anti_squat(ic, axle, ground_y, drive_pt, r_drive, r_cog,
                                   s.cog_height, front_axle_x=f.fcd, wheel_radius=f.wheel_r / 2)
        ar_pct = common.anti_rise(ic, axle, ground_y, s.cog_height, front_axle_x=f.fcd)
        states.append({"axle": axle, "idler": idler,
                       "shock_len": shock_len, "anti_squat": as_pct, "anti_rise": ar_pct,
                       "draw": {
                           "links": [[list(A), list(B)], [list(B), list(C)], [list(C), list(D)]],
                           "shock": [list(lo), list(shock_up)],
                           "axle": list(axle),
                           "idler": list(idler) if s.use_idler else None,
                       }})

    pivots_world = {
        "main": list(A), "horst": list(B0),
        "upper_frame": list(D), "upper_ss": list(C0),
        "shock_lower": list(shock_lo0), "shock_upper": list(shock_up),
        "idler": list(idler0), "rear_axle": list(rear_axle0),
    }
    return states, pivots_world
