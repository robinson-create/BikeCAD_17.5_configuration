"""
Import / Export BikeCAD .bcad — DOM Engineering Bike Tool
Assure la compatibilité totale avec BikeCAD 17.5

Le format .bcad est un XML Java Properties :
  <entry key="Head angle">64.0</entry>
"""

import xml.etree.ElementTree as ET
import shutil, math
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.bike import (
    BikeDesign, FrameGeometry, ForkConfig, HeadtubeConfig, HeadsetConfig,
    StemConfig, HandlebarConfig, SaddleConfig, SeatpostConfig,
    CranksConfig, WheelConfig, PedalsConfig, BrakeConfig, DrivetrainConfig,
    BatteryConfig, SuspensionConfig,
    GEARBOX_TYPES,
)


# ─── Mappage champs BikeDesign → clés BikeCAD ────────────────────────────────

# Toutes les clés ci-dessous sont les VRAIES clés BikeCAD 17.5 (vérifiées sur
# un fichier .bcad réel). Les champs sans clé BikeCAD native (ex. selle A→N,
# offsets de potence) ne sont volontairement PAS écrits, pour ne pas polluer
# le fichier avec des clés ignorées par BikeCAD.

FRAME_MAP = {
    "head_angle":          "Head angle",
    "seat_angle":          "Seat angle",
    "cs":                  "CS textfield",
    "bb_drop":             "BB textfield",
    "fcd":                 "FCD textfield",
    "seat_tube":           "Seat tube length",
    "head_tube":           "Head tube length textfield",
    "head_tube_upper_ext": "Head tube upper extension",
    "head_tube_lower_ext": "Head tube lower extension",
    "top_tube_d":          "Top tube diameter",
    "down_tube_d":         "Down tube diameter",
    "seat_tube_fd":        "Seat tube front diameter",
    "head_tube_d":         "Head tube diameter",
    "bb_width":            "BB length",
    "wheel_f":             "Wheel diameter front",
    "wheel_r":             "Wheel diameter rear",
}

FORK_MAP = {
    "travel":          "Fork travel",
    "sag":             "Fork sag",
    "a2c":             "FORK1L",
    "offset":          "FORK1R",
    "upper_stanchion": "FORK0L",
    "blade_width":     "FORK1W",
}

HEADTUBE_MAP = {
    "d_top":    "Head tube diameter",
}

HEADSET_MAP = {
    "spacers": "Headset spacers",
}

STEM_MAP = {
    "length":          "Stem length",
    "angle":           "Stem angle",
    "collar_height":   "Collar height",
    "collar_diameter": "Collar diameter",
}

# HBAR type : valeurs BikeCAD natives
HANDLEBAR_STYLE_MAP = {
    "flat_mtn":     "Generic BMX",
    "drop_anatomic":"Generic anatomic drop",
    "drop_compact": "Generic compact drop",
    "drop_ergo":    "Generic ergo drop",
    "bullhorn":     "Generic bullhorn",
    "track":        "Generic track",
    "BMX":          "Generic BMX",
}

CRANK_MAP = {
    "crank_length": "Crank length",
    "chainrings":   "Number of chainrings",
    "teeth_0":      "Teeth on chainring 0",
    "teeth_1":      "Teeth on chainring 1",
    "teeth_2":      "Teeth on chainring 2",
    "q_factor":     "Crank Q factor",
    "spider_dia":   "SPIDER_DIAMETER",
    "arm_thickness":"Crank thickness",
}

SADDLE_MAP = {
    "angle":       "Saddle angle",
    "length":      "Saddle length",
    "thickness":   "Saddle thickness",
    "ref_point_x": "SADDLE_REF_POINTX",
    "ref_point_y": "SADDLE_REF_POINTY",
}

SEATPOST_MAP = {
    "diameter":  "Seatpost diameter",
    "length":    "Seatpost LENGTH",
    "setback":   "Seatpost setback",
}

PEDAL_MAP = {
    "length":    "PEDAL_LENGTH",
    "width":     "Pedal width",
    "thickness": "Pedal thickness",
}


# ─── Lecture ──────────────────────────────────────────────────────────────────

def _parse_props(path: Path) -> dict[str, str]:
    """Lit un .bcad et retourne un dict {key: value}."""
    props: dict[str, str] = {}
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for entry in root.findall("entry"):
            k = entry.get("key", "")
            v = entry.text or ""
            props[k] = v
    except Exception as exc:
        raise ValueError(f"Impossible de lire {path}: {exc}") from exc
    return props


def _f(props: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(props.get(key, default))
    except (ValueError, TypeError):
        return default


def _b(props: dict, key: str, default: bool = False) -> bool:
    v = props.get(key, str(default)).strip().lower()
    return v in ("true", "1", "yes")


def _s(props: dict, key: str, default: str = "") -> str:
    return props.get(key, default)


def load_bcad(path: str | Path) -> BikeDesign:
    """Charge un fichier .bcad et retourne un BikeDesign."""
    p = Path(path)
    props = _parse_props(p)

    frame = FrameGeometry(
        head_angle          = _f(props, "Head angle",                  64.0),
        seat_angle          = _f(props, "Seat angle",                  78.0),
        cs                  = _f(props, "CS textfield",                435.0),
        bb_drop             = _f(props, "BB textfield",                 30.0),
        fcd                 = _f(props, "FCD textfield",               820.0),
        seat_tube           = _f(props, "Seat tube length",            423.0),
        head_tube           = _f(props, "Head tube length textfield",  125.0),
        head_tube_upper_ext = _f(props, "Head tube upper extension",     0.0),
        head_tube_lower_ext = _f(props, "Head tube lower extension",     0.0),
        top_tube_d          = _f(props, "Top tube diameter",            38.0),
        down_tube_d         = _f(props, "Down tube diameter",           44.0),
        seat_tube_fd        = _f(props, "Seat tube front diameter",     35.0),
        head_tube_d         = _f(props, "Head tube diameter",           44.0),
        bb_width            = _f(props, "BB length",                    68.0),
        wheel_f             = _f(props, "Wheel diameter front",        736.0),
        wheel_r             = _f(props, "Wheel diameter rear",         736.0),
    )

    fork = ForkConfig(
        travel          = _f(props, "Fork travel",  160.0),
        sag             = _f(props, "Fork sag",      40.0),
        a2c             = _f(props, "FORK1L",        570.8),
        offset          = _f(props, "FORK1R",         44.0),
        upper_stanchion = _f(props, "FORK0L",        425.0),
        blade_width     = _f(props, "FORK1W",         32.0),
        dual_crown      = _b(props, "DUAL_CROWN",    True),
        fork_style      = int(_f(props, "Fork style", 1)),
    )

    headtube = HeadtubeConfig(
        style    = "tapered",
        d_top    = _f(props, "Head tube diameter", 44.0),
        d_bottom = _f(props, "Head tube diameter", 56.0),
    )

    headset = HeadsetConfig(
        spacers     = _f(props, "Headset spacers", 20.0),
    )

    stem = StemConfig(
        length          = _f(props, "Stem length",     50.0),
        angle           = _f(props, "Stem angle",       6.0),
        collar_height   = _f(props, "Collar height",   25.0),
        collar_diameter = _f(props, "Collar diameter", 31.8),
    )

    # Style cintre (inverse du mappage)
    hbar_bcad_style = _s(props, "HBAR type", "Generic BMX")
    hbar_style = next(
        (k for k, v in HANDLEBAR_STYLE_MAP.items() if v == hbar_bcad_style),
        "flat_mtn"
    )
    handlebar = HandlebarConfig(
        style    = hbar_style,  # type: ignore
        width    = _f(props, "Handlebar width", 760.0),
        rise     = _f(props, "Mountain bar rise", 20.0),
        sweep    = _f(props, "Mountain bar sweep", 9.0),
        diameter = _f(props, "HBARDIA",         31.8),
        grip_dia = _f(props, "MTNGRIPDIA",      22.0),
        alpha    = _f(props, "HBARALPHA",        0.0),
        theta    = _f(props, "HBARTHETA",        0.0),
        extend   = _f(props, "HBAREXTEND",       0.0),
    )

    saddle = SaddleConfig(
        standard    = _s(props, "Saddle type", ""),
        angle       = _f(props, "Saddle angle",      0.0),
        ref_point_x = _f(props, "SADDLE_REF_POINTX", 0.0),
        ref_point_y = _f(props, "SADDLE_REF_POINTY", 0.0),
        length      = _f(props, "Saddle length",   270.0),
        thickness   = _f(props, "Saddle thickness", 35.0),
    )

    seatpost = SeatpostConfig(
        diameter     = _f(props, "Seatpost diameter",  30.9),
        length       = _f(props, "Seatpost LENGTH",   440.0),
        setback      = _f(props, "Seatpost setback",    0.0),
    )

    cranks = CranksConfig(
        crank_length  = _f(props, "Crank length",         165.0),
        chainrings    = int(_f(props, "Number of chainrings", 1)),
        teeth_0       = int(_f(props, "Teeth on chainring 0", 36)),
        teeth_1       = int(_f(props, "Teeth on chainring 1", 0)),
        teeth_2       = int(_f(props, "Teeth on chainring 2", 0)),
        q_factor      = _f(props, "Crank Q factor",       168.0),
        spider_dia    = _f(props, "SPIDER_DIAMETER",       64.0),
        arm_thickness = _f(props, "Crank thickness",       12.0),
    )

    def _wheel_from_props(side: str, default_dia: float) -> WheelConfig:
        suffix = "front" if side == "f" else "rear"
        return WheelConfig(
            tire_diameter     = _f(props, f"Wheel diameter {suffix}",      default_dia),
            tire_width        = _f(props, f"TIREWIDTH_{suffix.upper()}",    61.0),
            bead_seat_dia     = _f(props, f"BSD_{suffix.upper()}",         622.0),
            effective_rim_dia = _f(props, f"EFFECTIVE_RIM_DIA_{suffix.upper()}", 614.0),
            spokes            = int(_f(props, f"SPOKES_{suffix.upper()}", 32)),
            cross_pattern     = int(_f(props, f"CROSS_PATTERN_{suffix.upper()}", 3)),
            hub_flange_dia_ds = _f(props, f"HUB_FLANGE_DIA_{suffix.upper()}_DS", 58.0),
            hub_flange_dia_nd = _f(props, f"HUB_FLANGE_DIA_{suffix.upper()}_NDS",58.0),
            flange_dist_ds    = _f(props, f"FLANGEDIST_DS_{suffix.upper()}", 17.0),
            flange_dist_nd    = _f(props, f"FLANGEDIST_ND_{suffix.upper()}", 34.0),
        )

    wheel_f = _wheel_from_props("f", _f(props, "Wheel diameter front", 736.0))
    wheel_r = _wheel_from_props("r", _f(props, "Wheel diameter rear",  736.0))

    pedals = PedalsConfig(
        style    = _s(props, "Pedal style", "platform"),
        length   = _f(props, "PEDAL_LENGTH",  115.0),
        width    = _f(props, "Pedal width",   105.0),
        thickness= _f(props, "Pedal thickness", 20.0),
    )

    brakes = BrakeConfig()  # defaults, à enrichir si nécessaire

    motor_bcad = _s(props, "GEARBOXtype", "")
    motor_key = next((k for k, v in GEARBOX_TYPES.items() if v == motor_bcad), "none")
    belt_on   = (_s(props, "BELTorCHAIN", "1") == "2")
    drivetrain = DrivetrainConfig(
        drive_type  = "belt" if belt_on else "chain",
        # Un .bcad BikeCAD ne décrit PAS notre champ transmission : on choisit un
        # défaut COHÉRENT avec l'entraînement (courroie → moyeu IGH, chaîne →
        # dérailleur+cassette) pour ne pas plaquer un moyeu IGH sur un BMX/route.
        transmission = "igh" if belt_on else "derailleur",
        motor_key   = motor_key,
        use_motor   = _b(props, "USEgearbox", False),
        motor_angle = _f(props, "GEARBOXangle", 0.0),
        belt_pitch  = _f(props, "BELT_PITCH", 11.0),
        belt_width  = _f(props, "BELT_WIDTH", 11.0),
        idler_x     = _f(props, "REARCNTIshiftDX", 283.0),
        sprockets   = _s(props, "SPROCKETS type", "12-speed+10-50"),
    )

    return BikeDesign(
        name        = _s(props, "Name", p.stem) or p.stem,
        frame       = frame,
        fork        = fork,
        headtube    = headtube,
        headset     = headset,
        stem        = stem,
        handlebar   = handlebar,
        saddle      = saddle,
        seatpost    = seatpost,
        cranks      = cranks,
        wheel_f     = wheel_f,
        wheel_r     = wheel_r,
        pedals      = pedals,
        brakes      = brakes,
        drivetrain  = drivetrain,
        # Le .bcad ne contient PAS notre pack batterie (concept propre à l'outil
        # DOM) → on ne le force pas sur un vélo chargé (sinon batterie eMTB
        # 380 mm hors-cadre sur un BMX). La suspension reste au défaut : l'overlay
        # cinématique est opt-in (bouton), il n'encombre pas la vue 2D.
        battery     = BatteryConfig(enabled=False),
    )


# ─── Écriture ─────────────────────────────────────────────────────────────────

def save_bcad(
    bike: BikeDesign,
    path: str | Path,
    source_path: Optional[str | Path] = None,
    backup: bool = True,
    free_safe: bool = False,
) -> Path:
    """
    Exporte un BikeDesign vers un fichier .bcad.
    Si source_path est fourni, part du fichier existant (préserve les clés non gérées).

    free_safe : produit un fichier ouvrable SANS crash dans BikeCAD Free.
      BikeCAD Free plante sur BELTorCHAIN=2 (exception setSelectedIndex) → on
      rétrograde la transmission en chaîne (=1) dans le fichier exporté UNIQUEMENT.
      Le modèle interne et la bibliothèque JSON conservent la courroie ; le .bcad
      n'est qu'un export d'interop. (L'amortisseur / la cinématique restent non
      rendus par BikeCAD Free : ce sont des features Pro, hors de notre ressort.)
    """
    out = Path(path)

    # Charger les propriétés existantes si source disponible
    if source_path and Path(source_path).exists():
        props = _parse_props(Path(source_path))
    else:
        props = {}

    if backup and out.exists():
        bak = out.with_suffix(".bcad.bak")
        shutil.copy2(out, bak)

    # Écrire les valeurs du BikeDesign dans props
    f = bike.frame
    for attr, key in FRAME_MAP.items():
        props[key] = str(getattr(f, attr))

    fk = bike.fork
    for attr, key in FORK_MAP.items():
        props[key] = str(getattr(fk, attr))
    props["DUAL_CROWN"]   = str(fk.dual_crown).lower()
    props["Fork style"]   = str(fk.fork_style)
    props["SUSPENSION"]   = "true"

    headtube = bike.headtube
    for attr, key in HEADTUBE_MAP.items():
        props[key] = str(getattr(headtube, attr))

    hs = bike.headset
    for attr, key in HEADSET_MAP.items():
        props[key] = str(getattr(hs, attr))

    st = bike.stem
    for attr, key in STEM_MAP.items():
        props[key] = str(getattr(st, attr))

    props["HBAR type"] = HANDLEBAR_STYLE_MAP.get(bike.handlebar.style, "Generic BMX")
    hb = bike.handlebar
    props["Handlebar width"]    = str(hb.width)
    props["Mountain bar rise"]  = str(hb.rise)
    props["Mountain bar sweep"] = str(hb.sweep)
    props["HBARALPHA"]      = str(hb.alpha)
    props["HBARTHETA"]      = str(hb.theta)
    props["HBAREXTEND"]     = str(hb.extend)
    props["HBARDIA"]        = str(hb.diameter)
    props["MTNGRIPDIA"]     = str(hb.grip_dia)

    sd = bike.saddle
    for attr, key in SADDLE_MAP.items():
        props[key] = str(getattr(sd, attr))
    if sd.standard:
        props["Saddle type"] = sd.standard

    sp = bike.seatpost
    for attr, key in SEATPOST_MAP.items():
        props[key] = str(getattr(sp, attr))

    cr = bike.cranks
    for attr, key in CRANK_MAP.items():
        props[key] = str(getattr(cr, attr))

    pd = bike.pedals
    for attr, key in PEDAL_MAP.items():
        props[key] = str(getattr(pd, attr))

    dt = bike.drivetrain
    motor_bcad = GEARBOX_TYPES.get(dt.motor_key, "")
    props["GEARBOXtype"]     = motor_bcad
    props["USEgearbox"]      = str(dt.use_motor).lower()
    props["Display GEARBOX"] = str(dt.use_motor).lower()
    props["GEARBOXangle"]    = str(dt.motor_angle)
    # BikeCAD Free plante sur BELTorCHAIN=2 → en mode free_safe on force la chaîne.
    belt_export = (dt.drive_type == "belt") and not free_safe
    props["BELTorCHAIN"]     = "2" if belt_export else "1"
    if dt.sprockets:
        props["SPROCKETS type"] = dt.sprockets
    if belt_export:
        props["BELT_PITCH"]          = str(dt.belt_pitch)
        props["BELT_WIDTH"]          = str(dt.belt_width)
        props["CHAINSTAYASYMMETRIC"] = "true"
        props["REARCNTIXD"]          = "1"
        props["REARCNTIshiftDX"]     = str(dt.idler_x)
    else:
        props["CHAINSTAYASYMMETRIC"] = "false"
        props["REARCNTIXD"]          = "0"

    if bike.name:
        props["Name"] = bike.name

    # Générer le XML
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">',
        '<properties>',
        f'<comment>Generated by DOM Engineering Bike Tool on {datetime.now().strftime("%Y-%m-%d %H:%M")}</comment>',
    ]
    for key, val in sorted(props.items()):
        esc = (str(val)
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;")
               .replace('"', "&quot;"))
        lines.append(f'<entry key="{key}">{esc}</entry>')
    lines.extend(["</properties>", ""])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out
