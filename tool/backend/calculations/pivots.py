"""Hardware des pivots de suspension : roulements + axes + logements.

Pour chaque pivot de la topologie active, on pose la GÉOMÉTRIE de montage :
roulement standard (réf + Ø alésage/extérieur/largeur), axe/boulon, logement
usiné dans le lug. C'est une aide au pré-dimensionnement et à la CAO.

⚠ HORS PÉRIMÈTRE : charges réelles, durée de vie roulement, dimensionnement de
l'axe en fatigue → bureau d'études (engin motorisé, organe de sécurité).
"""
from collections import Counter
from ..models.bike import BEARING_CATALOG


def _bearing(ref):
    return BEARING_CATALOG.get(ref, BEARING_CATALOG["6902-2RS"])


def _bolt_for(bore: float) -> str:
    return "M8" if bore >= 15 else "M6" if bore >= 10 else "M5"


def compute_pivots(bike):
    from ..models.bike import PivotResult, PivotItem
    su = bike.suspension
    topo = su.linkage_type
    if not su.enabled:
        return PivotResult(ok=False, topology=topo, notes=["Suspension désactivée — aucun pivot."])

    items: list = []

    def add(name, role, pt, ref, qty, note=""):
        b = _bearing(ref)
        items.append(PivotItem(
            name=name, role=role, x=round(pt.x, 1), y=round(pt.y, 1),
            bearing=ref, bore=b["bore"], od=b["od"], width=b["width"], qty=qty,
            housing_od=round(b["od"] + 6.0, 1), axle_dia=b["bore"],
            bolt=_bolt_for(b["bore"]), note=note,
        ))

    main_ref, link_ref, idler_ref = su.pivot_bearing_main, su.pivot_bearing_link, su.idler_bearing

    if topo == "high_pivot_idler":
        add("main_pivot", "Pivot principal HAUT (single-pivot)", su.main_pivot, main_ref, 2,
            "Pivot haut → chemin d'axe reculé ; charge élevée (M620) → roulement renforcé.")
        add("upper_ss_pivot", "Liaison hauban/bielle", su.upper_ss_pivot, link_ref, 2)
    else:  # four_bar_horst / four_bar_generic
        add("main_pivot", "Pivot principal (cadre ↔ base)", su.main_pivot, main_ref, 2,
            "Pivot le plus chargé → 2 roulements + axe traversant.")
        add("horst_pivot", "Pivot Horst (base ↔ hauban, près de l'axe AR)", su.horst_pivot, link_ref, 2)
        add("upper_frame_pivot", "Biellette ↔ cadre", su.upper_frame_pivot, link_ref, 2)
        add("upper_ss_pivot", "Biellette ↔ hauban", su.upper_ss_pivot, link_ref, 2)

    # Ancrages amortisseur : bagues DU / rotules (pas de roulement à billes)
    add("shock_lower", "Œillet amortisseur (bas)", su.shock_lower, "bushing-DU", 1,
        "Bague DU/rotule (mouvement angulaire faible) — pas un roulement à billes.")
    add("shock_upper", "Œillet amortisseur (haut)", su.shock_upper, "bushing-DU", 1,
        "Bague DU/rotule.")

    if su.use_idler:
        add("idler", "Galet de renvoi courroie", su.idler, idler_ref, 2,
            "Galet sur 2 roulements ; étanchéité soignée (boue).")

    # Nomenclature agrégée (BOM)
    cnt = Counter()
    for it in items:
        cnt[it.bearing] += it.qty
    bom = []
    for ref, qty in cnt.items():
        b = _bearing(ref)
        bom.append({"ref": ref, "qty": qty,
                    "dims": f"{b['bore']:g}×{b['od']:g}×{b['width']:g}", "type": b["type"]})

    notes = [
        "Sélection de roulements STANDARD (géométrie) — charges, durée de vie et axe en "
        "fatigue à valider par un bureau d'études (engin motorisé ~80 km/h).",
        "Logement lug = Ø_ext roulement + ~6 mm de paroi ; montage press-fit (tol. H7), "
        "étanchéité 2RS, axe/collet en acier (ou Ti).",
        f"Couple de serrage des axes : {su.pivot_torque_nm:g} Nm (indicatif).",
    ]
    return PivotResult(ok=True, topology=topo, torque_nm=su.pivot_torque_nm,
                       pivots=items, bom=bom, notes=notes)
