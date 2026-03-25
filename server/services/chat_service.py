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

    # Enrich top results with actual source code
    source_root = Path(project.source_path)
    source_context = []
    for ctx in context_pieces[:3]:  # Top 3 most relevant
        src_path = ctx.source.replace('.md', '')  # strip .md to get .py path
        full_src_path = source_root / src_path
        if full_src_path.exists() and full_src_path.is_file():
            try:
                code = full_src_path.read_text(errors='replace')
                if len(code) > 8000:
                    code = code[:8000] + "\n... (truncated)"
                source_context.append({"path": src_path, "code": code})
            except Exception:
                pass

    # Build message history
    prev_messages = await get_conversation_messages(db, conversation.id, limit=config.chat.history_length)
    messages = []

    # System prompt
    system_prompt = _build_system_prompt(project, context_pieces, pinned_files, source_context)
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
        "source_files_included": len(source_context),
    }
    yield _sse("context_used", context_summary)

    # Define tools the LLM can use to look up more files
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_codebase",
                "description": "Search the codebase for files matching a query. Use this when you need to find additional source files to answer the user's question. Returns file paths and documentation summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g. 'node creation endpoints', 'workflow builder routes')"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the actual source code of a file by its relative path. Use when you need to see the exact implementation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path to the file (e.g. 'microservices/salt-builder-service/service/app/api/routes/builds.py')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]

    # Stream LLM response with tool use loop
    full_response = ""
    model = config.models.chat
    max_tool_rounds = 3
    try:
        import litellm

        for tool_round in range(max_tool_rounds + 1):
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
                stream=True,
                tools=tools if tool_round < max_tool_rounds else None,
            )

            tool_calls_buffer = {}  # id -> {name, arguments}
            has_tool_calls = False

            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # Handle streaming text
                if delta.content:
                    token = delta.content
                    full_response += token
                    yield _sse("token", {"content": token})

                # Handle tool calls
                if delta.tool_calls:
                    has_tool_calls = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_buffer[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["arguments"] += tc.function.arguments

            if not has_tool_calls:
                break  # Normal response, no tools needed

            # Process tool calls
            # Add the assistant message with tool calls to history
            assistant_tc_msg = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    }
                    for tc in tool_calls_buffer.values()
                ]
            }
            messages.append(assistant_tc_msg)

            for tc in tool_calls_buffer.values():
                tool_name = tc["name"]
                try:
                    import json as _json
                    args = _json.loads(tc["arguments"])
                except Exception:
                    args = {}

                result = ""
                if tool_name == "search_codebase":
                    query = args.get("query", "")
                    yield _sse("token", {"content": f"\n\n*🔍 Searching: {query}...*\n\n"})
                    full_response += f"\n\n*🔍 Searching: {query}...*\n\n"
                    try:
                        if config.chat.retrieval_method == "vector":
                            from repotalk.retriever import VectorRetriever
                            vr = VectorRetriever(config, docs_dir)
                            extra_ctx = await vr.retrieve(query, top_k=5)
                        else:
                            from repotalk.retriever import DocumentRetriever
                            kr = DocumentRetriever(config, docs_dir)
                            extra_ctx = kr.retrieve_keyword(query, top_k=5)

                        parts = []
                        for ctx in extra_ctx:
                            parts.append(f"### {ctx.source}\n{ctx.content[:1500]}\n")
                            # Also send as reference
                            yield _sse("reference", {"source": ctx.source, "relevance": ctx.relevance_score, "type": ctx.doc_type})
                        result = "\n".join(parts) if parts else "No results found."

                        # Load source for top result
                        if extra_ctx:
                            top_path = extra_ctx[0].source.replace('.md', '')
                            src_file = source_root / top_path
                            if src_file.exists():
                                code = src_file.read_text(errors='replace')[:6000]
                                result += f"\n\n### Source: {top_path}\n```python\n{code}\n```"
                    except Exception as e:
                        result = f"Search failed: {e}"

                elif tool_name == "read_file":
                    fpath = args.get("path", "")
                    yield _sse("token", {"content": f"\n\n*📄 Reading: {fpath}...*\n\n"})
                    full_response += f"\n\n*📄 Reading: {fpath}...*\n\n"
                    src_file = source_root / fpath
                    if src_file.exists():
                        code = src_file.read_text(errors='replace')
                        if len(code) > 8000:
                            code = code[:8000] + "\n... (truncated)"
                        result = f"```python\n{code}\n```"
                        yield _sse("reference", {"source": fpath, "relevance": 1.0, "type": "file"})
                    else:
                        result = f"File not found: {fpath}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

            # Continue the loop — LLM will process tool results and respond

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
    source_context: list[dict] | None = None,
) -> str:
    parts = [
        f"You are RepoTalk, an AI assistant that helps developers understand the codebase '{project.name}'.",
        f"The project source is at: {project.source_path}",
        "",
        "RULES:",
        "- Answer questions accurately using the documentation AND source code provided below.",
        "- Always cite specific files, functions, classes, and line references.",
        "- When you have the actual source code, read it carefully and give precise answers (exact route paths, function signatures, etc.).",
        "- Do NOT say 'inferred' or 'please check the source code' — you HAVE the source code below.",
        "- If you genuinely don't have enough context, say what specific file would help.",
        "",
    ]

    if pinned_files:
        parts.append("## Pinned Files (user focus)")
        for f in pinned_files:
            parts.append(f"  - {f}")
        parts.append("")

    # Include actual source code first (most valuable)
    if source_context:
        parts.append("## Actual Source Code (read carefully)")
        parts.append("")
        for src in source_context:
            parts.append(f"### File: {src['path']}")
            parts.append(f"```python\n{src['code']}\n```")
            parts.append("")

    # Then include documentation summaries
    if context_pieces:
        parts.append("## Documentation Summaries")
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
