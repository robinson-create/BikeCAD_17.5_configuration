"""
Export DXF (R12 ASCII) — DOM Engineering Bike Tool

Génère un DXF 2D de la silhouette du vélo (vue de côté) directement
importable dans SolidWorks (Insérer → DXF/DWG → esquisse 2D).

Format : AutoCAD R12 minimal (sections HEADER/TABLES/ENTITIES), sans
dépendance externe. Unités = mm. Repère monde : BB = (0,0), x avant +,
y haut +. Le DXF conserve ce repère (y vers le haut, comme SolidWorks).

Calques (layers) :
  GEOMETRY    points & axes de construction (lignes centrales)
  TUBES       contours des tubes (polylignes fermées)
  WHEELS      cercles pneus / jantes / axes
  PIVOTS      pivots de suspension + bielles (si tout-suspendu)
  DIMS_TEXT   repères texte
"""

import math
from ..models.bike import BikeDesign, CalcResult


# ─── Primitives DXF R12 ─────────────────────────────────────────────────────────

class _Dxf:
    def __init__(self):
        self.body = []

    def _pair(self, code, value):
        self.body.append(str(code))
        self.body.append(str(value))

    def line(self, x1, y1, x2, y2, layer="0"):
        self._pair(0, "LINE"); self._pair(8, layer)
        self._pair(10, f"{x1:.4f}"); self._pair(20, f"{y1:.4f}"); self._pair(30, 0.0)
        self._pair(11, f"{x2:.4f}"); self._pair(21, f"{y2:.4f}"); self._pair(31, 0.0)

    def circle(self, cx, cy, r, layer="0"):
        if r <= 0:
            return
        self._pair(0, "CIRCLE"); self._pair(8, layer)
        self._pair(10, f"{cx:.4f}"); self._pair(20, f"{cy:.4f}"); self._pair(30, 0.0)
        self._pair(40, f"{r:.4f}")

    def polyline(self, pts, layer="0", closed=True):
        if len(pts) < 2:
            return
        self._pair(0, "POLYLINE"); self._pair(8, layer)
        self._pair(66, 1)                 # vertices follow
        self._pair(70, 1 if closed else 0)
        for x, y in pts:
            self._pair(0, "VERTEX"); self._pair(8, layer)
            self._pair(10, f"{x:.4f}"); self._pair(20, f"{y:.4f}"); self._pair(30, 0.0)
        self._pair(0, "SEQEND")

    def text(self, x, y, h, s, layer="DIMS_TEXT"):
        self._pair(0, "TEXT"); self._pair(8, layer)
        self._pair(10, f"{x:.4f}"); self._pair(20, f"{y:.4f}"); self._pair(30, 0.0)
        self._pair(40, f"{h:.4f}"); self._pair(1, s)

    def render(self, layers):
        out = []
        # HEADER
        out += ["0", "SECTION", "2", "HEADER",
                "9", "$INSUNITS", "70", "4",   # 4 = millimètres
                "0", "ENDSEC"]
        # TABLES (calques)
        out += ["0", "SECTION", "2", "TABLES",
                "0", "TABLE", "2", "LAYER", "70", str(len(layers))]
        for name, color in layers.items():
            out += ["0", "LAYER", "2", name, "70", "0",
                    "62", str(color), "6", "CONTINUOUS"]
        out += ["0", "ENDTAB", "0", "ENDSEC"]
        # ENTITIES
        out += ["0", "SECTION", "2", "ENTITIES"]
        out += self.body
        out += ["0", "ENDSEC", "0", "EOF"]
        return "\n".join(out) + "\n"


# ─── Construction de tube (polygone rectangulaire le long d'un axe) ─────────────

def _tube_poly(p1, p2, dia):
    x1, y1 = p1; x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-6:
        return []
    nx, ny = -dy / L, dx / L
    r = dia / 2.0
    return [
        (x1 + nx * r, y1 + ny * r),
        (x2 + nx * r, y2 + ny * r),
        (x2 - nx * r, y2 - ny * r),
        (x1 - nx * r, y1 - ny * r),
    ]


# ─── Export principal ───────────────────────────────────────────────────────────

def export_dxf(bike: BikeDesign, calc: CalcResult,
               include_tubes=True, include_wheels=True,
               include_pivots=True) -> str:
    d = _Dxf()
    f = bike.frame

    bb        = (calc.bb.x, calc.bb.y)
    rear_axle = (calc.rear_axle.x, calc.rear_axle.y)
    front_axle= (calc.front_axle.x, calc.front_axle.y)
    crown     = (calc.crown.x, calc.crown.y)
    ht_top    = (calc.ht_top.x, calc.ht_top.y)
    st_top    = (calc.seat_tube_top.x, calc.seat_tube_top.y)

    # ── Lignes centrales (construction) ─────────────────────────────────────
    d.line(*rear_axle, *bb, "GEOMETRY")              # base
    d.line(*bb, *st_top, "GEOMETRY")                 # tube de selle
    d.line(*st_top, *ht_top, "GEOMETRY")             # tube horizontal
    d.line(*bb, *crown, "GEOMETRY")                  # tube diagonal
    d.line(*crown, *ht_top, "GEOMETRY")              # tube de direction
    d.line(*crown, *front_axle, "GEOMETRY")          # fourche
    d.line(*rear_axle, *st_top, "GEOMETRY")          # hauban (approx)

    # ── Contours des tubes ───────────────────────────────────────────────────
    if include_tubes:
        for p1, p2, dia in [
            (rear_axle, bb, f.chainstay_d),
            (bb, st_top, f.seat_tube_fd),
            (st_top, ht_top, f.top_tube_d),
            (bb, crown, f.down_tube_d),
            (crown, ht_top, f.head_tube_d),
            (rear_axle, st_top, f.seatstay_d),
        ]:
            poly = _tube_poly(p1, p2, dia)
            if poly:
                d.polyline(poly, "TUBES", closed=True)
        # Tube de direction (longueur réelle)
        d.circle(*ht_top, f.head_tube_d / 2, "TUBES")
        d.circle(*crown, f.head_tube_d / 2, "TUBES")
        # Boîtier de pédalier
        d.circle(*bb, f.bb_shell_d / 2, "TUBES")

    # ── Roues ────────────────────────────────────────────────────────────────
    if include_wheels:
        rf = f.wheel_f / 2.0
        rr = f.wheel_r / 2.0
        d.circle(*rear_axle, rr, "WHEELS")                 # pneu AR
        d.circle(*front_axle, rf, "WHEELS")                # pneu AV
        # jantes (approx BSD)
        d.circle(*rear_axle, bike.wheel_r.bead_seat_dia / 2, "WHEELS")
        d.circle(*front_axle, bike.wheel_f.bead_seat_dia / 2, "WHEELS")
        # axes (croix)
        for c in (rear_axle, front_axle):
            d.line(c[0] - 10, c[1], c[0] + 10, c[1], "WHEELS")
            d.line(c[0], c[1] - 10, c[0], c[1] + 10, "WHEELS")

    # ── Pivots de suspension + bielles ───────────────────────────────────────
    if include_pivots and bike.suspension.enabled:
        s = bike.suspension
        pivots = {
            "MAIN": (s.main_pivot.x, s.main_pivot.y),
            "HORST": (s.horst_pivot.x, s.horst_pivot.y),
            "UPPER_FRAME": (s.upper_frame_pivot.x, s.upper_frame_pivot.y),
            "UPPER_SS": (s.upper_ss_pivot.x, s.upper_ss_pivot.y),
            "SHOCK_LO": (s.shock_lower.x, s.shock_lower.y),
            "SHOCK_UP": (s.shock_upper.x, s.shock_upper.y),
        }
        for name, p in pivots.items():
            d.circle(p[0], p[1], 4, "PIVOTS")
            d.text(p[0] + 6, p[1] + 6, 8, name, "DIMS_TEXT")
        A = pivots["MAIN"]; B = pivots["HORST"]
        C = pivots["UPPER_SS"]; D = pivots["UPPER_FRAME"]
        d.line(*A, *B, "PIVOTS")     # bases
        d.line(*B, *C, "PIVOTS")     # haubans
        d.line(*C, *D, "PIVOTS")     # rocker
        d.line(*pivots["SHOCK_LO"], *pivots["SHOCK_UP"], "PIVOTS")  # amortisseur
        if s.use_idler:
            d.circle(s.idler.x, s.idler.y, s.idler_dia / 2, "PIVOTS")

    # ── Repère + cartouche ──────────────────────────────────────────────────
    d.circle(*bb, 3, "GEOMETRY")
    d.text(bb[0] + 8, bb[1] - 18, 10, "BB (0,0)", "DIMS_TEXT")
    info = (f"{bike.name}  |  reach {calc.reach:.0f}  stack {calc.stack:.0f}  "
            f"HTA {f.head_angle:.1f}  WB {calc.wheelbase:.0f}  trail {calc.trail:.0f} (mm)")
    d.text(rear_axle[0], calc.ground_level - 60, 16, info, "DIMS_TEXT")

    layers = {
        "GEOMETRY": 8, "TUBES": 7, "WHEELS": 5,
        "PIVOTS": 1, "DIMS_TEXT": 3,
    }
    return d.render(layers)
