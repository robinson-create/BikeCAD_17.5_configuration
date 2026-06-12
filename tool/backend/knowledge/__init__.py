"""Banque de connaissances vélo + récupération RAG (pour l'assistant).

`bank.py` fusionne en un seul corpus : entrées curées (specs M620, courroie Gates,
gearbox, concepts cinématique, cibles DOM), fichiers JSON du dossier, catalogue de
pièces BikeCAD scanné dans le dépôt, et CHUNKS de documents déposés dans
`knowledge/docs/` (PDF/txt/md exportés du NotebookLM, ingérés par `ingest.py`).

`search()` score tout avec **BM25 Okapi** (pondération IDF + saturation de fréquence,
cf. `bm25.py`) — pur Python, zéro dépendance lourde. L'index BM25 peut être remplacé
par un index d'embeddings plus tard sans changer l'API.
"""
from .bank import search, entries, reindex, stats  # noqa: F401
# Source DISTANTE optionnelle : base vectorielle QDRANT du projet latelier (~1,7 M chunks
# vélo). Configurée par env (LATELIER_QDRANT_URL + VOYAGE_API_KEY) — voir latelier.py.
from .latelier import (  # noqa: F401
    remote_search,
    available as remote_available,
    stats as remote_stats,
)
