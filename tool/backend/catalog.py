"""Catalogue EXHAUSTIF de pièces et réglages — fusion de toutes les configs BikeCAD.

Combine les bibliothèques de PLUSIEURS installs BikeCAD (Pro 16.0 + Free 17.5…) :
  • PIÈCES : union de toutes les catégories de composants (.bcad partiels), dédupliquées
    par fichier, taguées par version source. On parse chaque pièce via `load_bcad`
    (mappings déjà validés) → patch {section: valeurs} applicable au design.
  • MODÈLES : vélos complets (dossier BIKE/) comme presets de design entiers.
  • RÉGLAGES : référence exhaustive de toutes les clés BikeCAD (union sur les
    fichiers de référence), pour explorer/chercher tout l'espace de paramètres.

Racines auto-détectées dans $HOME (toutes celles qui existent), ordre Pro→Free.
Surcharge possible : BIKECAD_CONFIG_DIR = chemins séparés par ':'.
"""

import os
from pathlib import Path
from functools import lru_cache
from .io.bcad_io import load_bcad


# Catégorie → (sous-dossier, sections de BikeDesign à extraire). "bike" = design complet.
CATEGORIES = {
    "fork":      ("FORK",      ["fork"]),
    "saddle":    ("SADDLE",    ["saddle"]),
    "wheel":     ("WHEELS",    ["wheel_f", "wheel_r"]),
    "headset":   ("HEADSET",   ["headset"]),
    "headtube":  ("HEADTUBE",  ["headtube"]),
    "cranks":    ("CRANKS",    ["cranks"]),
    "stem":      ("STEM",      ["stem"]),
    "handlebar": ("HANDLEBAR", ["handlebar"]),
    "seatpost":  ("SEATPOST",  ["seatpost"]),
    "pedals":    ("PEDALS",    ["pedals"]),
    "bike":      ("BIKE",      None),          # None → design complet (preset)
}

# Catégories présentes dans BikeCAD mais sans mapping modèle (listées en référence)
REFERENCE_ONLY = ["SPROCKETS", "FRONTDISCBRAKE", "REARDISCBRAKE", "FRONTBRAKE",
                  "REARBRAKE", "REARDROPOUTS", "CARGO", "RACK", "PANNIERS",
                  "FRONTRACK", "FRONTCARGO", "LOWRIDER", "PEDALS"]


def _version_label(root: Path) -> str:
    """'BikeCAD_16.0_configuration' → '16.0'."""
    n = root.name
    for tok in n.replace("_", " ").split():
        if tok[:1].isdigit():
            return tok
    return n


def config_roots() -> list[Path]:
    """Toutes les racines de config BikeCAD existantes (Pro d'abord, puis Free)."""
    roots = []
    env = os.environ.get("BIKECAD_CONFIG_DIR")
    if env:
        roots += [Path(p) for p in env.split(":") if p]
    home = Path.home()
    for name in ("BikeCAD_16.0_configuration", "BikeCAD_17.5_configuration"):
        roots.append(home / name)
    # dédup + ne garder que les dossiers de config valides
    seen, out = set(), []
    for r in roots:
        rp = r.resolve()
        if rp in seen or not r.is_dir():
            continue
        if (r / "FORK").is_dir() or (r / "BIKE").is_dir():
            seen.add(rp)
            out.append(r)
    return out


def list_parts(category: str) -> list[dict]:
    """Union des pièces d'une catégorie sur toutes les racines.
    Chaque entrée : {name, file, sources:[versions]}."""
    if category not in CATEGORIES:
        return []
    folder = CATEGORIES[category][0]
    merged: dict[str, dict] = {}
    for root in config_roots():
        d = root / folder
        if not d.is_dir():
            continue
        ver = _version_label(root)
        for p in sorted(d.glob("*.bcad")):
            entry = merged.setdefault(
                p.name, {"name": p.name[:-5].replace("+", " "),
                         "file": p.name, "sources": []})
            if ver not in entry["sources"]:
                entry["sources"].append(ver)
    return sorted(merged.values(), key=lambda e: e["name"].lower())


def _find_file(folder: str, file: str) -> Path | None:
    safe = Path(file).name                  # anti path-traversal
    for root in config_roots():
        p = root / folder / safe
        if p.is_file():
            return p
    return None


def load_part(category: str, file: str) -> dict | None:
    """Patch applicable : {section: valeurs}. Pour 'bike' → {'__full__': design}."""
    if category not in CATEGORIES:
        return None
    folder, sections = CATEGORIES[category]
    path = _find_file(folder, file)
    if path is None:
        return None
    bd = load_bcad(path)
    if sections is None:                    # preset de vélo complet
        return {"__full__": bd.model_dump()}
    return {sec: getattr(bd, sec).model_dump() for sec in sections}


@lru_cache(maxsize=1)
def _all_keys() -> list[tuple[str, str]]:
    """Union triée de toutes les clés BikeCAD vues dans les vélos de référence."""
    import xml.etree.ElementTree as ET
    keys: dict[str, str] = {}
    for root in config_roots():
        for p in (root / "BIKE").glob("*.bcad"):
            try:
                for e in ET.parse(p).findall(".//entry"):
                    k = e.get("key", "")
                    if k and k not in keys:
                        keys[k] = (e.text or "")
            except Exception:
                continue
    return sorted(keys.items())


def setting_keys(query: str = "", limit: int = 300) -> dict:
    """Référence exhaustive des réglages BikeCAD, filtrée par sous-chaîne."""
    allk = _all_keys()
    q = query.lower().strip()
    rows = [{"key": k, "value": v} for k, v in allk if (not q or q in k.lower())]
    return {"total": len(allk), "matched": len(rows), "rows": rows[:limit]}


def overview() -> dict:
    """Racines détectées + nb de pièces par catégorie + total réglages."""
    roots = config_roots()
    return {
        "roots": [{"path": str(r), "version": _version_label(r)} for r in roots],
        "categories": {c: len(list_parts(c)) for c in CATEGORIES},
        "reference_categories": REFERENCE_ONLY,
        "total_settings": len(_all_keys()),
    }
