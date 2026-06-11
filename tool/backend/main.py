"""
FastAPI — DOM Engineering Bike Tool
Routes :
  POST /api/calc           → CalcResult
  POST /api/render/svg     → SVG string
  GET  /api/load/bcad      → BikeDesign chargé depuis un .bcad
  POST /api/export/bcad    → écrit un .bcad, retourne le chemin
  GET  /api/parts/{cat}    → liste des pièces catalogue (futur)
  GET  /api/default        → BikeDesign par défaut (eMTB DOM)
"""

import os
from pathlib import Path
from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from fastapi.responses import PlainTextResponse

from .models.bike import BikeDesign, CalcResult, KinematicsResult, FitResult, GEARBOX_TYPES, SuspensionConfig
from .presets import PRESETS
from .calculations.geometry import calculate
from .calculations.kinematics import solve_kinematics
from .calculations.fit import compute_fit
from .calculations.battery import compute_battery
from .io.bcad_io import load_bcad, save_bcad
from .io.svg_export import render_svg
from .io.dxf_export import export_dxf
from .io.drawing_export import render_drawing_svg
from .lugs.joint_model import build_joints
from .lugs import export_cad as lugs_export
from . import library
from . import catalog

app = FastAPI(title="DOM Engineering Bike Tool", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemins par défaut
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BCAD = REPO_ROOT / "BIKE" / "eMTB_DOM_Engineering.bcad"


def _repo_path(p):
    """Résout un chemin : absolu inchangé, relatif → depuis la racine du dépôt
    (le backend tourne avec CWD=tool/, donc 'BIKE/x' doit pointer la racine)."""
    if not p:
        return p
    q = Path(p)
    return str(q if q.is_absolute() else (REPO_ROOT / q))


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/default")
def get_default() -> BikeDesign:
    """Retourne le design eMTB DOM Engineering par défaut."""
    if DEFAULT_BCAD.exists():
        return load_bcad(DEFAULT_BCAD)
    return BikeDesign()


@app.post("/api/calc")
def calc_geometry(bike: BikeDesign) -> CalcResult:
    """Calcule la géométrie complète à partir d'un BikeDesign."""
    try:
        return calculate(bike)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class RenderRequest(BaseModel):
    bike: BikeDesign
    width: int = 1400
    height: int = 750
    show_dims: bool = True
    show_rider: bool = False
    show_suspension: bool = False    # overlay biellette sur la vue 2D
    animate_suspension: bool = False # animation SMIL de la course
    show_lugs: bool = False          # afficher les lugs CNC aux jonctions
    show_pivots: bool = False        # afficher roulements/axes aux pivots


@app.post("/api/render/svg")
def render(req: RenderRequest):
    """Calcule la géométrie et rend le SVG côté latérale."""
    try:
        calc = calculate(req.bike)
        fit = None
        if req.show_rider and req.bike.rider is not None:
            fit = compute_fit(req.bike, calc)
        frames = None
        if req.show_suspension and req.bike.suspension.enabled:
            kin = solve_kinematics(req.bike)
            if kin.ok:
                frames = kin.frames
        lug_nodes = build_joints(req.bike, calc) if req.show_lugs else None
        pivots = None
        if req.show_pivots and req.bike.suspension.enabled:
            from .calculations.pivots import compute_pivots
            pr = compute_pivots(req.bike)
            pivots = pr if pr.ok else None
        svg  = render_svg(req.bike, calc, req.width, req.height, req.show_dims, fit,
                          suspension=frames, animate_suspension=req.animate_suspension,
                          lugs=lug_nodes, pivots=pivots)
        return JSONResponse(content={"svg": svg, "calc": calc.model_dump()})
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/catalog")
def catalog_overview():
    """Racines BikeCAD détectées + nb de pièces par catégorie + total réglages."""
    return catalog.overview()


@app.get("/api/catalog/keys")
def catalog_keys(q: str = "", limit: int = 300):
    """Référence exhaustive des réglages BikeCAD (union), filtrée par sous-chaîne."""
    return catalog.setting_keys(q, limit)


@app.get("/api/catalog/{category}")
def catalog_list(category: str):
    """Liste (union multi-versions) des composants d'une catégorie."""
    return catalog.list_parts(category)


class CatalogLoadRequest(BaseModel):
    file: str


@app.post("/api/catalog/{category}/load")
def catalog_load(category: str, req: CatalogLoadRequest):
    """Retourne {section: patch} pour appliquer un composant catalogue."""
    part = catalog.load_part(category, req.file)
    if part is None:
        raise HTTPException(status_code=404, detail="Composant introuvable.")
    return part


@app.post("/api/battery")
def battery_endpoint(bike: BikeDesign):
    """Vérifie l'intégration de la batterie dans le triangle avant."""
    try:
        calc = calculate(bike)
        return compute_battery(bike, calc)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/transmission")
def transmission_endpoint(bike: BikeDesign):
    """Transmission : dérailleur/IGH, étendue, garde-fou couple moyeu."""
    from .calculations.transmission import compute_transmission
    try:
        return compute_transmission(bike)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/igh")
def igh_list():
    """Catalogue des moyeux à vitesses intégrées sélectionnables."""
    from .models.bike import IGH_TYPES
    return [{"key": k, **v} for k, v in IGH_TYPES.items()]


@app.post("/api/pivots")
def pivots_endpoint(bike: BikeDesign):
    """Hardware des pivots : roulements + axes + logements par pivot + nomenclature."""
    from .calculations.pivots import compute_pivots
    try:
        return compute_pivots(bike)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/bearings")
def bearings_list():
    """Catalogue de roulements de pivot sélectionnables."""
    from .models.bike import BEARING_CATALOG
    return [{"ref": k, **v} for k, v in BEARING_CATALOG.items()]


class PivotsExportRequest(BaseModel):
    bike: BikeDesign
    fmt: str = "csv"   # csv | json | summary


@app.post("/api/export/pivots")
def export_pivots(req: PivotsExportRequest):
    """Exporte le hardware de pivots (roulements/axes) en CSV/JSON/résumé."""
    from .calculations.pivots import compute_pivots
    from .io import pivot_export
    try:
        pres = compute_pivots(req.bike)
        if req.fmt == "json":
            return PlainTextResponse(pivot_export.to_json(pres), media_type="application/json")
        if req.fmt == "summary":
            return PlainTextResponse(pivot_export.to_summary(pres), media_type="text/plain")
        return PlainTextResponse(pivot_export.to_csv(pres), media_type="text/csv")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/fit")
def fit_endpoint(bike: BikeDesign) -> FitResult:
    """Calcule le fit pilote (angles articulaires, KOPS, reach/drop)."""
    try:
        calc = calculate(bike)
        return compute_fit(bike, calc)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class LoadRequest(BaseModel):
    path: str


@app.post("/api/load/bcad")
def load(req: LoadRequest) -> BikeDesign:
    """Charge un fichier .bcad depuis le chemin donné."""
    p = Path(req.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable : {p}")
    try:
        return load_bcad(p)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class ExportRequest(BaseModel):
    bike: BikeDesign
    path: str
    source_path: Optional[str] = None
    backup: bool = True
    free_safe: bool = True   # par défaut : .bcad ouvrable sans crash dans BikeCAD Free


@app.post("/api/export/bcad")
def export_bcad(req: ExportRequest):
    """Exporte un BikeDesign vers un fichier .bcad.
    free_safe=True (défaut) rétrograde la courroie en chaîne pour ne pas faire
    planter BikeCAD Free (BELTorCHAIN=2). La fidélité totale (courroie/suspension)
    reste dans la bibliothèque JSON."""
    try:
        # Résout les chemins relatifs depuis la RACINE du dépôt (le CWD = tool/).
        out = save_bcad(req.bike, _repo_path(req.path), _repo_path(req.source_path),
                        req.backup, req.free_safe)
        return {"path": str(out), "ok": True, "free_safe": req.free_safe}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/kinematics")
def kinematics(bike: BikeDesign) -> KinematicsResult:
    """Résout la cinématique four-bar (course, levier, anti-squat, belt growth)."""
    try:
        return solve_kinematics(bike)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class DxfRequest(BaseModel):
    bike: BikeDesign
    path: Optional[str] = None
    include_tubes: bool = True
    include_wheels: bool = True
    include_pivots: bool = True


@app.post("/api/export/dxf")
def export_dxf_route(req: DxfRequest):
    """Génère un DXF 2D. Si `path` est fourni, écrit le fichier ;
    sinon retourne le contenu DXF en texte brut (téléchargement client)."""
    try:
        calc = calculate(req.bike)
        dxf = export_dxf(req.bike, calc, req.include_tubes,
                         req.include_wheels, req.include_pivots)
        if req.path:
            p = Path(req.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(dxf, encoding="utf-8")
            return {"path": str(p), "ok": True, "bytes": len(dxf)}
        return PlainTextResponse(content=dxf, media_type="application/dxf")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class DrawingRequest(BaseModel):
    bike: BikeDesign
    designer: str = "Robinson Joubert"
    path: Optional[str] = None


@app.post("/api/export/drawing")
def export_drawing_route(req: DrawingRequest):
    """Plan technique d'ingénierie (SVG vectoriel) : cotation, axes, visserie,
    lugs, table de coordonnées, cartouche. Téléchargement client ou écriture disque."""
    from datetime import date as _date
    try:
        calc = calculate(req.bike)
        nodes = build_joints(req.bike, calc)
        svg = render_drawing_svg(req.bike, calc, nodes,
                                 project=req.bike.name, designer=req.designer,
                                 date=_date.today().isoformat())
        if req.path:
            p = Path(req.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(svg, encoding="utf-8")
            return {"path": str(p), "ok": True, "bytes": len(svg)}
        return PlainTextResponse(content=svg, media_type="image/svg+xml")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class SaveBikeRequest(BaseModel):
    bike: BikeDesign
    name: Optional[str] = None


@app.post("/api/library/save")
def library_save(req: SaveBikeRequest):
    """Sauvegarde LOSSLESS du BikeDesign complet (tous composants) en biblio."""
    try:
        p = library.save_bike(req.bike, req.name)
        return {"ok": True, "path": str(p), "file": p.name, "name": req.bike.name}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/library")
def library_list():
    """Liste les vélos de la bibliothèque native (JSON complet)."""
    return library.list_bikes()


class LibraryLoadRequest(BaseModel):
    name: str          # nom de fichier ou chemin dans la bibliothèque


@app.post("/api/library/load")
def library_load(req: LibraryLoadRequest) -> BikeDesign:
    """Charge un vélo COMPLET (tous composants, suspension comprise)."""
    try:
        return library.load_bike(req.name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/suspension/preset/{name}")
def suspension_preset(name: str) -> SuspensionConfig:
    """Retourne un preset de configuration suspension (ex. high_pivot_m620)."""
    factory = PRESETS.get(name)
    if factory is None:
        raise HTTPException(status_code=404, detail=f"Preset inconnu : {name}")
    return factory()


class LugsRequest(BaseModel):
    bike: BikeDesign
    bond_gap: float = 0.4
    insertion_factor: float = 1.5
    fmt: str = "json"          # json | csv | summary
    path: Optional[str] = None  # si fourni : écrit le fichier (csv/summary/json)


@app.post("/api/export/lugs")
def export_lugs(req: LugsRequest):
    """Calcule les nœuds-lugs (douilles, angles) et exporte JSON/CSV/résumé."""
    try:
        calc = calculate(req.bike)
        nodes = build_joints(req.bike, calc, req.bond_gap, req.insertion_factor)
        if req.fmt == "csv":
            content = lugs_export.to_design_table_csv(nodes)
        elif req.fmt == "summary":
            content = lugs_export.to_summary(nodes)
        else:
            content = lugs_export.to_json(nodes)
        if req.path:
            p = Path(req.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"path": str(p), "ok": True, "bytes": len(content)}
        if req.fmt == "json":
            return JSONResponse(content=lugs_export.to_dict(nodes))
        return PlainTextResponse(content=content, media_type="text/plain")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/motors")
def list_motors():
    """Liste les types de moteur disponibles."""
    return [{"key": k, "label": v} for k, v in GEARBOX_TYPES.items() if k != "none"]


@app.get("/api/bikes")
def list_bikes():
    """Liste les .bcad disponibles dans le dossier BIKE/."""
    bike_dir = REPO_ROOT / "BIKE"
    if not bike_dir.exists():
        return []
    return [
        {"name": p.stem, "path": str(p)}
        for p in sorted(bike_dir.glob("*.bcad"))
        if not p.name.endswith(".bak")
    ]


class AssistantRequest(BaseModel):
    messages: list[dict[str, Any]]   # [{role: "user"|"assistant", content: str}]
    bike: BikeDesign


@app.get("/api/assistant/available")
def assistant_available():
    """Indique si l'assistant est utilisable (clé API présente)."""
    return {"available": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.post("/api/assistant")
def assistant_endpoint(req: AssistantRequest):
    """Pilote le vélo via l'assistant (Claude + tool use). Retourne réponse,
    vélo mis à jour, et liste des actions effectuées."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Assistant indisponible : variable ANTHROPIC_API_KEY non configurée.")
    try:
        from .assistant import run_assistant
        import anthropic
        return run_assistant(req.messages, req.bike)
    except anthropic.AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Clé API Anthropic invalide.") from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Erreur API Anthropic : {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/health")
def health():
    return {"status": "ok", "tool": "DOM Engineering Bike Tool v1.0"}
