# CLAUDE.md — BikeCAD 17.5 configuration / DOM Engineering

Contexte du dépôt et conventions pour l'assistant. Langue de travail : **français**.

## Vue d'ensemble

Deux choses cohabitent dans ce dépôt :

1. **Projet cadre e-MTB custom** (DOM Engineering, Robinson Joubert) — géométrie BikeCAD
   d'un VTT électrique haute performance. Fichier de référence :
   `BIKE/eMTB_DOM_Engineering.bcad`. Données cinématiques : `linkage_DOM_eMTB.txt`.
2. **Outil maison de remplacement de BikeCAD** dans `tool/` (FastAPI + Svelte) :
   couvre les fenêtres/calculs BikeCAD, ajoute cinématique suspension (3 topologies,
   levier/anti-squat/**anti-rise**/belt growth/kickback), enveloppe/dégagement carter moteur,
   mode lugs (jonctions tube↔lug → SolidWorks), **hardware de pivots (roulements + axes)**,
   **visserie (chaque point de vis/boulon + type + couple)**,
   **transmission dérailleur OU moyeu à vitesses IGH (Rohloff / 3×3) + garde-fou couple**,
   **calculateur batterie/autonomie**, bibliothèque lossless, fit pilote, comparaison,
   exports SVG/DXF/.bcad/lugs/pivots/visserie, et un **assistant conversationnel (Claude)**.
   Rendu **style BikeCAD** (fond gris, cadre détouré, formes RÉELLES de pièces extraites des
   exports BikeCAD : fourche, amortisseur, dérailleur, batterie ; moteur exact du JAR) +
   vue **« Rendu BikeCAD »** (import du SVG natif BikeCAD pour fidélité 100 %).

`bcad_tool.py` (racine) = ancien CLI Python d'origine, conservé pour référence.

## Lancer l'outil

```bash
cd tool && ./start.sh          # backend :8000 (uvicorn) + frontend :5173 (vite)
```
- Backend seul : `cd tool && PYTHONPATH=. .venv/bin/uvicorn backend.main:app --reload`
- venv Python : `tool/.venv` (fastapi, uvicorn, pydantic, pyyaml, **anthropic**, **pypdf** pour le RAG)
- Frontend : `cd tool/frontend && npm run dev` (ou `npm run build` pour vérifier la compilation)
- App : http://localhost:5173 — API docs : http://localhost:8000/docs
- **Base vélo distante** (optionnelle) : copier `tool/.env.latelier.example` → `tool/.env.latelier`
  (gitignoré, sourcé auto par `start.sh`) avec `LATELIER_QDRANT_URL` + `VOYAGE_API_KEY` (récup via
  `railway variables -s latelier/qdrant`). Active `search_velo_db` / `/api/knowledge/remote/*`. Sans
  ce fichier, l'outil tourne normalement (recherche distante désactivée).
- **Tests E2E** (11 sections, sans serveur) : `cd tool && PYTHONPATH=. .venv/bin/python tests/e2e_test.py`
- **Tests de FIABILISATION** (`tests/validation.py`) : golden (eMTB ≈ cotes documentées),
  cohérence interne (trail = formule canonique, reach/stack = points clés), **round-trip .bcad
  lossless** (6195→6195), **cross-validation anti-squat** (recalcul indépendant ≡ méthode
  `bikinematicsolver`), trail dynamique, plausibilité sur tous les vélos du dépôt.
- **Cross-validation cinématique** (`tests/crossval_kinematics.py`) : notre four-bar Horst comparé,
  géométrie IDENTIQUE, à la VRAIE librairie `mark-bak/bikinematicsolver` exécutée indépendamment.
  Deux cas : (1) four-bar synthétique → **levier ±0.003**, **chemin d'axe ±0.1 mm**, **anti-squat ±0.2 %** ;
  (2) **vélo de SÉRIE Vitus Sommet** (enduro, pivots tracés réels, amortisseur sur biellette) →
  **levier ±0.004**, **axe ±0.08 mm**, **anti-squat ±0.2 %**. Notre moteur ≡ la référence. Oracle
  capturé en GOLDEN (pur Python, pas de numpy/scipy en dépendance).
  ⚠ L'anti-squat utilise le **contact pneu INSTANTANÉ** (axe − rayon roue, repère cadre — il remonte
  au tassement, méthode bikinematicsolver), datum de hauteur = sol topout fixe (`common.anti_squat`,
  param `wheel_radius`). La tangente de chaîne est la **tangente commune externe** des 2 poulies.
  `SuspensionConfig.shock_mount` (rocker | chainstay | coupler | auto) : membre portant l'œillet bas
  d'amortisseur — **rocker = cas standard des enduros modernes** (géré dans `four_bar.py`).
- **Cross-validation MULTI-SYSTÈMES** (`tests/crossval_suspension_systems.py`) : le four-bar GÉNÉRAL
  reproduit, vs la vraie librairie, **Horst Link / Split-Pivot / DW-Link** (twin-link, AS NON-monotone)
  à **±0.11 % AS / ±0.07 mm axe** chacun, + **Single-Pivot** (high_pivot) solvable/plausible. Les
  systèmes ne diffèrent que par la POSITION des pivots (même solveur prouvé).
- **Tests E2E « parcours interface »** (HTTP, backend en route) : `.venv/bin/python tests/e2e_interface.py`
  — construit le vélo aux specs projet via les mêmes endpoints que le frontend, vérifie
  fonctionnel + graphique (13 composants, rien hors-canvas, pas de NaN, cotes).
- **Assistant** : nécessite `ANTHROPIC_API_KEY` dans l'environnement (sinon l'endpoint renvoie 503 et l'onglet affiche une notice). Modèle `claude-opus-4-8`.
- ⚠️ **`uvicorn --reload` rate souvent les changements** (surtout après beaucoup de fichiers) →
  si « rien ne marche » / rendu périmé / endpoint 404, **couper et relancer `./start.sh`** +
  recharge forcée navigateur (Cmd+Shift+R). Diagnostic rapide : `curl localhost:8000/api/igh`
  (404 = backend périmé). Debug navigateur possible en **Chrome headless + CDP** (Node `WebSocket`).
- **Outils de rendu/extraction** (`tool/scripts/`) : `svgtool` (wrapper) → `svg_part_tool.py`
  (lève les `<path>` des SVG BikeCAD : `paths`/`context`/`render`/`extract`), `normalize_parts.py`
  (ré-oriente les sprites), `render_test.py [chain|belt|battery|susp] [cx cy w]` (rend + zoom PNG).
  Rasterisation via **cairosvg** (dans le venv) → nécessite `DYLD_LIBRARY_PATH=/opt/homebrew/lib`
  (déjà posé par le wrapper `svgtool`/`rtest`). Sprites : `tool/refs/bikecad_parts/*.json`.

## Architecture `tool/`

**Backend** (`tool/backend/`)
- `models/bike.py` — tous les modèles Pydantic v2. `BikeDesign` = design complet
  (frame, fork, headtube, headset, stem, handlebar, saddle, seatpost, cranks,
  wheel_f, wheel_r, pedals, brakes, drivetrain, suspension, battery, rider?).
  Résultats : `CalcResult`, `KinematicsResult`, `FitResult`, `BatteryResult`,
  `TransmissionResult`, `PivotResult`. Constantes : `GEARBOX_TYPES` (moteurs),
  `IGH_TYPES` (moyeux : rohloff_14, 3x3_nine — nb vitesses/étendue/couple max/ratio mini),
  `BEARING_CATALOG` (roulements pivot std : 6902/6802/688/6900/6901/MR15268/7902-AC…).
  `DrivetrainConfig` : `transmission` (derailleur|igh), `igh_model`, `motor_torque_nm`,
  + champs autonomie batterie (`nominal_power_w`, `peak_power_w`, `consumption_whkm`).
  `SuspensionConfig` : `pivot_bearing_main/link`, `idler_bearing`, `pivot_torque_nm`.
- `calculations/battery.py` — `compute_battery()` : enveloppe du pack (décalé depuis la
  **SURFACE** du tube diagonal, pas l'axe → ne traverse plus le cadre) + test d'intégration
  (triangle / carter / tubes) + **calculateur autonomie** (Ah, courant nominal/crête, régime C,
  tenue à P crête, autonomie Éco/Rando/Boost km). Patron de référence pour AJOUTER UN COMPOSANT
  (modèle → calcul → svg `_draw_*` → endpoint → panneau/store).
- `calculations/transmission.py` — `compute_transmission()` : dérailleur (cassette) OU IGH
  (Rohloff 130 Nm / 3×3 250 Nm). **Garde-fou couple** : couple moteur ÷ rapport primaire
  (plateau/pignon) = couple entrée moyeu ≤ limite ; + rapport primaire mini. **Géométrie +
  TENSION courroie** : une courroie est sans fin (pas de tendeur de dérailleur) → l'entraxe
  doit être RÉGLABLE. `_belt_geometry()` calcule entraxe (≈ chainstay), longueur 2-poulies,
  nb de dents Gates, et ΔC/dent ; `belt_tension_ok` = course de réglage `dropout_adjust_mm` ≥
  un incrément de dent. `SuspensionConfig.belt_tension_method` (sliding_dropout | eccentric_bb |
  eccentric_pivot) + `dropout_adjust_mm`. Rendu : `_draw_dropout()` (glissière + axe + cote ↔,
  class="dropout", auto si drive=belt). Endpoint `/api/transmission`.
- `calculations/pivots.py` — `compute_pivots()` : par pivot de la topologie → roulement
  (catalogue), axe, logement, nomenclature. Sélection GÉOMÉTRIQUE (charges/fatigue = bureau
  d'études). Pivot principal en **contact oblique 7902** (charges combinées e-MTB) ; amortisseur
  en **bague DU/rotule** (pas de roulement). Exports `io/pivot_export.py` (JSON/CSV/résumé).
- `calculations/fasteners.py` — `compute_fasteners(bike, calc)` : **chaque point de vis/boulon**
  du vélo (cockpit, tige de selle, freins, roues, transmission, moteur, suspension, divers) →
  position monde + taille + empreinte (Torx/hex) + qté + couple de RÉFÉRENCE + nomenclature.
  Couples = specs constructeur agrégées (Park Tool / Specialized Matrix / SRAM/Shimano / **manuel
  Bafang M620** : fixation 3× M8 @ 35 Nm, manivelles 45–50). Toujours prioriser la valeur GRAVÉE
  sur la pièce ; sélection GÉOMÉTRIQUE (fatigue/impact = bureau d'études). Rendu `_draw_fasteners`
  (tête colorée par catégorie + empreinte + légende), export `io/fastener_export.py` (JSON/CSV/résumé).
  Connaissance : `knowledge/fastener_torques.json` (3 entrées). Endpoints `/api/fasteners`,
  `/api/export/fasteners` ; flag render `show_fasteners` ; panneau frontend `Visserie`.
- `calculations/tubes.py` — `compute_tubes(bike, calc, test_moment_nm, test_tube, adhesive)` :
  **par tube** (Ø ext donné + paroi → Ø INTÉRIEUR = OD−2·paroi) → propriétés de SECTION
  (A=π/4(OD²−ID²), I=π/64(OD⁴−ID⁴), Z=I/(OD/2)), masse (A·L·ρ), capacité **INDICATIVE** à la
  limite élastique (M_y=Z·Re, F_y=A·Re) + **jonction lug-and-bond** (insertion L=Re·paroi/τ_adm,
  surface π·OD·L, cisaillement adm. τ·π·OD·L). Test de résistance optionnel : σ=M/Z, FS=Re/σ
  (cible ≥2, von Mises ductile). Matériaux dans `MATERIALS` (acier 4130, alu 6061/7075-T6, titane
  Gr9/Gr5, carbone UD anisotrope→pas de Re scalaire), adhésifs dans `ADHESIVES` (DP460/EA9466/E-120HP,
  τ_adm de calcul réduit). Champs `FrameGeometry` : `*_wall` (6 parois) + `frame_material`/`lug_material`.
  Export `io/tube_export.py` (JSON/CSV/résumé). Connaissance `knowledge/tube_materials.json` (3 entrées).
  Endpoints `/api/materials`, `/api/tubes`, `/api/export/tubes` ; panneau frontend `Tubes & Lugs`
  (groupe Cadre). ⚠ Pré-dimensionnement / comparaison matériaux — fatigue/impact = bureau d'études.
- `calculations/geometry.py` — `calculate()` géométrie exacte (reach, stack, trail, WB…).
- `calculations/kinematics.py` — **DISPATCHER** `solve_kinematics()` : route par
  `suspension.linkage_type` vers `calculations/layouts/`. Piloté **par la course roue**.
  Ajoute le dégagement carter moteur (`motor_clearance_ok`/`motor_collisions`).
- `calculations/layouts/` — `common.py` (primitives géom + `anti_squat()` (IC + brin moteur)
  + `anti_rise()` (freinage : IC + contact pneu AR, source `bikinematicsolver`/Bikerumor) +
  `build_result()` = toute la métrologie : échantillonnage, levier, progressivité, belt growth,
  **pedal kickback**, **anti-rise**, synthèse). `four_bar.py` (Horst, 4 pivots),
  `high_pivot.py` (single-pivot haut + galet fixe — cas M620), `generic.py` (solveur
  **par contraintes Newton-Raphson** pur Python, prouvé ≡ four_bar — fondation 6-bar).
  Levier + chemin d'axe + anti-squat CROSS-VALIDÉS vs `mark-bak/bikinematicsolver` (±0.003 /
  ±0.1 mm / ±0.2 % — cf. `tests/crossval_kinematics.py`) ; brin moteur = dernier segment
  (galet→pignon si galet présent).
- `calculations/motor.py` — enveloppes carter (polygone **M620** du manuel : 234×140,
  bossages R78.5/R58), `motor_envelope_world()`, `point_in_polygon()`, `clearance_check()`.
- `calculations/fit.py` — `compute_fit()` bike-fit 2D (IK 2-barres) : angles articulaires, KOPS, reach/drop.
- `calculations/analysis.py` — analyses dérivées : `compute_sag()` (sag arrière coil :
  raideur→sag mm/% ou cible→raideur requise ; force roue×LR), `compression_state()` (état à
  une compression mm/%/sag, interpolé), `wheel_axles()` (axes AV/AR + chemin d'axe AR).
- `knowledge/` — banque de connaissances + **RAG BM25** (pur Python, zéro dépendance lourde).
  - `bank.py` — fusionne un seul corpus : entrées curées (M620, amortos, Gates, gearbox, concepts
    cinématique, cibles DOM, **Rohloff/3×3**) + catalogue de pièces du dépôt + `_loaded_entries()`
    (tous les `knowledge/*.json`, ex. `geometry_dh.json`, `pivot_hardware.json`) + **chunks de
    documents** (`ingest.doc_chunks()`). `search()` score TOUT via **BM25 Okapi** (IDF + saturation
    de fréquence ; titre×2, tags×3 injectés dans le flux indexé). Résultats = `{title, text, score,
    source?, page?}` (source/page présents pour un chunk de document → **citation**). `reindex()` /
    `stats()`. Index BM25 mémoïsé, invalidé sur empreinte mtime des documents.
  - `bm25.py` — `BM25` Okapi (k1=1.5, b=0.75) : index inversé + IDF, `scores()`/`top_k()`.
  - `ingest.py` — lit `knowledge/docs/` (`.txt`/`.md`/`.pdf` via **pypdf**), nettoie (recolle les
    césures PDF), **chunke** (~900 car., chevauchement 150) avec frontières de paragraphe ; chaque
    chunk = `{id, title, tags, text, source, page}`. `README.md`/`.gitignore` ignorés.
  - `knowledge/docs/` — dossier où **déposer les sources** (PDF/txt/md exportés du **NotebookLM** :
    le notebook n'est PAS accessible par l'outil — privé/Google ; exporter les sources en fichiers).
    Non suivi par git (`.gitignore`). Voir `docs/README.md` pour la procédure d'export. **Docs déjà
    ingérés** (juin 2026, ~112 chunks) : `SPEC_eMTB_DOM_Engineering.md` (spec projet faisant autorité),
    `RECAP DE LECHANGE DE BASE.md` (préco géométrie BikeCAD), `BF-DM-C-MM G510-EN.pdf` (manuel moteur
    M620), `AM.150_GeoChart.pdf` (géométrie Atherton, benchmark), `Kavenz+Kinematics+VHP.pdf` (courbes
    AS/kickback), `Kavenz_videos_recap_ep0-1.md` + `Kavenz_fabrication_collage_EFBE.md` (lugs CNC,
    carbone Compotech, collage 3M DP490, tests EFBE Cat 5). Les **vidéos YouTube** ne sont ingérables
    que via leur transcript collé en `.txt`/`.md`.
  - Endpoints : `GET /api/knowledge/stats`, `POST /api/knowledge/search`, `POST /api/knowledge/reindex`.
  - **Source DISTANTE optionnelle** (`knowledge/latelier.py`) : base vectorielle **QDRANT du projet
    « latelier »** (~1,7 M chunks vélo : manuels, docs SAV, fiches produits ; collection `mecano_chunks`,
    embeddings **Voyage `voyage-3` 1024-dim cosine**). `remote_search(query,k)` = embed Voyage → search
    QDRANT → hits {title,text,score,source,page,brands,models,component_types}. **Config par ENV** (jamais
    de secret en dur) : `LATELIER_QDRANT_URL` (proxy TCP public du service qdrant Railway), `VOYAGE_API_KEY`,
    `LATELIER_QDRANT_COLLECTION` (défaut mecano_chunks), `LATELIER_EMBED_MODEL` (défaut voyage-3). Repli
    gracieux : `remote_available()` False + `remote_search()` → [] si non configuré (l'outil reste 100 %
    fonctionnel hors-ligne). Secrets dans `tool/.env.latelier` (gitignoré, sourcé par `start.sh` ;
    modèle `.env.latelier.example` ; récup via `railway variables -s latelier/qdrant`). Endpoints
    `GET /api/knowledge/remote/stats`, `POST /api/knowledge/remote/search` (503 si non configuré).
    Outil assistant **`search_velo_db`** (requête EN de préférence). C'est un COMPLÉMENT à la banque
    locale (curée/projet) ; l'assistant l'interroge « si besoin » (spec composant, compatibilité, SAV).
    NB : certains chunks de leur corpus ont une extraction PDF brouillée (cipher) — qualité variable.
  - **Pour brancher une vraie base vectorielle** locale (embeddings) plus tard : remplacer l'index BM25 par
    un index ANN ; l'API `search()` ne change pas. NB : caches `lru_cache` → après ajout d'un JSON
    curé, relancer le backend ; après ajout d'un **document**, `reindex()` suffit (détecte le mtime).
- `presets.py` — presets `SuspensionConfig` : `high_pivot_m620` (dégage le carter) ;
  `high_pivot_emtb_tuned` (accordé belt+M620 : levier 3.3→2.7, AS sag ~97 %, kickback 3.8°,
  belt growth ~4.2 mm) ; `kavenz_vhp_style` (façon Kavenz VHP : galet AU pivot haut → axe reculé
  ~20 mm, **kickback ~1.7°, belt growth ~1.8 mm**, AS sag ~90 %) ; `scott_ransom_style`
  (enduro 170 mm à chaîne, levier 2.8→2.6, AS 92 %, kickback ~21° — pas de galet). Boutons dans
  le panneau Suspension ; sélectionnables via `/api/suspension/preset/{name}`. **Vélo complet
  Scott Ransom 900 (L)** (géométrie constructeur taille L : HA 63.8°, reach 483, WB 1270, BB 350,
  cs 440, 170 mm, dérailleur 29") enregistré dans la bibliothèque (`tool/bikes/`, sélecteur 📁).
- `lugs/` — mode lug-and-bond : `joint_model.build_joints()` (graphe cadre → 5 nœuds-lugs
  avec douilles {axe, alésage, profondeur, out_of_plane}), `miter.py`, `export_cad.py` (JSON /
  CSV table de conception SolidWorks / résumé).
- `library.py` — bibliothèque LOSSLESS : sauve/charge le BikeDesign COMPLET (suspension
  comprise) en JSON dans `tool/bikes/*.bike.json`. Anti path-traversal.
  - **Vélo de référence assemblé** : `eMTB_DOM_complet.bike.json` = build cohérent complet
    (juin 2026). Géométrie aux cibles RECAP/SPEC (reach 478, stack 619, WB 1248, HA 64°, STA eff
    77.5°, CS 435, douille 122 ; fcd résolu pour reach). Suspension `high_pivot_m620` avec
    **ancrages d'amortisseur RETUNÉS** (`shock_lower(-220,105)` / `shock_upper(-54,244)` → levier
    3.18→2.92 au lieu de ~7, course amorto exploitée ; cf. leçon dans « Faits vérifiés »). Drivetrain
    **M620 150 Nm + courroie Gates + moyeu 3X3 NINE** (plateau 39/pignon 24 → primaire 1.62 ≥ 1.60 ;
    couple moyeu 92/250 Nm) + **patte coulissante 15 mm** (tension courroie). AS 112 %, belt growth
    4.7 mm, kickback 4°, carter dégagé. ⚠ Progressivité ~8 % (limite du single-pivot à amorto direct ;
    vraie progression = biellette/6-barres).
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
  `compression_state`, `wheel_axles`, `search_knowledge` (RAG BM25 LOCAL : banque curée + docs ingérés),
  **`search_velo_db`** (base vélo DISTANTE QDRANT latelier, ~1,7 M chunks — voir `knowledge/latelier.py`),
  `save_bike`/`load_bike`/`list_library`. L'assistant cite les sources ; il interroge la distante « si
  besoin » quand la locale ne suffit pas. Garde-fou structurel dans le system prompt.
- `io/bcad_io.py` — `load_bcad()` / `save_bcad()`. **Voir section .bcad ci-dessous.**
  `load_bcad` charge un vélo **GÉNÉRIQUE** : batterie **OFF** (concept DOM), **suspension arrière
  OFF** (un .bcad = géométrie de cadre HARDTAIL ; la suspension est une couche de l'outil → sinon
  un Road/BMX héritait d'un amortisseur four-bar dans le vide), `transmission` déduite de
  l'entraînement (courroie→igh, chaîne→dérailleur), roues lues du fichier. ⚠ Le **projet eMTB**
  étant tout-suspendu, `/api/default` réactive `suspension.enabled=True` ; toggle « Suspension
  active » dans le panneau pour les autres vélos.
- `io/svg_export.py` — `render_svg()` vue de côté **style BikeCAD** : fond gris, cadrage plein
  cadre + recentré, **dégradé global de cadre 2-stops + liseré #333 + cercles de fillet aux nœuds**
  (jonctions fondues), roues détaillées **pilotées par WheelConfig** (BSD+profil, croisement,
  flasque, cercle de croisement), **pneu cranté MTB** (couronne de pavés + bande centrale, look
  enduro), **bras oscillant épaissi** (pièce moulée) en tout-suspendu, **moteur dessiné DERRIÈRE le cadre** (les tubes
  se rejoignent au BB ; `_draw_motor`, **sans flip Y** — sinon carter à l'envers), formes RÉELLES
  des pièces (sprites `_PARTS` : fork/rear_shock/battery normalisés, derailleur), **courroie noire
  crantée / chaîne grise à rouleaux** (jamais un fil), `_draw_pivots` (coupe roulement), fourche
  **rigide si travel=0 sinon fourche PARAMÉTRIQUE** (plongeur argent court ~34 % en haut + fourreaux
  noirs longs en bas — proportions réelles ; le sprite `fork_norm` rendait un long plongeur blanc
  inversé → abandonné). **Amorto ancré** : `_draw_susp_links_static` dessine une **patte d'ancrage**
  de l'œillet fixe au tube le plus proche (selle/diagonal) → l'amorto est boulonné au cadre, pas dans
  le vide. **Œillets d'amorto posés SUR les tubes** (bas sur la base, haut sur le tube de selle) +
  **pattes d'ancrage auto** des 2 œillets au membre le plus proche (cadre / bras) si écart → l'amorto
  est toujours « en face des trous », jamais flottant. Pivots dessinés **selon la topologie** (pas de
  dots C/D parasites en single-pivot). `/api/default` applique le preset **high_pivot_emtb_tuned**
  (amorto sur tubes, levier 2.85→2.51, kickback 2.5°) au projet eMTB. `_draw_fasteners` (têtes de vis colorées par
  catégorie + empreinte Torx/hex + légende). Flags : `show_dims/rider/suspension/lugs/ground/pivots/fasteners`.
  PALETTE = thème clair. `_xform_path` place les sprites (M/L/Q/C/Z).
  **Contours RÉELS** (`_OUTLINE_*` + `_norm_path` : recherche web de profils de pièces) pour la
  **selle** (court e-MTB : nez fin/queue relevée), les **étriers** (`_draw_calipers`, contour
  4-pistons enjambant le disque, dessinés PAR-DESSUS la fourche → visibles, AV φ≈158° / AR φ≈48°),
  et le **carter M620**. **Cockpit** (vue de côté) : potence fine + **montant VERTICAL court** (le
  rise) + barre quasi à plat vers le pilote + grip caoutchouc (PAS de barre à 45° / ape-hanger).
  **TOUT-SUSPENDU rendu par défaut** (`full_susp`) : l'arrière devient bras oscillant +
  hauban→biellette + **amortisseur PARAMÉTRIQUE** (`_draw_shock` : bonbonne air + tige argent +
  bague de sag rouge + molette + œillets — lisible comme un vrai amorto, PLUS le sprite-slab) +
  axes de pivot via `_draw_susp_links_static` (l'overlay
  `show_suspension` n'ajoute que bielles colorées + animation). **Fixation moteur** visible
  (`_draw_motor_mount` : 3 bossages + boulons M8 + brides vers les tubes).
- `io/dxf_export.py` — `export_dxf()` DXF R12 ASCII pour SolidWorks (calques GEOMETRY/TUBES/WHEELS/PIVOTS/DIMS_TEXT).
- `io/pivot_export.py` — export hardware pivots (JSON/CSV table SolidWorks/résumé).
- `io/fastener_export.py` — export visserie (JSON/CSV nomenclature d'assemblage/résumé).
- `io/tube_export.py` — export tubes & lugs (JSON/CSV nomenclature + section/masse/collage/résumé).
- `main.py` — FastAPI. Endpoints : `/api/default`, `/api/calc`, `/api/render/svg`,
  `/api/kinematics`, `/api/fit`, `/api/battery`, `/api/transmission`, `/api/igh`,
  `/api/pivots`, `/api/bearings`, `/api/fasteners`, `/api/materials`, `/api/tubes`,
  `/api/export/tubes`, `/api/export/dxf`, `/api/export/bcad`,
  `/api/export/lugs`, `/api/export/pivots`, `/api/export/fasteners`,
  `/api/export/drawing`, `/api/load/bcad`, `/api/library` (+`/save`,`/load`),
  `/api/catalog…`, `/api/suspension/preset/{name}`, `/api/assistant` (+`/available`),
  `/api/motors`, `/api/bikes`, `/api/health`. Chemins relatifs résolus depuis la RACINE du dépôt
  (`_repo_path`, car CWD=tool/).

**Frontend** (`tool/frontend/src/`) — **thème CLAIR** (variables CSS `:root` dans `App.svelte` :
`--bg/panel/surface/border/text/accent/brand/ok/no…`). Tout composant utilise `var(--…)`.
- `App.svelte` — toolbar + **6 onglets groupés** (`GROUPS` dans store.js : Cadre · Suspension ·
  Motorisation · Roues & freins · Pilotage · Pilote ; chaque groupe EMPILE ses panneaux) +
  bascule de vue (Vélo 2D / Cinématique / Comparaison / **🅑 Rendu BikeCAD** / Réglages / 🤖 Assistant).
  Toggles d'affichage : Cotes / Suspension / Animer / Lugs / **Pivots** / **Visserie**.
  **Badge nom de modèle** (`.model-name`, lié à `$bike.name`) dans le header → le titre change
  quand on charge un modèle. Le sélecteur `🚲 Modèle` (CatalogSelect category="bike") GARDE la
  sélection visible (vélo complet) ; les sélecteurs de composant se ré-arment. Câblage validé
  en headless (titre + specs + preview changent à la sélection).
- `lib/store.js` — stores (dont `transmission`, `pivots`, `showPivots`), refresh debouncé 180 ms.
- `lib/api.js` — REST (+ `fetchTransmission`, `listIgh`, `fetchPivots`, `listBearings`, `exportPivots`).
- `lib/Diagram.svelte` — schéma de cotes + **légende lettre→sens** ; `lib/CatalogSelect.svelte`.
- `panels/*.svelte` — un par section, aligné sur le modèle Pydantic. **Pastilles de cote**
  `.dimkey` sur les champs (Cadre HA/STA/CS/BB/FCD/ST/HT, Fourche AC/L, Pédalier Q, Roues BSD/A,
  Transmission W/P, Freins Ø, Potence J/M). `Battery.svelte` (autonomie + alimentation),
  `Drivetrain.svelte` (dérailleur/IGH + garde-fou couple), `Suspension.svelte` (pivots/roulements + export).
- `BikeRenderer.svelte`, `Kinematics.svelte` (levier/AS/**anti-rise**/belt/kickback + verdicts),
  `Compare.svelte`, `BikeCADView.svelte` (génère le .bcad du design → import du SVG natif BikeCAD,
  rendu pixel-perfect), `Assistant.svelte`.
- ⚠️ Câblage 2D : un champ doit non seulement exister sur le modèle mais être LU par `render_svg`/
  un calc, sinon il change le `.bcad` exporté mais pas l'aperçu. Les cotes **latérales/3D**
  (Q-factor, largeur BB, entretoises de moyeu, selle A–N, coords d'étrier) ne sont pas rendables
  en vue de côté (par construction).

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
- Défaut four-bar Horst **assaini** (mai 2026) pour un rendu cohérent : bras oscillant
  (main_pivot→axe), hauban→biellette (rocker), amortisseur **~vertical** dans le triangle avant
  (œillet bas sur le bras, haut sur le triangle avant ; entraxe 230 mm). Levier ≈ **2.9→2.75**
  (cible 2.8–3.2 ✓), kinématique qui résout proprement. **Toujours INDICATIF** — AS/progressivité/
  belt growth à affiner et **valider dans Linkage** (bureau d'études). L'ancien défaut était proche
  du point mort (levier 2.7–3.1 mais belt growth 16 mm, progressivité −1 %).
- Anti-squat = méthode IC + ligne de courroie, **INDICATIVE — à valider dans Linkage** avant fabrication.
  Méthode **cross-validée verbatim** vs `mark-bak/bikinematicsolver` ; le brin moteur pris en compte est
  le **dernier segment** (galet→pignon si galet présent). Avec ce calcul correct, l'AS du four-bar
  placeholder ≈ **540 %** (l'ancien 92 % ignorait le galet). Le preset **high_pivot_m620** (single-pivot
  haut + galet près du pivot, dégage le carter) donne AS≈112 %, belt growth≈4.7 mm, kickback≈4.3°.
- **Anti-rise** (freinage) = même méthode mais via le **centre instantané** (le couple de frein passe
  par le bras, pas la chaîne) : four-bar placeholder ≈ 14 %, high-pivot ≈ 96 %. Cible affichée 50–130 %.
- **Leçon ancrages d'amortisseur (single-pivot high_pivot_idler)** : le levier = L_bras_roue / (taux de
  compression amorto) ; le taux dépend de la **distance ET de l'orientation** de l'ancrage bas (sur le
  bras) par rapport au pivot. Le preset d'origine plaçait l'axe d'amorto presque radial au pivot → seul
  ~39 % de la vitesse tangentielle compressait l'amorto → **levier ~7, 23 mm de course sur 60** (amorto
  inerte). Fix par **recherche numérique** des ancrages (objectif : course amorto ≈ 60 mm) → levier
  ~2.9–3.2. ⚠ Un single-pivot à amorto **direct** reste quasi LINÉAIRE (progressivité ~8 %) : pour
  20–30 % de progression il faut une **biellette/rocker** (topologie 6-barres via le solveur générique).
- **Tension courroie (construction)** : une courroie Gates est sans fin → pas de tendeur de dérailleur →
  l'entraxe doit être **réglable** (`belt_tension_method` : patte coulissante / BB ou pivot excentrique
  + `dropout_adjust_mm`). `compute_transmission` calcule l'entraxe (≈ chainstay), le nb de dents Gates
  (~111 pour CS 435), et vérifie que la course de réglage couvre **un incrément de dent** (ΔC/dent ≈
  pas/2 ≈ 5.5 mm) — sinon aucune longueur entière ne tombe juste. Patte coulissante 15 mm = OK (2.7 dents).
- **Moteur M620** = `bafang_m620` dans `GEARBOX_TYPES` (string BikeCAD `"BafangM620"` best-guess, à vérifier
  dans BikeCAD 17.5). Le fichier de référence utilise encore `bafang_mm520`.
- **Trail dynamique** : la fourche se comprime au sag → le nez plonge → l'angle de direction se REDRESSE,
  trail ET empattement DIMINUENT. `geometry.py` calcule `trail_sag`/`head_angle_sag`/`wheelbase_sag`
  (approx petit-angle, fourche seule ; formule trail canonique). Ex. eMTB : trail 130→118 mm au sag.

## Validation & références externes (fiabilisation)

- **Tester d'abord** `tests/validation.py` (golden + cohérence + round-trip .bcad lossless + cross-val AS).
  Test de non-régression le plus puissant = **importer de vrais .bcad et comparer les cotes dérivées**.
- **Cross-validation cinématique** : `mark-bak/bikinematicsolver` (Python, **la** réf ; notre AS cross-validé
  **verbatim** ; idler+kickback = roadmap chez eux), `nickmccleery/open-kinematics` (solveur de contraintes
  Levenberg-Marquardt + Jacobiens — réf d'architecture), **mtbgraphs.com** / **Linkage X3** = oracles de
  courbes (Levo/Decoy/Atherton). Géométrie : `bikegeo.net`, `bikegeocalc.com` ; stabilité (futur)
  `moorepants/BicycleParameters` (Whipple/Meijaard 2007). Trail : Wikipedia « Bicycle and motorcycle geometry ».
- ⚠️ **AS/anti-rise dépendent du CG** (`cog_height` exposé) : comparer 2 courbes seulement à **mêmes
  hypothèses** CG/taille/plateau/pignon. eMTB M620 (~4,5 kg) + 960 Wh → CG plus bas/central qu'un bio-bike.
- **Normes** (banque RAG : `knowledge/standards_validation.json`) : EN 15194 (EPAC ≤25 km/h/250 W/≤48 V, CE,
  +A1:2023 batterie EN 50604-1), EN 17404 (EPAC VTT ; **exclut la cat. 5 DH/extrême**), ISO 4210-6:2023
  (méthodes d'essai cadre/fourche : impacts masse tombante, fatigue pédalage/horizontale/verticale 100 000 cy ;
  critères → ISO 4210-2), ASTM F2043 cond. 1-5 / EFBE Tri-Test (poids système 120/130/135 kg conv./EPAC/S-pedelec).
  **Point clé légal** : >250 W ou >25 km/h ⇒ N'EST PAS un EPAC (EN 15194) ; 45 km/h = L1e-B (S-pedelec) ;
  **~80 km/h = cyclomoteur/moto (L1e/L3e), réception véhicule + bureau d'études** — pas un vélo.

## Garde-fous métier

Engin motorisé ~80 km/h, organe de sécurité. **Le dimensionnement structurel / fatigue / impact est
HORS PÉRIMÈTRE** : délégué à un bureau d'études qualifié. Proposer des itérations de géométrie et de
cinématique, jamais improviser une validation structurelle. Idem pour le **hardware de pivots**
(roulements/axes) : on pose la GÉOMÉTRIE de montage (sélection std, alésages, logements), pas les
charges/durée de vie/tenue en fatigue. Cinématique (AS/anti-rise) = **indicative, à valider dans Linkage**.

## Conventions de code

- Backend : Python 3.13, Pydantic v2 (`Field(default, description=...)`), pas de dépendance lourde
  inutile (DXF écrit à la main). Commentaires/labels en français.
- Frontend : Svelte 4, stores réactifs, `updateSection(section, patch)` pour les éditions ;
  chaque champ d'input doit correspondre à un attribut réel du modèle (sinon l'édition est ignorée).
- Tester un changement IO via le round-trip sur `BIKE/eMTB_DOM_Engineering.bcad` (0 junk attendu),
  et lancer `tests/e2e_test.py` (11 sections) après toute modif backend. Pour vérifier qu'un
  réglage **agit sur l'aperçu** : perturber le champ → re-`render_svg` → comparer le SVG.
- **Assistant / Claude** : SDK `anthropic`, modèle `claude-opus-4-8`, boucle tool-use manuelle.
  Opus 4.8 = adaptive thinking (`thinking={"type":"adaptive"}`), **pas** de `temperature`/`budget_tokens`
  (400). Clé via `ANTHROPIC_API_KEY` (jamais en dur). Les outils de l'assistant doivent rester
  side-effect-safe et re-valider le BikeDesign (Pydantic) après édition.
- Toute nouvelle topologie de suspension = un module dans `calculations/layouts/` renvoyant
  `(states, pivots_world)` ; la métrologie reste dans `common.build_result` (un seul endroit).
