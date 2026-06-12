"""Presets de configuration (cinématique).

`high_pivot_m620` : point de départ réaliste pour un single-pivot HAUT à galet
sur un mid-drive Bafang M620. Pivot principal et galet placés AU-DESSUS du carter
M620 (cf. calculations/motor.py), galet proche du pivot pour minimiser le belt
growth. Valeurs initiales À AFFINER en simulation — pas une géométrie figée.
"""

from .models.bike import SuspensionConfig, Pivot


def high_pivot_m620() -> SuspensionConfig:
    return SuspensionConfig(
        linkage_type="high_pivot_idler",
        main_pivot=Pivot(x=-15.0, y=105.0),     # haut, légèrement derrière le BB
        idler=Pivot(x=-5.0, y=92.0),            # proche du pivot → belt growth mini
        shock_lower=Pivot(x=-130.0, y=15.0),    # sur le bras (tourne avec l'axe)
        shock_upper=Pivot(x=-15.0, y=205.0),    # sur le cadre (tube de selle)
        use_idler=True,
        idler_dia=32.0,
        rear_travel=160.0,
        shock_stroke=60.0,
        shock_eye_to_eye=205.0,
    )


def high_pivot_emtb_tuned() -> SuspensionConfig:
    """Géométrie high-pivot+galet ACCORDÉE pour l'eMTB DOM (belt + M620, 160 mm),
    issue d'une recherche sur le solveur cross-validé. Cibles atteintes : levier
    3.29→2.70 (prog ~18 %), anti-squat sag ~95 %, pedal kickback ~3.8°, belt growth
    ~4.2 mm (vs 16 mm du placeholder), axe reculé ~6 mm. INDICATIVE — à affiner dans
    l'outil (glisser les pivots, lire les courbes) / valider en bureau d'études."""
    return SuspensionConfig(
        linkage_type="high_pivot_idler",
        main_pivot=Pivot(x=5.0, y=100.0),       # pivot haut (dégage le carter M620)
        idler=Pivot(x=13.0, y=88.0),            # galet juste sous le pivot → belt growth mini
        shock_lower=Pivot(x=-200.0, y=120.0),   # œillet bas sur le bras (bras de levier tangentiel)
        shock_upper=Pivot(x=90.0, y=320.0),     # œillet haut sur le triangle avant
        use_idler=True,
        idler_dia=32.0,
        rear_travel=160.0,
        shock_stroke=60.0,
        shock_eye_to_eye=230.0,
    )


def kavenz_vhp_style() -> SuspensionConfig:
    """Façon KAVENZ VHP (Virtual High Pivot) : pivot HAUT + galet collé au pivot
    → chemin d'axe RECULÉ (franchissement) avec belt growth ~0 et pedal kickback
    quasi nul (la signature Kavenz, cf. knowledge/docs Kavenz VHP12-18). Métriques
    (solveur cross-validé) : axe reculé ~20 mm, kickback ~1.7°, belt growth ~1.8 mm,
    AS sag ~88 %, levier 3.30→2.93. INDICATIVE — affiner dans l'outil / bureau d'études.
    (Le vrai VHP est un 4-barres à pivot VIRTUEL haut ; ici single-pivot haut + galet
    qui reproduit le COMPORTEMENT ; passer en four_bar_horst pour un IC mobile.)"""
    return SuspensionConfig(
        linkage_type="high_pivot_idler",
        main_pivot=Pivot(x=50.0, y=170.0),      # pivot TRÈS haut → axe reculé marqué
        idler=Pivot(x=66.0, y=166.0),           # galet AU pivot → belt growth ~0, kickback ~0
        shock_lower=Pivot(x=-230.0, y=110.0),
        shock_upper=Pivot(x=50.0, y=370.0),
        use_idler=True,
        idler_dia=34.0,
        rear_travel=160.0,
        shock_stroke=60.0,
        shock_eye_to_eye=230.0,
    )


PRESETS = {
    "high_pivot_m620": high_pivot_m620,
    "high_pivot_emtb_tuned": high_pivot_emtb_tuned,
    "kavenz_vhp_style": kavenz_vhp_style,
}
