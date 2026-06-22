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
    rows.append("NOMENCLATURE D'ACHAT (par spec) — total a commander")
    rows.append("Spec,Membres,Nombre,Longueur_totale_mm,Stock_conseille_mm,Masse_totale_g")
    for b in res.bom:
        members = "; ".join(b.get("members", []))
        rows.append(f"{b.get('stock_label')},{members},{b.get('count')},"
                    f"{b.get('total_length_mm')},{b.get('stock_length_mm')},{b.get('total_mass_g')}")
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
    if res.bom:
        out.append("NOMENCLATURE D'ACHAT (ce qu'il faut commander) :")
        for b in res.bom:
            out.append(f"  • {b.get('stock_label')}  ×{b.get('count')}  "
                       f"({'; '.join(b.get('members', []))})")
            out.append(f"      longueur totale {b.get('total_length_mm'):g} mm  →  "
                       f"barre conseillée {b.get('stock_length_mm'):g} mm (marge chute)  ·  "
                       f"{b.get('total_mass_g'):g} g")
        out.append("")
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


# ── Fiche de FABRICATION : tubes ↔ jonctions de lugs ─────────────────────────
# Joint la nomenclature des tubes (compute_tubes) aux nœuds-lugs (build_joints)
# pour donner, par tube, ses 2 extrémités : lug, emmanchement, alésage, et les
# angles inter-tubes au nœud → « savoir exactement quoi couper et assembler ».

def _ends_by_member(nodes):
    """member -> [(node_name, socket, node)] (ses extrémités équipées d'un lug)."""
    ends = {}
    for n in nodes:
        for s in n.sockets:
            ends.setdefault(s.member, []).append((n.name, s, n))
    return ends


def to_fabrication_csv(res, nodes) -> str:
    ends = _ends_by_member(nodes)
    rows = ["Membre,Label,Spec,Entraxe_mm,Bout1_lug,Bout1_emmanchement_mm,Bout1_alesage_mm,"
            "Bout2_lug,Bout2_emmanchement_mm,Bout2_alesage_mm,Masse_g"]
    for t in res.tubes:
        e = ends.get(t.member, [])
        c1 = e[0][1] if len(e) > 0 else None
        c2 = e[1][1] if len(e) > 1 else None
        n1 = e[0][0] if len(e) > 0 else "—"
        n2 = e[1][0] if len(e) > 1 else "—"
        spec = f"Ø{t.od:g}x{t.wall:g} {t.material}"
        rows.append(
            f"{t.member},{t.label},{spec},{t.length},"
            f"{n1},{c1.depth if c1 else '—'},{c1.bore_dia if c1 else '—'},"
            f"{n2},{c2.depth if c2 else '—'},{c2.bore_dia if c2 else '—'},{t.mass_g}")
    rows.append("")
    rows.append("ANGLES DE LUG (entre tubes a chaque noeud)")
    rows.append("Noeud,Paire,Angle_deg")
    for n in nodes:
        for key, ang in n.angles.items():
            rows.append(f"{n.name},{key.replace('|','/')},{ang}")
    return "\n".join(rows) + "\n"


def to_fabrication_summary(res, nodes) -> str:
    ends = _ends_by_member(nodes)
    out = [f"FICHE DE FABRICATION — TUBES & JONCTIONS",
           f"Tubes {res.frame_material} · manchons {res.lug_material} · adhésif {res.adhesive} "
           f"(τ_adm {res.bond_tau_adm:g} MPa)", ""]
    for t in res.tubes:
        e = ends.get(t.member, [])
        out.append(f"■ {t.label}  ·  Ø{t.od:g} × {t.wall:g} mm  ·  {t.material}")
        out.append(f"    entraxe nœud-à-nœud {t.length:g} mm  ·  Ø int {t.id:g} mm  ·  {t.mass_g:g} g")
        if e:
            for node_name, s, _ in e:
                out.append(f"    ↳ lug {node_name:13s} : emmanchement {s.depth:g} mm  ·  "
                           f"alésage Ø{s.bore_dia:g} (jeu collage)"
                           f"{'  [écart 3D]' if s.out_of_plane else ''}")
        else:
            out.append("    ↳ extrémités sans lug (membre articulé / bras oscillant — voir Pivots)")
        out.append("")
    out.append("ANGLES DE LUG (entre tubes, par nœud) :")
    for n in nodes:
        if not n.angles:
            continue
        out.append(f"  ● {n.name}")
        for key, ang in n.angles.items():
            out.append(f"      {key.replace('|', ' / '):26s} = {ang:.2f}°")
    out.append("")
    out.append("⚠ Entraxe = longueur des AXES (nœud-à-nœud). Longueur de COUPE réelle = "
               "entraxe corrigé de la géométrie du lug (corps + emmanchement) — à figer en CAO.")
    return "\n".join(out)
