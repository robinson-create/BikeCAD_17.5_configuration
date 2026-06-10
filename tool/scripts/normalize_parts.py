#!/usr/bin/env python3
"""Normalise les sprites allongés dans une orientation canonique réutilisable.

Les sprites bruts (fork, rear_shock, battery) ont l'angle du vélo source « cuit »
dedans (angle de direction, angle du tube diagonal…). On les ré-oriente via l'axe
principal (PCA) pour qu'ils soient placables sur une géométrie quelconque :

  - fork, rear_shock : axe principal VERTICAL, ancre d'origine (patte/œillet bas)
    ramenée à (0,0), corps au-dessus (+y).
  - battery          : axe principal HORIZONTAL, ancre = centre de la bbox.

Écrit <part>_norm.json à côté du brut. Le placement runtime (svg_export) n'a plus
qu'à : rotation cible + échelle + translation de l'ancre.
"""
import json, os, math, re

PARTS_DIR = os.path.join(os.path.dirname(__file__), "..", "refs", "bikecad_parts")
_NUM = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?')
_NPAIRS = {"M": 1, "L": 1, "T": 1, "Q": 2, "S": 2, "C": 3, "Z": 0, "H": 0, "V": 0}

CONFIG = {
    "fork":       {"axis": "v", "anchor": "origin", "method": "pca"},
    "rear_shock": {"axis": "v", "anchor": "origin", "method": "pca"},
    "battery":    {"axis": "h", "anchor": "center", "method": "minbox"},
}


def _points(d):
    pts, i, n, cmd = [], 0, len(d), None
    while i < n:
        c = d[i]
        if c.isalpha():
            cmd = c; i += 1; continue
        nums, j = [], i
        while j < n and not d[j].isalpha():
            m = _NUM.match(d, j)
            if m:
                nums.append(float(m.group())); j = m.end()
                while j < n and d[j] in ' ,\t\n\r': j += 1
            else:
                j += 1
        i = j
        if cmd in ("M", "L", "T"):
            for k in range(0, len(nums) - 1, 2): pts.append((nums[k], nums[k+1]))
        elif cmd == "C":
            for k in range(0, len(nums) - 5, 6):
                pts += [(nums[k], nums[k+1]), (nums[k+2], nums[k+3]), (nums[k+4], nums[k+5])]
        elif cmd in ("S", "Q"):
            for k in range(0, len(nums) - 3, 4):
                pts += [(nums[k], nums[k+1]), (nums[k+2], nums[k+3])]
    return pts


def _apply(d, fn):
    """Réécrit un path en appliquant fn(x,y)->(x,y) à chaque coordonnée."""
    res, i, n, cmd = [], 0, len(d), None
    while i < n:
        c = d[i]
        if c.isalpha():
            cmd = c; res.append(c); i += 1; continue
        m = _NUM.match(d, i)
        if not m:
            i += 1; continue
        nums, j = [], i
        while j < n and not d[j].isalpha():
            mm = _NUM.match(d, j)
            if mm:
                nums.append(float(mm.group())); j = mm.end()
                while j < n and d[j] in ' ,\t\n\r': j += 1
            else:
                j += 1
        i = j
        out = []
        for k in range(0, len(nums) - 1, 2):
            x, y = fn(nums[k], nums[k+1])
            out += [x, y]
        if len(nums) % 2:  # impair (ne devrait pas arriver ici) → garder tel quel
            out.append(nums[-1])
        res.append(" ".join(f"{v:.3f}" for v in out))
    return " ".join(res)


def principal_angle(pts):
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    sxx = sum((p[0]-cx)**2 for p in pts) / n
    syy = sum((p[1]-cy)**2 for p in pts) / n
    sxy = sum((p[0]-cx)*(p[1]-cy) for p in pts) / n
    # angle du vecteur propre dominant de la covariance [[sxx,sxy],[sxy,syy]]
    theta = 0.5 * math.atan2(2*sxy, sxx - syy)
    return theta, (cx, cy)


def flattest_angle(pts):
    """Orientation de l'axe long = celle qui minimise l'extension perpendiculaire
    (bbox le plus plat). Robuste pour une forme allongée asymétrique (capsule)."""
    best, best_h = 0.0, None
    steps = 360
    for k in range(steps):
        a = math.pi * k / steps          # 0..pi
        # extension perpendiculaire après rotation par -a : y' = -x*sin(a) + y*cos(a)
        ys = [-x*math.sin(a) + y*math.cos(a) for (x, y) in pts]
        h = max(ys) - min(ys)
        if best_h is None or h < best_h:
            best_h, best = h, a
    return best


def normalize(name):
    raw = json.load(open(os.path.join(PARTS_DIR, name + ".json"), encoding="utf-8"))
    cfg = CONFIG[name]
    allpts = []
    for sp in raw["paths"]:
        allpts += _points(sp["d"])
    if cfg.get("method") == "minbox":
        theta = flattest_angle(allpts)
        cx = sum(p[0] for p in allpts)/len(allpts); cy = sum(p[1] for p in allpts)/len(allpts)
    else:
        theta, (cx, cy) = principal_angle(allpts)
    # On veut amener l'axe principal sur vertical (90°) ou horizontal (0°).
    target = math.pi/2 if cfg["axis"] == "v" else 0.0
    rot = target - theta
    ca, sa = math.cos(rot), math.sin(rot)

    def R(x, y):  # rotation autour de l'origine locale
        return x*ca - y*sa, x*sa + y*ca

    # points après rotation pour décider du signe et de l'ancre
    rp = [R(x, y) for (x, y) in allpts]
    rcx = sum(p[0] for p in rp)/len(rp); rcy = sum(p[1] for p in rp)/len(rp)
    flip = False
    if cfg["anchor"] == "origin":
        # l'ancre d'origine = (0,0) ; on veut le corps AU-DESSUS (rcy > 0 après recentrage sur l'ancre)
        # l'ancre tournée :
        ax, ay = R(0.0, 0.0)  # = (0,0)
        if rcy - ay < 0:      # corps en dessous → flip 180°
            flip = True
    if flip:
        ca, sa = math.cos(rot+math.pi), math.sin(rot+math.pi)
        def R(x, y):
            return x*ca - y*sa, x*sa + y*ca
        rp = [R(x, y) for (x, y) in allpts]

    # ancre finale
    if cfg["anchor"] == "origin":
        ax, ay = R(0.0, 0.0)
    else:
        ax = (min(p[0] for p in rp)+max(p[0] for p in rp))/2
        ay = (min(p[1] for p in rp)+max(p[1] for p in rp))/2

    def T(x, y):
        rx, ry = R(x, y)
        return rx - ax, ry - ay

    paths = [{"d": _apply(sp["d"], T), "fill": sp.get("fill"), "stroke": sp.get("stroke")}
             for sp in raw["paths"]]
    np = [T(x, y) for (x, y) in allpts]
    bb = [min(p[0] for p in np), min(p[1] for p in np), max(p[0] for p in np), max(p[1] for p in np)]
    out = {"source": raw.get("source"), "from": name,
           "axis": cfg["axis"], "anchor_kind": cfg["anchor"],
           "rot_applied_deg": round(math.degrees(rot + (math.pi if flip else 0)), 2),
           "bbox_local": [round(v, 3) for v in bb],
           "size": [round(bb[2]-bb[0], 3), round(bb[3]-bb[1], 3)],
           "axis_len": round(bb[3]-bb[1] if cfg["axis"] == "v" else bb[2]-bb[0], 3),
           "paths": paths}
    json.dump(out, open(os.path.join(PARTS_DIR, name + "_norm.json"), "w"), indent=1)
    print(f"{name:12s} rot={out['rot_applied_deg']:+7.2f}°  size={out['size']}  bbox={out['bbox_local']}  anchor={cfg['anchor']}")


if __name__ == "__main__":
    for n in CONFIG:
        normalize(n)
