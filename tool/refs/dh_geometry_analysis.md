# Analyse géométrie DH/enduro — DOM vs E22/E23 vs Specialized Levo

# Analyse géométrie — Projet e-MTB DOM vs E22/E23 vs Levo 4 X

## 1) Tableau comparatif synthétique

| Paramètre | E22 | E23 | Levo 4 X (S4) | Cibles DOM | Écart DOM vs E22/E23 | Écart DOM vs Levo 4 |
|---|---|---|---|---|---|---|
| **HA (angle direction)** | 66° | 66° | 64,5° | 63,5–64° | **−2 à −2,5°** (trop droit) | −0,5 à −1° (un peu plus slack) |
| **STA effectif** | 72,5° | 72,5° | 77° | 77–78° | **+4,5 à +5,5°** (E22/E23 trop couché) | ≈ identique |
| **Reach** | 420/446/470 | idem E22 | 480 (S4) | ≈480 | E22 plafonne à 470 en 20" | ≈ identique (S4) |
| **Bases (RC)** | 484 | 495 | 435 (→446) | 435 | **−49 à −60 mm** | ≈ identique |
| **BB drop** | 25 | 25 | 29,5 | 30 | +5 mm (DOM plus bas) | ≈ identique |
| **WB** | 1231–1284 | 1242–1294 | ~1264 (S4) | ~1254 (réf.) | DOM plus court (bases courtes) | ≈ comparable |
| **Stack** | 623–641 | idem | 638 (S4) | 622 (réf.) / HT 120–125 | comparable | DOM un peu plus bas |
| **Débattement AV/AR** | n.c. (tout-susp.) | idem | 160/150 (EVO 180/170) | 160 (V1) / 170 | — | DOM = EVO en V2 |
| **Roues** | 29 | 29 | mixtes 29/27,5 | **29 full** | identiques | DOM full 29 vs mullet |
| **Moteur** | M620 (fort couple) | idem | Specialized 3.1 (720W crête / 111 Nm) | M620 | identiques | couple comparable |

> Note : la fiche DOM cite « 850W/111Nm » pour le Levo ; le crête S-Works **vérifié** est 720 W (101 Nm/666 W en standard). À corriger dans la doc projet.

## 2) Positionnement du projet DOM et recommandations chiffrées

**Segment.** Les cibles DOM (HA 63,5–64°, STA eff 77–78°, bases 435, BB drop 30, reach ~480, débattement 160→170) placent le projet en **enduro / e-enduro agressif 2025**, cohérent avec la plage de marché (HA enduro 63–65°, reach M ~450–460 / L >500, STA eff 77–78°). Le DOM est **plus slack que le Levo 4 X de série** (proche du Levo 4 **EVO** : HA 63,6°, 170/180 mm) et **radicalement éloigné du E22/E23**, qui est un châssis **trail/SUV/touring** (direction droite, STA couché, bases 484–495) à recadrer fortement.

**Cohérence des cotes.** L'ensemble HA 63,5–64° + bases 435 + BB drop 30 + reach 480 est interne-cohérent et benchmarké quasi 1:1 sur le Levo 4 / EVO. Le seul point de tension structurel est la combinaison **bases 435 mm + carter M620 + roue 29 full** (voir §3).

**Recommandations chiffrées :**

1. **HA : verrouiller à 63,8° de série, avec jeu de direction excentrique ±1°** (→ 62,8–64,8°). C'est la solution Specialized (Geo Adj, Stumpjumper EVO) : règle l'accord HA/trail sans nouveau cadre. À HA 63,8° + offset **44 mm** (comme Levo), viser un **trail ~125–130 mm** (sweet-spot VTT 80–100 mm dépassé volontairement en enduro-gravity pour la stabilité ; rester ≤132 mm comme Levo).

2. **Bases : viser 440–445 mm plutôt que 435 mm strict.** 435 mm est le chiffre **musculaire** ; sur e-MTB la moyenne mesurée est **446 ±3,4 mm** à cause du carter. Avec le M620 (carter 234×140, plus gros qu'un Bosch/Specialized), tenir 435 mm en **29 full** est difficile (dégagement roue/carter). Recommandation : **base nominale 440 mm + flip-chip ±5 mm** (430–445), à valider par le calcul d'enveloppe carter (`calculations/motor.py`).

3. **Mullet (29/27,5 AR) à considérer sérieusement en V2.** Le Levo 4 et le Demo sont mullet précisément pour **raccourcir les bases et dégager le carter**. Passer la roue AR en 27,5" libère le compromis bases/carter du M620 et gagne en maniabilité — au prix d'un BB à recaler (~+5 mm via flip-chip). Le DOM full-29 est défendable, mais **le mullet est l'outil le plus direct pour atteindre des bases courtes avec ce moteur**.

4. **BB drop : 30 mm OK en 29 full** (hauteur BB ~350 mm, conforme Demo/V10/Levo). Si passage mullet, le drop apparent change → **prévoir un flip-chip BB ±6 mm** (pratique Demo/Status) pour garder ~350 mm de hauteur sol et limiter le pedal-strike (manivelles courtes 160–165 mm recommandées sur e-MTB à BB haut).

5. **Débattement : figer 160 mm AR (V1) avec ressort progressif, viser 170 mm AR (V2) façon Levo EVO.** Côté fourche, **170–180 mm AV** (simple-té enduro, A2C ~577–590 mm) cohérent avec HA 63,8°. Conserver la progressivité **20–30 %** ciblée (le placeholder actuel est à ~−1 %, à retravailler).

## 3) Pièges e-MTB spécifiques au projet DOM

- **Bases longues imposées par le carter M620.** Le M620 est un moteur **fort couple (160–170 Nm, conçu eCargo/eFat)** : carter volumineux qui **repousse l'axe arrière**. Vouloir 435 mm en 29 full est le piège n°1 — risque de collision roue/carter et de bases plus longues que prévu à la fabrication. → valider l'enveloppe avant de figer (`motor_clearance_ok`).

- **Kickback courroie (Gates) amplifié par le couple moteur.** La courroie + moyeu 3×3 ne tolère pas la **croissance de longueur (belt growth)** comme une chaîne : cible **<2 mm** (le four-bar placeholder actuel est à **16 mm** — rédhibitoire). Le couple M620 amplifie les efforts de chaîne/courroie → **un AS élevé en milieu de course augmente le kickback**. Le preset **high_pivot_m620** (single-pivot haut + galet près du pivot) ramène belt growth ≈4,7 mm, kickback ≈4,3°, AS ≈112 % : c'est la bonne direction, mais **4,7 mm reste > cible 2 mm** → affiner la position du galet (distance galet→pivot quasi constante en compression annule le kickback).

- **BB haut + carter → pedal-strike.** Le carter impose un BB plus haut ; compenser par **manivelles courtes (160–165 mm)** plutôt que par un drop réduit (ne pas retomber dans le BB drop 25 du E22).

- **STA effectif dépend de la hauteur de selle.** 77–78° est un **STA effectif** : à valider à la **hauteur de pédalage réelle** du pilote (grands cadres → bassin reculé si non corrigé). Sur long débattement + e-MTB, soigner l'angle réel, pas l'angle « tube ».

- **Masse centrale (moteur + batterie 840 Wh-class).** Batterie dans le tube diagonal (largeur interne ≥100 mm pour pack 52V) : **mal placés, moteur+batterie dégradent la suspension et la tenue de route même avec une bonne géométrie**. Garder la masse basse et centrée, valider le dégagement batterie/tube/carter (`calculations/battery.py`).

- **Anti-squat « indicatif ».** L'AS calculé par l'outil (méthode IC + ligne de courroie, cross-validée vs `bikinematicsolver`) reste **à valider dans Linkage avant fabrication** — organe de sécurité ~80 km/h, dimensionnement structurel **hors périmètre** (bureau d'études).