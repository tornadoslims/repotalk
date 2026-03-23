"""Document retrieval — vector (ChromaDB) and keyword modes."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from repotalk.config import Config
from repotalk.embedder import Embedder
from repotalk.models import RetrievedContext

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieves relevant documentation chunks for RAG."""

    def __init__(self, config: Config, docs_dir: Path) -> None:
        self.config = config
        self.docs_dir = docs_dir
        self._doc_cache: dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load all documentation into memory."""
        if self._loaded:
            return

        if not self.docs_dir.exists():
            logger.warning("Docs directory not found: %s", self.docs_dir)
            self._loaded = True
            return

        for md_file in self.docs_dir.rglob("*.md"):
            rel = str(md_file.relative_to(self.docs_dir))
            self._doc_cache[rel] = md_file.read_text(errors="replace")

        logger.info("Loaded %d documentation files", len(self._doc_cache))
        self._loaded = True

    def retrieve_keyword(self, query: str, top_k: int | None = None) -> list[RetrievedContext]:
        """Keyword-based retrieval using simple TF scoring."""
        self._ensure_loaded()
        top_k = top_k or self.config.chat.top_k

        query_terms = set(re.findall(r'\w+', query.lower()))
        if not query_terms:
            return []

        scored: list[tuple[str, str, float]] = []

        for doc_path, content in self._doc_cache.items():
            content_lower = content.lower()
            score = 0.0
            for term in query_terms:
                count = content_lower.count(term)
                if count > 0:
                    score += count

            # Boost based on document type
            if doc_path.endswith("_overview.md") or doc_path.endswith("_summary.md"):
                score *= 1.2  # Slight boost for summaries
            if "PROJECT" in doc_path.upper():
                score *= 0.8  # Slight penalty for very high-level if specific query

            if score > 0:
                scored.append((doc_path, content, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[2], reverse=True)

        results = []
        for doc_path, content, score in scored[:top_k]:
            # Determine doc type from path
            doc_type = "file"
            if "/" not in doc_path or doc_path.count("/") <= 1:
                if "overview" in doc_path.lower() or "summary" in doc_path.lower():
                    doc_type = "directory"

            results.append(
                RetrievedContext(
                    source=doc_path,
                    content=content,
                    relevance_score=score,
                    doc_type=doc_type,
                )
            )

        return results


class VectorRetriever:
    """Vector-based retrieval using ChromaDB."""

    def __init__(self, config: Config, docs_dir: Path) -> None:
        self.config = config
        self.docs_dir = docs_dir
        self._collection = None
        self._embedder = Embedder(config)

    async def _ensure_collection(self) -> Any:
        """Lazy-initialize ChromaDB collection."""
        if self._collection is not None:
            return self._collection

        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "ChromaDB is required for vector retrieval. "
                "Install it with: pip install 'repotalk[vector]'"
            )

        chroma_dir = self.docs_dir / ".chroma"
        client = chromadb.PersistentClient(path=str(chroma_dir))
        self._collection = client.get_or_create_collection(
            name="salt_docs",
            metadata={"hnsw:space": "cosine"},
        )

        # Index docs if collection is empty
        if self._collection.count() == 0:
            await self._index_docs()

        return self._collection

    async def _index_docs(self) -> None:
        """Index all documentation into ChromaDB."""
        if not self.docs_dir.exists():
            return

        docs = []
        ids = []
        metadatas = []

        for md_file in self.docs_dir.rglob("*.md"):
            rel = str(md_file.relative_to(self.docs_dir))
            content = md_file.read_text(errors="replace")
            docs.append(content)
            ids.append(rel)
            metadatas.append({"source": rel})

        if not docs:
            return

        logger.info("Indexing %d documents into ChromaDB...", len(docs))
        embeddings = await self._embedder.embed_batch(docs)

        self._collection.add(
            documents=docs,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )
        logger.info("Indexed %d documents", len(docs))

    async def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedContext]:
        """Vector similarity search."""
        top_k = top_k or self.config.chat.top_k
        collection = await self._ensure_collection()

        query_embedding = await self._embedder.embed(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        contexts = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                source = results["ids"][0][i] if results["ids"] else "unknown"
                distance = results["distances"][0][i] if results["distances"] else 0.0
                contexts.append(
                    RetrievedContext(
                        source=source,
                        content=doc,
                        relevance_score=1.0 - distance,  # Convert distance to similarity
                        doc_type="file",
                    )
                )

        return contexts
