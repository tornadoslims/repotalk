"""User management endpoints (team mode)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.auth import CurrentUser, get_current_user, require_role
from server.dependencies import get_db
from server.models_db import User, UserRole
from server.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role("admin")),
):
    # Check uniqueness
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")

    user = User(
        username=body.username,
        email=body.email,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{userId}", response_model=UserOut)
async def get_user(
    userId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{userId}", response_model=UserOut)
async def update_user(
    userId: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None:
        user.email = body.email
    if body.role is not None:
        try:
            user.role = UserRole(body.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    if body.preferences is not None:
        user.preferences = body.preferences

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{userId}", status_code=204)
async def delete_user(
    userId: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: CurrentUser = Depends(require_role("admin")),
):
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
