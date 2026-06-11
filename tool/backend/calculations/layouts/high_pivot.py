"""Topologie high-pivot single-idler (Forbidden / Deviate-like) — cas M620.

  • Bras arrière RIGIDE pivotant autour d'un pivot principal HAUT (main_pivot),
    placé au-dessus / en avant du BB. L'axe AR décrit un arc de cercle autour de
    ce pivot → chemin de roue franchement reculé (rearward axle path).
  • Galet de renvoi (idler) FIXE sur le cadre, proche du pivot principal :
    le brin plateau→galet est constant, et le brin galet→pignon ne varie quasi
    pas tant que le galet est proche du pivot → belt growth ≈ 0 (clé du gearbox
    M620 + courroie Gates, qui ne tolère pas de variation de tension).
  • Amortisseur : point bas sur le bras (tourne avec l'axe), point haut au cadre.

Anti-squat : le centre instantané de la roue AR p/r au cadre EST le pivot
principal (single-pivot). Le brin moteur pris en compte est galet→pignon.

Pilotage : rotation du bras autour du pivot, du topout vers la compression.
Métrologie commune dans `common.build_result`.
"""

import math
from . import common
from ...models.bike import BikeDesign, KinematicsResult


def solve_high_pivot(bike: BikeDesign):
    """Retourne (states, pivots_world) ou un KinematicsResult d'échec."""
    s = bike.suspension
    f = bike.frame

    P = (s.main_pivot.x, s.main_pivot.y)        # pivot principal (haut, cadre)
    shock_up = (s.shock_upper.x, s.shock_upper.y)
    shock_lo0 = (s.shock_lower.x, s.shock_lower.y)
    idler0 = (s.idler.x, s.idler.y)             # galet FIXE sur le cadre

    # ── Géométrie roue / sol / transmission ─────────────────────────────────
    wheel_r_r = f.wheel_r / 2.0
    bb_height = wheel_r_r - f.bb_drop
    ground_y = -bb_height
    rear_axle0 = (-math.sqrt(max(f.cs ** 2 - f.bb_drop ** 2, 0.0)), f.bb_drop)

    L_arm = common.dist(P, rear_axle0)
    L_shock_arm = common.dist(P, shock_lo0)
    if L_arm < 1e-3:
        return KinematicsResult(ok=False, message="Pivot principal confondu avec l'axe AR.")
    if L_shock_arm < 1e-3:
        return KinematicsResult(ok=False, message="Ancrage bas amortisseur sur le pivot.")

    chainring = (0.0, 0.0)
    r_cr = s.chainring_teeth * s.belt_pitch / (2 * math.pi)
    r_cog = s.cog_teeth * s.belt_pitch / (2 * math.pi)
    r_idler = s.idler_dia / 2.0
    # Brin moteur : galet→pignon si galet actif, sinon plateau→pignon
    drive_pt = idler0 if s.use_idler else chainring
    r_drive = r_idler if s.use_idler else r_cr

    def state_at(phi):
        """Bras tourné de phi autour de P. Retourne (axle, idler, shock_len, lo)."""
        axle = common.rotate_about(rear_axle0, P, phi)
        lo = common.rotate_about(shock_lo0, P, phi)   # point bas sur le bras
        shock_len = common.dist(lo, shock_up)
        return axle, idler0, shock_len, lo           # galet fixe (cadre)

    # ── Sens de compression : phi qui fait MONTER l'axe ──────────────────────
    step = math.radians(0.25)
    ay0 = state_at(0.0)[0][1]
    ay_up = state_at(+step)[0][1]
    dir_compress = +1 if ay_up > ay0 else -1

    # ── Balayage topout → compression ────────────────────────────────────────
    target_travel = s.rear_travel
    axle_top = state_at(0.0)[0]
    sweep = [state_at(0.0)]
    phi = 0.0
    for _ in range(2000):
        phi += dir_compress * step
        st = state_at(phi)
        sweep.append(st)
        if st[0][1] - axle_top[1] > target_travel + 5:
            break

    if len(sweep) < 5:
        return KinematicsResult(ok=False, message="Plage de mouvement high-pivot trop courte.")

    # ── États : IC = pivot principal (single-pivot) ──────────────────────────
    states = []
    for axle, idler, shock_len, lo in sweep:
        as_pct = common.anti_squat(
            P, axle, ground_y, drive_pt, r_drive, r_cog, s.cog_height,
            front_axle_x=f.fcd,
        )
        ar_pct = common.anti_rise(P, axle, ground_y, s.cog_height, front_axle_x=f.fcd)
        states.append({
            "axle": axle, "idler": idler,
            "shock_len": shock_len, "anti_squat": as_pct, "anti_rise": ar_pct,
            "draw": {
                "links": [[list(P), list(axle)]],   # bras rigide pivot→axe
                "shock": [list(lo), list(shock_up)],
                "axle": list(axle),
                "idler": list(idler) if s.use_idler else None,
            },
        })

    pivots_world = {
        "main": list(P),
        "shock_lower": list(shock_lo0), "shock_upper": list(shock_up),
        "idler": list(idler0), "rear_axle": list(rear_axle0),
    }
    return states, pivots_world
