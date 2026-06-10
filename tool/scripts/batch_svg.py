#!/usr/bin/env python3
"""Pipeline batch : génère des SVG pour PLEIN de configs.
- tous les .bcad de BIKE/ (16.0 + 17.5) et du repo
- tous les vélos de la bibliothèque JSON (tool/bikes/*.bike.json)
Sortie : tool/out_svg/<nom>.svg
Lancer : cd tool && PYTHONPATH=. .venv/bin/python scripts/batch_svg.py
"""
import sys, json, glob, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.io.bcad_io import load_bcad
from backend.models.bike import BikeDesign
from backend.calculations.geometry import calculate
from backend.io.svg_export import render_svg

OUT = Path(__file__).resolve().parents[1] / "out_svg"
OUT.mkdir(exist_ok=True)
HOME = Path.home()

sources = []
for d in (HOME/"BikeCAD_16.0_configuration"/"BIKE", HOME/"BikeCAD_17.5_configuration"/"BIKE"):
    sources += [(p, "bcad") for p in sorted(d.glob("*.bcad"))]
for p in sorted((Path(__file__).resolve().parents[1]/"bikes").glob("*.bike.json")):
    sources += [(p, "json")]

n = 0
for path, kind in sources:
    try:
        if kind == "bcad":
            bike = load_bcad(path); name = path.stem
        else:
            bike = BikeDesign(**json.load(open(path))); name = path.stem
        calc = calculate(bike)
        svg = render_svg(bike, calc, 1400, 900, show_dims=True)
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
        n += 1
        print(f"  ✓ {name}")
    except Exception as e:
        print(f"  ✗ {path.name}: {e}")
print(f"\n{n} SVG générés dans {OUT}")
