"""BM25 Okapi — récupération lexicale pondérée, pur Python (zéro dépendance).

Améliore le simple recouvrement de tokens : un terme rare (IDF élevé) pèse plus
qu'un terme courant, et la fréquence d'un terme dans un document est saturée
(normalisée par la longueur du document). C'est le standard de référence pour la
recherche plein-texte sur du vocabulaire technique précis (« belt growth »,
« anti-squat », « M620 »…).

Usage :
    idx = BM25([["belt", "growth"], ["anti", "squat"], ...])   # corpus = listes de tokens
    scores = idx.scores(["belt", "growth"])                    # 1 score par document

Pour brancher une vraie base vectorielle (embeddings) plus tard : remplacer la
classe par un index ANN ; l'API `bank.search()` ne change pas.
"""

import math
from collections import Counter

K1 = 1.5   # saturation de la fréquence de terme
B = 0.75   # influence de la longueur du document


class BM25:
    """Index BM25 Okapi sur un corpus figé de documents tokenisés."""

    def __init__(self, corpus: list[list[str]]):
        self.corpus = corpus
        self.n = len(corpus)
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        # index inversé terme -> [(doc_idx, freq), ...] + fréquence documentaire
        self.postings: dict[str, list[tuple[int, int]]] = {}
        df: Counter = Counter()
        for i, doc in enumerate(corpus):
            tf = Counter(doc)
            for term, f in tf.items():
                self.postings.setdefault(term, []).append((i, f))
                df[term] += 1
        # IDF Okapi (variante +1 → toujours positif, jamais de score négatif)
        self.idf: dict[str, float] = {
            term: math.log(1 + (self.n - d + 0.5) / (d + 0.5)) for term, d in df.items()
        }

    def scores(self, query_tokens: list[str]) -> list[float]:
        """Score BM25 de chaque document du corpus pour la requête."""
        out = [0.0] * self.n
        if not self.n:
            return out
        for term in query_tokens:
            postings = self.postings.get(term)
            if not postings:
                continue
            idf = self.idf[term]
            for i, f in postings:
                denom = f + K1 * (1 - B + B * self.doc_len[i] / self.avgdl)
                out[i] += idf * f * (K1 + 1) / denom
        return out

    def top_k(self, query_tokens: list[str], k: int) -> list[tuple[int, float]]:
        """Indices des k meilleurs documents (score > 0), triés décroissant."""
        scored = [(i, s) for i, s in enumerate(self.scores(query_tokens)) if s > 0]
        scored.sort(key=lambda x: -x[1])
        return scored[:k]
