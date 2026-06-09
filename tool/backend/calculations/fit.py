"""
Fit pilote (bike fit 2D, plan sagittal) — DOM Engineering Bike Tool

Modèle squelette à partir de RiderConfig + points clés géométriques :
  • Hanche      = point d'assise (saddle_mid)
  • Pédalier    = BB (0,0), rayon manivelle = cranks.crank_length
  • Poignée     = handlebar_center (grip)

Postures calculées :
  • Jambe au point bas (BDC) : hanche→genou→cheville→pédale  → angle de genou
    (indicateur de hauteur de selle) + extension %.
  • KOPS : genou à l'aplomb de l'axe de pédale (manivelle horizontale avant).
  • Haut du corps : IK 2-barres hanche→épaule→poignée (torse + bras),
    bras légèrement fléchi (facteur 0.92) → angle de dos, d'épaule, de coude.

Toutes les longueurs en mm, angles en degrés. À considérer comme une aide à
la mise en position, pas un protocole de fitting clinique.
"""

import math
from ..models.bike import BikeDesign, CalcResult, FitResult, KeyPoint


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _two_bar_ik(p0, p2, l01, l12, sign=+1):
    """Position du joint intermédiaire p1 tel que |p0 p1|=l01, |p1 p2|=l12.
    `sign` choisit la branche (coude/genou d'un côté ou de l'autre)."""
    d = _dist(p0, p2)
    if d < 1e-6 or d > l01 + l12 or d < abs(l01 - l12):
        return None  # inatteignable
    a = (l01 ** 2 - l12 ** 2 + d ** 2) / (2 * d)
    h2 = l01 ** 2 - a ** 2
    h = math.sqrt(max(h2, 0.0))
    ux, uy = (p2[0] - p0[0]) / d, (p2[1] - p0[1]) / d
    mx, my = p0[0] + a * ux, p0[1] + a * uy
    return (mx - sign * h * uy, my + sign * h * ux)


def _angle_at(vertex, a, b):
    """Angle (°) au sommet `vertex` entre les segments vers a et vers b."""
    v1 = (a[0] - vertex[0], a[1] - vertex[1])
    v2 = (b[0] - vertex[0], b[1] - vertex[1])
    n1 = math.hypot(*v1); n2 = math.hypot(*v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0
    c = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def compute_fit(bike: BikeDesign, calc: CalcResult) -> FitResult:
    if bike.rider is None:
        return FitResult(ok=False, message="Aucun pilote défini.")
    r = bike.rider

    bb = (0.0, 0.0)
    hip = (calc.saddle_mid.x, calc.saddle_mid.y)
    grip = (calc.handlebar_center.x, calc.handlebar_center.y)
    L_crank = bike.cranks.crank_length

    notes = []

    # ── Cockpit (indépendant de la posture) ─────────────────────────────────
    saddle_to_bar_reach = grip[0] - hip[0]
    saddle_to_bar_drop = hip[1] - grip[1]
    saddle_height = _dist(bb, hip)

    # ── Jambe au point bas (BDC) — pédale à 6h ──────────────────────────────
    pedal_bdc = (bb[0], bb[1] - L_crank)
    leg_full = r.upper_leg + r.lower_leg
    reach_bdc = _dist(hip, pedal_bdc)
    leg_ext_pct = reach_bdc / leg_full * 100 if leg_full else 0.0
    knee_bdc = None
    if reach_bdc < leg_full:
        knee = _two_bar_ik(hip, pedal_bdc, r.upper_leg, r.lower_leg, sign=+1)
        if knee:
            knee_bdc = _angle_at(knee, hip, pedal_bdc)
    else:
        notes.append("Selle trop haute : jambe ne peut pas atteindre la pédale au point bas.")

    # ── KOPS — manivelle horizontale avant (pédale à 3h) ─────────────────────
    pedal_fwd = (bb[0] + L_crank, bb[1])
    kops_offset = None
    knee_fwd = _two_bar_ik(hip, pedal_fwd, r.upper_leg, r.lower_leg, sign=+1)
    if knee_fwd:
        kops_offset = knee_fwd[0] - pedal_fwd[0]   # + = genou en avant de l'axe

    # ── Hanche fermée au point haut (pédale à 12h) ──────────────────────────
    pedal_tdc = (bb[0], bb[1] + L_crank)
    hip_angle_tdc = None
    knee_tdc = _two_bar_ik(hip, pedal_tdc, r.upper_leg, r.lower_leg, sign=+1)

    # ── Haut du corps : torse + bras (IK 2-barres, bras fléchi 0.92) ────────
    arm_full = r.upper_arm + r.lower_arm
    eff_arm = arm_full * 0.92
    reach_hg = _dist(hip, grip)
    shoulder = elbow = head = None
    back_angle = shoulder_angle = elbow_angle = None
    if reach_hg > r.torso_length + eff_arm:
        notes.append("Cockpit trop long : le pilote est en surextension vers le cintre.")
    elif reach_hg < abs(r.torso_length - eff_arm):
        notes.append("Cockpit trop court : posture tassée.")
    else:
        shoulder = _two_bar_ik(hip, grip, r.torso_length, eff_arm, sign=+1)
        if shoulder:
            back_angle = math.degrees(math.atan2(
                shoulder[1] - hip[1], shoulder[0] - hip[0]))
            # coude réel (bras complet)
            elbow = _two_bar_ik(shoulder, grip, r.upper_arm, r.lower_arm, sign=+1)
            if elbow:
                elbow_angle = _angle_at(elbow, shoulder, grip)
                shoulder_angle = _angle_at(shoulder, hip, elbow)
            # tête : prolongement du torse au-delà de l'épaule
            tdir = ((shoulder[0] - hip[0]) / r.torso_length,
                    (shoulder[1] - hip[1]) / r.torso_length)
            head = (shoulder[0] + tdir[0] * r.shoulder_to_jaw,
                    shoulder[1] + tdir[1] * r.shoulder_to_jaw)

    if knee_tdc and shoulder:
        hip_angle_tdc = _angle_at(hip, knee_tdc, shoulder)

    def kp(p):
        return KeyPoint(x=round(p[0], 1), y=round(p[1], 1)) if p else None

    return FitResult(
        ok=True,
        message="",
        saddle_height=round(saddle_height, 1),
        saddle_to_bar_reach=round(saddle_to_bar_reach, 1),
        saddle_to_bar_drop=round(saddle_to_bar_drop, 1),
        leg_extension_pct=round(leg_ext_pct, 1),
        knee_angle_bdc=round(knee_bdc, 1) if knee_bdc is not None else None,
        hip_angle_tdc=round(hip_angle_tdc, 1) if hip_angle_tdc is not None else None,
        back_angle=round(back_angle, 1) if back_angle is not None else None,
        elbow_angle=round(elbow_angle, 1) if elbow_angle is not None else None,
        shoulder_angle=round(shoulder_angle, 1) if shoulder_angle is not None else None,
        kops_offset=round(kops_offset, 1) if kops_offset is not None else None,
        notes=notes,
        # squelette (pose : jambe au point bas)
        hip=kp(hip),
        knee=kp(_two_bar_ik(hip, pedal_bdc, r.upper_leg, r.lower_leg, sign=+1)),
        pedal=kp(pedal_bdc),
        shoulder=kp(shoulder),
        elbow=kp(elbow),
        hand=kp(grip),
        head=kp(head),
    )
