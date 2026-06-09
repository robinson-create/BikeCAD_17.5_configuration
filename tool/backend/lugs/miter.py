"""Utilitaires de coupe pour jonctions tubulaires.

Pour un cadre collé en lug, les abouts de tube sont en général droits (insérés
dans la douille). Ces fonctions servent aux cas soudés/coupés et à dimensionner
le plan d'about d'une douille.
"""

import math


def miter_angle(axis_a_deg: float, axis_b_deg: float) -> float:
    """Angle de coupe d'onglet (°) pour abouter le tube A contre le tube B.

    L'about du tube A est coupé selon la bissectrice de l'angle entre les deux
    axes : la coupe fait `included/2` avec l'axe du tube A, où `included` est
    l'angle inclus entre A et B.
    """
    d = abs((axis_a_deg - axis_b_deg) % 360.0)
    included = min(d, 360.0 - d)
    return round(included / 2.0, 2)


def saddle_depth(tube_od: float, mating_od: float) -> float:
    """Profondeur de la selle (coping) quand le tube de Ø `tube_od` s'aboute sur
    un tube de Ø `mating_od` à 90°. Approx. = différence rayon/flèche d'arc."""
    r = mating_od / 2.0
    half = min(tube_od / 2.0, r)
    return round(r - math.sqrt(max(r * r - half * half, 0.0)), 2)
