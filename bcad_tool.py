#!/usr/bin/env python3
"""
bcad_tool.py — Outil CLI pour lire, modifier et générer des fichiers BikeCAD .bcad
DOM Engineering / Robinson Joubert
"""

import xml.etree.ElementTree as ET
import re, sys, os, shutil, math
from pathlib import Path
from datetime import datetime

# ─── Types de moteurs disponibles dans BikeCAD ───────────────────────────────
GEARBOX_TYPES = {
    # Bafang
    "bafang_mm520":       "BafangMM520",       # M500/M510/M520/M620 — même encombrement
    "bafang_m800":        "BafangM800",         # Ultra Max (M820)
    "bafang_mmg330":      "BafangMMG330250",    # MM G330.250
    # Bosch
    "bosch_steel":        "BOSCH_STEEL_NODE_V23A",
    "bosch_alu":          "BOSCH_ALU_GEN4",
    "bosch_ti":           "BOSCH_TI_GEN4",
    # Shimano Steps
    "steps_6000":         "SHIMANO_STEPS_6000",
    "steps_6000_mc":      "SHIMANO_STEPS_6000_WITH_MOTOR_CABINET",
    "steps_8000":         "SHIMANO_STEPS_8000",
    "steps_8000_mc":      "SHIMANO_STEPS_8000_WITH_MOTOR_CABINET",
    # Pinion
    "pinion_p118":        "PINIONP118",
    "pinion_p118_steel":  "PINIONP118withSTEEL_BRIDGE",
    "pinion_p118_paragon":"PINIONP118withParagonPP0001",
}

# ─── Paramètres géométrie clés ────────────────────────────────────────────────
GEOMETRY_KEYS = {
    "head_angle":   "Head angle",
    "seat_angle":   "Seat angle",
    "cs":           "CS textfield",
    "bb_drop":      "BB textfield",
    "reach":        "FCD textfield",
    "seat_tube":    "Seat tube length",
    "head_tube":    "Head tube length textfield",
    "fork_travel":  "Fork travel",
    "fork_sag":     "Fork sag",
    "fork_a2c":     "FORK1L",
    "fork_offset":  "FORK1R",
    "dual_crown":   "DUAL_CROWN",
    "wheel_f":      "Wheel diameter front",
    "wheel_r":      "Wheel diameter rear",
    "bb_width":     "BB length",
    "chainring":    "Teeth on chainring 0",
    "belt":         "BELTorCHAIN",
    "belt_pitch":   "BELT_PITCH",
    "motor":        "GEARBOXtype",
    "use_motor":    "USEgearbox",
    "motor_angle":  "Bafangle",
    "top_tube_d":   "Top tube diameter",
    "down_tube_d":  "Down tube diameter",
    "seat_tube_fd": "Seat tube front diameter",
}


class BcadFile:
    """Lecture/écriture d'un fichier .bcad (Java Properties XML)."""

    def __init__(self, path: str):
        self.path = Path(path)
        self._props: dict[str, str] = {}
        if self.path.exists():
            self._load()

    def _load(self):
        tree = ET.parse(self.path)
        root = tree.getroot()
        for entry in root.findall('entry'):
            key = entry.get('key', '')
            val = entry.text or ''
            self._props[key] = val

    def get(self, key: str, default=None):
        return self._props.get(key, default)

    def set(self, key: str, value):
        self._props[key] = str(value)

    def get_float(self, key: str, default=0.0) -> float:
        try:
            return float(self._props.get(key, default))
        except (ValueError, TypeError):
            return default

    def geometry_summary(self) -> dict:
        """Retourne un résumé de la géométrie."""
        hta = self.get_float("Head angle")
        sta = self.get_float("Seat angle")
        cs  = self.get_float("CS textfield")
        bb  = self.get_float("BB textfield")
        fcd = self.get_float("FCD textfield")
        ht  = self.get_float("Head tube length textfield")
        st  = self.get_float("Seat tube length")
        ft  = self.get_float("Fork travel")
        a2c = self.get_float("FORK1L")
        rake= self.get_float("FORK1R")
        wf  = self.get_float("Wheel diameter front")

        # Reach = FCD - (offset horizontal de la fourche)
        hta_rad = math.radians(hta)
        fork_h  = a2c * math.sin(hta_rad)
        fork_dx = a2c * math.cos(hta_rad)
        reach_approx = fcd - fork_dx - rake * math.cos(hta_rad) - (wf / 2) * math.cos(hta_rad)

        return {
            "Head angle":        f"{hta}°",
            "Seat angle":        f"{sta}°",
            "Chainstay (CS)":    f"{cs} mm",
            "BB drop":           f"{bb} mm",
            "FCD (→ Reach)":     f"{fcd} mm",
            "Reach (estimé)":    f"{reach_approx:.0f} mm",
            "Seat tube":         f"{st} mm",
            "Head tube":         f"{ht} mm",
            "Fork travel":       f"{ft} mm",
            "A2C":               f"{a2c} mm",
            "Rake/Offset":       f"{rake} mm",
            "Dual crown":        self.get("DUAL_CROWN", "false"),
            "Wheel Ø front":     f"{wf} mm ({wf/25.4:.1f}\")",
            "Drive":             "Belt CDX" if self.get("BELTorCHAIN") == "2" else "Chain",
            "Motor":             self.get("GEARBOXtype", "none"),
            "Motor active":      self.get("USEgearbox", "false"),
        }

    def save(self, path: str = None, backup: bool = True):
        """Sauvegarde le fichier .bcad."""
        out = Path(path) if path else self.path
        if backup and out.exists():
            bak = out.with_suffix('.bcad.bak')
            shutil.copy2(out, bak)

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">',
            '<properties>',
            f'<comment>Generated by bcad_tool.py on {datetime.now().strftime("%Y-%m-%d %H:%M")}</comment>',
        ]
        for key, val in sorted(self._props.items()):
            escaped = (val
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
            lines.append(f'<entry key="{key}">{escaped}</entry>')
        lines.append('</properties>')
        lines.append('')

        out.write_text('\n'.join(lines), encoding='utf-8')
        return out

    def set_motor(self, motor_key: str, angle: float = 0.0,
                  offset_x: float = 0.0, offset_y: float = 0.0):
        """Configure le moteur/gearbox."""
        gtype = GEARBOX_TYPES.get(motor_key, motor_key)
        self.set("GEARBOXtype", gtype)
        self.set("USEgearbox", "true")
        self.set("Display GEARBOX", "true")
        self.set("Bafangle", str(angle))
        self.set("GEARBOX_X offset", str(offset_x))
        self.set("GEARBOX_Y offset", str(offset_y))
        self.set("GEARBOX_X offsetX", str(offset_x))
        self.set("GEARBOX_Y offsetX", str(offset_y))

    def set_geometry(self, **kwargs):
        """Configure la géométrie via les noms courts définis dans GEOMETRY_KEYS."""
        for short, val in kwargs.items():
            if short in GEOMETRY_KEYS:
                self.set(GEOMETRY_KEYS[short], str(val))
            else:
                self.set(short, str(val))

    def set_belt_drive(self, enabled: bool = True, pitch: float = 11.0,
                       width: float = 11.0, idler_x: float = 283.0):
        """Configure le Belt Drive Gates CDX."""
        self.set("BELTorCHAIN", "2" if enabled else "1")
        if enabled:
            self.set("BELT_PITCH", str(pitch))
            self.set("BELT_WIDTH", str(width))
            self.set("CHAINSTAYASYMMETRIC", "true")
            self.set("REARCNTIXD", "1")
            self.set("REARCNTIshiftDX", str(idler_x))
        else:
            self.set("CHAINSTAYASYMMETRIC", "false")
            self.set("REARCNTIXD", "0")

    @classmethod
    def create_emtb(cls, output_path: str, template_path: str = None) -> 'BcadFile':
        """Crée un nouveau fichier eMTB DOM Engineering à partir d'un template."""
        if template_path:
            shutil.copy2(template_path, output_path)
        bcad = cls(output_path)

        # ── Géométrie cible ──────────────────────────────────────────────────
        bcad.set_geometry(
            head_angle = 64.0,
            seat_angle = 78.0,
            cs         = 435.0,
            bb_drop    = 30.0,
            reach      = 820.0,   # FCD → Reach ≈ 480mm
            seat_tube  = 423.0,
            head_tube  = 125.0,
            top_tube_d = 38.0,
            down_tube_d= 44.0,
            seat_tube_fd = 35.0,
            bb_width   = 68.0,
        )
        bcad.set("Wheel diameter front", "736.0")   # 29 × 2.4"
        bcad.set("Wheel diameter rear",  "736.0")
        bcad.set("Top tube front center measure style", "1")

        # ── Fourche double couronne 160mm ─────────────────────────────────────
        bcad.set("Fork travel", "160.0")
        bcad.set("Fork sag",    "40.0")
        bcad.set("FORK1L",      "570.8")   # A2C
        bcad.set("FORK0L",      "425.0")   # Upper stanchion
        bcad.set("FORK1R",      "44.0")    # Rake
        bcad.set("DUAL_CROWN",  "true")
        bcad.set("Fork style",  "1")
        bcad.set("SUSPENSION",  "true")

        # ── Moteur Bafang M620 ≈ MM520 ───────────────────────────────────────
        bcad.set_motor("bafang_mm520", angle=0.0)

        # ── Guidon MTB ───────────────────────────────────────────────────────
        bcad.set("HBAR type", "Generic BMX")
        bcad.set("Number of chainrings", "1")
        bcad.set("Teeth on chainring 0", "36")

        return bcad


# ─── CLI ─────────────────────────────────────────────────────────────────────

def cmd_show(args):
    """Affiche la géométrie d'un fichier .bcad."""
    bcad = BcadFile(args[0])
    geo = bcad.geometry_summary()
    print(f"\n{'═'*52}")
    print(f"  {Path(args[0]).name}")
    print(f"{'═'*52}")
    for k, v in geo.items():
        print(f"  {k:<22} {v}")
    print(f"{'═'*52}\n")

def cmd_set(args):
    """Modifie une clé dans un fichier .bcad. Usage: set FILE KEY VALUE"""
    bcad = BcadFile(args[0])
    bcad.set(args[1], args[2])
    bcad.save()
    print(f"✓ {args[1]} = {args[2]}  →  {args[0]}")

def cmd_motor(args):
    """Configure le moteur. Usage: motor FILE MOTOR_TYPE [ANGLE]"""
    bcad = BcadFile(args[0])
    motor = args[1]
    angle = float(args[2]) if len(args) > 2 else 0.0
    bcad.set_motor(motor, angle=angle)
    bcad.save()
    gtype = GEARBOX_TYPES.get(motor, motor)
    print(f"✓ Moteur configuré: {gtype} (angle={angle}°)  →  {args[0]}")

def cmd_belt(args):
    """Configure le belt drive. Usage: belt FILE [on|off]"""
    bcad = BcadFile(args[0])
    enabled = (args[1].lower() in ('on', 'true', '1', 'yes')) if len(args) > 1 else True
    bcad.set_belt_drive(enabled)
    bcad.save()
    print(f"✓ Belt drive {'ON' if enabled else 'OFF'}  →  {args[0]}")

def cmd_list_motors(args):
    """Liste les moteurs disponibles."""
    print("\n  Moteurs disponibles (GEARBOXtype) :")
    print(f"  {'Clé courte':<22} {'Valeur BikeCAD'}")
    print(f"  {'─'*22} {'─'*35}")
    for short, full in GEARBOX_TYPES.items():
        mark = " ← M620 compatible" if "mm520" in short else ""
        print(f"  {short:<22} {full}{mark}")
    print()

def cmd_export_template(args):
    """Génère le template.bcad de BikeCAD avec notre eMTB."""
    conf_dir = "/Users/theodorelecointe/BikeCAD_17.5_configuration/BikeCAD_17.5_configuration"
    template = os.path.join(conf_dir, "template.bcad")
    src = args[0] if args else "/Users/theodorelecointe/BikeCAD_17.5_configuration/BIKE/eMTB_DOM_Engineering.bcad"

    bcad = BcadFile(src)
    # Version compatible BikeCAD Free (sans belt qui plante)
    bcad_free = BcadFile(src)
    bcad_free.set("BELTorCHAIN", "1")
    bcad_free.set("CHAINSTAYASYMMETRIC", "false")
    bcad_free.set("REARCNTIXD", "0")
    bcad_free.save(template)
    print(f"✓ Template BikeCAD mis à jour: {template}")

def cmd_keys(args):
    """Liste toutes les clés d'un fichier .bcad."""
    bcad = BcadFile(args[0])
    filter_str = args[1].upper() if len(args) > 1 else None
    count = 0
    for k, v in sorted(bcad._props.items()):
        if filter_str is None or filter_str in k.upper():
            print(f"  {k:<45} = {v}")
            count += 1
    print(f"\n  {count} clés affichées.")

def cmd_help(args):
    print("""
bcad_tool.py — Outil DOM Engineering pour fichiers BikeCAD

USAGE:
  python3 bcad_tool.py <commande> [arguments]

COMMANDES:
  show   FILE              Afficher la géométrie du fichier
  keys   FILE [FILTRE]     Lister toutes les clés (optionnel: filtre texte)
  set    FILE CLÉ VALEUR   Modifier une clé
  motor  FILE TYPE [ANGLE] Configurer le moteur
  belt   FILE [on|off]     Activer/désactiver le Belt Drive
  motors                   Lister les moteurs disponibles
  export FILE              Exporter vers template.bcad (BikeCAD Free)
  help                     Cette aide

EXEMPLES:
  python3 bcad_tool.py show BIKE/eMTB_DOM_Engineering.bcad
  python3 bcad_tool.py motor BIKE/eMTB_DOM_Engineering.bcad bafang_mm520
  python3 bcad_tool.py set BIKE/eMTB_DOM_Engineering.bcad "Head angle" 64.0
  python3 bcad_tool.py belt BIKE/eMTB_DOM_Engineering.bcad on
  python3 bcad_tool.py keys BIKE/eMTB_DOM_Engineering.bcad GEARBOX
  python3 bcad_tool.py motors
""")

COMMANDS = {
    "show":   cmd_show,
    "keys":   cmd_keys,
    "set":    cmd_set,
    "motor":  cmd_motor,
    "belt":   cmd_belt,
    "motors": cmd_list_motors,
    "export": cmd_export_template,
    "help":   cmd_help,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        cmd_help([])
        sys.exit(0)
    cmd = sys.argv[1]
    COMMANDS[cmd](sys.argv[2:])
