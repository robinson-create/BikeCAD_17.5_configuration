"""Analyses dérivées : sag, état en compression, axes/chemin de roue.

S'appuie sur `geometry.calculate()` et `kinematics.solve_kinematics()` — donc
indépendant de la topologie. Utilisé par l'assistant (outils) et exposable en REST.

Convention monde : BB=(0,0), x=avant +, y=haut +, mm.
"""

from ..models.bike import BikeDesign
from .geometry import calculate
from .kinematics import solve_kinematics

G = 9.81  # m/s²


def _interp_sample(samples, target_travel):
    """Interpole les métriques d'un KinematicSample à une course roue donnée."""
    keys = ("shock_stroke", "shock_length", "leverage", "anti_squat",
            "pedal_kickback", "belt_growth", "axle_x", "axle_y", "axle_dx")
    if target_travel <= samples[0].wheel_travel:
        s = samples[0]
        return {k: getattr(s, k) for k in keys}
    for a, b in zip(samples, samples[1:]):
        if a.wheel_travel <= target_travel <= b.wheel_travel and b.wheel_travel != a.wheel_travel:
            fr = (target_travel - a.wheel_travel) / (b.wheel_travel - a.wheel_travel)
            return {k: round(getattr(a, k) + fr * (getattr(b, k) - getattr(a, k)), 3) for k in keys}
    s = samples[-1]
    return {k: getattr(s, k) for k in keys}


def wheel_axles(bike: BikeDesign) -> dict:
    """Axes AV/AR, contacts au sol, empattement + chemin d'axe AR (cinématique)."""
    c = calculate(bike)
    out = {
        "rear_axle": [round(c.rear_axle.x, 1), round(c.rear_axle.y, 1)],
        "front_axle": [round(c.front_axle.x, 1), round(c.front_axle.y, 1)],
        "rear_contact": [round(c.rear_axle.x, 1), round(c.ground_level, 1)],
        "front_contact": [round(c.front_axle.x, 1), round(c.ground_level, 1)],
        "ground_level": round(c.ground_level, 1),
        "wheelbase": round(c.wheelbase, 1),
        "bb_height": round(c.bb_height, 1),
    }
    k = solve_kinematics(bike)
    if k.ok:
        out["rear_axle_path"] = [
            {"travel": s.wheel_travel, "x": s.axle_x, "y": s.axle_y, "rearward": s.axle_dx}
            for s in k.samples
        ]
        out["axle_path_rearward_max"] = k.axle_path_rearward
    return out


def compression_state(bike: BikeDesign, at_pct: float | None = None,
                      at_mm: float | None = None, at_sag: bool = False) -> dict:
    """État de la suspension à une compression donnée (mm, % de course, ou sag)."""
    k = solve_kinematics(bike)
    if not k.ok:
        return {"ok": False, "message": k.message}
    travel = k.total_travel
    if at_sag or (at_pct is None and at_mm is None):
        target = travel * bike.suspension.sag_percent / 100.0
        label = f"sag ({bike.suspension.sag_percent}%)"
    elif at_mm is not None:
        target = float(at_mm); label = f"{at_mm} mm"
    else:
        target = travel * float(at_pct) / 100.0; label = f"{at_pct}%"
    target = max(0.0, min(target, travel))
    m = _interp_sample(k.samples, target)
    return {
        "ok": True,
        "requested": label,
        "wheel_travel_mm": round(target, 1),
        "travel_pct": round(target / travel * 100, 1) if travel else 0.0,
        "total_travel_mm": travel,
        "leverage": m["leverage"],
        "shock_stroke_mm": m["shock_stroke"],
        "anti_squat_pct": m["anti_squat"],
        "belt_growth_mm": m["belt_growth"],
        "pedal_kickback_deg": m["pedal_kickback"],
        "axle": [m["axle_x"], m["axle_y"]],
        "axle_rearward_mm": m["axle_dx"],
    }


def compute_sag(bike: BikeDesign, rider_mass_kg: float = 90.0,
                bike_mass_kg: float = 25.0, rear_bias_pct: float = 60.0,
                spring_rate_n_per_mm: float | None = None,
                target_sag_pct: float | None = None) -> dict:
    """Sag arrière statique (ressort linéaire / coil).

    Physique (travail virtuel) : force amorto = force roue × LR (LR = course
    roue / course amorto). Coil linéaire de raideur k : course amorto = F_amorto/k,
    sag roue = course amorto × LR = F_roue × LR² / k.
    APPROXIMATION : LR pris constant = levier au sag ; charge sprung = (pilote +
    vélo) × g × bias arrière. Air = non linéaire → fournir une raideur effective.
    """
    k = solve_kinematics(bike)
    if not k.ok:
        return {"ok": False, "message": k.message}
    LR = k.leverage_sag
    travel = k.total_travel
    f_wheel = (rider_mass_kg + bike_mass_kg) * G * (rear_bias_pct / 100.0)
    f_shock = f_wheel * LR
    res = {
        "ok": True,
        "leverage_sag": LR,
        "total_travel_mm": travel,
        "rear_wheel_load_N": round(f_wheel, 1),
        "shock_force_N": round(f_shock, 1),
        "fork_static_load_N": round((rider_mass_kg + bike_mass_kg) * G * (1 - rear_bias_pct / 100.0), 1),
        "assumptions": {"rider_mass_kg": rider_mass_kg, "bike_mass_kg": bike_mass_kg,
                        "rear_bias_pct": rear_bias_pct},
        "method": "coil linéaire, LR constant au sag — indicatif (air = non linéaire)",
    }
    if target_sag_pct is not None and travel > 0:
        wheel_sag = travel * target_sag_pct / 100.0
        res["target_sag_pct"] = target_sag_pct
        res["target_wheel_sag_mm"] = round(wheel_sag, 1)
        res["required_spring_rate_N_per_mm"] = round(f_wheel * LR * LR / wheel_sag, 1) if wheel_sag else None
        res["required_spring_rate_lbs_per_in"] = (
            round(f_wheel * LR * LR / wheel_sag / 0.1751, 0) if wheel_sag else None)
    if spring_rate_n_per_mm:
        wheel_sag = f_wheel * LR * LR / spring_rate_n_per_mm
        res["spring_rate_N_per_mm"] = spring_rate_n_per_mm
        res["wheel_sag_mm"] = round(wheel_sag, 1)
        res["sag_pct"] = round(wheel_sag / travel * 100, 1) if travel else 0.0
        res["shock_stroke_at_sag_mm"] = round(wheel_sag / LR, 1) if LR else 0.0
    return res
