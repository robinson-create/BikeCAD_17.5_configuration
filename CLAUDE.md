# CLAUDE.md — BikeCAD 17.5 configuration / DOM Engineering

Contexte du dépôt et conventions pour l'assistant. Langue de travail : **français**.

## Vue d'ensemble

Deux choses cohabitent dans ce dépôt :

1. **Projet cadre e-MTB custom** (DOM Engineering, Robinson Joubert) — géométrie BikeCAD
   d'un VTT électrique haute performance. Fichier de référence :
   `BIKE/eMTB_DOM_Engineering.bcad`. Données cinématiques : `linkage_DOM_eMTB.txt`.
2. **Outil maison de remplacement de BikeCAD** dans `tool/` (FastAPI + Svelte) :
   couvre les fenêtres/calculs BikeCAD, ajoute cinématique suspension, fit pilote,
   comparaison de géométries, et exports SVG/DXF/.bcad.

`bcad_tool.py` (racine) = ancien CLI Python d'origine, conservé pour référence.

## Lancer l'outil

```bash
cd tool && ./start.sh          # backend :8000 (uvicorn) + frontend :5173 (vite)
```
- Backend seul : `cd tool && PYTHONPATH=. .venv/bin/uvicorn backend.main:app --reload`
- venv Python : `tool/.venv` (fastapi, uvicorn, pydantic, pyyaml)
- Frontend : `cd tool/frontend && npm run dev` (ou `npm run build` pour vérifier la compilation)
- App : http://localhost:5173 — API docs : http://localhost:8000/docs

## Architecture `tool/`

**Backend** (`tool/backend/`)
- `models/bike.py` — tous les modèles Pydantic v2. `BikeDesign` = design complet
  (frame, fork, headtube, headset, stem, handlebar, saddle, seatpost, cranks,
  wheel_f, wheel_r, pedals, brakes, drivetrain, suspension, rider?).
  Résultats : `CalcResult`, `KinematicsResult`, `FitResult`. `GEARBOX_TYPES` = moteurs.
- `calculations/geometry.py` — `calculate()` géométrie exacte (reach, stack, trail, WB…).
- `calculations/kinematics.py` — `solve_kinematics()` four-bar Horst, piloté **par la
  course roue** (pas par l'amortisseur). Levier, progressivité, anti-squat, belt growth, axle path.
- `calculations/fit.py` — `compute_fit()` bike-fit 2D (IK 2-barres) : angles articulaires, KOPS, reach/drop.
- `io/bcad_io.py` — `load_bcad()` / `save_bcad()`. **Voir section .bcad ci-dessous.**
- `io/svg_export.py` — `render_svg()` vue de côté (cadre, roues, fourche, **transmission**, pilote optionnel).
- `io/dxf_export.py` — `export_dxf()` DXF R12 ASCII pour SolidWorks (calques GEOMETRY/TUBES/WHEELS/PIVOTS/DIMS_TEXT).
- `main.py` — FastAPI. Endpoints : `/api/default`, `/api/calc`, `/api/render/svg`,
  `/api/kinematics`, `/api/fit`, `/api/export/dxf`, `/api/export/bcad`, `/api/load/bcad`,
  `/api/motors`, `/api/bikes`, `/api/health`.

**Frontend** (`tool/frontend/src/`)
- `App.svelte` — layout : toolbar + onglets (panels) + bascule de vue (Vélo 2D / Cinématique / Comparaison).
- `lib/store.js` — stores Svelte, refresh debouncé 180 ms, `snapshotBaseline()` pour la comparaison.
- `lib/api.js` — appels REST.
- `panels/*.svelte` — un panneau par section, **aligné sur les champs du modèle Pydantic**.
- `BikeRenderer.svelte` (SVG), `Kinematics.svelte` (graphes), `Compare.svelte` (deltas géométrie).

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
  exposée) : volontairement **non écrits** pour ne pas polluer le fichier.
- Avant d'ajouter un mapping de clé : **vérifier qu'elle existe dans le vrai .bcad**
  (`grep`/parse XML), sinon c'est du junk ignoré par BikeCAD.

## Faits vérifiés sur le fichier de référence

- Roue réelle = **752 mm** (pas 736) → **reach ≈ 482 mm** (cible projet ≈ 480 ✓), stack ≈ 622, WB ≈ 1254.
- Cinématique des pivots actuels (linkage approximatif) : course 160 mm, levier 2.7–3.1 (cible 2.8–3.2),
  mais **belt growth 16 mm** (cible <2), **progressivité ~−1 %** (cible 20–30), anti-squat sag 92 %.
  → pivots à retravailler ; position de conception proche du point mort du four-bar.
- Anti-squat = méthode IC + ligne de courroie, **INDICATIVE — à valider dans Linkage** avant fabrication.

## Garde-fous métier

Engin motorisé ~80 km/h, organe de sécurité. **Le dimensionnement structurel / fatigue / impact est
HORS PÉRIMÈTRE** : délégué à un bureau d'études qualifié. Proposer des itérations de géométrie et de
cinématique, jamais improviser une validation structurelle.

## Conventions de code

- Backend : Python 3.13, Pydantic v2 (`Field(default, description=...)`), pas de dépendance lourde
  inutile (DXF écrit à la main). Commentaires/labels en français.
- Frontend : Svelte 4, stores réactifs, `updateSection(section, patch)` pour les éditions ;
  chaque champ d'input doit correspondre à un attribut réel du modèle (sinon l'édition est ignorée).
- Tester un changement IO via le round-trip sur `BIKE/eMTB_DOM_Engineering.bcad` (0 junk attendu).
