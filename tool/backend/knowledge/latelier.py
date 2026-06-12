"""Source de connaissances DISTANTE — base vectorielle QDRANT du projet « latelier ».

L'atelier (la-telier.com) maintient une énorme base QDRANT (~1,7 M de chunks issus de
manuels, docs SAV, fiches produits vélo) indexée avec des embeddings Voyage AI (voyage-3,
1024 dims, cosine). Ce module l'interroge en sémantique : embed la requête via Voyage →
recherche le top-k dans la collection QDRANT → renvoie des hits normalisés.

C'est un COMPLÉMENT à la banque locale (knowledge/bank.py, BM25 sur les docs du projet) :
la base locale = sources curées du projet DOM ; la base distante = corpus vélo généraliste
massif. L'assistant interroge la distante « si besoin » (specs composants, compatibilités…).

CONFIG PAR ENVIRONNEMENT (jamais de secret en dur) — actif seulement si tout est présent :
  - LATELIER_QDRANT_URL        ex. http://centerbeam.proxy.rlwy.net:24428  (proxy TCP du
                               service qdrant Railway, ou tout endpoint QDRANT HTTP)
  - VOYAGE_API_KEY             clé Voyage AI (celle du service latelier)
  - LATELIER_QDRANT_COLLECTION défaut « mecano_chunks » (vélo ; « moto_chunks » pour moto)
  - LATELIER_EMBED_MODEL       défaut « voyage-3 »

Sans config → `available()` renvoie False et `remote_search()` renvoie [] (aucune erreur,
l'outil reste 100 % fonctionnel hors-ligne).
"""

import json
import os
import urllib.request
import urllib.error

VOYAGE_ENDPOINT = "https://api.voyageai.com/v1/embeddings"
DEFAULT_COLLECTION = "mecano_chunks"
DEFAULT_MODEL = "voyage-3"
TIMEOUT = 30


def _cfg():
    return {
        "qdrant": os.environ.get("LATELIER_QDRANT_URL", "").rstrip("/"),
        "voyage_key": os.environ.get("VOYAGE_API_KEY", ""),
        "collection": os.environ.get("LATELIER_QDRANT_COLLECTION", DEFAULT_COLLECTION),
        "model": os.environ.get("LATELIER_EMBED_MODEL", DEFAULT_MODEL),
    }


def available() -> bool:
    """True si l'endpoint QDRANT et la clé Voyage sont configurés."""
    c = _cfg()
    return bool(c["qdrant"] and c["voyage_key"])


def _embed(text: str, cfg: dict) -> list:
    req = urllib.request.Request(
        VOYAGE_ENDPOINT,
        data=json.dumps({"input": [text], "model": cfg["model"], "input_type": "query"}).encode(),
        headers={"Authorization": f"Bearer {cfg['voyage_key']}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=TIMEOUT))["data"][0]["embedding"]


def remote_search(query: str, k: int = 5, collection: str | None = None) -> list:
    """Recherche sémantique dans la base QDRANT distante.

    Retourne une liste de hits normalisés {title, text, score, source, brands, models,
    component_types, page}. Liste vide si non configuré ou en cas d'erreur réseau (l'appel
    ne lève jamais — le retrieval local reste la source primaire)."""
    if not query or not available():
        return []
    cfg = _cfg()
    coll = collection or cfg["collection"]
    try:
        vec = _embed(query, cfg)
        body = {"vector": vec, "limit": k, "with_payload": True}
        req = urllib.request.Request(
            f"{cfg['qdrant']}/collections/{coll}/points/search",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        result = json.load(urllib.request.urlopen(req, timeout=TIMEOUT)).get("result") or []
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError, OSError):
        return []
    out = []
    for h in result:
        pl = h.get("payload") or {}
        out.append({
            "title": (pl.get("section_title") or pl.get("document_filename") or "").strip(),
            "text": (pl.get("content") or "").strip(),
            "score": round(h.get("score", 0.0), 3),
            "source": pl.get("document_filename"),
            "page": pl.get("page_number"),
            "brands": pl.get("brands") or [],
            "models": pl.get("models") or [],
            "component_types": pl.get("component_types") or [],
        })
    return out


def stats() -> dict:
    """État de la source distante (configurée ? collection ? nb de points)."""
    c = _cfg()
    info = {"available": available(), "collection": c["collection"], "model": c["model"],
            "endpoint_set": bool(c["qdrant"]), "voyage_key_set": bool(c["voyage_key"])}
    if available():
        try:
            r = json.load(urllib.request.urlopen(
                f"{c['qdrant']}/collections/{c['collection']}", timeout=TIMEOUT))
            info["points"] = r["result"].get("points_count")
        except Exception:
            info["points"] = None
    return info
