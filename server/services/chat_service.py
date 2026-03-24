"""Chat service — RAG chat with streaming and context assembly."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.models_db import Conversation, Message, MessageRole, Project

logger = logging.getLogger("repotalk.chat_service")


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def stream_chat_response(
    db: AsyncSession,
    conversation: Conversation,
    user_message: str,
    project: Project,
    llm_client: Any,
    config: Any,
    pinned_files: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a chat response as SSE events.

    Yields SSE-formatted strings: "event: <type>\ndata: <json>\n\n"
    """
    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=user_message,
    )
    db.add(user_msg)
    await db.flush()

    # Build context using the core retriever
    output_path = project.output_path
    if not output_path:
        yield _sse("error", {"message": "Project not indexed yet"})
        yield _sse("done", {})
        return

    docs_dir = Path(output_path)
    context_pieces = []
    references = []

    try:
        # Try vector retrieval first (semantic search), fall back to keyword
        retriever = None
        contexts = []
        if config.chat.retrieval_method == "vector":
            try:
                from repotalk.retriever import VectorRetriever
                vr = VectorRetriever(config, docs_dir)
                contexts = await vr.retrieve(user_message, top_k=config.chat.top_k)
                retriever = vr
                logger.info("Vector retrieval: %d results for '%s'", len(contexts), user_message[:50])
            except Exception as vec_err:
                logger.warning("Vector retrieval failed, falling back to keyword: %s", vec_err)
                contexts = []

        if not contexts:
            from repotalk.retriever import DocumentRetriever
            retriever = DocumentRetriever(config, docs_dir)
            contexts = retriever.retrieve_keyword(user_message, top_k=config.chat.top_k)
            logger.info("Keyword retrieval: %d results for '%s'", len(contexts), user_message[:50])

        for ctx in contexts:
            context_pieces.append(ctx)
            ref = {"source": ctx.source, "relevance": ctx.relevance_score, "type": ctx.doc_type}
            references.append(ref)
            yield _sse("reference", ref)

    except Exception as exc:
        logger.warning("Retrieval failed: %s", exc)

    # Build message history
    prev_messages = await get_conversation_messages(db, conversation.id, limit=config.chat.history_length)
    messages = []

    # System prompt
    system_prompt = _build_system_prompt(project, context_pieces, pinned_files)
    messages.append({"role": "system", "content": system_prompt})

    # History
    for msg in prev_messages:
        if msg.id == user_msg.id:
            continue
        messages.append({"role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})

    # Send context_used event
    context_summary = {
        "sources": [r["source"] for r in references],
        "total_context_pieces": len(context_pieces),
    }
    yield _sse("context_used", context_summary)

    # Stream LLM response
    full_response = ""
    model = config.models.chat
    try:
        # Use litellm for streaming
        import litellm
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                token = delta.content
                full_response += token
                yield _sse("token", {"content": token})

        # Extract usage if available
        input_tokens = 0
        output_tokens = 0
        cost = 0.0
        try:
            from litellm import completion_cost
            cost = completion_cost(model=model, prompt=str(messages), completion=full_response)
        except Exception:
            pass

    except Exception as exc:
        logger.exception("LLM streaming failed")
        error_msg = f"Error generating response: {exc}"
        full_response = error_msg
        yield _sse("error", {"message": error_msg})

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=full_response,
        references={"sources": references},
        context_used=context_summary,
        model_used=model,
        token_count_in=input_tokens if 'input_tokens' in dir() else 0,
        token_count_out=output_tokens if 'output_tokens' in dir() else 0,
        cost=cost if 'cost' in dir() else 0.0,
        parent_message_id=user_msg.id,
    )
    db.add(assistant_msg)

    # Update conversation title if first message
    if not conversation.title:
        conversation.title = user_message[:100]
    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Suggest follow-up questions
    suggestions = _generate_suggestions(user_message, full_response)
    if suggestions:
        yield _sse("suggestions", {"suggestions": suggestions})

    yield _sse("done", {"message_id": str(assistant_msg.id)})


def _build_system_prompt(
    project: Project,
    context_pieces: list,
    pinned_files: list[str] | None = None,
) -> str:
    parts = [
        f"You are RepoTalk, an AI assistant that helps developers understand the codebase '{project.name}'.",
        f"The project source is at: {project.source_path}",
        "",
        "Use the following retrieved documentation context to answer questions accurately.",
        "Always cite specific files and functions when possible.",
        "If you're not sure about something, say so rather than guessing.",
        "",
    ]

    if pinned_files:
        parts.append("The user has pinned these files for focus:")
        for f in pinned_files:
            parts.append(f"  - {f}")
        parts.append("")

    if context_pieces:
        parts.append("## Retrieved Context")
        parts.append("")
        for ctx in context_pieces:
            parts.append(f"### {ctx.source} (relevance: {ctx.relevance_score:.2f})")
            parts.append(ctx.content[:2000])
            parts.append("")

    return "\n".join(parts)


def _generate_suggestions(question: str, response: str) -> list[str]:
    """Generate simple follow-up suggestions based on the conversation."""
    suggestions = []
    if "function" in response.lower() or "def " in response.lower():
        suggestions.append("What are the parameters and return types?")
    if "class" in response.lower():
        suggestions.append("What methods does this class expose?")
    if "import" in response.lower() or "depend" in response.lower():
        suggestions.append("Show me the dependency graph for this module")
    if not suggestions:
        suggestions = [
            "Can you explain this in more detail?",
            "What are the related files?",
            "Show me the call trace",
        ]
    return suggestions[:3]


def _sse(event: str, data: Any) -> str:
    """Format an SSE event. Include type in data payload for easy frontend parsing."""
    payload = {"type": event, **data} if isinstance(data, dict) else {"type": event, "data": data}
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
