"""Ingestion de documents sources → chunks indexables (RAG).

Lit les fichiers déposés dans `knowledge/docs/` (.txt, .md, .pdf), en extrait le
texte, et le découpe en chunks avec chevauchement. Chaque chunk devient une
entrée de connaissance {id, title, tags, text, source, page} consommée par
`bank.search()` (BM25).

C'est ici qu'arrivent les sources exportées du NotebookLM : exporte chaque source
en PDF ou en texte, dépose-la dans `knowledge/docs/`, puis réindexe
(POST /api/knowledge/reindex, ou redémarre le backend).

PDF : extraction via `pypdf` (pur Python). Si pypdf est absent, les PDF sont
ignorés avec un avertissement (les .txt/.md restent ingérés).
"""

import re
from functools import lru_cache
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent / "docs"

# Cible de découpe : ~900 caractères par chunk, ~150 de chevauchement. Assez grand
# pour garder le contexte d'un paragraphe, assez petit pour une récupération ciblée.
CHUNK_CHARS = 900
OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 80   # on jette les miettes (en-têtes isolés, numéros de page)


def _read_txt(path: Path) -> list[tuple[int, str]]:
    """Texte brut → une seule 'page' (page 0)."""
    try:
        return [(0, path.read_text(encoding="utf-8", errors="replace"))]
    except Exception:
        return []


def _read_pdf(path: Path) -> list[tuple[int, str]]:
    """PDF → liste (numéro de page 1-based, texte). Vide si pypdf absent."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    try:
        reader = PdfReader(str(path))
        return [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]
    except Exception:
        return []


_READERS = {".txt": _read_txt, ".md": _read_txt, ".markdown": _read_txt, ".pdf": _read_pdf}

# Fichiers de service du dossier docs/ : consignes, pas du contenu à indexer.
_SKIP_NAMES = {"readme.md", "readme.txt", "readme"}


def _is_source(p: Path) -> bool:
    return (p.is_file() and p.suffix.lower() in _READERS
            and p.name.lower() not in _SKIP_NAMES)


def _clean(text: str) -> str:
    """Normalise les espaces, recolle les césures de fin de ligne (mot-\\n)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)        # césure PDF : « suspen-\nsion »
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk(text: str) -> list[str]:
    """Découpe en chunks ~CHUNK_CHARS, frontières de paragraphe, chevauchement."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paras:
        if len(buf) + len(para) + 2 <= CHUNK_CHARS:
            buf = f"{buf}\n\n{para}" if buf else para
            continue
        if buf:
            chunks.append(buf)
        # un paragraphe plus grand qu'un chunk → découpe dure avec chevauchement
        if len(para) > CHUNK_CHARS:
            start = 0
            while start < len(para):
                chunks.append(para[start:start + CHUNK_CHARS])
                start += CHUNK_CHARS - OVERLAP_CHARS
            buf = ""
        else:
            buf = para
    if buf:
        chunks.append(buf)
    # chevauchement inter-chunks : préfixe la fin du précédent
    out: list[str] = []
    for i, c in enumerate(chunks):
        if i > 0:
            tail = chunks[i - 1][-OVERLAP_CHARS:]
            c = f"…{tail.strip()} {c}"
        if len(c) >= MIN_CHUNK_CHARS:
            out.append(c)
    return out


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _docs_fingerprint() -> tuple:
    """Empreinte (chemin, taille, mtime) des fichiers sources → invalide le cache."""
    if not DOCS_DIR.is_dir():
        return ()
    files = []
    for p in sorted(DOCS_DIR.rglob("*")):
        if _is_source(p):
            st = p.stat()
            files.append((str(p), st.st_size, int(st.st_mtime)))
    return tuple(files)


@lru_cache(maxsize=4)
def _chunks_for(fingerprint: tuple) -> list:
    """Construit les entrées-chunks pour une empreinte donnée (mémoïsé)."""
    out = []
    for path_str, _size, _mtime in fingerprint:
        path = Path(path_str)
        reader = _READERS.get(path.suffix.lower())
        if not reader:
            continue
        doc_slug = _slugify(path.stem)
        tags = ["document", "source"] + [t for t in re.split(r"[^a-zà-ÿ0-9]+", path.stem.lower()) if len(t) > 2]
        for page_no, raw in reader(path):
            text = _clean(raw)
            if not text:
                continue
            for ci, chunk in enumerate(_chunk(text)):
                loc = f"p.{page_no}" if page_no else f"§{ci + 1}"
                out.append({
                    "id": f"doc-{doc_slug}-{page_no}-{ci}",
                    "title": f"{path.stem} ({loc})",
                    "tags": tags,
                    "text": chunk,
                    "source": path.name,
                    "page": page_no,
                })
    return out


def doc_chunks() -> list:
    """Entrées-chunks issues des documents de knowledge/docs/ (mémoïsé sur mtime)."""
    return _chunks_for(_docs_fingerprint())


def stats() -> dict:
    """État de l'ingestion : fichiers, chunks, dépendance PDF."""
    fp = _docs_fingerprint()
    chunks = _chunks_for(fp)
    try:
        import pypdf  # noqa: F401
        pdf_ok = True
    except ImportError:
        pdf_ok = False
    by_source: dict[str, int] = {}
    for c in chunks:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    return {
        "docs_dir": str(DOCS_DIR),
        "exists": DOCS_DIR.is_dir(),
        "files": len(fp),
        "chunks": len(chunks),
        "by_source": by_source,
        "pdf_support": pdf_ok,
    }
