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


PRESETS = {
    "high_pivot_m620": high_pivot_m620,
}
