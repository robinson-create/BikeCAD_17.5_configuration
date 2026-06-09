"""Export des lugs : JSON structuré, table de conception CSV (SolidWorks),
résumé lisible.

Pas d'export STEP (aucun noyau CAO disponible ici) : on exporte des PARAMÈTRES
qui pilotent une pièce paramétrique SolidWorks (équations / design table), plus
un JSON complet et un résumé. L'ingénieur construit le lug dans SW à partir de
ces cotes.
"""

import json


def to_dict(nodes) -> dict:
    return {
        "nodes": [
            {
                "name": n.name,
                "position": [round(n.x, 2), round(n.y, 2)],
                "sockets": [
                    {
                        "member": s.member,
                        "axis_deg": s.axis_deg,
                        "bore_dia": s.bore_dia,
                        "tube_od": s.tube_od,
                        "depth": s.depth,
                        "out_of_plane": s.out_of_plane,
                    } for s in n.sockets
                ],
                "angles_deg": n.angles,
            } for n in nodes
        ]
    }


def to_json(nodes) -> str:
    return json.dumps(to_dict(nodes), indent=2, ensure_ascii=False)


def to_design_table_csv(nodes) -> str:
    """CSV `Parameter,Value` consommable par une table/équations SolidWorks.
    Noms : <noeud>_<membre>_<axis|bore|depth> et <noeud>_angle_<A>_<B>."""
    rows = ["Parameter,Value,Unit"]
    for n in nodes:
        for s in n.sockets:
            base = f"{n.name}_{s.member}"
            rows.append(f"{base}_axis,{s.axis_deg},deg")
            rows.append(f"{base}_bore,{s.bore_dia},mm")
            rows.append(f"{base}_depth,{s.depth},mm")
        for key, ang in n.angles.items():
            safe = key.replace("|", "_")
            rows.append(f"{n.name}_angle_{safe},{ang},deg")
    return "\n".join(rows) + "\n"


def to_summary(nodes) -> str:
    """Tableau texte lisible (revue rapide)."""
    out = []
    for n in nodes:
        out.append(f"■ LUG {n.name.upper()}  @ ({n.x:.1f}, {n.y:.1f}) mm")
        for s in n.sockets:
            flag = "  [3D: écart latéral]" if s.out_of_plane else ""
            out.append(
                f"    douille {s.member:10s} axe {s.axis_deg:7.2f}°  "
                f"alésage Ø{s.bore_dia:.2f} (tube Ø{s.tube_od:.1f})  "
                f"insertion {s.depth:.1f} mm{flag}")
        for key, ang in n.angles.items():
            out.append(f"      angle {key:24s} = {ang:.2f}°")
        out.append("")
    return "\n".join(out)
