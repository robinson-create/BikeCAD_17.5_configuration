#!/usr/bin/env python3
"""Rend le vélo par défaut (et variantes) en SVG+PNG pour vérifier les sprites.
Usage: render_test.py [chain|belt|battery|susp] -> /tmp/rt_<variant>.png"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.models.bike import BikeDesign
from backend.calculations.geometry import calculate
from backend.calculations.kinematics import solve_kinematics
from backend.io.svg_export import render_svg
import cairosvg

variant = sys.argv[1] if len(sys.argv) > 1 else "chain"
bike = BikeDesign()
if variant in ("chain", "battery", "susp"):
    bike.drivetrain.drive_type = "chain"
if variant == "battery":
    bike.battery.enabled = True
calc = calculate(bike)

kw = dict(width=1400, height=750, show_dims=False)
if variant == "susp":
    try:
        kin = solve_kinematics(bike)
        kw["suspension"] = kin
    except Exception as e:
        print("kin err", e)

svg = render_svg(bike, calc, **kw)
out_svg = f"/tmp/rt_{variant}.svg"
open(out_svg, "w").write(svg)
cairosvg.svg2png(url=out_svg, write_to=f"/tmp/rt_{variant}.png", output_width=1400)
print(f"/tmp/rt_{variant}.png")

# Zoom optionnel : render_test.py <variant> <cx> <cy> <w>  (coords px sur 1400x750)
if len(sys.argv) >= 5:
    cx, cy, w = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    h = w * 750 / 1400
    vb = f'{cx-w/2:.0f} {cy-h/2:.0f} {w:.0f} {h:.0f}'
    zsvg = svg.replace('viewBox="0 0 1400 750"', f'viewBox="{vb}"')
    open(f"/tmp/rt_{variant}_zoom.svg", "w").write(zsvg)
    cairosvg.svg2png(url=f"/tmp/rt_{variant}_zoom.svg",
                     write_to=f"/tmp/rt_{variant}_zoom.png", output_width=900)
    print(f"/tmp/rt_{variant}_zoom.png")
