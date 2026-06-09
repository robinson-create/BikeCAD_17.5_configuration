"""Topologies de suspension — un module par cinématique.

Chaque layout expose `solve_<nom>(bike) -> list[State] | KinematicsResult`.
Le module `common` fournit les primitives géométriques partagées et
`build_result(bike, states)` qui transforme une liste d'états (balayage
topout → compression) en `KinematicsResult` (échantillonnage, levier,
progressivité, belt growth, pedal kickback, synthèse).

Convention d'un État (dict) produit par un layout, ordonné du topout (index 0)
vers la compression :
    {
        "axle":      (x, y),   # axe AR, coordonnées monde (mm)
        "idler":     (x, y),   # galet de renvoi courroie (mm)
        "shock_len": float,    # longueur amortisseur courante (mm)
        "anti_squat":float,    # anti-squat % (calculé par le layout, IC propre)
    }
"""
