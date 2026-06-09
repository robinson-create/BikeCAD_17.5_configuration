"""Dispatcher cinématique — DOM Engineering Bike Tool.

Convention monde : BB = (0,0), x = avant (+), y = haut (+), mm.

`solve_kinematics(bike)` route vers la topologie `bike.suspension.linkage_type` :
  - four_bar_horst   → layouts.four_bar     (Horst Link, 4 pivots)
  - high_pivot_idler → layouts.high_pivot   (single-pivot haut + galet fixe)

Chaque layout produit un balayage d'états (topout → compression) ; toute la
métrologie partagée (levier, anti-squat, belt growth, pedal kickback,
échantillonnage, synthèse) vit dans `layouts.common.build_result`.
"""

from ..models.bike import BikeDesign, KinematicsResult
from .layouts import common
from .layouts.four_bar import solve_four_bar
from .layouts.high_pivot import solve_high_pivot
from .layouts.generic import solve_four_bar_generic
from .motor import motor_envelope_world, clearance_check


_SOLVERS = {
    "four_bar_horst": solve_four_bar,
    "high_pivot_idler": solve_high_pivot,
    "four_bar_generic": solve_four_bar_generic,
}


def solve_kinematics(bike: BikeDesign) -> KinematicsResult:
    s = bike.suspension
    if not s.enabled:
        return KinematicsResult(ok=False, message="Cadre rigide (suspension désactivée).")

    solver = _SOLVERS.get(s.linkage_type)
    if solver is None:
        return KinematicsResult(
            ok=False, message=f"Topologie inconnue : {s.linkage_type}")

    result = solver(bike)
    if isinstance(result, KinematicsResult):   # échec remonté par le layout
        return result
    states, pivots_world = result
    res = common.build_result(bike, states, pivots_world)

    # Dégagement carter moteur : hardpoints (positions de conception) hors carter
    poly = motor_envelope_world(bike.drivetrain)
    if poly is not None and res.ok:
        hardpoints = {
            "pivot principal": (s.main_pivot.x, s.main_pivot.y),
            "amorto bas":      (s.shock_lower.x, s.shock_lower.y),
            "amorto haut":     (s.shock_upper.x, s.shock_upper.y),
        }
        if s.use_idler:
            hardpoints["galet"] = (s.idler.x, s.idler.y)
        if s.linkage_type == "four_bar_horst":
            hardpoints["pivot Horst"] = (s.horst_pivot.x, s.horst_pivot.y)
            hardpoints["rocker/cadre"] = (s.upper_frame_pivot.x, s.upper_frame_pivot.y)
            hardpoints["rocker/hauban"] = (s.upper_ss_pivot.x, s.upper_ss_pivot.y)
        collisions = clearance_check(hardpoints, poly)
        res.motor_collisions = collisions
        res.motor_clearance_ok = not collisions
        if collisions:
            warn = f"Collision carter moteur : {', '.join(collisions)} dans le M620."
            res.message = (res.message + " " + warn).strip()
    return res
