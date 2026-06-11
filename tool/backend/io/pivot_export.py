"""Export du hardware de pivots (roulements + axes) : JSON, CSV table de
conception SolidWorks, résumé lisible. Paramètres pour piloter une pièce
paramétrique (logements, axes) — pas de noyau CAO ici."""
import json


def to_json(pres) -> str:
    return json.dumps(pres.model_dump(), indent=2, ensure_ascii=False)


def to_csv(pres) -> str:
    rows = ["Pivot,Role,X_mm,Y_mm,Roulement,Alesage_mm,OD_mm,Largeur_mm,Qte,Logement_OD_mm,Axe_mm,Boulon,Note"]
    for p in pres.pivots:
        note = p.note.replace(",", ";")
        rows.append(f"{p.name},{p.role},{p.x},{p.y},{p.bearing},{p.bore},{p.od},"
                    f"{p.width},{p.qty},{p.housing_od},{p.axle_dia},{p.bolt},{note}")
    rows.append("")
    rows.append("Nomenclature,Reference,Qte,Dimensions,Type")
    for b in pres.bom:
        rows.append(f",{b['ref']},{b['qty']},{b['dims']},{b['type']}")
    return "\n".join(rows) + "\n"


def to_summary(pres) -> str:
    out = [f"PIVOTS — topologie {pres.topology} · couple axes {pres.torque_nm:g} Nm", ""]
    for p in pres.pivots:
        out.append(f"■ {p.name.upper()}  ({p.role})  @ ({p.x:.1f}, {p.y:.1f}) mm")
        out.append(f"    {p.qty}× {p.bearing}  Ø{p.bore:g}×{p.od:g}×{p.width:g} mm  "
                   f"logement Ø{p.housing_od:g}  axe Ø{p.axle_dia:g} ({p.bolt})")
        if p.note:
            out.append(f"      {p.note}")
        out.append("")
    out.append("NOMENCLATURE (roulements) :")
    for b in pres.bom:
        out.append(f"    {b['qty']}× {b['ref']}  ({b['dims']})  {b['type']}")
    out.append("")
    out += ["• " + n for n in pres.notes]
    return "\n".join(out)
