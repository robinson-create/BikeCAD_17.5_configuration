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
    """Géométrie high-pivot+galet ACCORDÉE pour l'eMTB DOM (belt + M620, 160 mm).
    Amortisseur posé DROIT SUR LES TUBES (œillet bas sur la base, œillet haut sur le
    tube de selle) → eyelets EN FACE des trous, pas de patte flottante. Cibles
    (solveur cross-validé) : levier 2.85→2.51 (prog ~12 %), AS sag ~84 %, kickback
    ~2.5°, belt growth ~2.7 mm. INDICATIVE — affiner dans l'outil / bureau d'études."""
    return SuspensionConfig(
        linkage_type="high_pivot_idler",
        main_pivot=Pivot(x=5.0, y=100.0),       # pivot haut (dégage le carter M620)
        idler=Pivot(x=17.0, y=92.0),            # galet juste sous le pivot → belt growth mini
        shock_lower=Pivot(x=-179.0, y=71.0),    # œillet bas SUR la base (bras oscillant)
        shock_upper=Pivot(x=-66.0, y=310.0),    # œillet haut SUR le tube de selle (cadre)
        use_idler=True,
        idler_dia=34.0,
        rear_travel=160.0,
        shock_stroke=60.0,
        shock_eye_to_eye=250.0,
    )


def kavenz_vhp_style() -> SuspensionConfig:
    """Façon KAVENZ VHP (Virtual High Pivot) : pivot HAUT + galet collé au pivot
    → chemin d'axe RECULÉ (franchissement) avec belt growth ~0 et pedal kickback
    quasi nul (la signature Kavenz, cf. knowledge/docs Kavenz VHP12-18). Métriques
    (solveur cross-validé) : kickback ~1.7°, belt growth ~1.9 mm (signature ami-courroie),
    levier 3.20→2.63, AS sag ~73 %, axe reculé ~4 mm. Pivot à hauteur RÉALISTE (~95 mm).
    INDICATIVE — affiner dans l'outil / bureau d'études. (Le vrai VHP est un 4-barres à pivot
    VIRTUEL haut → plus de recul ; ici single-pivot haut + galet qui reproduit la signature
    kickback/belt growth ; passer en four_bar_horst avec IC haut pour un vrai pivot virtuel.)"""
    return SuspensionConfig(
        linkage_type="high_pivot_idler",
        main_pivot=Pivot(x=35.0, y=95.0),       # pivot haut RÉALISTE (≈ vrais high-pivots)
        idler=Pivot(x=47.0, y=89.0),            # galet AU pivot → belt growth ~0, kickback ~0
        shock_lower=Pivot(x=-200.0, y=30.0),
        shock_upper=Pivot(x=40.0, y=340.0),
        use_idler=True,
        idler_dia=34.0,
        rear_travel=160.0,
        shock_stroke=60.0,
        shock_eye_to_eye=230.0,
    )


def scott_ransom_style() -> SuspensionConfig:
    """Façon SCOTT RANSOM (enduro 170 mm). Le VRAI Ransom est un 6-barres avec amorto
    intégré DANS le tube diagonal (pivot principal au BB, biellette basse, course 65 mm) — non
    reproductible fidèlement par un four-bar (la cinématique ne suit pas). On en donne une
    approximation : amortisseur incliné dans le triangle avant, œillet bas (-164,105) qui DÉGAGE
    le plateau/carter, piloté par le bras. Métriques (solveur cross-validé, SANS galet → chaîne) :
    course 170 mm, levier 2.55→2.34 (PROGRESSIF ~8 %), AS sag ~100 %, kickback ~22° (élevé car
    pas de galet — normal sur un enduro à chaîne). INDICATIVE — affiner / bureau d'études.
    ⚠ Sur un vélo à COURROIE, ce kickback tirerait sur la courroie → préférer un high-pivot+galet."""
    return SuspensionConfig(
        linkage_type="four_bar_horst",
        main_pivot=Pivot(x=6.0, y=45.0),
        horst_pivot=Pivot(x=-405.0, y=5.0),
        upper_ss_pivot=Pivot(x=-115.0, y=222.0),
        upper_frame_pivot=Pivot(x=34.0, y=252.0),
        shock_lower=Pivot(x=-164.0, y=105.0),
        shock_upper=Pivot(x=-20.0, y=235.0),
        shock_mount="chainstay",
        shock_on_chainstay=True,
        use_idler=False,
        rear_travel=170.0,
        shock_stroke=72.0,
        shock_eye_to_eye=194.0,
    )


PRESETS = {
    "high_pivot_m620": high_pivot_m620,
    "high_pivot_emtb_tuned": high_pivot_emtb_tuned,
    "kavenz_vhp_style": kavenz_vhp_style,
    "scott_ransom_style": scott_ransom_style,
}
