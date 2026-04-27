"""Settings API — check API key status and available providers."""

import os
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings(request: Request):
    """Get current settings and provider status."""
    llm = request.app.state.llm_clients
    providers = llm.get_available_providers()

    return {
        "providers": providers,
        "groq_configured": "groq" in providers,
        "gemini_configured": "gemini" in providers,
        "nim_configured": "nim" in providers,
        "openrouter_configured": "openrouter" in providers,
        "glm_configured": "glm" in providers,
        "groq_model": llm.groq_model,
        "gemini_model": llm.gemini_model,
        "nim_model": llm.nim_model,
        "openrouter_model": llm.openrouter_model,
        "glm_model": llm.glm_model,
        "max_llm_concurrency": int(os.getenv("MAX_LLM_CONCURRENCY", "4")),
        "max_playwright_concurrency": int(os.getenv("MAX_PLAYWRIGHT_CONCURRENCY", "2")),
    }


class TestProviderRequest(BaseModel):
    provider: str


@router.post("/test-provider")
async def test_provider(req: TestProviderRequest, request: Request):
    """Test a specific LLM provider with a simple prompt."""
    llm = request.app.state.llm_clients
    try:
        result = await llm.generate(
            system_prompt="You are a helpful test.",
            user_prompt='Reply with just the word "OK" and nothing else.',
            temperature=0.5,
            max_tokens=10,
            provider=req.provider,
        )
        return {"status": "ok", "provider": req.provider, "response": result}
    except Exception as e:
        return {"status": "error", "provider": req.provider, "error": str(e)}
