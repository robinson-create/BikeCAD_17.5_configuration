"""Transmission : dérailleur (cassette) ou IGH (moyeu à vitesses intégrées).

Garde-fou clé pour un e-MTB à fort couple : le couple à l'ENTRÉE du moyeu IGH
= couple moteur (au pédalier) / rapport primaire (plateau/pignon). Il doit rester
sous la limite du moyeu (Rohloff 130 Nm, 3X3 NINE 250 Nm). On contrôle aussi le
rapport primaire minimal recommandé. Aide au pré-dimensionnement (pas une validation
structurelle — déléguée au bureau d'études).

Pour une transmission par COURROIE : géométrie (entraxe, nb de dents Gates) et
TENSION. Une courroie est sans fin et n'a pas de tendeur de dérailleur → l'entraxe
doit être réglable (patte coulissante / BB ou pivot excentrique) pour la tendre.
"""
import math

from ..models.bike import IGH_TYPES

_TENSION_LABEL = {
    "sliding_dropout": "patte coulissante",
    "eccentric_bb": "boîtier de pédalier excentrique",
    "eccentric_pivot": "pivot principal excentrique",
}


def _belt_geometry(bike):
    """Géométrie courroie (modèle 2-poulies, courroie ouverte plateau↔pignon).

    Retourne (nb_dents, entraxe_mm, delta_entraxe_par_dent_mm). L'entraxe ≈ distance
    BB → axe AR (le pignon est au moyeu). Le galet de renvoi rallonge le brin réel
    mais le nb de dents est dimensionné sur l'entraxe principal — INDICATIF (la
    longueur exacte se valide avec le calculateur Gates Carbon Drive)."""
    su = bike.suspension
    f = bike.frame
    pitch = max(1e-3, su.belt_pitch)
    r_cr = su.chainring_teeth * pitch / (2 * math.pi)
    r_cog = su.cog_teeth * pitch / (2 * math.pi)
    # Entraxe = distance BB(0,0) → axe AR ; axe AR = (-√(cs²−drop²), drop) → |·| = cs
    C = max(1.0, math.hypot(math.sqrt(max(f.cs**2 - f.bb_drop**2, 0.0)), f.bb_drop))
    # Longueur de courroie ouverte : L = 2C·cosα + r_cr(π+2α) + r_cog(π−2α)
    alpha = math.asin(max(-1.0, min(1.0, (r_cr - r_cog) / C)))
    L = 2 * C * math.cos(alpha) + r_cr * (math.pi + 2 * alpha) + r_cog * (math.pi - 2 * alpha)
    teeth = round(L / pitch)
    # Variation d'entraxe pour 1 dent de courroie : dL/dC ≈ 2cosα → ΔC = pitch/(2cosα)
    dC_per_tooth = pitch / (2 * math.cos(alpha)) if math.cos(alpha) > 1e-3 else pitch / 2
    return teeth, C, dC_per_tooth


def compute_transmission(bike):
    from ..models.bike import TransmissionResult
    dt = bike.drivetrain
    su = bike.suspension
    cr = max(1, su.chainring_teeth)
    cog = max(1, su.cog_teeth)
    primary = cr / cog
    notes = []
    is_belt = dt.drive_type == "belt"

    # ── Géométrie + tension courroie (commun dérailleur/IGH) ─────────────────
    belt_teeth = belt_center = 0.0
    tension_ok = True
    if is_belt:
        belt_teeth, belt_center, dC_per_tooth = _belt_geometry(bike)
        method = su.belt_tension_method
        adjust = su.dropout_adjust_mm
        # Pour tendre N'IMPORTE QUELLE courroie entière, le réglage d'entraxe doit
        # couvrir au moins un incrément de dent (sinon aucune longueur Gates ne tombe juste).
        tension_ok = adjust >= dC_per_tooth
        mlabel = _TENSION_LABEL.get(method, method)
        if adjust <= 0.1:
            tension_ok = False
            notes.append("Courroie SANS réglage d'entraxe : impossible à tendre. "
                         "Prévoir une patte coulissante, un BB ou un pivot excentrique.")
        elif not tension_ok:
            notes.append(f"Réglage d'entraxe {adjust:.0f} mm < {dC_per_tooth:.1f} mm/dent "
                         f"({mlabel}) : insuffisant pour caler une courroie Gates entière. "
                         f"Viser ≥ {math.ceil(dC_per_tooth)} mm.")
        else:
            notes.append(f"Tension courroie : {mlabel}, course {adjust:.0f} mm "
                         f"(couvre {adjust / dC_per_tooth:.1f} dent(s) — OK). "
                         f"Courroie ≈ {belt_teeth} dents, entraxe {belt_center:.0f} mm.")

    if dt.transmission != "igh":
        rng = (dt.rear_cog_max / max(1, dt.rear_cog_min)) * 100 if dt.rear_cog_max else 0.0
        belt_ok = not is_belt  # dérailleur → chaîne obligatoire
        if is_belt:
            notes.append("Dérailleur = chaîne obligatoire (la courroie impose mono-vitesse ou un moyeu IGH).")
        return TransmissionResult(
            kind="derailleur", label="Dérailleur + cassette",
            gears=0, range_pct=round(rng, 0), primary_ratio=round(primary, 2),
            belt_ok=belt_ok, belt=is_belt, belt_teeth=belt_teeth,
            belt_center_mm=round(belt_center, 1), belt_tension_method=su.belt_tension_method,
            dropout_adjust_mm=su.dropout_adjust_mm, belt_tension_ok=tension_ok, notes=notes,
        )

    spec = IGH_TYPES.get(dt.igh_model)
    if spec and dt.igh_model in IGH_TYPES:
        gears, rng, maxt = spec["gears"], spec["range_pct"], spec["max_torque_nm"]
        minr, wt, label, belt = spec["min_ratio"], spec["weight_g"], spec["label"], spec["belt"]
    else:
        gears, rng, maxt = dt.igh_gears, dt.igh_range_pct, dt.igh_max_torque_nm
        minr, wt, label, belt = 1.90, 0, "IGH personnalisé", True

    hub_in = dt.motor_torque_nm / primary if primary > 0 else 0.0
    torque_ok = hub_in <= maxt
    ratio_ok = primary >= minr
    if not torque_ok:
        notes.append(f"Couple à l'entrée du moyeu {hub_in:.0f} Nm > limite {maxt:.0f} Nm — "
                     f"augmenter le rapport primaire (plus de dents au plateau / moins au pignon).")
    if not ratio_ok:
        notes.append(f"Rapport primaire {primary:.2f} < mini {minr:.2f} recommandé pour ce moyeu "
                     f"(risque de surcharge / garantie).")
    belt_ok = belt or not is_belt
    if is_belt and not belt:
        notes.append("Ce moyeu n'est pas homologué courroie.")

    return TransmissionResult(
        kind="igh", label=label, gears=gears, range_pct=rng, weight_g=wt,
        primary_ratio=round(primary, 2), hub_input_nm=round(hub_in, 1), max_torque_nm=maxt,
        torque_ok=torque_ok, ratio_ok=ratio_ok, min_ratio=minr, belt_ok=belt_ok,
        belt=is_belt, belt_teeth=belt_teeth, belt_center_mm=round(belt_center, 1),
        belt_tension_method=su.belt_tension_method, dropout_adjust_mm=su.dropout_adjust_mm,
        belt_tension_ok=tension_ok, notes=notes,
    )
