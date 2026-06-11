"""
Models Pydantic — DOM Engineering Bike Tool
Couvre l'ensemble des paramètres BikeCAD Phase 1 :
Frame, Fork, Headtube, Stem, Handlebar, Saddle, Seatpost
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ─── CADRE ────────────────────────────────────────────────────────────────────

class FrameGeometry(BaseModel):
    # Angles
    head_angle: float = Field(64.0, description="Angle de direction (° / horizontale)")
    seat_angle: float = Field(78.0, description="Angle de tube de selle (° / horizontale)")

    # Longueurs principales (mm)
    cs:         float = Field(435.0, description="Longueur bases (BB → axe AR, mm)")
    bb_drop:    float = Field(30.0,  description="Chute du BB sous les axes (mm)")
    fcd:        float = Field(820.0, description="Front center horizontal (BB → axe AV, mm)")
    seat_tube:  float = Field(423.0, description="Longueur tube de selle c-c (mm)")
    head_tube:  float = Field(125.0, description="Longueur tube de direction (mm)")
    head_tube_upper_ext: float = Field(0.0,  description="Extension HT haut (mm)")
    head_tube_lower_ext: float = Field(0.0,  description="Extension HT bas (mm)")

    # Diamètres tubes (mm)
    top_tube_d:    float = Field(38.0, description="Ø tube horizontal (mm)")
    down_tube_d:   float = Field(44.0, description="Ø tube diagonal (mm)")
    seat_tube_fd:  float = Field(35.0, description="Ø tube de selle avant (mm)")
    head_tube_d:   float = Field(44.0, description="Ø tube de direction (mm)")
    chainstay_d:   float = Field(32.0, description="Ø bases (mm, approx rendu)")
    seatstay_d:    float = Field(20.0, description="Ø haubans (mm, approx rendu)")

    # BB
    bb_width:    float = Field(68.0,  description="Largeur boîtier de pédalier (mm)")
    bb_shell_d:  float = Field(34.8,  description="Ø extérieur boîtier (mm)")

    # Roues
    wheel_f: float = Field(736.0, description="Ø extérieur roue avant (mm)")
    wheel_r: float = Field(736.0, description="Ø extérieur roue arrière (mm)")


# ─── FOURCHE ──────────────────────────────────────────────────────────────────

class ForkConfig(BaseModel):
    travel:         float = Field(160.0, description="Débattement fourche (mm)")
    sag:            float = Field(40.0,  description="Sag statique (mm)")
    a2c:            float = Field(570.8, description="Axe-à-couronne A2C (mm)")
    offset:         float = Field(44.0,  description="Déport / rake (mm)")
    dual_crown:     bool  = Field(True,  description="Double couronne")
    fork_style:     int   = Field(1,     description="Style fourche BikeCAD (1=suspendu)")
    upper_stanchion:float = Field(425.0, description="Longueur tube plongeur haut (mm)")
    blade_width:    float = Field(32.0,  description="Largeur lame fourche (mm)")

    # Boulon de frein
    brake_hole_to_crown: float = Field(490.0, description="Distance trou frein → couronne (mm)")
    brake_hole_to_axle:  float = Field(0.0,   description="Distance trou frein → axe (mm)")


# ─── TUBE DE DIRECTION ────────────────────────────────────────────────────────

class HeadtubeConfig(BaseModel):
    style:   str   = Field("tapered", description="Style : straight | tapered")
    d_top:   float = Field(44.0, description="Ø haut tube de direction (mm)")
    d_bottom:float = Field(56.0, description="Ø bas tube de direction (mm, tapered)")


# ─── JEUX DE DIRECTION ────────────────────────────────────────────────────────

class HeadsetConfig(BaseModel):
    standard:    str   = Field("", description="Référence jeu de direction")
    upper_stack: float = Field(8.5,  description="Stack haut (mm)")
    lower_stack: float = Field(6.5,  description="Stack bas (mm)")
    spacers:     float = Field(20.0, description="Total entretoises (mm)")


# ─── POTENCE ──────────────────────────────────────────────────────────────────

class StemConfig(BaseModel):
    length:          float = Field(50.0,  description="Longueur potence (mm)")
    angle:           float = Field(6.0,   description="Angle potence (°, + = relevé)")
    x:               float = Field(0.0,   description="Offset X (mm)")
    y:               float = Field(0.0,   description="Offset Y (mm)")
    collar_height:   float = Field(25.0,  description="Hauteur collier (mm)")
    collar_diameter: float = Field(31.8,  description="Ø collier cintre (mm)")
    steerer_exposed: float = Field(40.0,  description="Dépassement de tube de fourche (mm)")


# ─── CINTRE ───────────────────────────────────────────────────────────────────

HandlebarStyle = Literal["flat_mtn", "drop_anatomic", "drop_compact", "drop_ergo", "bullhorn", "track", "BMX"]

class HandlebarConfig(BaseModel):
    style:    HandlebarStyle = Field("flat_mtn", description="Style cintre")
    width:    float = Field(760.0, description="Largeur hors-tout (mm)")
    rise:     float = Field(20.0,  description="Relevé (mm)")
    sweep:    float = Field(9.0,   description="Sweep arrière (°)")
    diameter: float = Field(31.8,  description="Ø centre (mm)")
    # Pour cintres plats / VTT
    grip_dia: float = Field(22.0,  description="Ø poignée (mm)")
    # Pour cintres route (drop)
    reach:    float = Field(80.0,  description="Reach cintre route (mm)")
    drop:     float = Field(125.0, description="Drop cintre route (mm)")
    # Angles
    alpha:    float = Field(0.0,   description="Rotation alpha (°)")
    theta:    float = Field(0.0,   description="Angle theta (°)")
    # Prolongateurs
    extend:   float = Field(0.0,   description="Extension (mm)")
    # Leviers
    include_brakes:  bool = Field(True, description="Inclure leviers de frein")
    lever_position:  float = Field(0.0, description="Position levier (°)")


# ─── SELLE ────────────────────────────────────────────────────────────────────

class SaddleConfig(BaseModel):
    standard: str   = Field("", description="Référence selle standard")
    # Dimensions BikeCAD A→N
    a: float = Field(0.0, description="Selle A (mm)")
    b: float = Field(0.0, description="Selle B (mm)")
    c: float = Field(0.0, description="Selle C (mm)")
    d: float = Field(0.0, description="Selle D (mm)")
    e: float = Field(0.0, description="Selle E (mm)")
    f: float = Field(0.0, description="Selle F (mm)")
    g: float = Field(0.0, description="Selle G (mm)")
    h: float = Field(0.0, description="Selle H (mm)")
    i: float = Field(0.0, description="Selle I (mm)")
    j: float = Field(0.0, description="Selle J (mm)")
    k: float = Field(0.0, description="Selle K (mm)")
    l: float = Field(0.0, description="Selle L (mm)")
    m: float = Field(0.0, description="Selle M (mm)")
    n: float = Field(0.0, description="Selle N (mm)")
    # Orientation / position
    angle:       float = Field(0.0,   description="Angle selle (°)")
    setback:     float = Field(0.0,   description="Recul selle (mm)")
    ref_point_x: float = Field(0.0,   description="Référence X (mm)")
    ref_point_y: float = Field(0.0,   description="Référence Y (mm)")
    length:      float = Field(270.0, description="Longueur selle (mm)")
    thickness:   float = Field(35.0,  description="Épaisseur selle (mm)")


# ─── TIGE DE SELLE ────────────────────────────────────────────────────────────

SeatpostStyle = Literal["standard", "dropper", "aero"]

class SeatpostConfig(BaseModel):
    style:        SeatpostStyle = Field("dropper", description="Type tige de selle")
    diameter:     float = Field(30.9, description="Ø tige de selle (mm)")
    length:       float = Field(440.0, description="Longueur totale (mm)")
    setback:      float = Field(0.0,   description="Recul (mm)")
    exposed:      float = Field(150.0, description="Longueur exposée (mm)")
    chord_length: float = Field(0.0,   description="Longueur corde (mm)")
    # Dropper
    travel:       float = Field(150.0, description="Course dropper (mm)")
    dropper_d2:   float = Field(0.0,   description="Ø corps dropper (mm)")
    dropper_d3:   float = Field(0.0,   description="Ø corps dropper D3 (mm)")


# ─── MANIVELLES ───────────────────────────────────────────────────────────────

class CranksConfig(BaseModel):
    standard:       str   = Field("", description="Référence manivelles standard")
    crank_length:   float = Field(165.0, description="Longueur manivelle (mm)")
    chainrings:     int   = Field(1,     description="Nombre plateaux (1-3)")
    teeth_0:        int   = Field(36,    description="Dents plateau 0")
    teeth_1:        int   = Field(0,     description="Dents plateau 1")
    teeth_2:        int   = Field(0,     description="Dents plateau 2")
    q_factor:       float = Field(168.0, description="Q-factor (mm)")
    width_at_bb:    float = Field(68.0,  description="Largeur aux pédaliers (mm)")
    width_at_pedal: float = Field(168.0, description="Largeur aux pédales (mm)")
    arm_thickness:  float = Field(12.0,  description="Épaisseur bras (mm)")
    spider_dia:     float = Field(64.0,  description="Ø araignée (mm)")
    spider_arm_width:float = Field(12.0, description="Largeur bras araignée (mm)")
    # L1-L4 (positions bras)
    l1: float = Field(0.0)
    l2: float = Field(0.0)
    l3: float = Field(0.0)
    l4: float = Field(0.0)
    # W1-W4 (largeurs intermédiaires)
    w1: float = Field(0.0)
    w2: float = Field(0.0)
    w3: float = Field(0.0)
    w4: float = Field(0.0)
    crank_clearance: float = Field(0.0, description="Jeu manivelle/base (mm)")
    chng_spacing:    float = Field(0.0, description="Espacement plateaux (mm)")
    chng_thick:      float = Field(0.0, description="Épaisseur plateau (mm)")


# ─── ROUES ────────────────────────────────────────────────────────────────────

class WheelConfig(BaseModel):
    standard:          str   = Field("", description="Standard roue")
    tire_diameter:     float = Field(736.0, description="Ø extérieur total (mm)")
    tire_width:        float = Field(61.0,  description="Largeur pneu (mm)")
    bead_seat_dia:     float = Field(622.0, description="BSD / diamètre ETRTO (mm)")
    effective_rim_dia: float = Field(614.0, description="Ø effectif jante (mm)")
    rim_depth:         float = Field(25.0,  description="Profil jante (mm)")
    rim_sidewall:      bool  = Field(True,  description="Montrer flanc jante")
    # Rayons
    spokes:            int   = Field(32,    description="Nombre de rayons")
    spoke_hole_dia:    float = Field(2.4,   description="Ø trou rayon (mm)")
    spoke_circ_dia:    float = Field(0.0,   description="Ø cercle de croisement (mm)")
    cross_pattern:     int   = Field(3,     description="Croisement rayons")
    hub_flange_dia_ds: float = Field(58.0,  description="Ø flasque DS (mm)")
    hub_flange_dia_nd: float = Field(58.0,  description="Ø flasque NDS (mm)")
    flange_dist_ds:    float = Field(17.0,  description="Distance flasque DS (mm)")
    flange_dist_nd:    float = Field(34.0,  description="Distance flasque NDS (mm)")
    spoke_offset:      float = Field(0.0,   description="Offset rayon (mm)")


# ─── PÉDALES ──────────────────────────────────────────────────────────────────

class PedalsConfig(BaseModel):
    style:     str   = Field("platform", description="Style pédales")
    standard:  str   = Field("",         description="Référence standard")
    length:    float = Field(115.0, description="Longueur pédale (mm)")
    width:     float = Field(105.0, description="Largeur pédale (mm)")
    thickness: float = Field(20.0,  description="Épaisseur pédale (mm)")


# ─── FREINS ───────────────────────────────────────────────────────────────────

BrakeStyle = Literal["disc_flat_mount", "disc_is", "disc_post_mount", "v_brake", "caliper"]

class BrakeConfig(BaseModel):
    style:       BrakeStyle = Field("disc_flat_mount")
    rotor_front: float = Field(203.0, description="Ø disque avant (mm)")
    rotor_rear:  float = Field(180.0, description="Ø disque arrière (mm)")
    mount_type:  str   = Field("flat_mount", description="Type de fixation")
    # Positions (BikeCAD AX/AY/BX/BY/PX/PY/L/D)
    ax: float = Field(0.0)
    ay: float = Field(0.0)
    bx: float = Field(0.0)
    by: float = Field(0.0)
    px: float = Field(0.0)
    py: float = Field(0.0)
    bl: float = Field(0.0)
    bd: float = Field(0.0)
    bw: float = Field(0.0)
    bh: float = Field(0.0)


# ─── TRANSMISSION ─────────────────────────────────────────────────────────────

DriveType = Literal["chain", "belt"]

GEARBOX_TYPES = {
    "bafang_m620":        "BafangM620",
    "bafang_mm520":       "BafangMM520",
    "bafang_m800":        "BafangM800",
    "bafang_mmg330":      "BafangMMG330250",
    "bosch_steel":        "BOSCH_STEEL_NODE_V23A",
    "bosch_alu":          "BOSCH_ALU_GEN4",
    "bosch_ti":           "BOSCH_TI_GEN4",
    "steps_6000":         "SHIMANO_STEPS_6000",
    "steps_6000_mc":      "SHIMANO_STEPS_6000_WITH_MOTOR_CABINET",
    "steps_8000":         "SHIMANO_STEPS_8000",
    "steps_8000_mc":      "SHIMANO_STEPS_8000_WITH_MOTOR_CABINET",
    "pinion_p118":        "PINIONP118",
    "pinion_p118_steel":  "PINIONP118withSTEEL_BRIDGE",
    "pinion_p118_paragon":"PINIONP118withParagonPP0001",
    "none":               "",
}

# Moyeux/boîtes à vitesses intégrées (IGH) sélectionnables. Données vérifiées
# (sites fabricants) — voir knowledge/bank.py. min_ratio = facteur de transmission
# primaire (plateau/pignon) minimal recommandé pour ne pas dépasser le couple moyeu.
IGH_TYPES = {
    "rohloff_14": {"label": "Rohloff SPEEDHUB 500/14", "gears": 14, "range_pct": 526.0,
                   "max_torque_nm": 130.0, "min_ratio": 1.90, "weight_g": 1820, "belt": True},
    "3x3_nine":   {"label": "3X3 NINE (3x3.bike)", "gears": 9, "range_pct": 554.0,
                   "max_torque_nm": 250.0, "min_ratio": 1.60, "weight_g": 2000, "belt": True},
}
TransmissionType = Literal["derailleur", "igh"]


class DrivetrainConfig(BaseModel):
    drive_type:  DriveType = Field("belt", description="Chaîne ou courroie")
    transmission: TransmissionType = Field("igh",
                   description="Type de transmission : dérailleur (cassette) ou IGH (moyeu à vitesses)")
    igh_model:   str       = Field("3x3_nine", description="Modèle IGH (voir IGH_TYPES) ou 'custom'")
    igh_gears:   int       = Field(14,    description="Nb vitesses IGH (si custom)")
    igh_range_pct:float    = Field(526.0, description="Étendue IGH % (si custom)")
    igh_max_torque_nm:float= Field(130.0, description="Couple d'entrée max moyeu (Nm, si custom)")
    motor_torque_nm: float = Field(150.0, description="Couple moteur au pédalier (Nm)")
    motor_key:   str       = Field("bafang_mm520", description="Clé moteur (voir GEARBOX_TYPES)")
    use_motor:   bool      = Field(True,  description="Afficher le moteur")
    motor_angle: float     = Field(0.0,   description="Angle moteur (°)")
    motor_x:     float     = Field(0.0,   description="Offset X moteur (mm)")
    motor_y:     float     = Field(0.0,   description="Offset Y moteur (mm)")
    # Belt Gates CDX
    belt_pitch:  float     = Field(11.0,  description="Pas courroie (mm)")
    belt_width:  float     = Field(11.0,  description="Largeur courroie (mm)")
    idler_x:     float     = Field(283.0, description="Position galet X (mm)")
    # Sprockets
    sprockets:   str       = Field("12-speed+10-50", description="Cassette")
    rear_cog_min:int       = Field(10,    description="Pignon min")
    rear_cog_max:int       = Field(50,    description="Pignon max")


# ─── SUSPENSION / CINÉMATIQUE (four-bar Horst Link) ─────────────────────────────
# NB : coordonnées MONDE (BB = origine, x = avant +, y = haut +, mm).
# Le fichier linkage_DOM_eMTB.txt utilise x = arrière + ; les défauts ci-dessous
# sont déjà convertis (x monde = -x linkage).

class Pivot(BaseModel):
    x: float = 0.0
    y: float = 0.0

class SuspensionConfig(BaseModel):
    enabled: bool = Field(True, description="Cadre tout-suspendu (sinon rigide)")
    linkage_type: Literal["four_bar_horst", "high_pivot_idler", "four_bar_generic"] = Field(
        "four_bar_horst",
        description="Topologie : four_bar_horst | high_pivot_idler | four_bar_generic (solveur par contraintes)",
    )

    # Pivots (coordonnées monde)
    main_pivot:        Pivot = Field(default_factory=lambda: Pivot(x=-10.0, y=18.0))
    horst_pivot:       Pivot = Field(default_factory=lambda: Pivot(x=-383.0, y=-23.0))
    upper_frame_pivot: Pivot = Field(default_factory=lambda: Pivot(x=18.0, y=295.0))
    upper_ss_pivot:    Pivot = Field(default_factory=lambda: Pivot(x=-62.0, y=250.0))

    # Amortisseur
    shock_lower:       Pivot = Field(default_factory=lambda: Pivot(x=-200.0, y=-12.0))
    shock_upper:       Pivot = Field(default_factory=lambda: Pivot(x=-8.0, y=185.0))
    shock_eye_to_eye:  float = Field(205.0, description="Entraxe amortisseur (mm)")
    shock_stroke:      float = Field(60.0,  description="Course amortisseur (mm)")
    shock_on_chainstay:bool  = Field(True,  description="Montage bas sur les bases (sinon rocker)")
    rear_travel:       float = Field(160.0, description="Course roue arrière cible (mm)")

    # Galet de renvoi courroie (sur les bases)
    idler:             Pivot = Field(default_factory=lambda: Pivot(x=-283.0, y=-18.0))
    idler_dia:         float = Field(32.0,  description="Ø galet (mm)")
    use_idler:         bool  = Field(True,  description="Galet de renvoi actif")

    # Transmission (pour belt growth + anti-squat)
    chainring_teeth:   int   = Field(36, description="Dents plateau")
    cog_teeth:         int   = Field(24, description="Dents pignon AR (moyeu)")
    belt_pitch:        float = Field(11.0, description="Pas courroie CDX (mm)")

    # Anti-squat
    cog_height:        float = Field(1100.0, description="Hauteur centre de gravité / sol (mm)")
    sag_percent:       float = Field(30.0,   description="Sag amortisseur (% course)")

    # Discrétisation
    samples:           int   = Field(33, description="Nombre de points sur la course")


# ─── RIDER ────────────────────────────────────────────────────────────────────

class RiderConfig(BaseModel):
    inseam:          float = Field(810.0, description="Entrejambe (mm)")
    lower_leg:       float = Field(380.0, description="Jambe basse (mm)")
    upper_leg:       float = Field(430.0, description="Jambe haute (mm)")
    torso_length:    float = Field(580.0, description="Longueur torse (mm)")
    upper_arm:       float = Field(300.0, description="Bras haut (mm)")
    lower_arm:       float = Field(260.0, description="Avant-bras (mm)")
    shoulder_width:  float = Field(410.0, description="Largeur épaules (mm)")
    shoe_length:     float = Field(270.0, description="Pointure (mm)")
    # Épaisseurs / morphologie
    pelvis_thickness:float = Field(200.0)
    knee_thickness:  float = Field(90.0)
    ankle_thickness: float = Field(65.0)
    elbow_thickness: float = Field(70.0)
    arm_thickness:   float = Field(80.0)
    forehead_to_back:float = Field(200.0)
    shoulder_to_jaw: float = Field(220.0)
    # Angles (calculés)
    hip_angle:       float = Field(0.0)
    knee_angle:      float = Field(0.0)
    torso_angle:     float = Field(0.0)
    shoulder_angle:  float = Field(0.0)
    elbow_angle:     float = Field(0.0)
    shoulder_roll:   float = Field(0.0)


# ─── BATTERIE ──────────────────────────────────────────────────────────────────
# Batterie e-bike logée dans le triangle avant (le long du tube diagonal).
# Repère monde : BB=(0,0), x avant +, y haut +, mm.

class BatteryConfig(BaseModel):
    enabled:    bool  = Field(True,   description="Batterie présente")
    voltage:    float = Field(52.0,   description="Tension nominale (V)")
    capacity_wh:float = Field(960.0,  description="Capacité (Wh)")
    # Encombrement du pack (vue de côté = length × height ; width = transversal)
    length:     float = Field(380.0,  description="Longueur du pack (mm)")
    height:     float = Field(90.0,   description="Hauteur du pack (mm)")
    width:      float = Field(90.0,   description="Largeur transversale (mm)")
    # Placement le long du tube diagonal (BB → couronne)
    mount_offset: float = Field(120.0, description="Décalage depuis le BB le long du tube diagonal (mm)")
    standoff:     float = Field(8.0,  description="Jeu entre la SURFACE du tube diagonal et le pack (mm)")
    in_downtube:  bool  = Field(False, description="Intégrée DANS le tube diagonal (sinon posée dessus)")
    # ── Alimentation / puissance (calculateur d'autonomie) ──────────────────────
    nominal_power_w: float = Field(500.0,  description="Puissance moteur nominale (W)")
    peak_power_w:    float = Field(1000.0, description="Puissance moteur crête (W)")
    consumption_whkm:float = Field(14.0,   description="Conso moyenne de référence (Wh/km)")


# ─── DESIGN COMPLET ───────────────────────────────────────────────────────────

class BikeDesign(BaseModel):
    name: str = Field("eMTB DOM Engineering", description="Nom du vélo")

    frame:      FrameGeometry   = Field(default_factory=FrameGeometry)
    fork:       ForkConfig      = Field(default_factory=ForkConfig)
    headtube:   HeadtubeConfig  = Field(default_factory=HeadtubeConfig)
    headset:    HeadsetConfig   = Field(default_factory=HeadsetConfig)
    stem:       StemConfig      = Field(default_factory=StemConfig)
    handlebar:  HandlebarConfig = Field(default_factory=HandlebarConfig)
    saddle:     SaddleConfig    = Field(default_factory=SaddleConfig)
    seatpost:   SeatpostConfig  = Field(default_factory=SeatpostConfig)
    cranks:     CranksConfig    = Field(default_factory=CranksConfig)
    wheel_f:    WheelConfig     = Field(default_factory=WheelConfig)
    wheel_r:    WheelConfig     = Field(default_factory=WheelConfig)
    pedals:     PedalsConfig    = Field(default_factory=PedalsConfig)
    brakes:     BrakeConfig     = Field(default_factory=BrakeConfig)
    drivetrain: DrivetrainConfig= Field(default_factory=DrivetrainConfig)
    suspension: SuspensionConfig= Field(default_factory=SuspensionConfig)
    battery:    BatteryConfig   = Field(default_factory=BatteryConfig)
    rider:      Optional[RiderConfig] = Field(None, description="Rider (optionnel)")


# ─── RÉSULTAT DES CALCULS ─────────────────────────────────────────────────────

class KeyPoint(BaseModel):
    x: float
    y: float

class CalcResult(BaseModel):
    # Géométrie principale (mm)
    reach:             float
    stack:             float
    trail:             float
    wheelbase:         float
    bb_height:         float
    front_center:      float
    tt_effective:      float
    standover:         float
    effective_sta:     float
    wheel_flop:        float
    front_normal_trail:float
    rear_normal_trail: float
    arctan_trail:      float

    # Points clés (coordonnées monde, BB=origine)
    bb:            KeyPoint
    rear_axle:     KeyPoint
    front_axle:    KeyPoint
    crown:         KeyPoint
    ht_top:        KeyPoint
    seat_tube_top: KeyPoint
    stem_base:     KeyPoint
    stem_tip:      KeyPoint
    handlebar_center: KeyPoint
    saddle_tip:    KeyPoint
    saddle_mid:    KeyPoint
    ground_level:  float   # Y de la ligne de sol (négatif, relatif au BB)


# ─── RÉSULTAT CINÉMATIQUE ──────────────────────────────────────────────────────

class KinematicSample(BaseModel):
    wheel_travel:  float  # course roue AR depuis topout (mm)
    shock_stroke:  float  # course amortisseur consommée (mm)
    shock_length:  float  # longueur amortisseur (mm)
    leverage:      float  # ratio de levier d(roue)/d(amorto)
    anti_squat:    float  # anti-squat (%)
    pedal_kickback:float = 0.0  # recul pédalier cumulé depuis topout (° manivelle)
    belt_growth:   float  # variation longueur courroie vs topout (mm)
    axle_x:        float  # position axe AR x (monde, mm)
    axle_y:        float  # position axe AR y (monde, mm)
    axle_dx:       float  # recul horizontal de l'axe vs topout (mm, + = recule)

class FitResult(BaseModel):
    ok:                  bool
    message:             str = ""
    # Cockpit
    saddle_height:       float = 0.0
    saddle_to_bar_reach: float = 0.0
    saddle_to_bar_drop:  float = 0.0
    leg_extension_pct:   float = 0.0
    # Angles articulaires (°)
    knee_angle_bdc:      Optional[float] = None
    hip_angle_tdc:       Optional[float] = None
    back_angle:          Optional[float] = None
    elbow_angle:         Optional[float] = None
    shoulder_angle:      Optional[float] = None
    kops_offset:         Optional[float] = None
    notes:               list[str] = []
    # Squelette (coordonnées monde)
    hip:      Optional[KeyPoint] = None
    knee:     Optional[KeyPoint] = None
    pedal:    Optional[KeyPoint] = None
    shoulder: Optional[KeyPoint] = None
    elbow:    Optional[KeyPoint] = None
    hand:     Optional[KeyPoint] = None
    head:     Optional[KeyPoint] = None


class BatteryResult(BaseModel):
    ok:              bool
    enabled:         bool = True
    fits_triangle:   bool = True      # le pack tient dans le triangle avant
    clears_motor:    bool = True      # pas de collision avec le carter moteur
    clears_tubes:    bool = True      # ne traverse pas tube de selle / direction
    polygon:         list = []        # 4 coins du pack (coords monde)
    volume_l:        float = 0.0      # volume du pack (litres)
    est_capacity_wh: float = 0.0      # capacité estimée d'après le volume
    # ── Calculateur alimentation / autonomie ────────────────────────────────────
    capacity_ah:      float = 0.0     # capacité (Ah) = Wh / V
    nominal_current_a:float = 0.0     # courant nominal = P_nom / V
    peak_current_a:   float = 0.0     # courant crête = P_crête / V
    c_rate_peak:      float = 0.0     # régime de décharge crête (C)
    runtime_nominal_h:float = 0.0     # autonomie à puissance nominale continue (h)
    runtime_peak_min: float = 0.0     # tenue à puissance crête (min)
    autonomy:         list = []       # [{mode, whkm, km}] éco/rando/boost + perso
    notes:           list[str] = []


class TransmissionResult(BaseModel):
    ok:               bool = True
    kind:             str = "derailleur"     # derailleur | igh
    label:            str = ""               # nom de l'IGH le cas échéant
    gears:            int = 0
    range_pct:        float = 0.0
    weight_g:         int = 0
    primary_ratio:    float = 0.0            # plateau/pignon
    hub_input_nm:     float = 0.0            # couple à l'entrée du moyeu
    max_torque_nm:    float = 0.0            # limite moyeu
    torque_ok:        bool = True
    ratio_ok:         bool = True
    min_ratio:        float = 0.0
    belt_ok:          bool = True            # compat courroie
    notes:            list[str] = []


class KinematicsResult(BaseModel):
    ok:               bool
    message:          str = ""
    samples:          list[KinematicSample] = []
    # Synthèse
    total_travel:     float = 0.0   # course roue totale (mm)
    leverage_start:   float = 0.0
    leverage_end:     float = 0.0
    leverage_sag:     float = 0.0
    progressivity:    float = 0.0   # (LR_start - LR_end)/LR_start * 100
    anti_squat_sag:   float = 0.0
    pedal_kickback_max:float = 0.0  # recul pédalier max sur la course (° manivelle)
    belt_growth_max:  float = 0.0
    axle_path_rearward:float = 0.0  # recul max de l'axe (mm)
    shock_stroke_used:float = 0.0   # course amortisseur réelle pour la course roue (mm)
    shock_stroke_spec:float = 0.0   # course amortisseur spécifiée (mm)
    # Dégagement carter moteur
    motor_clearance_ok:bool = True       # aucun hardpoint dans le carter moteur
    motor_collisions: list[str] = []     # noms des hardpoints en collision
    # Points pour tracé du schéma cinématique (positions au sag)
    pivots_world:     dict = {}
    # Frames d'animation : chaque entrée = géométrie monde de la suspension à un
    # pas de course. {travel, links:[[[x,y],[x,y]],...], shock:[[x,y],[x,y]],
    # axle:[x,y], idler:[x,y]|None}. Topout = frames[0].
    frames:           list[dict] = []
