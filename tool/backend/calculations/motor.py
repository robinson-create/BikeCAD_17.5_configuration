"""Enveloppes de carter moteur + contrôle de dégagement (clearance).

But : empêcher de placer un pivot / galet / ancrage d'amortisseur À L'INTÉRIEUR
du carter moteur. Sur un mid-drive M620 (gros carter), c'est une contrainte
physique forte du placement de la cinématique high-pivot.

Repère LOCAL d'une enveloppe : axe BB (spindle de sortie) = origine,
+x = avant vélo, +y = haut (mm). On l'oriente dans le monde par `GEARBOXangle`
(`drivetrain.motor_angle`) puis on la décale de (motor_x, motor_y).

⚠ Les polygones sont des APPROXIMATIONS dérivées des cotes du manuel revendeur,
à vérifier visuellement (le SVG les dessine). Ils ne prétendent pas au mm près.
"""

import math


# Bafang M620 (MM G510.750/1000/1300.C) — manuel BF-DM-C-MM G510 :
# encombrement latéral 234 × 140.29 mm ; bossages de fixation à R≈78.5 mm @ 61.42°
# et R≈58 mm @ 46° depuis l'axe BB. Spindle (BB) à droite de l'outline, carter
# (logo) qui s'étend vers l'avant-bas, bras de fixation vers l'arrière-haut.
M620_ENVELOPE_LOCAL = [
    (-60.0,  20.0),   # arrière-haut (vers tube de selle)
    (-57.0,  55.0),   # haut du bras de fixation
    (-38.0,  69.0),   # bossage R78.5 @ 61.42° ≈ (37.6, 68.9)
    (40.0,   70.0),   # haut du carter vers l'avant
    (120.0,  60.0),
    (170.0,  10.0),   # nez avant (longueur totale ≈ 60-(-170)=230 ≈ 234)
    (170.0, -20.0),
    (120.0, -55.0),
    (40.0,  -70.0),   # bas avant (hauteur ≈ 70-(-70)=140)
    (-20.0, -68.0),
    (-55.0, -45.0),
    (-62.0, -10.0),
]

# Clé moteur (models.bike.GEARBOX_TYPES) → enveloppe locale
ENVELOPES = {
    "bafang_m620": M620_ENVELOPE_LOCAL,
}


def motor_envelope_world(drivetrain):
    """Polygone du carter en coords monde (BB=origine), ou None si indisponible."""
    if not getattr(drivetrain, "use_motor", False):
        return None
    poly = ENVELOPES.get(drivetrain.motor_key)
    if poly is None:
        return None
    a = math.radians(drivetrain.motor_angle)
    c, s = math.cos(a), math.sin(a)
    ox, oy = drivetrain.motor_x, drivetrain.motor_y
    return [(ox + c * x - s * y, oy + s * x + c * y) for (x, y) in poly]


def point_in_polygon(p, poly):
    """Ray casting. True si le point p=(x,y) est strictement dans le polygone."""
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def clearance_check(points: dict, poly) -> list:
    """points : {nom: (x,y)}. Retourne la liste des noms tombant dans le carter."""
    if poly is None:
        return []
    return [name for name, p in points.items() if point_in_polygon(p, poly)]
