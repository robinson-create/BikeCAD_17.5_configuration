"""Export Tubes & Lugs : nomenclature des tubes (Ø ext/int, paroi, matériau,
section, masse, capacité INDICATIVE) en JSON / CSV / résumé."""
import json


def to_json(res) -> str:
    return json.dumps(res.model_dump(), indent=2, ensure_ascii=False)


def to_csv(res) -> str:
    rows = ["Membre,Label,OD_mm,ID_mm,Paroi_mm,Longueur_mm,Materiau,Aire_mm2,"
            "Inertie_mm4,Module_mm3,Masse_g,Moment_elastique_Nm,Axial_elastique_N,"
            "Collage_L_mm,Collage_surface_mm2,Collage_cisaillement_N,Note"]
    for t in res.tubes:
        note = t.note.replace(",", ";")
        rows.append(f"{t.member},{t.label},{t.od},{t.id},{t.wall},{t.length},{t.material},"
                    f"{t.area_mm2},{t.inertia_mm4:.0f},{t.modulus_mm3},{t.mass_g},"
                    f"{t.moment_yield_nm},{t.axial_yield_n:.0f},"
                    f"{t.bond_length_mm},{t.bond_area_mm2:.0f},{t.bond_shear_n:.0f},{note}")
    rows.append("")
    rows.append(f"Masse totale tubes (g),{res.total_mass_g}")
    rows.append(f"Materiau tubes,{res.frame_material}")
    rows.append(f"Materiau lugs,{res.lug_material}")
    rows.append(f"Adhesif,{res.adhesive},tau_adm_MPa,{res.bond_tau_adm}")
    if res.load_case:
        lc = res.load_case
        rows.append("")
        rows.append(f"Test resistance,{lc.get('name')},sigma_MPa,{lc.get('sigma_mpa')},"
                    f"Re_MPa,{lc.get('re_mpa')},marge,{lc.get('margin')},ok,{lc.get('ok')}")
    return "\n".join(rows) + "\n"


def to_summary(res) -> str:
    out = [f"TUBES & LUGS — tubes {res.frame_material}, manchons {res.lug_material} "
           f"({res.lug_material_props.get('label','')}), adhésif {res.adhesive} (τ_adm {res.bond_tau_adm:g} MPa)",
           f"Masse totale tubes : {res.total_mass_g:g} g", ""]
    for t in res.tubes:
        out.append(f"■ {t.label}  ({t.member})")
        out.append(f"    Ø {t.od} ext / {t.id} int  paroi {t.wall} mm  ·  L {t.length:g} mm  ·  {t.material}")
        out.append(f"    section A={t.area_mm2:g} mm²  I={t.inertia_mm4:.0f} mm⁴  Z={t.modulus_mm3:g} mm³  ·  {t.mass_g:g} g")
        if t.moment_yield_nm:
            out.append(f"    capacité INDICATIVE : flexion {t.moment_yield_nm:g} N·m, axial {t.axial_yield_n:.0f} N (limite élastique)")
        if t.bond_length_mm:
            out.append(f"    collage : insertion L≈{t.bond_length_mm:g} mm, surface {t.bond_area_mm2:.0f} mm², "
                       f"cisaillement adm. {t.bond_shear_n:.0f} N")
        if t.note:
            out.append(f"      {t.note}")
    if res.load_case:
        lc = res.load_case
        out.append("")
        out.append(f"TEST RÉSISTANCE (INDICATIF) : {lc.get('name')}")
        out.append(f"    σ = {lc.get('sigma_mpa')} MPa  vs  Re = {lc.get('re_mpa')} MPa  →  marge {lc.get('margin')} "
                   f"({'OK' if lc.get('ok') else 'INSUFFISANTE (<1.5)'})")
    out.append("")
    out += ["• " + n for n in res.notes]
    return "\n".join(out)
