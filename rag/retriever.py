from __future__ import annotations

import logging
import re
from typing import Any

from core.config import Settings, settings as default_settings
from rag.ingest import Doc, load_seed_docs

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "will", "with", "your", "you", "our", "we", "can", "not", "but",
}


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


class Retriever:
    """Hybrid retrieval: BM25 + dense vectors, fused with Reciprocal Rank Fusion."""

    def __init__(self, docs: list[Doc] | None = None, cfg: Settings = default_settings):
        self.cfg = cfg
        self.docs = docs or load_seed_docs()
        self.by_id = {d.doc_id: d for d in self.docs}
        self.bm25 = None
        self.chroma = None
        self.embedder = None
        self._init_bm25()
        self._init_chroma()

    def _init_bm25(self) -> None:
        try:
            from rank_bm25 import BM25Okapi

            self.bm25 = BM25Okapi([tokenize(d.content) for d in self.docs])
        except Exception as exc:  # optional dependency
            logger.warning("BM25 unavailable: %s", exc)

    def _init_chroma(self) -> None:
        if not self.cfg.embedding_ready:
            logger.warning("Embeddings disabled; retrieval will use BM25 only.")
            return
        try:
            import chromadb
            from langchain_openai import OpenAIEmbeddings

            self.embedder = OpenAIEmbeddings(
                model=self.cfg.embedding_model,
                api_key=self.cfg.openai_api_key,
                base_url=self.cfg.openai_base_url,
            )
            client = chromadb.PersistentClient(path=str(self.cfg.chroma_dir))
            try:
                client.delete_collection("amz_ops")
            except Exception:
                pass
            collection = client.create_collection(
                "amz_ops", metadata={"hnsw:space": "cosine"}
            )
            embeddings = self.embedder.embed_documents([d.content for d in self.docs])
            collection.add(
                ids=[d.doc_id for d in self.docs],
                documents=[d.content for d in self.docs],
                metadatas=[
                    {
                        "doc_type": d.doc_type,
                        "title": d.title,
                        **{
                            k: v
                            for k, v in d.metadata.items()
                            if isinstance(v, (str, int, float, bool))
                        },
                    }
                    for d in self.docs
                ],
                embeddings=embeddings,
            )
            self.chroma = collection
        except Exception as exc:
            logger.warning("Vector index unavailable, falling back to BM25: %s", exc)
            self.chroma = None
            self.embedder = None

    @staticmethod
    def _rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, doc_id in enumerate(ranking):
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
        return sorted(scores.items(), key=lambda item: -item[1])

    def search(
        self,
        query: str,
        top_k: int | None = None,
        doc_types: list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        top_k = top_k or self.cfg.top_k

        def matches(doc: Doc) -> bool:
            if doc_types and doc.doc_type not in doc_types:
                return False
            if metadata_filter and any(
                doc.metadata.get(key) != value
                for key, value in metadata_filter.items()
            ):
                return False
            return True

        candidates = [doc for doc in self.docs if matches(doc)]
        if not candidates:
            return []

        bm25_ranking: list[str] = []
        if self.bm25 is not None:
            scores = self.bm25.get_scores(tokenize(query))
            ranked = sorted(zip(self.docs, scores), key=lambda item: -item[1])
            bm25_ranking = [
                doc.doc_id for doc, _ in ranked if matches(doc)
            ][:20]

        vector_ranking: list[str] = []
        if self.chroma is not None and self.embedder is not None:
            try:
                query_vec = self.embedder.embed_query(query)
                kwargs: dict[str, Any] = {
                    "query_embeddings": [query_vec],
                    "n_results": 20,
                }
                if metadata_filter:
                    kwargs["where"] = metadata_filter
                res = self.chroma.query(**kwargs)
                ids = res.get("ids", [[]])[0]
                vector_ranking = [
                    doc_id
                    for doc_id in ids
                    if doc_id in self.by_id and matches(self.by_id[doc_id])
                ]
            except Exception as exc:
                logger.warning("Vector search failed: %s", exc)

        fused = self._rrf([bm25_ranking, vector_ranking])
        if not fused:
            query_tokens = set(tokenize(query))
            scored = [
                (doc.doc_id, len(query_tokens & set(tokenize(doc.content))))
                for doc in candidates
            ]
            fused = sorted(scored, key=lambda item: -item[1])

        results: list[dict[str, Any]] = []
        for doc_id, score in fused[:top_k]:
            doc = self.by_id.get(doc_id)
            if doc is None:
                continue
            results.append(
                {
                    "doc_id": doc.doc_id,
                    "doc_type": doc.doc_type,
                    "title": doc.title,
                    "snippet": doc.content[:420].replace("\n", " "),
                    "score": round(float(score), 5),
                }
            )
        return results
