"""Export de la visserie (chaque point de vis/boulon + type) : JSON, CSV
(nomenclature d'assemblage), résumé lisible. Couples = specs constructeur
de référence — prioriser toujours la valeur gravée sur la pièce."""
import json


def to_json(fres) -> str:
    return json.dumps(fres.model_dump(), indent=2, ensure_ascii=False)


def to_csv(fres) -> str:
    rows = ["Categorie,Jonction,Repere,X_mm,Y_mm,Taille,Empreinte,Qte,Couple_Nm,Note"]
    for it in fres.items:
        note = it.note.replace(",", ";")
        rows.append(f"{it.category},{it.name},{it.where},{it.x},{it.y},{it.size},"
                    f"{it.drive},{it.qty},{it.torque_nm},{note}")
    rows.append("")
    rows.append("Nomenclature,Taille,Empreinte,Qte")
    for b in fres.bom:
        rows.append(f",{b['size']},{b['drive']},{b['qty']}")
    return "\n".join(rows) + "\n"


def to_summary(fres) -> str:
    out = ["VISSERIE — points de vis/boulons par jonction", ""]
    cat = None
    for it in fres.items:
        if it.category != cat:
            cat = it.category
            out.append(f"── {cat.upper()} ──")
        out.append(f"■ {it.name}  @ ({it.x:.1f}, {it.y:.1f}) mm")
        out.append(f"    {it.qty}× {it.size}  empreinte {it.drive}  couple {it.torque_nm} Nm")
        if it.note:
            out.append(f"      {it.note}")
    out.append("")
    out.append("NOMENCLATURE :")
    for b in fres.bom:
        out.append(f"    {b['qty']}× {b['size']}  ({b['drive']})")
    out.append("")
    out += ["• " + n for n in fres.notes]
    return "\n".join(out)
