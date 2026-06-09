"""Mode lugs — jonctions tube↔lug pour cadre collé (lug-and-bond).

Cadre DOM : lugs CNC (Ti/Al) + tubes droits, collage époxy. Les tubes s'insèrent
dans des DOUILLES usinées dans le lug ; la géométrie clé d'un lug = pour chaque
douille : l'axe (direction du tube), l'alésage (Ø tube + jeu de collage), la
profondeur d'insertion, et les angles entre douilles.

  - `joint_model` : construit le graphe du cadre depuis BikeDesign+CalcResult et
    en déduit les nœuds-lugs et leurs douilles.
  - `miter`       : utilitaires de coupe (angle de bissectrice tube↔tube, plan
    de coupe d'about) — pour les cas soudés ou les abouts de douille.
  - `export_cad`  : export JSON + table de conception CSV (SolidWorks) + résumé.
"""
