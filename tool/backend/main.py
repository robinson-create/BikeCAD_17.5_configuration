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
from typing import Optional
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
from .io.bcad_io import load_bcad, save_bcad
from .io.svg_export import render_svg
from .io.dxf_export import export_dxf
from .lugs.joint_model import build_joints
from .lugs import export_cad as lugs_export

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


@app.post("/api/render/svg")
def render(req: RenderRequest):
    """Calcule la géométrie et rend le SVG côté latérale."""
    try:
        calc = calculate(req.bike)
        fit = None
        if req.show_rider and req.bike.rider is not None:
            fit = compute_fit(req.bike, calc)
        svg  = render_svg(req.bike, calc, req.width, req.height, req.show_dims, fit)
        return JSONResponse(content={"svg": svg, "calc": calc.model_dump()})
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


@app.post("/api/export/bcad")
def export_bcad(req: ExportRequest):
    """Exporte un BikeDesign vers un fichier .bcad."""
    try:
        out = save_bcad(req.bike, req.path, req.source_path, req.backup)
        return {"path": str(out), "ok": True}
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


@app.get("/api/health")
def health():
    return {"status": "ok", "tool": "DOM Engineering Bike Tool v1.0"}
