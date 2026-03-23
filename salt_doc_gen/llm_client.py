"""Unified LLM interface via litellm with retry, rate limiting, cost tracking."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

from salt_doc_gen.config import Config
from salt_doc_gen.models import CostRecord

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True


class LLMClient:
    """Async LLM client with concurrency control, retry, and cost tracking."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._semaphore = asyncio.Semaphore(config.processing.concurrency)
        self._cost_records: list[CostRecord] = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_cost = 0.0

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        phase: str = "",
        file_path: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        """Make a completion request with concurrency control and retry."""
        async with self._semaphore:
            return await self._complete_with_retry(
                messages=messages,
                model=model,
                phase=phase,
                file_path=file_path,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _complete_with_retry(
        self,
        messages: list[dict[str, str]],
        model: str,
        phase: str,
        file_path: str | None,
        temperature: float,
        max_tokens: int,
        **kwargs: Any,
    ) -> str:
        """Inner completion with retry logic."""
        start = time.monotonic()

        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        elapsed = time.monotonic() - start
        content = response.choices[0].message.content or ""

        # Track costs
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = 0.0

        record = CostRecord(
            phase=phase,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            file_path=file_path,
        )
        self._cost_records.append(record)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        self._total_cost += cost

        logger.debug(
            "%s [%s] %s — %d in / %d out tokens, $%.4f, %.1fs",
            phase,
            model,
            file_path or "N/A",
            input_tokens,
            output_tokens,
            cost,
            elapsed,
        )

        return content

    @property
    def cost_records(self) -> list[CostRecord]:
        return list(self._cost_records)

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_tokens(self) -> tuple[int, int]:
        return self._total_input_tokens, self._total_output_tokens

    def cost_summary(self) -> dict[str, Any]:
        """Return cost summary grouped by phase."""
        phases: dict[str, dict[str, Any]] = {}
        for r in self._cost_records:
            if r.phase not in phases:
                phases[r.phase] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            phases[r.phase]["calls"] += 1
            phases[r.phase]["input_tokens"] += r.input_tokens
            phases[r.phase]["output_tokens"] += r.output_tokens
            phases[r.phase]["cost"] += r.cost

        return {
            "phases": phases,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_cost": self._total_cost,
        }
