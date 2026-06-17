"""Optional ChromaDB evidence store for explainable RAG.

This module is intentionally optional.  The main deck-generation pipeline must
continue to work even when ChromaDB is not installed, cannot initialize, or when
an embedding model is unavailable.  The public entry point is
``try_build_chroma_store``; it returns ``None`` instead of raising in normal
failure cases.

Default embedding backend
-------------------------
For hackathon reliability, the default embedding function is a deterministic
local hashing embedding.  It has no network calls and no model downloads.

For better semantic retrieval, install sentence-transformers and set:

    EXEC_INTEL_EMBED_BACKEND=sentence_transformers
    EXEC_INTEL_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

Chroma remains a retrieval backend only; all reasoning and PPT rendering stay in
ai_analyzer.py / presentation modules.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]+|\d+(?:\.\d+)?%?|\$?\d+(?:\.\d+)?[BMK]?", re.I)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def _hash_embedding(text: str, dim: int = 384) -> List[float]:
    """Fast deterministic embedding with no external dependency.

    This is not as semantic as a transformer embedding, but it provides a stable
    local vector representation for Chroma and pairs well with the existing BM25
    retriever in hybrid mode.
    """
    vec = [0.0] * dim
    for tok in _tokens(text):
        digest = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class _SentenceTransformerEmbedder:
    def __init__(self, model_name: Optional[str] = None):
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model_name = model_name or os.getenv(
            "EXEC_INTEL_EMBED_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        embeddings = self.model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, emb)) for emb in embeddings]


class _HashEmbedder:
    model_name = "local_hash_embedding_384"

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        return [_hash_embedding(text) for text in texts]


def _make_embedder():
    backend = os.getenv("EXEC_INTEL_EMBED_BACKEND", "hash").strip().lower()
    if backend in {"sentence_transformers", "sentence-transformer", "st"}:
        try:
            return _SentenceTransformerEmbedder()
        except Exception as exc:
            print(f"[chroma_store] sentence-transformers unavailable; using hash embeddings: {exc}")
    return _HashEmbedder()


def _metadata_value(value: Any) -> Any:
    """Chroma metadata values must be scalar."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)) or value is None:
        return "" if value is None else value
    return _clean_text(value)[:500]


def _sanitize_metadata(item: Dict[str, Any], doc_id: str, domain: str) -> Dict[str, Any]:
    meta = dict(item.get("metadata") or {})
    meta.update({
        "doc_id": doc_id,
        "domain": domain or "general",
        "evidence_id": item.get("id", ""),
        "source_type": item.get("source_type", "document"),
        "has_number": bool(item.get("has_number")),
    })
    return {str(k): _metadata_value(v) for k, v in meta.items()}


class ChromaEvidenceStore:
    """Tiny wrapper around a Chroma collection for one document's evidence."""

    def __init__(self, collection, items: Sequence[Dict[str, Any]], doc_id: str, domain: str, embedder):
        self.collection = collection
        self.items = list(items or [])
        self.doc_id = doc_id
        self.domain = domain or "general"
        self.embedder = embedder
        self.id_index = {item.get("id"): dict(item) for item in self.items if item.get("id")}
        self.embedding_backend = getattr(embedder, "model_name", embedder.__class__.__name__)

    @classmethod
    def build(
        cls,
        items: Sequence[Dict[str, Any]],
        doc_id: str,
        domain: str = "general",
        path: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> "ChromaEvidenceStore":
        import chromadb  # type: ignore

        path = path or os.getenv("EXEC_INTEL_CHROMA_PATH", ".exec_intel_chroma")
        collection_name = collection_name or os.getenv("EXEC_INTEL_CHROMA_COLLECTION", "exec_intel_evidence")

        client = chromadb.PersistentClient(path=path)
        collection = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        embedder = _make_embedder()

        store = cls(collection=collection, items=items, doc_id=doc_id, domain=domain, embedder=embedder)
        store.reset_document()
        store.add_items(items)
        return store

    def reset_document(self) -> None:
        try:
            self.collection.delete(where={"doc_id": self.doc_id})
        except Exception:
            # Collection may be empty or backend may not support deletion for an
            # empty where result.  This should never block PPT generation.
            pass

    def add_items(self, items: Sequence[Dict[str, Any]]) -> None:
        docs, ids, metas = [], [], []
        for item in items:
            eid = item.get("id")
            text = _clean_text(item.get("text"))
            if not eid or not text:
                continue
            ids.append(f"{self.doc_id}_{eid}")
            docs.append(text)
            metas.append(_sanitize_metadata(item, self.doc_id, self.domain))

        if not docs:
            return

        embeddings = self.embedder.encode(docs)
        # Chroma add can handle batches; keep one call for small/medium docs.
        self.collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    def search(self, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        query = _clean_text(query)
        if not query:
            return []
        query_embedding = self.embedder.encode([query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(1, top_k),
            where={"doc_id": self.doc_id},
            include=["documents", "metadatas", "distances"],
        )

        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits = []
        for document, metadata, distance in zip(docs, metas, distances):
            eid = (metadata or {}).get("evidence_id")
            item = dict(self.id_index.get(eid, {}))
            if not item:
                item = {
                    "id": eid,
                    "source_type": (metadata or {}).get("source_type", "document"),
                    "text": document,
                    "metadata": metadata or {},
                    "has_number": bool((metadata or {}).get("has_number")),
                }
            # cosine distance is smaller-is-better; convert to a rough score.
            score = 1.0 / (1.0 + float(distance or 0.0))
            item["score"] = round(score, 4)
            item["retrieval_backend"] = "chroma"
            hits.append(item)
        return hits

    def search_many(self, queries: Iterable[str], top_k_each: int = 6, max_items: int = 14) -> List[Dict[str, Any]]:
        dedup: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        for query in queries:
            for item in self.search(query, top_k=top_k_each):
                eid = item.get("id")
                if not eid:
                    continue
                existing = dedup.get(eid)
                if existing is None or item.get("score", 0) > existing.get("score", 0):
                    dedup[eid] = item
        return list(dedup.values())[:max_items]


def try_build_chroma_store(
    items: Sequence[Dict[str, Any]],
    doc_id: str,
    domain: str = "general",
) -> Optional[ChromaEvidenceStore]:
    """Return a Chroma store or None without breaking the pipeline."""
    backend = os.getenv("EXEC_INTEL_RAG_BACKEND", "auto").strip().lower()
    if backend in {"local", "bm25", "memory", "in_memory", "off", "false", "0"}:
        return None
    try:
        return ChromaEvidenceStore.build(items=items, doc_id=doc_id, domain=domain)
    except Exception as exc:
        print(f"[chroma_store] Chroma disabled; using local RAG fallback: {exc}")
        return None
