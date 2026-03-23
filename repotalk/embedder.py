"""Embedding generation via litellm."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import litellm

from repotalk.config import Config

logger = logging.getLogger(__name__)


class Embedder:
    """Generate embeddings using litellm (supports any provider)."""

    def __init__(self, config: Config) -> None:
        self.model = config.models.embeddings
        self._semaphore = asyncio.Semaphore(config.processing.concurrency)

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        async with self._semaphore:
            response = await litellm.aembedding(
                model=self.model,
                input=[text],
            )
            return response.data[0]["embedding"]

    async def embed_batch(self, texts: list[str], batch_size: int = 20) -> list[list[float]]:
        """Embed a batch of texts with batching."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            async with self._semaphore:
                response = await litellm.aembedding(
                    model=self.model,
                    input=batch,
                )
                batch_embeddings = [item["embedding"] for item in response.data]
                all_embeddings.extend(batch_embeddings)

        return all_embeddings
