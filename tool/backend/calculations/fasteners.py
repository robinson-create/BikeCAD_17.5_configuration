"""Visserie : chaque point de vis/boulon du vélo + le type de vis choisi.

Pour chaque jonction boulonnée on pose la GÉOMÉTRIE de montage (position monde),
la taille (M5/M6/M8…), l'empreinte (Hex/Torx), la quantité et un couple de
serrage de RÉFÉRENCE inter-marques. C'est une aide à l'assemblage et à la CAO,
analogue à l'onglet Pivots (roulements).

Sources des couples (tables constructeurs agrégées) : Park Tool « Torque
Specifications », Specialized Torque Matrix, Race Face / Thomson / ENVE,
SRAM / Shimano, manuel dealer Bafang M620 (G510).

⚠ Règle d'or : TOUJOURS prioriser le couple GRAVÉ/IMPRIMÉ sur la pièce montée.
⚠ HORS PÉRIMÈTRE : ces couples sont des specs d'assemblage ; le dimensionnement
   fatigue/impact de la visserie d'un engin motorisé reste au bureau d'études.
"""
import math
from collections import OrderedDict


def _saddle_clamp(bike, calc):
    """Chariot de selle ≈ haut de tige exposée, le long de l'axe du tube de selle."""
    sa = math.radians(bike.frame.seat_angle)
    dx, dy = -math.cos(sa), math.sin(sa)          # vers le haut-arrière
    exp = max(0.0, bike.seatpost.exposed)
    return (calc.seat_tube_top.x + dx * exp, calc.seat_tube_top.y + dy * exp)


def compute_fasteners(bike, calc):
    from ..models.bike import FastenerResult, FastenerItem

    items: list = []

    def add(cat, name, where, pt, size, drive, qty, torque, note=""):
        items.append(FastenerItem(
            category=cat, name=name, where=where,
            x=round(pt[0], 1), y=round(pt[1], 1),
            size=size, drive=drive, qty=qty, torque_nm=torque, note=note))

    f = bike.frame
    bb = (calc.bb.x, calc.bb.y)
    hta = math.radians(f.head_angle)
    sax, say = -math.cos(hta), math.sin(hta)       # axe de direction (haut-arrière)

    # ─── COCKPIT ────────────────────────────────────────────────────────────
    add("Cockpit", "Serrage potence sur pivot de fourche", "stem_steerer",
        (calc.stem_base.x, calc.stem_base.y), "M5", "Hex 4 / Torx T25", 2, "5–6",
        "Serrer APRÈS réglage du top cap, fourche alignée. DH/direct-mount : jusqu'à 9.")
    add("Cockpit", "Faceplate (serrage cintre)", "stem_faceplate",
        (calc.stem_tip.x, calc.stem_tip.y), "M5", "Hex 4 / Torx T25", 4, "5–6",
        "Serrer le haut puis le bas, jeu 0 mm en haut, en croix progressive.")
    add("Cockpit", "Capuchon de jeu de direction (précontrainte)", "top_cap",
        (calc.stem_base.x + sax * 14, calc.stem_base.y + say * 14), "M6", "Hex 4/5", 1, "3–4",
        "Vis de PRÉCONTRAINTE du roulement — ne retient PAS la potence.")

    # ─── TIGE DE SELLE ─────────────────────────────────────────────────────
    add("Tige de selle", "Collier de selle (cadre)", "seat_collar",
        (calc.seat_tube_top.x, calc.seat_tube_top.y), "M5", "Hex 4 / Torx T25", 1, "5–6",
        "Tige carbone : viser le bas de la plage + pâte de montage carbone.")
    add("Tige de selle", "Chariot de rails de selle", "saddle_rails",
        _saddle_clamp(bike, calc), "M6", "Hex 4/5", 2, "9",
        "Rails carbone : suivre la notice de la selle (souvent < 9).")

    # ─── FREINS À DISQUE ───────────────────────────────────────────────────
    if str(bike.brakes.style).startswith("disc"):
        for label, axle, where, rot in (
            ("avant", calc.front_axle, "rotor_front", bike.brakes.rotor_front),
            ("arrière", calc.rear_axle, "rotor_rear", bike.brakes.rotor_rear),
        ):
            add("Freins", f"Disque {label} (6 trous)", where, (axle.x, axle.y),
                "M5", "Torx T25", 6, "6.2",
                "Ou Center Lock (1 bague cannelée, 40 Nm). Shimano vis pré-traitées : 2–4.")
        # étriers : au sommet du disque (post-mount), vers le cadre
        add("Freins", "Étrier avant (post-mount)", "caliper_front",
            (calc.front_axle.x, calc.front_axle.y + bike.brakes.rotor_front * 0.42),
            "M6", "Hex 5", 2, "6–9", "SRAM post-mount 9.5 ; Shimano 6–8 ; centrer disque serré.")
        add("Freins", "Étrier arrière (post-mount)", "caliper_rear",
            (calc.rear_axle.x, calc.rear_axle.y + bike.brakes.rotor_rear * 0.42),
            "M6", "Hex 5", 2, "6–9")

    # ─── ROUES (axes traversants) ──────────────────────────────────────────
    add("Roues", "Axe traversant avant (15 mm)", "axle_front",
        (calc.front_axle.x, calc.front_axle.y), "15 mm", "Hex 6 / levier", 1, "9–10",
        "RockShox Maxle : fermer en zone verte (pas de couple chiffré).")
    add("Roues", "Axe traversant arrière (12 mm)", "axle_rear",
        (calc.rear_axle.x, calc.rear_axle.y), "12 mm", "Hex 6", 1, "15",
        "Shimano E-Thru 12 mm.")

    # ─── TRANSMISSION ──────────────────────────────────────────────────────
    add("Transmission", "Plateau direct-mount (3 vis)", "chainring", bb,
        "—", "Torx T25", 3, "9",
        "SRAM 3-bolt ; sur M620 le plateau est bloqué par un écrou cannelé (35 Nm).")
    add("Transmission", "Boulon/vis de manivelle", "crank_bolt", bb,
        "M15 / M8", "Hex 8", 2, "45–50",
        "Bafang M620 : manivelles 45–50 Nm. SRAM DUB auto-extracteur : 54.")
    dt = bike.drivetrain
    if getattr(dt, "transmission", "") == "derailleur":
        add("Transmission", "Patte de dérailleur / UDH", "udh",
            (calc.rear_axle.x, calc.rear_axle.y), "UDH", "Hex 5", 1, "25",
            "UDH = filetage à GAUCHE. Eagle Transmission Full Mount (Hex 8) : 35.")

    # ─── MOTEUR (Bafang M620) ──────────────────────────────────────────────
    if getattr(dt, "use_motor", False) and getattr(dt, "motor_key", "none") != "none":
        add("Moteur", "Fixation moteur → cadre", "motor_mount",
            (bb[0] - 30, bb[1] + 10), "M8", "Hex (interne)", 3, "35",
            "M620 : boulons spéciaux + rondelles plates + écrous-frein.")
        add("Moteur", "Capot moteur", "motor_cover", (bb[0] + 25, bb[1] - 20),
            "M3×8", "Torx", 3, "1.5")
        add("Moteur", "Capteur de vitesse", "motor_sensor",
            (calc.rear_axle.x * 0.45, calc.rear_axle.y + 30), "—", "Cruciforme/étoile", 1, "1.5–2")

    # ─── SUSPENSION (axes de pivot + œillets amortisseur) ──────────────────
    su = bike.suspension
    if getattr(su, "enabled", False):
        add("Suspension", "Axe pivot principal", "pivot_main",
            (su.main_pivot.x, su.main_pivot.y), "M8", "Hex 6", 1, "12–24",
            "Voir aussi l'onglet Pivots (roulements + logements).")
        add("Suspension", "Œillet amortisseur (bas)", "shock_lower",
            (su.shock_lower.x, su.shock_lower.y), "M8", "Hex", 1, "11–22")
        add("Suspension", "Œillet amortisseur (haut)", "shock_upper",
            (su.shock_upper.x, su.shock_upper.y), "M8", "Hex", 1, "15–22")
        if str(su.linkage_type).startswith("four_bar"):
            add("Suspension", "Pivot Horst (base↔hauban)", "horst_pivot",
                (su.horst_pivot.x, su.horst_pivot.y), "M6", "Hex", 1, "12–18")
            add("Suspension", "Biellette ↔ cadre", "link_frame",
                (su.upper_frame_pivot.x, su.upper_frame_pivot.y), "M6", "Hex", 1, "12–18")
            add("Suspension", "Biellette ↔ hauban", "link_ss",
                (su.upper_ss_pivot.x, su.upper_ss_pivot.y), "M6", "Hex", 1, "12–18")
        else:
            add("Suspension", "Pivot hauban/biellette", "upper_ss",
                (su.upper_ss_pivot.x, su.upper_ss_pivot.y), "M6", "Hex", 1, "12–18")
        if getattr(su, "use_idler", False):
            add("Suspension", "Axe galet de renvoi", "idler",
                (su.idler.x, su.idler.y), "M6", "Hex", 1, "10")

    # ─── DIVERS ────────────────────────────────────────────────────────────
    add("Divers", "Porte-bidon (inserts cadre)", "bottle_cage",
        ((bb[0] + calc.crown.x) / 2, (bb[1] + calc.crown.y) / 2),
        "M5", "Hex 4", 2, "3", "Ne pas surserrer (max ~4 Nm sur inserts).")

    # ─── BOM (nomenclature de visserie) ────────────────────────────────────
    counter: "OrderedDict[tuple, int]" = OrderedDict()
    for it in items:
        key = (it.size, it.drive)
        counter[key] = counter.get(key, 0) + it.qty
    bom = [{"size": k[0], "drive": k[1], "qty": v} for k, v in counter.items()]
    total = sum(it.qty for it in items)

    notes = [
        f"{len(items)} jonctions boulonnées, {total} vis/boulons au total.",
        "Règle d'or : prioriser le couple GRAVÉ/IMPRIMÉ sur la pièce montée ; "
        "ces valeurs sont des références inter-marques (Park Tool, Specialized, SRAM/Shimano, Bafang).",
        "Carbone (cintre, tige, collier sur tube carbone) : ne pas dépasser le couple mini "
        "constructeur + pâte de montage carbone (friction).",
        "HORS PÉRIMÈTRE structurel : specs d'assemblage uniquement ; le dimensionnement "
        "fatigue/impact de la visserie (engin motorisé) reste au bureau d'études.",
    ]
    return FastenerResult(ok=True, items=items, bom=bom, notes=notes)
