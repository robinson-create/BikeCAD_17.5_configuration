"""Tubes & lugs : géométrie (Ø ext / Ø int / paroi), matériau, propriétés de
SECTION (aire, inertie, module) et pré-dimensionnement INDICATIF de résistance.

Pour chaque membre du cadre on calcule :
  • Ø extérieur (donné), paroi (donné) → Ø INTÉRIEUR = OD − 2·paroi ;
  • aire A = π/4·(OD²−ID²), inertie I = π/64·(OD⁴−ID⁴), module Z = I/(OD/2) ;
  • masse = A·longueur·ρ (matériau) ;
  • capacité INDICATIVE : moment de flexion à la limite élastique M_y = Z·Re,
    effort axial F_y = A·Re.

⚠ HORS PÉRIMÈTRE : c'est de la pré-conception (propriétés de section + 1er ordre).
   Le dimensionnement FATIGUE / IMPACT validé (ISO 4210-6, EN 17404) reste au
   BUREAU D'ÉTUDES. Les capacités sont des ordres de grandeur, PAS une garantie.
"""
import math
from ..models.bike import MATERIALS, ADHESIVES


def _mat(key):
    return MATERIALS.get(key, MATERIALS["alu_6061_t6"])


def _adh(key):
    return ADHESIVES.get(key, ADHESIVES["dp460"])


def _section(od, wall):
    """Propriétés de section d'un tube creux (mm) : (id, A mm², I mm⁴, Z mm³)."""
    id_ = max(0.0, od - 2.0 * wall)
    a = math.pi / 4.0 * (od ** 2 - id_ ** 2)
    i = math.pi / 64.0 * (od ** 4 - id_ ** 4)
    z = i / (od / 2.0) if od > 0 else 0.0
    return id_, a, i, z


def compute_tubes(bike, calc, test_moment_nm: float = 0.0, test_tube: str = "down_tube",
                  adhesive: str = "dp460"):
    from ..models.bike import TubeResult, TubeSpec

    f = bike.frame
    P = {
        "bb": (calc.bb.x, calc.bb.y), "ht_top": (calc.ht_top.x, calc.ht_top.y),
        "crown": (calc.crown.x, calc.crown.y), "stt": (calc.seat_tube_top.x, calc.seat_tube_top.y),
        "axle": (calc.rear_axle.x, calc.rear_axle.y),
    }
    def L(a, b):
        return math.hypot(P[a][0] - P[b][0], P[a][1] - P[b][1])

    ht_len = f.head_tube + f.head_tube_upper_ext + f.head_tube_lower_ext
    # membre : (label, OD, paroi, longueur mm)
    members = [
        ("top_tube",  "Tube supérieur",  f.top_tube_d,  f.top_tube_wall,  L("stt", "ht_top")),
        ("down_tube", "Tube diagonal",   f.down_tube_d, f.down_tube_wall, L("bb", "crown")),
        ("seat_tube", "Tube de selle",   f.seat_tube_fd, f.seat_tube_wall, L("bb", "stt")),
        ("head_tube", "Tube direction",  f.head_tube_d, f.head_tube_wall, ht_len),
        ("chainstay", "Base",            f.chainstay_d, f.chainstay_wall, L("bb", "axle")),
        ("seatstay",  "Hauban",          f.seatstay_d,  f.seatstay_wall,  L("axle", "stt")),
    ]
    mat = _mat(f.frame_material)
    re = mat.get("re")          # MPa (None pour carbone)
    rho = mat["rho"]            # kg/m³
    adh = _adh(adhesive)
    tau = adh["tau_adm"]        # cisaillement admissible de calcul (MPa)

    tubes = []
    total_mass = 0.0
    for key, label, od, wall, length in members:
        id_, a, i, z = _section(od, wall)
        mass_g = a * length * rho / 1e9 * 1000.0            # mm³ → m³ (×1e-9), kg→g (×1000)
        total_mass += mass_g
        # capacités INDICATIVES (None si matériau sans limite élastique scalaire)
        m_y = (z * re / 1000.0) if re else 0.0              # Z[mm³]·Re[N/mm²] = N·mm → N·m
        f_y = (a * re) if re else 0.0                       # N
        # jonction collée : longueur d'insertion pour équilibrer joint ↔ tube,
        # L = Re·paroi / τ_adm ; surface = π·OD·L ; cisaillement admissible = τ_adm·π·OD·L
        if re and tau > 0:
            bl = re * wall / tau
            ba = math.pi * od * bl
            bs = tau * ba
        else:
            bl = ba = bs = 0.0
        note = "carbone anisotrope : capacité scalaire N/D" if re is None else ""
        tubes.append(TubeSpec(
            member=key, label=label, od=round(od, 1), id=round(id_, 1), wall=round(wall, 2),
            length=round(length, 1), material=f.frame_material,
            area_mm2=round(a, 1), inertia_mm4=round(i, 0), modulus_mm3=round(z, 1),
            mass_g=round(mass_g, 1), moment_yield_nm=round(m_y, 1), axial_yield_n=round(f_y, 0),
            bond_length_mm=round(bl, 1), bond_area_mm2=round(ba, 0), bond_shear_n=round(bs, 0),
            note=note,
        ))

    # ── Test de résistance INDICATIF : moment de flexion appliqué sur un tube ──
    # σ = M/Z ; facteur de sécurité FS = Re/σ. Cible FS ≥ 2 en statique pour un
    # organe roulant (indicatif). On vérifie aussi le joint collé du même tube.
    load_case = {}
    if test_moment_nm and test_moment_nm > 0:
        t = next((x for x in tubes if x.member == test_tube), tubes[1])
        if t.modulus_mm3 > 0 and re:
            sigma = test_moment_nm * 1000.0 / t.modulus_mm3   # N·m→N·mm / mm³ = MPa
            fs = re / sigma if sigma > 0 else 0.0
            load_case = {
                "name": f"Flexion {test_moment_nm:g} N·m sur {t.label}",
                "tube": test_tube, "moment_nm": round(test_moment_nm, 1),
                "sigma_mpa": round(sigma, 1), "re_mpa": re,
                "fs": round(fs, 2), "margin": round(fs - 1.0, 2), "ok": fs >= 2.0,
                "bond_length_mm": t.bond_length_mm,
            }

    lug = _mat(f.lug_material)
    notes = [
        "Ø intérieur = Ø extérieur − 2·paroi. Section : A=π/4(OD²−ID²), I=π/64(OD⁴−ID⁴), Z=I/(OD/2).",
        "Capacités = Z·Re (flexion) et A·Re (axial) à la LIMITE ÉLASTIQUE — ordres de grandeur 1er ordre. "
        "Critère ductile (acier/alu/Ti) = von Mises σ_vm ≤ Re/FS, viser FS ≥ 2 en statique.",
        f"Jonction lug-and-bond ({adh['label']}) : alésage = Ø tube + jeu de collage 0.05–0.15 mm ; "
        f"τ admissible de calcul ≈ {tau:g} MPa (réduit des {adh['tau_test']:g} MPa fiche, pour bords/fatigue/"
        "vieillissement humide). Longueur d'insertion conseillée L = Re·paroi/τ → joint aussi fort que le tube ; "
        "tenue collée = τ·π·OD·L. La tenue réelle du JOINT (adhésif, état de surface, recouvrement) prime souvent.",
        "Réf. ISO 4210-6 (VTT) — orientation d'essai, pas un calcul ici : fatigue pédalage F1 = 1200 N "
        "(120 000 cycles), impact masse tombante 22.5 kg / chute 360 mm, masses cadre M1=30/M2=10/M3=50 kg.",
        "⚠ HORS PÉRIMÈTRE : fatigue/impact/durée de vie (ISO 4210-6, EN 17404) = BUREAU D'ÉTUDES. "
        "Engin motorisé ~80 km/h : ces chiffres ne valident RIEN, ils orientent la pré-conception.",
    ]
    return TubeResult(
        ok=True, tubes=tubes, total_mass_g=round(total_mass, 0),
        frame_material=f.frame_material, lug_material=f.lug_material,
        lug_material_props={"label": lug["label"], "re": lug.get("re"), "rm": lug.get("rm"),
                            "E": lug["E"], "rho": lug["rho"]},
        adhesive=adhesive, bond_tau_adm=tau,
        load_case=load_case, notes=notes,
    )
