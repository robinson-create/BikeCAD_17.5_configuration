"""Banque de connaissances vélo + récupération (pour l'assistant).

`bank.py` : entrées curées (specs M620, amortisseurs, courroie Gates, gearbox,
concepts cinématique, cibles du projet DOM) + catalogue de pièces BikeCAD scanné
dans le dépôt. `search()` fait une récupération LEXICALE (recouvrement de tokens,
tags pondérés). Le scorer est isolé → on peut brancher un backend vectoriel
(embeddings) plus tard sans changer l'API.
"""
from .bank import search, entries  # noqa: F401
