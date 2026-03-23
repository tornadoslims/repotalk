"""Chat endpoints with SSE streaming."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from server.auth import CurrentUser, get_current_user
from server.dependencies import get_config, get_db, get_llm_client, get_project
from server.models_db import Conversation, Message, Project
from server.schemas import (
    BranchRequest,
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
)
from server.services import chat_service

router = APIRouter(tags=["chat"])


@router.get("/api/projects/{id}/conversations", response_model=list[ConversationOut])
async def list_conversations(
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project.id)
        .order_by(Conversation.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/api/projects/{id}/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    project: Project = Depends(get_project),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    conv = Conversation(
        project_id=project.id,
        user_id=user.user_id,
        title=body.title,
        scope=body.scope,
        pinned_files=body.pinned_files,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/api/conversations/{convId}/messages", response_model=list[MessageOut])
async def get_messages(
    convId: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    # Verify conversation exists
    result = await db.execute(select(Conversation).where(Conversation.id == convId))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await chat_service.get_conversation_messages(db, convId, limit, offset)
    return messages


@router.post("/api/conversations/{convId}/messages")
async def send_message(
    convId: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Send a message and receive SSE-streamed response."""
    result = await db.execute(select(Conversation).where(Conversation.id == convId))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get the project
    from server.models_db import Project
    proj_result = await db.execute(select(Project).where(Project.id == conv.project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    config = get_config()
    llm_client = get_llm_client()

    return StreamingResponse(
        chat_service.stream_chat_response(
            db=db,
            conversation=conv,
            user_message=body.content,
            project=project,
            llm_client=llm_client,
            config=config,
            pinned_files=body.pinned_files,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/api/conversations/{convId}", status_code=204)
async def delete_conversation(
    convId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Conversation).where(Conversation.id == convId))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()


@router.post("/api/conversations/{convId}/messages/{msgId}/branch", response_model=ConversationOut)
async def branch_conversation(
    convId: uuid.UUID,
    msgId: uuid.UUID,
    body: BranchRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Branch a conversation from a specific message."""
    # Get original conversation
    result = await db.execute(select(Conversation).where(Conversation.id == convId))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages up to and including the branch point
    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == convId)
        .order_by(Message.created_at)
    )
    messages = msgs_result.scalars().all()

    # Find the branch point message
    branch_idx = None
    for i, msg in enumerate(messages):
        if msg.id == msgId:
            branch_idx = i
            break
    if branch_idx is None:
        raise HTTPException(status_code=404, detail="Message not found in conversation")

    # Create new conversation
    new_conv = Conversation(
        project_id=conv.project_id,
        user_id=user.user_id,
        title=f"Branch: {conv.title or 'Untitled'}",
        scope=conv.scope,
        pinned_files=conv.pinned_files,
    )
    db.add(new_conv)
    await db.flush()

    # Copy messages up to branch point
    for msg in messages[: branch_idx + 1]:
        new_msg = Message(
            conversation_id=new_conv.id,
            role=msg.role,
            content=msg.content,
            references=msg.references,
            context_used=msg.context_used,
            model_used=msg.model_used,
            token_count_in=msg.token_count_in,
            token_count_out=msg.token_count_out,
            cost=msg.cost,
        )
        db.add(new_msg)

    await db.commit()
    await db.refresh(new_conv)
    return new_conv
