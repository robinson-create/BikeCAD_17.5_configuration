"""
Moteur de calcul géométrique exact — DOM Engineering Bike Tool

Convention coordonnées monde :
  BB = (0, 0), X = avant (positif), Y = haut (positif), unités mm
  Head angle, Seat angle = degrés depuis l'horizontale
"""

import math
from ..models.bike import BikeDesign, CalcResult, KeyPoint


def calculate(bike: BikeDesign) -> CalcResult:
    f = bike.frame
    fk = bike.fork
    st = bike.stem
    hb = bike.handlebar
    sd = bike.saddle
    sp = bike.seatpost

    hta = math.radians(f.head_angle)
    sta = math.radians(f.seat_angle)

    wheel_r_f = f.wheel_f / 2
    wheel_r_r = f.wheel_r / 2

    # ── Axes ────────────────────────────────────────────────────────────────
    # BB est à (wheel_r_r - bb_drop) du sol → axe AR est à bb_drop AU-DESSUS du BB
    # Pour des roues de taille différente : axe AV à (wheel_r_f - wheel_r_r + bb_drop) AU-DESSUS
    rear_axle_y = f.bb_drop
    rear_axle_x = -math.sqrt(max(f.cs**2 - f.bb_drop**2, 0.0))

    front_axle_y = wheel_r_f - wheel_r_r + f.bb_drop
    front_axle_x = f.fcd  # FCD = distance horizontale BB → axe AV

    # ── Fourche : couronne (bas du HT) ─────────────────────────────────────
    # Direction de la tige de fourche (de la couronne vers l'axe AV, bas et avant)
    fork_dir_x = math.cos(hta)
    fork_dir_y = -math.sin(hta)
    # Direction perpendiculaire (déport, positif = avant et haut)
    perp_x = math.sin(hta)
    perp_y = math.cos(hta)

    # A2C effectif avec sag (fourche comprimée au sag statique)
    a2c_eff = fk.a2c - fk.sag

    # axe_AV = couronne + A2C_eff * fork_dir + offset * perp
    # → couronne = axe_AV - A2C_eff * fork_dir - offset * perp
    crown_x = front_axle_x - a2c_eff * fork_dir_x - fk.offset * perp_x
    crown_y = front_axle_y - a2c_eff * fork_dir_y - fk.offset * perp_y

    # ── Tube de direction ──────────────────────────────────────────────────
    # Direction du HT (bas → haut) : monte et recule
    ht_dir_x = -math.cos(hta)
    ht_dir_y = math.sin(hta)

    ht_len = f.head_tube + f.head_tube_upper_ext + f.head_tube_lower_ext
    ht_top_x = crown_x + ht_len * ht_dir_x
    ht_top_y = crown_y + ht_len * ht_dir_y

    # ── Géométrie fondamentale ─────────────────────────────────────────────
    reach    = ht_top_x
    stack    = ht_top_y
    wheelbase = front_axle_x - rear_axle_x

    # Trail (formule canonique : trail = (R·cos(HTA) − offset)/sin(HTA))
    # Source : Wikipedia "Bicycle and motorcycle geometry".
    trail = (wheel_r_f * math.cos(hta) - fk.offset) / math.sin(hta)

    # Trail DYNAMIQUE au sag fourche : la fourche se comprime de `fk.sag`, le nez
    # plonge → le vélo tangue (pitch) autour du contact AR → l'angle de direction
    # se REDRESSE et le trail + l'empattement DIMINUENT (cf. Wikipedia). Approx
    # petit-angle, fourche seule : pitch ≈ Δ·sin(HTA)/empattement.
    sag_f = max(0.0, fk.sag)
    pitch = (sag_f * math.sin(hta) / wheelbase) if wheelbase > 1 else 0.0   # rad, nez bas
    hta_sag = hta + pitch                                                   # plus raide
    trail_sag = (wheel_r_f * math.cos(hta_sag) - fk.offset) / math.sin(hta_sag)
    head_angle_sag = math.degrees(hta_sag)
    wheelbase_sag = wheelbase - sag_f * math.cos(hta)                       # le front recule

    # Trail normal (perpendiculaire à la route) et arctangente
    front_normal_trail = trail * math.sin(hta)
    rear_normal_trail  = trail * math.cos(hta)
    arctan_trail = math.degrees(math.atan(trail / wheel_r_f)) if wheel_r_f > 0 else 0.0

    # Wheel flop
    wheel_flop = trail * math.sin(hta) * math.cos(hta)

    # Hauteur BB du sol
    bb_height = wheel_r_r - f.bb_drop

    # ── Tube de selle ──────────────────────────────────────────────────────
    # Direction : monte et recule depuis le BB
    # seat_angle = angle avec horizontale → direction = (-cos(STA), sin(STA))
    st_dir_x = -math.cos(sta)
    st_dir_y = math.sin(sta)

    seat_tube_top_x = f.seat_tube * st_dir_x
    seat_tube_top_y = f.seat_tube * st_dir_y

    # ── Top tube effectif (horizontal reach → TT junction) ─────────────────
    tt_effective = reach - seat_tube_top_x

    # ── Standover (hauteur cadre au point milieu, environ au-dessus du BB) ──
    # Approximation : hauteur du tube horizontal au-dessus du sol à BB x=0
    # On prend la hauteur minimale entre TT côté selle et côté HT, moins le rayon pneu
    standover = min(seat_tube_top_y, stack) + bb_height

    # ── Angle de selle effectif (angle de la ligne BB→sommet selle / horizontal) ─
    effective_sta = math.degrees(math.atan2(seat_tube_top_y, -seat_tube_top_x))

    # ── Potence ────────────────────────────────────────────────────────────
    stem_angle_rad = math.radians(st.angle)
    # Base de la potence : haut du HT + headset + spacers
    headset_height = bike.headset.upper_stack + bike.headset.lower_stack + bike.headset.spacers
    stem_base_x = ht_top_x + headset_height * ht_dir_x
    stem_base_y = ht_top_y + headset_height * ht_dir_y

    # Direction de la potence (dans le plan du vélo) :
    # angle de potence = positif = relevé par rapport au prolongement du HT
    # axe potence = prolongement du steerer ± stem_angle
    stem_ax = math.cos(hta + stem_angle_rad + math.pi / 2)
    stem_ay = math.sin(hta + stem_angle_rad + math.pi / 2)
    stem_tip_x = stem_base_x + st.length * stem_ax
    stem_tip_y = stem_base_y + st.length * stem_ay

    # ── Cintre ─────────────────────────────────────────────────────────────
    hbar_cx = stem_tip_x
    hbar_cy = stem_tip_y + hb.rise

    # ── Selle ──────────────────────────────────────────────────────────────
    # Tige de selle exposée depuis le top de tube de selle
    saddle_clamp_x = seat_tube_top_x + sp.exposed * st_dir_x
    saddle_clamp_y = seat_tube_top_y + sp.exposed * st_dir_y
    # Pointe de selle (recul + longueur)
    saddle_tip_x = saddle_clamp_x - (sd.length * 0.4 + sd.setback)
    saddle_tip_y = saddle_clamp_y + sd.thickness
    saddle_mid_x = saddle_clamp_x + sd.length * 0.1
    saddle_mid_y = saddle_clamp_y + sd.thickness

    return CalcResult(
        reach=round(reach, 1),
        stack=round(stack, 1),
        trail=round(trail, 1),
        trail_sag=round(trail_sag, 1),
        head_angle_sag=round(head_angle_sag, 2),
        wheelbase_sag=round(wheelbase_sag, 1),
        wheelbase=round(wheelbase, 1),
        bb_height=round(bb_height, 1),
        front_center=round(front_axle_x, 1),
        tt_effective=round(tt_effective, 1),
        standover=round(standover, 1),
        effective_sta=round(effective_sta, 2),
        wheel_flop=round(wheel_flop, 2),
        front_normal_trail=round(front_normal_trail, 1),
        rear_normal_trail=round(rear_normal_trail, 1),
        arctan_trail=round(arctan_trail, 2),

        bb=KeyPoint(x=0.0, y=0.0),
        rear_axle=KeyPoint(x=round(rear_axle_x, 1), y=round(rear_axle_y, 1)),
        front_axle=KeyPoint(x=round(front_axle_x, 1), y=round(front_axle_y, 1)),
        crown=KeyPoint(x=round(crown_x, 1), y=round(crown_y, 1)),
        ht_top=KeyPoint(x=round(ht_top_x, 1), y=round(ht_top_y, 1)),
        seat_tube_top=KeyPoint(x=round(seat_tube_top_x, 1), y=round(seat_tube_top_y, 1)),
        stem_base=KeyPoint(x=round(stem_base_x, 1), y=round(stem_base_y, 1)),
        stem_tip=KeyPoint(x=round(stem_tip_x, 1), y=round(stem_tip_y, 1)),
        handlebar_center=KeyPoint(x=round(hbar_cx, 1), y=round(hbar_cy, 1)),
        saddle_tip=KeyPoint(x=round(saddle_tip_x, 1), y=round(saddle_tip_y, 1)),
        saddle_mid=KeyPoint(x=round(saddle_mid_x, 1), y=round(saddle_mid_y, 1)),
        ground_level=round(-bb_height, 1),
    )
