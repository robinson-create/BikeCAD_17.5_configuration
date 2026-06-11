"""Banque de connaissances vélo + recherche lexicale.

Entrées curées (domaine vélo + projet DOM e-MTB M620) + catalogue de pièces
BikeCAD scanné dans le dépôt. `search(query, k)` retourne les k entrées les plus
pertinentes par recouvrement de tokens (tags pondérés ×3).

Pour brancher une VRAIE base vectorielle plus tard : remplacer `_score()` par un
appel d'embeddings + similarité cosinus ; l'API `search()`/`entries()` ne change pas.
"""

import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# ── Connaissances curées ─────────────────────────────────────────────────────
CURATED = [
    {
        "id": "motor-m620", "title": "Moteur Bafang M620 (MM G510)",
        "tags": ["moteur", "m620", "bafang", "mid-drive", "gearbox", "couple", "puissance"],
        "text": ("Bafang M620 / MM G510.750/1000/1300.C : mid-drive à l'axe du BB, ISIS. "
                 "Puissance nominale 750/1000/1300 W, 48/52 V, couple ~150 Nm, IP65, EN14766. "
                 "Chain line 48 ou 70 mm. Encombrement carter latéral ≈ 234 × 140 mm, bossages "
                 "de fixation à R≈78.5 mm @61.42° et R≈58 mm @46° depuis l'axe BB → contrainte "
                 "forte de placement des pivots/galet (voir enveloppe motor.py, clé GEARBOX bafang_m620)."),
    },
    {
        "id": "belt-gates", "title": "Courroie Gates CDX",
        "tags": ["courroie", "belt", "gates", "cdx", "transmission", "galet", "idler", "belt growth"],
        "text": ("Gates CDX : courroie crantée carbone, pas (pitch) ≈ 11 mm. Ne tolère PAS de "
                 "variation de tension agressive : viser belt growth < 2 mm sur toute la course, "
                 "sinon saut de courroie / surcharge moyeu. Triangle arrière FENDU obligatoire pour "
                 "passer la courroie (cadre monobloc impossible). Le galet de renvoi est un guide, "
                 "pas un tendeur actif."),
    },
    {
        "id": "gearbox-hub", "title": "Moyeu à vitesses 3X3 NINE (3x3.bike)",
        "tags": ["gearbox", "moyeu", "3x3", "3x3nine", "igh", "transmission", "rapports", "courroie", "couple"],
        "text": ("3X3 NINE (H+B Hightech GmbH / 3X3 Bikes, DE) : moyeu ARRIÈRE à vitesses intégrées "
                 "(IGH), 9 rapports via 3 étages planétaires × 3 (= 3×3, d'où le nom). Étendue 554 %, "
                 "pas ≈ 24 % (larges, orienté e-bike). COUPLE D'ENTRÉE MAX ≈ 250 Nm (vs 130 Nm Rohloff) "
                 "→ encaisse les gros mid-drive type M620. ~2000 g. Axes 135 QR / 142×12 / 148×12 Boost, "
                 "alésage 12 mm, 32/36 trous, roues 20–29″. Chaîne OU courroie Gates (pignons Gates). "
                 "Sans vidange d'huile (graissé). Shifters : R9.S (mécanique, tirage R.SB) ou E9.XP "
                 "(électronique sans fil). Moyeu ≈900 $, kit méca ≈1485 $, kit e-shift ≈1765 $. "
                 "Masse non suspendue arrière (~2 kg) — n'aide pas à centraliser la masse ni à dégager "
                 "le carter moteur (≠ boîte au pédalier). Belt growth < 2 mm requis sur TOUS les rapports."),
    },
    {
        "id": "rohloff-speedhub", "title": "Rohloff SPEEDHUB 500/14",
        "tags": ["rohloff", "speedhub", "igh", "moyeu", "gearbox", "14", "courroie", "couple", "e-14", "transmission"],
        "text": ("Rohloff SPEEDHUB 500/14 : moyeu arrière IGH 14 rapports égaux (pas ~13,6 %), "
                 "étendue 526 %, rendement ~95–99 %, ~1700 g (moyeu) / ~1820 g installé. "
                 "COUPLE D'ENTRÉE MAX = 130 Nm AU MÉCANISME (moteur + pédalage combinés APRÈS la "
                 "réduction plateau/pignon, PAS au boîtier). Garde-fou e-MTB : respecter le facteur de "
                 "transmission MIN (plateau/pignon) ≥ 1,90 (pilote <100 kg) ou ≥ 2,50 (fort couple / "
                 ">100 kg / tandem) — avec un mid-drive 120–150 Nm, un primaire ~2,3 (ex. 42:18) ramène "
                 "l'entrée moyeu bien sous 130 Nm. Versions : CC/TS/EX, A12 (thru-axle 12 mm + boulons "
                 "M7), DB (disque Rohloff 4 trous). E-14 = passage ÉLECTRONIQUE (180 ms, coupure couple "
                 "moteur ; eShift Bosch Smart System / Panasonic, Direct Shift Bafang/Brose). "
                 "Courroie Gates via Splined Carrier L (réf. 8540L, pignon mini 15 t ; CDX:EXP 19/20/22 t). "
                 "Pignon chaîne M34×6 (13/15/16/17 t). Vidange huile : 25 ml init., 12,5 ml / 5000 km ou 1 an. "
                 "Homologué S-Pedelec 45 km/h. Moyeu rigide (axe plein/traversant) → chemin d'axe AR et "
                 "pedal kickback se calculent normalement."),
    },
    {
        "id": "shock-sizes", "title": "Amortisseurs (entraxe × course)",
        "tags": ["amortisseur", "shock", "coil", "air", "ressort", "eye-to-eye", "stroke"],
        "text": ("Tailles métriques courantes pour ce cadre : 205×60 et 185×55 mm (entraxe × course). "
                 "Coil = ressort linéaire (raideur k en N/mm ou lbs/in) ; Air = non linéaire (réglage "
                 "par pression + volume spacers). Course amorto requise = course roue / levier moyen. "
                 "Vérifier que la course amorto demandée ≤ course spécifiée (sinon revoir les ancrages)."),
    },
    {
        "id": "kin-anti-squat", "title": "Anti-squat (définition + cible)",
        "tags": ["anti-squat", "antisquat", "cinematique", "squat", "acceleration", "pedalage"],
        "text": ("Anti-squat (%) : réaction de la suspension à la force de chaîne/courroie sous "
                 "accélération. 100 % = la force de chaîne contre exactement le transfert de masse "
                 "(pas de squat). Cible e-MTB ~100–115 % au sag pour contrer le couple moteur. "
                 "Méthode : centre instantané (IC) + ligne du brin moteur (dernier segment, galet→pignon "
                 "s'il y a un galet) projetée sur la verticale de l'axe avant / hauteur du CG. INDICATIVE."),
    },
    {
        "id": "kin-kickback", "title": "Pedal kickback & belt growth",
        "tags": ["kickback", "pedal", "belt growth", "courroie", "manivelle", "cinematique"],
        "text": ("Belt/chain growth : allongement du brin moteur sur la course → pedal kickback = "
                 "recul des manivelles, en degrés ≈ deg(belt_growth / rayon_plateau). Sur un high-pivot "
                 "à galet, placer le galet PRÈS du pivot principal annule le belt growth (et donc le "
                 "kickback) : c'est la propriété clé pour préserver la courroie Gates."),
    },
    {
        "id": "kin-leverage", "title": "Ratio de levier & progressivité",
        "tags": ["levier", "leverage", "progressivite", "ratio", "cinematique", "talonnage"],
        "text": ("Ratio de levier LR = d(course roue)/d(course amorto). Progressivité = (LR_début − "
                 "LR_fin)/LR_début × 100 ; viser 20–30 % (LR décroissant) pour éviter le talonnage en "
                 "fin de course. Force amorto = force roue × LR (travail virtuel). LR au sag ~2.8–3.2 "
                 "pour un amorto 205×60 sur ce cadre."),
    },
    {
        "id": "kin-axle-path", "title": "Chemin d'axe & high-pivot",
        "tags": ["axle path", "chemin axe", "high-pivot", "recul", "rearward", "pivot"],
        "text": ("Chemin d'axe arrière : trajectoire de l'axe en compression. Un recul (rearward axle "
                 "path) améliore le franchissement. Plus le pivot principal est HAUT, plus l'axe recule. "
                 "High-pivot + galet = recul marqué + belt growth maîtrisé (galet près du pivot)."),
    },
    {
        "id": "sag-guide", "title": "Sag (réglage statique)",
        "tags": ["sag", "compression", "ressort", "raideur", "reglage", "pilote"],
        "text": ("Sag = enfoncement statique sous le poids pilote+vélo. Cible : 25–30 % de course "
                 "arrière, 15–20 % fourche. Sag roue = force_roue × LR² / raideur (coil). Force roue "
                 "≈ (m_pilote + m_vélo) × g × biais arrière (~60 % assis). Pilote réf DOM = 90 kg, "
                 "e-MTB ~25 kg. Régler le sag d'abord, puis détente/compression."),
    },
    {
        "id": "project-geo", "title": "Géométrie cible — e-MTB DOM",
        "tags": ["projet", "dom", "geometrie", "cible", "reach", "head angle", "emtb"],
        "text": ("e-MTB DOM Engineering : head angle 63.5–64°, seat angle eff. 77–78°, chainstay 435, "
                 "BB drop 30, reach ≈480 (roue réelle 752 mm → reach 482), head tube 120–125, "
                 "débattement 160 (V1) / 170 possible, roues 29″. Lugs CNC + tubes droits collés époxy, "
                 "M620 + courroie Gates + moyeu 3×3.bike (triangle arrière fendu)."),
    },
    {
        "id": "lugs", "title": "Cadre lug-and-bond (jonctions collées)",
        "tags": ["lugs", "jonction", "douille", "collage", "tube", "solidworks", "cnc"],
        "text": ("Cadre lug-and-bond : lugs CNC (Ti/Al) + tubes droits collés époxy aérospatiale. "
                 "Chaque douille de lug = axe (direction du tube), alésage (Ø tube + jeu de collage "
                 "~0.4 mm), profondeur d'insertion (~1.5× Ø tube). Bases/haubans écartés latéralement "
                 "→ finition 3D dans SolidWorks. Export via /api/export/lugs (JSON/CSV/résumé)."),
    },
]


@lru_cache(maxsize=1)
def _parts_catalogue() -> list:
    """Scanne le dépôt pour les pièces BikeCAD disponibles (une entrée par catégorie)."""
    cats = {
        "CRANKS": ("manivelles", ["manivelle", "crank", "pedalier"]),
        "SPROCKETS": ("pignons / plateaux", ["pignon", "plateau", "sprocket", "cassette"]),
        "FORK": ("fourches", ["fourche", "fork"]),
        "WHEELS": ("roues", ["roue", "wheel", "jante"]),
        "SADDLE": ("selles", ["selle", "saddle"]),
        "STEM": ("potences", ["potence", "stem"]),
        "HANDLEBAR": ("cintres", ["cintre", "handlebar", "guidon"]),
        "HEADSET": ("jeux de direction", ["jeu de direction", "headset"]),
        "SEATPOST": ("tiges de selle", ["tige de selle", "seatpost", "dropper"]),
        "PEDALS": ("pédales", ["pedale", "pedal"]),
        "REARDISCBRAKE": ("freins à disque AR", ["frein", "disque", "brake"]),
        "FRONTDISCBRAKE": ("freins à disque AV", ["frein", "disque", "brake"]),
    }
    out = []
    for d, (label, tags) in cats.items():
        path = REPO_ROOT / d
        if not path.is_dir():
            continue
        names = sorted(p.stem.replace("+", " ") for p in path.glob("*.bcad"))
        if not names:
            continue
        listing = ", ".join(names[:40]) + (" …" if len(names) > 40 else "")
        out.append({
            "id": f"parts-{d.lower()}", "title": f"Catalogue BikeCAD — {label} ({len(names)})",
            "tags": ["piece", "catalogue", "bibliotheque"] + tags,
            "text": f"Pièces {label} disponibles dans la bibliothèque BikeCAD du dépôt ({d}/) : {listing}.",
        })
    return out


@lru_cache(maxsize=1)
def _loaded_entries() -> list:
    """Entrées de connaissances chargées des JSON du dossier knowledge/
    (ex. geometry_dh.json : géométrie DH/enduro/e-MTB + Specialized). Format :
    liste de {id, title, tags, text}."""
    import json as _json
    here = Path(__file__).resolve().parent
    out = []
    for jf in sorted(here.glob("*.json")):
        try:
            data = _json.load(open(jf, encoding="utf-8"))
            if isinstance(data, list):
                out += [e for e in data if isinstance(e, dict) and e.get("text")]
        except Exception:
            continue
    return out


def entries() -> list:
    return CURATED + _loaded_entries() + _parts_catalogue()


def _tokens(s: str) -> list:
    return re.findall(r"[a-zà-ÿ0-9]+", s.lower())


def _score(query_tokens: set, entry: dict) -> int:
    body = _tokens(entry["title"] + " " + entry["text"])
    tagtok = _tokens(" ".join(entry.get("tags", [])))
    return sum(1 for t in body if t in query_tokens) + 3 * sum(1 for t in tagtok if t in query_tokens)


def search(query: str, k: int = 4) -> list:
    """Récupération lexicale : retourne les k entrées les plus pertinentes."""
    qt = set(_tokens(query))
    if not qt:
        return []
    scored = [(_score(qt, e), e) for e in entries()]
    scored = [(s, e) for s, e in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    return [{"title": e["title"], "text": e["text"], "score": s} for s, e in scored[:k]]
