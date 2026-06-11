"""Batterie e-bike dans le triangle avant — enveloppe + test d'intégration.

Repère monde : BB=(0,0), x avant +, y haut +, mm.

Le pack est posé le long du tube diagonal (BB → couronne), décalé d'un jeu, et
s'étend vers l'intérieur du triangle (vers le tube de selle). On vérifie :
  • qu'il tient dans le triangle avant (BB, haut du tube de direction, haut du
    tube de selle) ;
  • qu'il dégage le carter moteur (cf. calculations/motor.py) ;
  • qu'il ne traverse pas le tube de selle / le tube de direction.

Méthode volontairement géométrique 2D (vue de côté) — comme l'enveloppe moteur,
c'est une aide au pré-dimensionnement, pas une validation packaging 3D.
"""

import math
from .motor import motor_envelope_world, point_in_polygon


def _seg_intersect(p1, p2, p3, p4):
    """True si les segments [p1,p2] et [p3,p4] se croisent."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and \
           (ccw(p1, p2, p3) != ccw(p1, p2, p4))


def battery_polygon_world(bike, calc):
    """4 coins du pack en coords monde, ou None si désactivé."""
    bat = bike.battery
    if not bat.enabled:
        return None

    bb = (calc.bb.x, calc.bb.y)
    crown = (calc.crown.x, calc.crown.y)

    # Direction du tube diagonal (BB → couronne) + normale "vers l'intérieur" (haut)
    dx, dy = crown[0] - bb[0], crown[1] - bb[1]
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return None
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux            # normale ; tournée vers le haut du triangle
    if ny < 0:
        nx, ny = -nx, -ny

    # Décalage mesuré depuis la SURFACE du tube diagonal (pas son axe) → le pack
    # ne traverse plus le tube. Externe : posé sur la surface + jeu. Intégrée :
    # centrée sur l'axe (le tube diagonal EST le logement, surdimensionné).
    dt_r = getattr(bike.frame, "down_tube_d", 50.0) / 2.0
    base = (-bat.height * 0.4) if bat.in_downtube else (dt_r + bat.standoff)
    sx = bb[0] + ux * bat.mount_offset + nx * base
    sy = bb[1] + uy * bat.mount_offset + ny * base
    ex = sx + ux * bat.length
    ey = sy + uy * bat.length
    # 4 coins : base (le long du tube) puis +height vers l'intérieur
    return [
        (sx, sy),
        (ex, ey),
        (ex + nx * bat.height, ey + ny * bat.height),
        (sx + nx * bat.height, sy + ny * bat.height),
    ]


def compute_battery(bike, calc):
    """Retourne un BatteryResult (importé tardivement pour éviter les cycles)."""
    from ..models.bike import BatteryResult
    bat = bike.battery
    if not bat.enabled:
        return BatteryResult(ok=True, enabled=False)

    poly = battery_polygon_world(bike, calc)
    if poly is None:
        return BatteryResult(ok=False, enabled=True, notes=["Pack non plaçable."])

    notes = []

    # Intérieur du triangle avant : quad BB → couronne → haut direction → haut selle
    # (borné par tube diagonal, tube de direction, tube horizontal, tube de selle).
    interior = [(calc.bb.x, calc.bb.y),
                (calc.crown.x, calc.crown.y),
                (calc.ht_top.x, calc.ht_top.y),
                (calc.seat_tube_top.x, calc.seat_tube_top.y)]
    fits = all(point_in_polygon(c, interior) for c in poly)
    if not fits:
        notes.append("Le pack dépasse du triangle avant — réduire longueur/hauteur "
                     "ou rapprocher du BB.")

    # Dégagement carter moteur
    motor_poly = motor_envelope_world(bike.drivetrain)
    clears_motor = True
    if motor_poly:
        if any(point_in_polygon(c, motor_poly) for c in poly) or \
           any(point_in_polygon(m, poly) for m in motor_poly):
            clears_motor = False
            notes.append("Collision batterie ↔ carter moteur — augmenter le "
                         "décalage depuis le BB.")

    # Ne traverse pas tube de selle (BB→haut selle) ni tube de direction (couronne→haut)
    edges = [c for c in zip(poly, poly[1:] + poly[:1])]
    seat_tube = ((calc.bb.x, calc.bb.y), (calc.seat_tube_top.x, calc.seat_tube_top.y))
    head_tube = ((calc.crown.x, calc.crown.y), (calc.ht_top.x, calc.ht_top.y))
    clears_tubes = True
    for a, b in edges:
        if _seg_intersect(a, b, *seat_tube) or _seg_intersect(a, b, *head_tube):
            clears_tubes = False
            break
    if not clears_tubes:
        notes.append("Le pack croise un tube du cadre.")

    vol_l = bat.length * bat.height * bat.width / 1e6
    # densité énergétique pack 21700 ~ 0.25–0.30 Wh/cm³ ; on prend 0.27
    est_wh = vol_l * 1000 * 0.27
    # Avertissement si la capacité demandée dépasse ce que le volume peut contenir
    if bat.capacity_wh > est_wh * 1.05:
        notes.append(f"Capacité demandée ({bat.capacity_wh:.0f} Wh) > volume du pack "
                     f"(~{est_wh:.0f} Wh à 0,27 Wh/cm³) — agrandir le pack ou réduire la capacité.")

    # ── Calculateur alimentation / autonomie ────────────────────────────────────
    V = max(1.0, bat.voltage)
    cap_ah = bat.capacity_wh / V
    nom_i = bat.nominal_power_w / V
    peak_i = bat.peak_power_w / V
    c_rate = (peak_i / cap_ah) if cap_ah > 0 else 0.0
    runtime_nom_h = (bat.capacity_wh / bat.nominal_power_w) if bat.nominal_power_w > 0 else 0.0
    runtime_peak_min = (bat.capacity_wh / bat.peak_power_w * 60.0) if bat.peak_power_w > 0 else 0.0
    # Scénarios de conso (Wh/km) : éco / rando / boost, calés autour de la conso de réf.
    cref = max(1.0, bat.consumption_whkm)
    usable = bat.capacity_wh * 0.92      # ~8 % réserve / rendement BMS
    scenarios = [("Éco", cref * 0.62), ("Rando", cref), ("Boost", cref * 1.6)]
    autonomy = [{"mode": m, "whkm": round(w, 1), "km": round(usable / w, 1)} for m, w in scenarios]
    autonomy.append({"mode": "Perso", "whkm": round(cref, 1), "km": round(usable / cref, 1)})
    if c_rate > 10:
        notes.append(f"Régime de décharge crête élevé (~{c_rate:.0f}C) — vérifier le BMS / "
                     f"le calibre cellules pour la puissance crête {bat.peak_power_w:.0f} W.")

    return BatteryResult(
        ok=True,
        enabled=True,
        fits_triangle=fits,
        clears_motor=clears_motor,
        clears_tubes=clears_tubes,
        polygon=[list(c) for c in poly],
        volume_l=round(vol_l, 2),
        est_capacity_wh=round(est_wh, 0),
        capacity_ah=round(cap_ah, 1),
        nominal_current_a=round(nom_i, 1),
        peak_current_a=round(peak_i, 1),
        c_rate_peak=round(c_rate, 1),
        runtime_nominal_h=round(runtime_nom_h, 2),
        runtime_peak_min=round(runtime_peak_min, 1),
        autonomy=autonomy,
        notes=notes,
    )
