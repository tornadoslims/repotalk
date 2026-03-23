"""Settings and usage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from server.auth import CurrentUser, get_current_user, require_role
from server.dependencies import get_config, get_llm_client
from server.schemas import ModelInfo, SettingsOut, SettingsUpdate, UsageStats

router = APIRouter(tags=["settings"])

KNOWN_MODELS = [
    ModelInfo(id="anthropic/claude-sonnet-4-20250514", name="Claude Sonnet 4", provider="Anthropic", context_window=200000),
    ModelInfo(id="anthropic/claude-opus-4-20250514", name="Claude Opus 4", provider="Anthropic", context_window=200000),
    ModelInfo(id="anthropic/claude-haiku-3-5-20241022", name="Claude 3.5 Haiku", provider="Anthropic", context_window=200000),
    ModelInfo(id="openai/gpt-4o", name="GPT-4o", provider="OpenAI", context_window=128000),
    ModelInfo(id="openai/gpt-4o-mini", name="GPT-4o Mini", provider="OpenAI", context_window=128000),
    ModelInfo(id="gemini/gemini-2.5-flash", name="Gemini 2.5 Flash", provider="Google", context_window=1000000),
    ModelInfo(id="gemini/gemini-2.5-pro", name="Gemini 2.5 Pro", provider="Google", context_window=1000000),
    ModelInfo(id="openai/text-embedding-3-small", name="Text Embedding 3 Small", provider="OpenAI", context_window=8192, supports_streaming=False),
]


@router.get("/api/settings", response_model=SettingsOut)
async def get_settings(user: CurrentUser = Depends(get_current_user)):
    config = get_config()
    return SettingsOut(
        models=config.models.model_dump(),
        processing=config.processing.model_dump(),
        chat=config.chat.model_dump(),
        output=config.output.model_dump(),
    )


@router.patch("/api/settings", response_model=SettingsOut)
async def update_settings(
    body: SettingsUpdate,
    user: CurrentUser = Depends(require_role("admin")),
):
    config = get_config()

    if body.models:
        for key, value in body.models.items():
            if hasattr(config.models, key):
                setattr(config.models, key, value)

    if body.processing:
        for key, value in body.processing.items():
            if hasattr(config.processing, key):
                setattr(config.processing, key, value)

    if body.chat:
        for key, value in body.chat.items():
            if hasattr(config.chat, key):
                setattr(config.chat, key, value)

    if body.output:
        for key, value in body.output.items():
            if hasattr(config.output, key):
                setattr(config.output, key, value)

    return SettingsOut(
        models=config.models.model_dump(),
        processing=config.processing.model_dump(),
        chat=config.chat.model_dump(),
        output=config.output.model_dump(),
    )


@router.get("/api/settings/models", response_model=list[ModelInfo])
async def list_models():
    return KNOWN_MODELS


@router.get("/api/usage", response_model=UsageStats)
async def get_usage():
    try:
        client = get_llm_client()
        summary = client.cost_summary()
        return UsageStats(
            total_input_tokens=summary.get("total_input_tokens", 0),
            total_output_tokens=summary.get("total_output_tokens", 0),
            total_cost=summary.get("total_cost", 0.0),
            by_phase=summary.get("phases", {}),
        )
    except Exception:
        return UsageStats()
