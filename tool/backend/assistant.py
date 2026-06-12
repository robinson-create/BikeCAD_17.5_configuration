"""Assistant conversationnel qui PILOTE l'outil — DOM Engineering Bike Tool.

Claude API + tool use (boucle agentique manuelle, exécutée côté backend) : à
chaque requête, l'assistant peut appeler des outils qui modifient le BikeDesign
courant, recalculent la géométrie/cinématique, appliquent des presets, ou gèrent
la bibliothèque. Le vélo modifié est renvoyé au frontend qui rafraîchit l'UI.

Modèle : claude-opus-4-8 (SDK anthropic). Clé via ANTHROPIC_API_KEY.
Outils côté serveur uniquement (pas de container distant) → simple, sûr, rapide.
"""

import json
import math

import anthropic

from .models.bike import BikeDesign
from .calculations.geometry import calculate
from .calculations.kinematics import solve_kinematics
from .calculations.analysis import compute_sag, compression_state, wheel_axles
from . import library
from . import knowledge
from .presets import PRESETS

MODEL = "claude-opus-4-8"
MAX_LOOPS = 8

# Sections éditables et exemples de champs (pour le system prompt)
EDITABLE = {
    "frame": "head_angle, seat_angle, cs, bb_drop, fcd, seat_tube, head_tube, wheel_r, wheel_f",
    "fork": "travel, sag, a2c, offset",
    "suspension": ("linkage_type (four_bar_horst|high_pivot_idler|four_bar_generic), "
                   "rear_travel, sag_percent, shock_stroke, shock_eye_to_eye, use_idler, "
                   "idler_dia, chainring_teeth, cog_teeth, cog_height ; "
                   "pivots {x,y} via axis : main_pivot, horst_pivot, upper_frame_pivot, "
                   "upper_ss_pivot, shock_lower, shock_upper, idler"),
    "drivetrain": "motor_key (bafang_m620, ...), drive_type (belt|chain), use_motor, belt_pitch",
    "stem": "length, angle", "handlebar": "width, rise", "seatpost": "exposed, travel",
    "cranks": "crank_length", "wheel_r": "tire_diameter", "wheel_f": "tire_diameter",
}

TOOLS = [
    {
        "name": "set_parameters",
        "description": ("Modifier un ou plusieurs paramètres du vélo courant. Pour un pivot de "
                        "suspension {x,y}, fournir 'axis' (x ou y). Coordonnées monde : BB=(0,0), "
                        "x=avant +, y=haut +, mm."),
        "input_schema": {
            "type": "object",
            "properties": {
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {"type": "string"},
                            "field": {"type": "string"},
                            "axis": {"type": "string", "enum": ["x", "y"]},
                            "value": {"type": ["number", "string", "boolean"]},
                        },
                        "required": ["section", "field", "value"],
                    },
                }
            },
            "required": ["edits"],
        },
    },
    {
        "name": "apply_preset",
        "description": "Appliquer un preset de configuration (ex. high_pivot_m620 = single-pivot haut M620).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "enum": list(PRESETS.keys())}},
            "required": ["name"],
        },
    },
    {
        "name": "get_state",
        "description": "Recalculer et lire l'état courant : géométrie (reach/stack/WB...), "
                       "cinématique (course/levier/anti-squat/belt growth/kickback/recul axe), "
                       "dégagement carter moteur.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "compute_sag",
        "description": ("Calculer le sag arrière statique (ressort coil linéaire). Donner la raideur "
                        "(spring_rate_n_per_mm) pour obtenir le sag mm/%, OU target_sag_pct pour obtenir "
                        "la raideur requise. Masses/biais ont des défauts (pilote 90 kg, vélo 25 kg, "
                        "biais AR 60 %)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "rider_mass_kg": {"type": "number"},
                "bike_mass_kg": {"type": "number"},
                "rear_bias_pct": {"type": "number"},
                "spring_rate_n_per_mm": {"type": "number"},
                "target_sag_pct": {"type": "number"},
            },
        },
    },
    {
        "name": "compression_state",
        "description": ("Lire l'état de la suspension à une compression donnée : au sag (at_sag=true), "
                        "à un % de course (at_pct), ou à une course en mm (at_mm). Retourne levier, "
                        "anti-squat, belt growth, kickback, position et recul de l'axe."),
        "input_schema": {
            "type": "object",
            "properties": {
                "at_sag": {"type": "boolean"},
                "at_pct": {"type": "number"},
                "at_mm": {"type": "number"},
            },
        },
    },
    {
        "name": "wheel_axles",
        "description": "Positions des axes AV/AR, contacts au sol, empattement, et chemin d'axe AR "
                       "sur la course (cinématique).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_knowledge",
        "description": ("Interroger la banque de connaissances vélo (récupération RAG BM25) : specs M620, "
                        "amortisseurs, courroie Gates, gearbox, concepts cinématique, cibles du projet DOM, "
                        "catalogue de pièces BikeCAD du dépôt, ET les DOCUMENTS sources ingérés (PDF/txt/md "
                        "déposés dans knowledge/docs/, ex. exports NotebookLM). Utiliser pour toute spec, "
                        "pièce, ou rappel de méthode. Quand un extrait vient d'un document (champ 'source'), "
                        "CITER la source et la page dans la réponse."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_velo_db",
        "description": ("Interroger la BASE VÉLO DISTANTE (QDRANT du projet latelier, ~1,7 M de chunks : "
                        "manuels, docs SAV, fiches produits — Shimano, SRAM, Gates, Rohloff, Bafang, etc.). "
                        "Recherche SÉMANTIQUE (embeddings Voyage). À utiliser SI BESOIN quand la banque locale "
                        "(search_knowledge) ne suffit pas : spec composant précise, compatibilité, procédure SAV, "
                        "valeur constructeur. Formuler la requête en ANGLAIS de préférence (corpus surtout EN). "
                        "Chaque hit porte source/page/marque/modèle → CITER. Indisponible si non configuré "
                        "(renvoie un message ; ne pas réessayer en boucle)."),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_library",
        "description": "Lister les vélos sauvegardés en bibliothèque.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "save_bike",
        "description": "Sauvegarder le vélo courant (complet, tous composants) en bibliothèque.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "load_bike",
        "description": "Charger un vélo de la bibliothèque (remplace le vélo courant). "
                       "Donner le nom de fichier renvoyé par list_library.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
]


def _system_prompt(state_summary: str) -> str:
    fields = "\n".join(f"  - {sec} : {f}" for sec, f in EDITABLE.items())
    return (
        "Tu es l'assistant de conception du DOM Engineering Bike Tool (remplacement maison de "
        "BikeCAD pour un e-MTB custom Bafang M620, courroie Gates). Langue : français.\n\n"
        "Tu PILOTES l'outil via les outils fournis : modifier des paramètres (set_parameters), appliquer "
        "un preset, recalculer l'état (get_state), calculer le SAG (compute_sag), lire l'état en "
        "COMPRESSION (compression_state : au sag, à un %, ou à une course mm), lire les AXES de roue + "
        "chemin d'axe (wheel_axles), interroger la BANQUE DE CONNAISSANCES vélo + le catalogue de pièces "
        "BikeCAD + les DOCUMENTS sources ingérés (search_knowledge, récupération RAG BM25), et gérer la "
        "bibliothèque. Pour des specs (moteur M620, amortisseurs, courroie, pièces) ou un rappel de "
        "méthode, appelle search_knowledge plutôt que d'inventer ; si un extrait porte une 'source' "
        "(document ingéré), CITE-la (nom + page). Si la banque LOCALE ne suffit pas (spec composant "
        "précise, compatibilité, procédure SAV constructeur), interroge la BASE VÉLO DISTANTE avec "
        "search_velo_db (QDRANT latelier, ~1,7 M de chunks ; requête en anglais de préférence) et cite "
        "la source. "
        "Après une modification, VÉRIFIE le résultat (get_state) et explique brièvement l'impact.\n\n"
        "Convention monde : BB=(0,0), x=avant +, y=haut +, mm. Angles depuis l'horizontale.\n\n"
        "Sections et champs éditables (set_parameters) :\n" + fields + "\n\n"
        "Cibles cinématique e-MTB : anti-squat sag 100–115 %, belt growth < 2 mm (courroie Gates), "
        "pedal kickback faible, recul d'axe > 0. Le galet placé près du pivot principal minimise le "
        "belt growth (propriété du high-pivot).\n\n"
        "GARDE-FOU : tu proposes des itérations de géométrie/cinématique. Tu n'improvises JAMAIS de "
        "validation structurelle/fatigue (hors périmètre, déléguée à un bureau d'études). Anti-squat "
        "= méthode indicative, à valider dans Linkage avant fabrication.\n\n"
        "## État courant du vélo\n" + state_summary
    )


def _state_summary(data: dict) -> str:
    """Résumé compact (géométrie + cinématique) pour ancrer l'assistant."""
    try:
        bike = BikeDesign.model_validate(data)
        c = calculate(bike)
        out = [
            f"nom: {data.get('name')}",
            f"frame: head_angle={data['frame']['head_angle']} seat_angle={data['frame']['seat_angle']} "
            f"cs={data['frame']['cs']} bb_drop={data['frame']['bb_drop']} fcd={data['frame']['fcd']}",
            f"géométrie: reach={c.reach:.0f} stack={c.stack:.0f} WB={c.wheelbase:.0f} trail={c.trail:.0f} "
            f"bb_height={c.bb_height:.0f}",
            f"suspension: linkage_type={data['suspension']['linkage_type']} "
            f"rear_travel={data['suspension']['rear_travel']} use_idler={data['suspension']['use_idler']}",
            f"drivetrain: motor_key={data['drivetrain']['motor_key']} drive_type={data['drivetrain']['drive_type']}",
        ]
        k = solve_kinematics(bike)
        if k.ok:
            out.append(
                f"cinématique: course={k.total_travel} levier_sag={k.leverage_sag} "
                f"anti_squat_sag={k.anti_squat_sag}% belt_growth_max={k.belt_growth_max}mm "
                f"kickback_max={k.pedal_kickback_max}° recul_axe={k.axle_path_rearward}mm "
                f"dégagement_moteur={'OK' if k.motor_clearance_ok else 'COLLISION:'+','.join(k.motor_collisions)}")
        else:
            out.append(f"cinématique: non résolue ({k.message})")
        return "\n".join(out)
    except Exception as exc:  # pragma: no cover - robustesse
        return f"(état non calculable: {exc})"


# ── Exécution des outils (mutent `data`, journalisent dans `actions`) ────────

def _exec_tool(name: str, inp: dict, data: dict, actions: list) -> str:
    if name == "set_parameters":
        done, errs = [], []
        for e in inp.get("edits", []):
            sec, field, val = e.get("section"), e.get("field"), e.get("value")
            axis = e.get("axis")
            if sec not in data or not isinstance(data[sec], dict):
                errs.append(f"section inconnue: {sec}"); continue
            if axis:
                if field not in data[sec] or not isinstance(data[sec][field], dict):
                    errs.append(f"pivot inconnu: {sec}.{field}"); continue
                data[sec][field][axis] = val
                done.append(f"{sec}.{field}.{axis}={val}")
            else:
                if field not in data[sec]:
                    errs.append(f"champ inconnu: {sec}.{field}"); continue
                data[sec][field] = val
                done.append(f"{sec}.{field}={val}")
        # Validation Pydantic (coercition de types + bornes)
        try:
            BikeDesign.model_validate(data)
        except Exception as exc:
            return f"ERREUR validation après édition: {exc}. Édits tentés: {done}"
        actions.extend(done)
        msg = f"Modifié: {', '.join(done) if done else 'rien'}."
        if errs:
            msg += " Échecs: " + "; ".join(errs)
        return msg + "\n\nNouvel état:\n" + _state_summary(data)

    if name == "apply_preset":
        factory = PRESETS.get(inp.get("name"))
        if not factory:
            return f"Preset inconnu: {inp.get('name')}"
        preset = factory().model_dump()
        data["suspension"] = preset
        if inp.get("name") == "high_pivot_m620":
            data["drivetrain"]["motor_key"] = "bafang_m620"
            data["drivetrain"]["use_motor"] = True
        actions.append(f"preset:{inp.get('name')}")
        return f"Preset '{inp.get('name')}' appliqué.\n\nNouvel état:\n" + _state_summary(data)

    if name == "get_state":
        return _state_summary(data)

    if name == "compute_sag":
        try:
            bike = BikeDesign.model_validate(data)
            kw = {k: inp[k] for k in ("rider_mass_kg", "bike_mass_kg", "rear_bias_pct",
                                      "spring_rate_n_per_mm", "target_sag_pct") if k in inp}
            return json.dumps(compute_sag(bike, **kw), ensure_ascii=False)
        except Exception as exc:
            return f"ERREUR compute_sag: {exc}"

    if name == "compression_state":
        try:
            bike = BikeDesign.model_validate(data)
            return json.dumps(compression_state(
                bike, at_pct=inp.get("at_pct"), at_mm=inp.get("at_mm"),
                at_sag=bool(inp.get("at_sag"))), ensure_ascii=False)
        except Exception as exc:
            return f"ERREUR compression_state: {exc}"

    if name == "wheel_axles":
        try:
            bike = BikeDesign.model_validate(data)
            res = wheel_axles(bike)
            res.pop("rear_axle_path", None)  # trop long pour le contexte ; garder la synthèse
            return json.dumps(res, ensure_ascii=False)
        except Exception as exc:
            return f"ERREUR wheel_axles: {exc}"

    if name == "search_knowledge":
        hits = knowledge.search(inp.get("query", ""), int(inp.get("k", 4)))
        if not hits:
            return "Aucune entrée pertinente dans la banque de connaissances."
        blocks = []
        for h in hits:
            cite = f"  [source: {h['source']}" + (f", p.{h['page']}" if h.get("page") else "") + "]" if h.get("source") else ""
            blocks.append(f"### {h['title']}{cite}\n{h['text']}")
        return "\n\n".join(blocks)

    if name == "search_velo_db":
        if not knowledge.remote_available():
            return ("Base vélo distante non configurée (LATELIER_QDRANT_URL + VOYAGE_API_KEY absents). "
                    "S'appuyer sur search_knowledge (banque locale).")
        hits = knowledge.remote_search(inp.get("query", ""), int(inp.get("k", 5)))
        if not hits:
            return "Aucun résultat dans la base vélo distante."
        blocks = []
        for h in hits:
            meta = " · ".join(filter(None, [
                ", ".join(h.get("brands") or []),
                ", ".join(h.get("component_types") or [])]))
            cite = f"  [{h['source']}" + (f", p.{h['page']}" if h.get("page") else "") + "]" if h.get("source") else ""
            head = h["title"] or (h.get("source") or "extrait")
            blocks.append(f"### {head}{cite}\n" + (f"_{meta}_\n" if meta else "") + h["text"][:600])
        return "\n\n".join(blocks)

    if name == "list_library":
        items = library.list_bikes()
        if not items:
            return "Bibliothèque vide."
        return "\n".join(f"- {x['name']}  (fichier: {x['file']})" for x in items)

    if name == "save_bike":
        try:
            bike = BikeDesign.model_validate(data)
            p = library.save_bike(bike, inp.get("name"))
            actions.append(f"save:{p.name}")
            return f"Vélo sauvegardé : {p.name}"
        except Exception as exc:
            return f"ERREUR sauvegarde: {exc}"

    if name == "load_bike":
        try:
            bike = library.load_bike(inp.get("name"))
            data.clear(); data.update(bike.model_dump())
            actions.append(f"load:{inp.get('name')}")
            return f"Vélo chargé.\n\nNouvel état:\n" + _state_summary(data)
        except FileNotFoundError as exc:
            return f"Introuvable: {exc}"
        except Exception as exc:
            return f"ERREUR chargement: {exc}"

    return f"Outil inconnu: {name}"


def run_assistant(messages: list, bike: BikeDesign) -> dict:
    """Exécute un tour de conversation avec boucle tool-use.

    messages : historique [{role, content(str)}]. Retourne {reply, bike(dict), actions}.
    """
    client = anthropic.Anthropic()
    data = bike.model_dump()
    actions: list = []
    system = _system_prompt(_state_summary(data))

    convo = [{"role": m["role"], "content": m["content"]} for m in messages
             if m.get("role") in ("user", "assistant") and m.get("content")]
    if not convo or convo[-1]["role"] != "user":
        # Rien à traiter (garde-fou)
        return {"reply": "(aucun message utilisateur)", "bike": data, "actions": actions}

    resp = None
    for _ in range(MAX_LOOPS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            messages=convo,
        )
        if resp.stop_reason != "tool_use":
            break
        convo.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                out = _exec_tool(block.name, block.input, data, actions)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": out,
                })
        convo.append({"role": "user", "content": results})

    reply = " ".join(b.text for b in (resp.content if resp else []) if b.type == "text").strip()
    return {"reply": reply or "(pas de réponse)", "bike": data, "actions": actions}
