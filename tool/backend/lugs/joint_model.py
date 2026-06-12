"""Graphe de cadre → nœuds-lugs avec douilles.

Repère monde : BB=(0,0), x=avant +, y=haut +, mm (cohérent avec geometry.py).
Modèle 2D plan-sagittal : les angles de douille sont calculés dans le plan du
vélo. Les membres latéralement écartés (bases/haubans en triangle arrière fendu)
ont en plus un écart hors-plan → signalé par `out_of_plane=True`, à traiter en 3D
dans SolidWorks (l'angle 2D reste la projection utile).
"""

import math
from dataclasses import dataclass, field
from ..models.bike import BikeDesign
from ..models.bike import CalcResult


@dataclass
class Socket:
    member: str          # nom du tube
    axis_deg: float      # direction de l'axe de douille (° / horizontale, monde)
    bore_dia: float      # alésage de la douille (mm) = Ø tube + jeu de collage
    tube_od: float       # Ø extérieur du tube (mm)
    depth: float         # profondeur d'insertion (mm)
    out_of_plane: bool = False   # membre écarté latéralement (à finir en 3D)


@dataclass
class LugNode:
    name: str
    x: float
    y: float
    sockets: list = field(default_factory=list)
    angles: dict = field(default_factory=dict)   # "memberA|memberB" -> angle (°)


def _ang_deg(dx, dy):
    return math.degrees(math.atan2(dy, dx))


def _between(a, b):
    """Plus petit angle (°) entre deux directions données en degrés."""
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def build_joints(bike: BikeDesign, calc: CalcResult,
                 bond_gap: float = 0.4, insertion_factor: float = 1.5,
                 max_depth: float = 60.0) -> list:
    """Construit les nœuds-lugs. `bond_gap` = jeu de collage radial total (mm) ;
    profondeur d'insertion = insertion_factor × Ø tube, plafonnée à `max_depth`."""
    f = bike.frame
    P = {
        "bb":           (calc.bb.x, calc.bb.y),
        "head_top":     (calc.ht_top.x, calc.ht_top.y),
        "head_bottom":  (calc.crown.x, calc.crown.y),
        "seat_cluster": (calc.seat_tube_top.x, calc.seat_tube_top.y),
        "dropout":      (calc.rear_axle.x, calc.rear_axle.y),
    }

    OD = {
        "top_tube":  f.top_tube_d,
        "down_tube": f.down_tube_d,
        "seat_tube": f.seat_tube_fd,
        "head_tube": f.head_tube_d,
        "chainstay": f.chainstay_d,
        "seatstay":  f.seatstay_d,
    }

    # Nœud -> [(member, node_voisin, out_of_plane)]
    topology = {
        "head_top":     [("head_tube", "head_bottom", False),
                         ("top_tube",  "seat_cluster", False)],
        "head_bottom":  [("head_tube", "head_top", False),
                         ("down_tube", "bb", False)],
        "bb":           [("down_tube", "head_bottom", False),
                         ("seat_tube", "seat_cluster", False),
                         ("chainstay", "dropout", True)],
        "seat_cluster": [("seat_tube", "bb", False),
                         ("top_tube",  "head_top", False),
                         ("seatstay",  "dropout", True)],
        "dropout":      [("chainstay", "bb", True),
                         ("seatstay",  "seat_cluster", True)],
    }

    # TOUT-SUSPENDU : l'arrière n'est PAS un triangle bondé mais un bras oscillant
    # articulé (pivots → onglet Pivots). On ne pose donc des lugs que sur le
    # TRIANGLE AVANT (les bases/haubans ne sont pas collés au cadre).
    if getattr(bike.suspension, "enabled", False):
        topology.pop("dropout", None)
        topology["bb"] = [m for m in topology["bb"] if m[0] != "chainstay"]
        topology["seat_cluster"] = [m for m in topology["seat_cluster"] if m[0] != "seatstay"]

    nodes = []
    for name, members in topology.items():
        nx, ny = P[name]
        node = LugNode(name=name, x=nx, y=ny)
        for member, neighbour, oop in members:
            tx, ty = P[neighbour]
            axis = _ang_deg(tx - nx, ty - ny)
            od = OD[member]
            node.sockets.append(Socket(
                member=member,
                axis_deg=round(axis, 2),
                bore_dia=round(od + bond_gap, 2),
                tube_od=od,
                depth=round(min(insertion_factor * od, max_depth), 1),
                out_of_plane=oop,
            ))
        # Angles entre paires de douilles (angles du lug)
        for i in range(len(node.sockets)):
            for j in range(i + 1, len(node.sockets)):
                si, sj = node.sockets[i], node.sockets[j]
                key = f"{si.member}|{sj.member}"
                node.angles[key] = round(_between(si.axis_deg, sj.axis_deg), 2)
        nodes.append(node)
    return nodes
