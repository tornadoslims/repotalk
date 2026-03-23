"""Chat/RAG interface — CLI chat, REPL, context export."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from repotalk.config import Config
from repotalk.llm_client import LLMClient
from repotalk.models import ChatMessage, RetrievedContext
from repotalk.retriever import DocumentRetriever, VectorRetriever

logger = logging.getLogger(__name__)
console = Console()


def _load_chat_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "chat_system.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return _DEFAULT_CHAT_PROMPT


_DEFAULT_CHAT_PROMPT = """\
You are an expert code assistant with deep knowledge of the codebase described in the provided documentation.

Your role is to:
- Answer questions about the codebase accurately, citing specific files and functions
- Explain architecture decisions and code patterns
- Help users understand data flow and dependencies
- Suggest where to find or modify specific functionality

When answering:
- Reference specific files, classes, and functions by name
- Explain how components connect to each other
- If you're unsure about something, say so rather than guessing
- Keep answers concise but thorough
"""


class ChatSession:
    """Interactive chat session with codebase documentation."""

    def __init__(
        self,
        config: Config,
        docs_dir: Path,
        client: LLMClient,
    ) -> None:
        self.config = config
        self.docs_dir = docs_dir
        self.client = client
        self.history: list[ChatMessage] = []
        self.system_prompt = _load_chat_system_prompt()

        # Initialize retriever based on config
        if config.chat.retrieval_method == "vector":
            self._vector_retriever = VectorRetriever(config, docs_dir)
            self._keyword_retriever = None
        else:
            self._keyword_retriever = DocumentRetriever(config, docs_dir)
            self._vector_retriever = None

    async def retrieve_context(self, query: str) -> list[RetrievedContext]:
        """Retrieve relevant documentation for a query."""
        if self._vector_retriever:
            return await self._vector_retriever.retrieve(query)
        elif self._keyword_retriever:
            return self._keyword_retriever.retrieve_keyword(query)
        return []

    async def ask(self, question: str) -> str:
        """Ask a question and get a response."""
        # Retrieve relevant context
        contexts = await self.retrieve_context(question)

        # Build context block
        context_text = ""
        if contexts:
            context_parts = []
            for ctx in contexts:
                context_parts.append(
                    f"### Source: {ctx.source} (relevance: {ctx.relevance_score:.2f})\n{ctx.content}"
                )
            context_text = "\n\n---\n\n".join(context_parts)

        # Build messages
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        if context_text:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant documentation:\n\n{context_text}",
                }
            )

        # Add conversation history (limited by config)
        history_limit = self.config.chat.history_length * 2  # pairs
        for msg in self.history[-history_limit:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": question})

        # Get response
        response = await self.client.complete(
            messages=messages,
            model=self.config.models.chat,
            phase="chat",
            max_tokens=4096,
            temperature=0.5,
        )

        # Update history
        self.history.append(ChatMessage(role="user", content=question))
        self.history.append(ChatMessage(role="assistant", content=response))

        return response

    async def run_repl(self) -> None:
        """Run interactive chat REPL."""
        console.print(
            Panel(
                "[bold green]repotalk Chat[/bold green]\n"
                "Ask questions about your codebase. Type 'quit' or 'exit' to stop.\n"
                "Type 'clear' to reset conversation history.",
                title="Codebase Chat",
            )
        )

        while True:
            try:
                question = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\nGoodbye!")
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                console.print("Goodbye!")
                break
            if question.lower() == "clear":
                self.history.clear()
                console.print("[dim]History cleared.[/dim]")
                continue
            if question.lower() == "cost":
                summary = self.client.cost_summary()
                console.print(f"[dim]Total cost: ${summary['total_cost']:.4f}[/dim]")
                continue

            with console.status("[bold green]Thinking..."):
                response = await self.ask(question)

            console.print("\n[bold green]Assistant:[/bold green]")
            console.print(Markdown(response))


def export_context(
    query: str,
    config: Config,
    docs_dir: Path,
) -> str:
    """Export relevant context for a query (for use with external LLMs).

    Returns a formatted context string.
    """
    retriever = DocumentRetriever(config, docs_dir)
    contexts = retriever.retrieve_keyword(query)

    parts = [
        f"# Context for: {query}\n",
        f"Retrieved {len(contexts)} relevant documents.\n",
    ]

    for ctx in contexts:
        parts.append(f"---\n## {ctx.source}\n\n{ctx.content}\n")

    return "\n".join(parts)
