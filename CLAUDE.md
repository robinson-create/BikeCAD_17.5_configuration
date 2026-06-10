# CLAUDE.md — BikeCAD 17.5 configuration / DOM Engineering

Contexte du dépôt et conventions pour l'assistant. Langue de travail : **français**.

## Vue d'ensemble

Deux choses cohabitent dans ce dépôt :

1. **Projet cadre e-MTB custom** (DOM Engineering, Robinson Joubert) — géométrie BikeCAD
   d'un VTT électrique haute performance. Fichier de référence :
   `BIKE/eMTB_DOM_Engineering.bcad`. Données cinématiques : `linkage_DOM_eMTB.txt`.
2. **Outil maison de remplacement de BikeCAD** dans `tool/` (FastAPI + Svelte) :
   couvre les fenêtres/calculs BikeCAD, ajoute cinématique suspension (3 topologies),
   enveloppe/dégagement carter moteur, mode lugs (jonctions tube↔lug → SolidWorks),
   bibliothèque de vélos lossless, fit pilote, comparaison, exports SVG/DXF/.bcad/lugs,
   et un **assistant conversationnel (Claude) qui pilote l'outil**.

`bcad_tool.py` (racine) = ancien CLI Python d'origine, conservé pour référence.

## Lancer l'outil

```bash
cd tool && ./start.sh          # backend :8000 (uvicorn) + frontend :5173 (vite)
```
- Backend seul : `cd tool && PYTHONPATH=. .venv/bin/uvicorn backend.main:app --reload`
- venv Python : `tool/.venv` (fastapi, uvicorn, pydantic, pyyaml, **anthropic**)
- Frontend : `cd tool/frontend && npm run dev` (ou `npm run build` pour vérifier la compilation)
- App : http://localhost:5173 — API docs : http://localhost:8000/docs
- **Tests E2E** (11 sections, sans serveur) : `cd tool && PYTHONPATH=. .venv/bin/python tests/e2e_test.py`
- **Tests E2E « parcours interface »** (HTTP, backend en route) : `.venv/bin/python tests/e2e_interface.py`
  — construit le vélo aux specs projet via les mêmes endpoints que le frontend, vérifie
  fonctionnel + graphique (13 composants, rien hors-canvas, pas de NaN, cotes).
- **Assistant** : nécessite `ANTHROPIC_API_KEY` dans l'environnement (sinon l'endpoint renvoie 503 et l'onglet affiche une notice). Modèle `claude-opus-4-8`.

## Architecture `tool/`

**Backend** (`tool/backend/`)
- `models/bike.py` — tous les modèles Pydantic v2. `BikeDesign` = design complet
  (frame, fork, headtube, headset, stem, handlebar, saddle, seatpost, cranks,
  wheel_f, wheel_r, pedals, brakes, drivetrain, suspension, battery, rider?).
  Résultats : `CalcResult`, `KinematicsResult`, `FitResult`, `BatteryResult`. `GEARBOX_TYPES` = moteurs.
- `calculations/battery.py` — `compute_battery()` : enveloppe du pack dans le triangle
  avant + test d'intégration (tient dans le triangle ? dégage le carter moteur ?
  croise un tube ?). Patron de référence pour AJOUTER UN COMPOSANT (modèle →
  calcul → svg `_draw_battery` → endpoint `/api/battery` → panneau+onglet+store).
- `calculations/geometry.py` — `calculate()` géométrie exacte (reach, stack, trail, WB…).
- `calculations/kinematics.py` — **DISPATCHER** `solve_kinematics()` : route par
  `suspension.linkage_type` vers `calculations/layouts/`. Piloté **par la course roue**.
  Ajoute le dégagement carter moteur (`motor_clearance_ok`/`motor_collisions`).
- `calculations/layouts/` — `common.py` (primitives géom + `anti_squat()` paramétrable
  par IC/brin moteur + `build_result()` = toute la métrologie : échantillonnage, levier,
  progressivité, belt growth, **pedal kickback**, synthèse). `four_bar.py` (Horst, 4 pivots),
  `high_pivot.py` (single-pivot haut + galet fixe — cas M620), `generic.py` (solveur
  **par contraintes Newton-Raphson** pur Python, prouvé ≡ four_bar — fondation 6-bar).
  Anti-squat CROSS-VALIDÉ verbatim vs `mark-bak/bikinematicsolver` ; brin moteur = dernier
  segment (galet→pignon si galet présent).
- `calculations/motor.py` — enveloppes carter (polygone **M620** du manuel : 234×140,
  bossages R78.5/R58), `motor_envelope_world()`, `point_in_polygon()`, `clearance_check()`.
- `calculations/fit.py` — `compute_fit()` bike-fit 2D (IK 2-barres) : angles articulaires, KOPS, reach/drop.
- `calculations/analysis.py` — analyses dérivées : `compute_sag()` (sag arrière coil :
  raideur→sag mm/% ou cible→raideur requise ; force roue×LR), `compression_state()` (état à
  une compression mm/%/sag, interpolé), `wheel_axles()` (axes AV/AR + chemin d'axe AR).
- `knowledge/bank.py` — banque de connaissances vélo (M620, amortos, courroie Gates, gearbox,
  concepts cinématique, cibles DOM) + **catalogue de pièces BikeCAD scanné dans le dépôt** ;
  `search()` lexical (recouvrement de tokens, tags ×3). Scorer isolé → backend vectoriel pluggable.
- `presets.py` — presets `SuspensionConfig` (ex. `high_pivot_m620`, dégage le carter).
- `lugs/` — mode lug-and-bond : `joint_model.build_joints()` (graphe cadre → 5 nœuds-lugs
  avec douilles {axe, alésage, profondeur, out_of_plane}), `miter.py`, `export_cad.py` (JSON /
  CSV table de conception SolidWorks / résumé).
- `library.py` — bibliothèque LOSSLESS : sauve/charge le BikeDesign COMPLET (suspension
  comprise) en JSON dans `tool/bikes/*.bike.json`. Anti path-traversal.
- `catalog.py` — catalogue EXHAUSTIF fusionnant TOUTES les configs BikeCAD de $HOME
  (Pro 16.0 + Free 17.5, surchargeable via `BIKECAD_CONFIG_DIR`). Union des pièces par
  fichier, taguées par version (`sources`). Catégories mappables : fork, saddle, wheel,
  headset, headtube, cranks, stem, handlebar, seatpost, pedals + `bike` (presets de design
  complet). Chaque pièce parsée via `load_bcad` (zéro nouvelle table de clés). Référence
  des réglages : `setting_keys(q)` = union de ~6900 clés BikeCAD sur les vélos de réf.
  Endpoints `/api/catalog`, `/api/catalog/keys`, `/api/catalog/{cat}`, `/api/catalog/{cat}/load`.
  Frontend : `lib/CatalogSelect.svelte` (sélecteur réutilisable, gère aussi `__full__` =
  preset vélo), `Settings.svelte` (vue « Réglages (réf.) » cherchable).
- `assistant.py` — assistant Claude (`claude-opus-4-8`, SDK `anthropic`, boucle tool-use
  manuelle côté serveur). Outils : `set_parameters`, `apply_preset`, `get_state`, `compute_sag`,
  `compression_state`, `wheel_axles`, `search_knowledge`, `save_bike`/`load_bike`/`list_library`.
  Garde-fou structurel dans le system prompt.
- `io/bcad_io.py` — `load_bcad()` / `save_bcad()`. **Voir section .bcad ci-dessous.**
- `io/svg_export.py` — `render_svg()` vue de côté (cadre, roues, fourche, **transmission**,
  carter moteur en polygone pour le M620, pilote optionnel).
- `io/dxf_export.py` — `export_dxf()` DXF R12 ASCII pour SolidWorks (calques GEOMETRY/TUBES/WHEELS/PIVOTS/DIMS_TEXT).
- `main.py` — FastAPI. Endpoints : `/api/default`, `/api/calc`, `/api/render/svg`,
  `/api/kinematics`, `/api/fit`, `/api/export/dxf`, `/api/export/bcad`, `/api/export/lugs`,
  `/api/load/bcad`, `/api/library` (+`/save`,`/load`), `/api/suspension/preset/{name}`,
  `/api/assistant` (+`/available`), `/api/motors`, `/api/bikes`, `/api/health`.

**Frontend** (`tool/frontend/src/`)
- `App.svelte` — layout : toolbar (Bibliothèque, 💾 Sauver, Importer .bcad, Charger, Export .bcad/DXF/lugs)
  + onglets (panels) + bascule de vue (Vélo 2D / Cinématique / Comparaison / 🤖 Assistant).
- `lib/store.js` — stores Svelte, refresh debouncé 180 ms, `snapshotBaseline()`, `applySuspensionPreset()`.
- `lib/api.js` — appels REST (calc, render, kinematics, lugs, bibliothèque, presets, assistant…).
- `panels/*.svelte` — un panneau par section, **aligné sur les champs du modèle Pydantic**.
  `Suspension.svelte` : sélecteur de topologie (masque les pivots inutiles) + bouton preset M620.
- `BikeRenderer.svelte` (SVG), `Kinematics.svelte` (graphes levier/AS/belt/kickback + verdicts),
  `Compare.svelte` (deltas géométrie), `Assistant.svelte` (chat qui applique le vélo renvoyé).

## Convention de coordonnées (monde)

BB = origine (0,0), **x = avant +, y = haut +**, unités mm. Angles (HTA, STA) depuis l'horizontale.
⚠️ `linkage_DOM_eMTB.txt` utilise **x = arrière +** ; les défauts de `SuspensionConfig`
sont déjà convertis (`x_monde = -x_linkage`).

## Format .bcad — RÈGLES IMPORTANTES

- C'est du XML Java Properties : `<entry key="Head angle">64.0</entry>`. Le vrai fichier ≈ **6195 clés**.
- `save_bcad` **recharge la source** et ne modifie que les clés gérées → les ~6100 autres clés
  sont préservées. Round-trip vérifié : 6195 → 6195, **0 perdue, 0 ajoutée**.
- Les clés BikeCAD 17.5 sont **HUMAN-READABLE**, PAS en majuscules. **Ne JAMAIS inventer de clés.**
  Exemples réels : `Head angle`, `Seat angle`, `Stem angle`, `Stem length`, `Collar height`,
  `Collar diameter`, `Crank Q factor`, `Crank thickness`, `Saddle length`, `Saddle thickness`,
  `Saddle angle`, `Saddle type`, `Seatpost diameter`, `Seatpost setback`, `Seatpost LENGTH`,
  `Handlebar width`, `Mountain bar rise/sweep`, `Headset spacers`, `Head tube upper/lower extension`,
  `GEARBOXangle`, `GEARBOXtype`, `BELTorCHAIN` (2=courroie), `Name`, `Pedal width/thickness`.
  Fourche : `FORK1L`=A2C, `FORK0L`=plongeur, `FORK1W`=largeur lame, `FORK1R`=déport.
- Champs du tool **sans équivalent BikeCAD natif** (selle A→N, offsets potence X/Y, longueur de tige
  exposée, **toute la suspension/cinématique**) : **non écrits ni lus** par bcad_io → un round-trip
  .bcad **perd ces champs** (la suspension revient au défaut au reload). C'est intrinsèque au format.
  → Pour conserver l'INTÉGRALITÉ d'un design, utiliser la **bibliothèque JSON** (`library.py`,
  `tool/bikes/*.bike.json`) ; le .bcad reste l'export d'interop BikeCAD.
- Avant d'ajouter un mapping de clé : **vérifier qu'elle existe dans le vrai .bcad**
  (`grep`/parse XML), sinon c'est du junk ignoré par BikeCAD.

## Faits vérifiés sur le fichier de référence

- Roue réelle = **752 mm** (pas 736) → **reach ≈ 482 mm** (cible projet ≈ 480 ✓), stack ≈ 622, WB ≈ 1254.
- Cinématique des pivots actuels (linkage approximatif) : course 160 mm, levier 2.7–3.1 (cible 2.8–3.2),
  mais **belt growth 16 mm** (cible <2), **progressivité ~−1 %** (cible 20–30).
  → pivots à retravailler ; position de conception proche du point mort du four-bar.
- Anti-squat = méthode IC + ligne de courroie, **INDICATIVE — à valider dans Linkage** avant fabrication.
  Méthode **cross-validée verbatim** vs `mark-bak/bikinematicsolver` ; le brin moteur pris en compte est
  le **dernier segment** (galet→pignon si galet présent). Avec ce calcul correct, l'AS du four-bar
  placeholder ≈ **540 %** (l'ancien 92 % ignorait le galet). Le preset **high_pivot_m620** (single-pivot
  haut + galet près du pivot, dégage le carter) donne AS≈112 %, belt growth≈4.7 mm, kickback≈4.3°.
- **Moteur M620** = `bafang_m620` dans `GEARBOX_TYPES` (string BikeCAD `"BafangM620"` best-guess, à vérifier
  dans BikeCAD 17.5). Le fichier de référence utilise encore `bafang_mm520`.

## Garde-fous métier

Engin motorisé ~80 km/h, organe de sécurité. **Le dimensionnement structurel / fatigue / impact est
HORS PÉRIMÈTRE** : délégué à un bureau d'études qualifié. Proposer des itérations de géométrie et de
cinématique, jamais improviser une validation structurelle.

## Conventions de code

- Backend : Python 3.13, Pydantic v2 (`Field(default, description=...)`), pas de dépendance lourde
  inutile (DXF écrit à la main). Commentaires/labels en français.
- Frontend : Svelte 4, stores réactifs, `updateSection(section, patch)` pour les éditions ;
  chaque champ d'input doit correspondre à un attribut réel du modèle (sinon l'édition est ignorée).
- Tester un changement IO via le round-trip sur `BIKE/eMTB_DOM_Engineering.bcad` (0 junk attendu),
  et lancer `tests/e2e_test.py` (10 sections) après toute modif backend.
- **Assistant / Claude** : SDK `anthropic`, modèle `claude-opus-4-8`, boucle tool-use manuelle.
  Opus 4.8 = adaptive thinking (`thinking={"type":"adaptive"}`), **pas** de `temperature`/`budget_tokens`
  (400). Clé via `ANTHROPIC_API_KEY` (jamais en dur). Les outils de l'assistant doivent rester
  side-effect-safe et re-valider le BikeDesign (Pydantic) après édition.
- Toute nouvelle topologie de suspension = un module dans `calculations/layouts/` renvoyant
  `(states, pivots_world)` ; la métrologie reste dans `common.build_result` (un seul endroit).
