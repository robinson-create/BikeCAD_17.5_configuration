"""Transmission : dérailleur (cassette) ou IGH (moyeu à vitesses intégrées).

Garde-fou clé pour un e-MTB à fort couple : le couple à l'ENTRÉE du moyeu IGH
= couple moteur (au pédalier) / rapport primaire (plateau/pignon). Il doit rester
sous la limite du moyeu (Rohloff 130 Nm, 3X3 NINE 250 Nm). On contrôle aussi le
rapport primaire minimal recommandé. Aide au pré-dimensionnement (pas une validation
structurelle — déléguée au bureau d'études).
"""
from ..models.bike import IGH_TYPES


def compute_transmission(bike):
    from ..models.bike import TransmissionResult
    dt = bike.drivetrain
    su = bike.suspension
    cr = max(1, su.chainring_teeth)
    cog = max(1, su.cog_teeth)
    primary = cr / cog
    notes = []

    if dt.transmission != "igh":
        rng = (dt.rear_cog_max / max(1, dt.rear_cog_min)) * 100 if dt.rear_cog_max else 0.0
        belt_ok = dt.drive_type == "chain"
        if not belt_ok:
            notes.append("Dérailleur = chaîne obligatoire (la courroie impose mono-vitesse ou un moyeu IGH).")
        return TransmissionResult(
            kind="derailleur", label="Dérailleur + cassette",
            gears=0, range_pct=round(rng, 0), primary_ratio=round(primary, 2),
            belt_ok=belt_ok, notes=notes,
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
    belt_ok = belt or dt.drive_type == "chain"
    if dt.drive_type == "belt" and not belt:
        notes.append("Ce moyeu n'est pas homologué courroie.")

    return TransmissionResult(
        kind="igh", label=label, gears=gears, range_pct=rng, weight_g=wt,
        primary_ratio=round(primary, 2), hub_input_nm=round(hub_in, 1), max_torque_nm=maxt,
        torque_ok=torque_ok, ratio_ok=ratio_ok, min_ratio=minr, belt_ok=belt_ok, notes=notes,
    )
