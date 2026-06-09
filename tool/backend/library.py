"""Bibliothèque de vélos — sauvegarde/chargement LOSSLESS du BikeDesign complet.

Le format .bcad (io/bcad_io) est une passerelle BikeCAD : il ne mappe pas tous
les champs de l'outil (la suspension/cinématique, la selle A→N, les offsets de
potence… ne sont PAS écrits → perdus au round-trip). Pour conserver l'INTÉGRALITÉ
d'un design (tous les composants, suspension comprise), on sérialise le BikeDesign
en JSON dans `tool/bikes/`. C'est le format natif de la bibliothèque.
"""

import re
from pathlib import Path
from .models.bike import BikeDesign

LIBRARY_DIR = Path(__file__).resolve().parents[1] / "bikes"
EXT = ".bike.json"


def _slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "velo").strip())
    return s.strip("_") or "velo"


def _safe_path(name_or_path: str) -> Path:
    """Résout vers un fichier DANS la bibliothèque (anti path-traversal)."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    p = Path(name_or_path)
    # On n'accepte qu'un nom de fichier (pas de chemin), résolu dans LIBRARY_DIR.
    fname = p.name
    if not fname.endswith(EXT):
        fname = _slug(fname.removesuffix(".json")) + EXT
    full = (LIBRARY_DIR / fname).resolve()
    if LIBRARY_DIR.resolve() not in full.parents:
        raise ValueError("Chemin hors de la bibliothèque.")
    return full


def save_bike(bike: BikeDesign, name: str | None = None) -> Path:
    """Écrit le BikeDesign complet en JSON. Retourne le chemin."""
    fname = _slug(name or bike.name) + EXT
    path = _safe_path(fname)
    path.write_text(bike.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_bike(name_or_path: str) -> BikeDesign:
    """Charge et VALIDE (Pydantic) un BikeDesign depuis la bibliothèque."""
    path = _safe_path(name_or_path)
    if not path.exists():
        raise FileNotFoundError(f"Vélo introuvable : {path.name}")
    return BikeDesign.model_validate_json(path.read_text(encoding="utf-8"))


def list_bikes() -> list:
    """Liste les vélos de la bibliothèque : [{name, path, file}]."""
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(LIBRARY_DIR.glob(f"*{EXT}")):
        try:
            bike = BikeDesign.model_validate_json(p.read_text(encoding="utf-8"))
            out.append({"name": bike.name, "path": str(p), "file": p.name})
        except Exception:
            continue
    return out
