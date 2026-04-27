"""LLM client with Groq (primary) → Gemini (fallback 1) → NIM (fallback 2) chain."""

import asyncio
import logging
import os
from typing import Optional

from groq import AsyncGroq
from openai import AsyncOpenAI
import google.genai as genai

log = logging.getLogger(__name__)


class LLMClients:
    """Manages connections to Groq, Gemini, NIM, OpenRouter, and GLM with automatic fallback."""

    def __init__(self):
        self.groq_client: Optional[AsyncGroq] = None
        self.gemini_client = None
        self.nim_client: Optional[AsyncOpenAI] = None
        self.openrouter_client: Optional[AsyncOpenAI] = None
        self.glm_client: Optional[AsyncOpenAI] = None

        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.nim_model = os.getenv("NIM_MODEL", "meta/llama-3.3-70b-instruct")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        self.glm_model = os.getenv("GLM_MODEL", "glm-4-flash")

        # Initialize clients based on available keys
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key and not groq_key.startswith("gsk_your"):
            self.groq_client = AsyncGroq(api_key=groq_key)
            log.info("Groq client initialized with model: %s", self.groq_model)

        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key and not gemini_key.startswith("your_"):
            self.gemini_client = genai.Client(api_key=gemini_key)
            log.info("Gemini client initialized with model: %s", self.gemini_model)

        nim_key = os.getenv("NIM_API_KEY", "")
        if nim_key and not nim_key.startswith("nvapi-your"):
            self.nim_client = AsyncOpenAI(
                api_key=nim_key,
                base_url="https://integrate.api.nvidia.com/v1",
            )
            log.info("NIM client initialized with model: %s", self.nim_model)

        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            self.openrouter_client = AsyncOpenAI(
                api_key=openrouter_key,
                base_url="https://openrouter.ai/api/v1",
            )
            log.info("OpenRouter client initialized with model: %s", self.openrouter_model)

        glm_key = os.getenv("GLM_API_KEY", "")
        if glm_key:
            self.glm_client = AsyncOpenAI(
                api_key=glm_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            )
            log.info("GLM client initialized with model: %s", self.glm_model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 1.0,
        max_tokens: int = 800,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        provider: str = "auto",
        timeout: float = 30.0,
    ) -> str:
        """Generate text with provider fallback chain. Each call has a hard timeout.

        Args:
            provider: "groq", "gemini", "nim", "openrouter", "glm", or "auto" (default fallback chain).
            timeout: Per-provider timeout in seconds.
        """
        attempts = []
        if provider == "auto":
            # Order: Gemini -> Groq -> OpenRouter -> NIM -> GLM
            if self.gemini_client:
                attempts.append(("gemini", self._gemini_generate, (system_prompt, user_prompt, temperature, max_tokens)))
            if self.groq_client:
                attempts.append(("groq", self._groq_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.openrouter_client:
                attempts.append(("openrouter", self._openrouter_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.nim_client:
                attempts.append(("nim", self._nim_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.glm_client:
                attempts.append(("glm", self._glm_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "gemini" and self.gemini_client:
            attempts.append(("gemini", self._gemini_generate, (system_prompt, user_prompt, temperature, max_tokens)))
        elif provider == "groq" and self.groq_client:
            attempts.append(("groq", self._groq_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "openrouter" and self.openrouter_client:
            attempts.append(("openrouter", self._openrouter_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "nim" and self.nim_client:
            attempts.append(("nim", self._nim_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "glm" and self.glm_client:
            attempts.append(("glm", self._glm_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))

        last_err = None
        for name, fn, args in attempts:
            try:
                return await asyncio.wait_for(fn(*args), timeout=timeout)
            except asyncio.TimeoutError as e:
                log.warning("%s timed out after %ds", name, timeout)
                last_err = e
            except Exception as e:
                log.warning("%s failed: %s", name, e)
                last_err = e

        raise RuntimeError(f"All LLM providers failed or none configured: {last_err}")

    async def _groq_generate(self, system: str, user: str, temp: float,
                              max_tokens: int, pp: float, fp: float) -> str:
        response = await self.groq_client.chat.completions.create(
            model=self.groq_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
            max_tokens=max_tokens,
            presence_penalty=pp,
            frequency_penalty=fp,
        )
        return response.choices[0].message.content.strip()

    async def _gemini_generate(self, system: str, user: str,
                                temp: float, max_tokens: int) -> str:
        combined_prompt = f"{system}\n\n---\n\n{user}"
        response = await asyncio.to_thread(
            self.gemini_client.models.generate_content,
            model=self.gemini_model,
            contents=combined_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text.strip()

    async def _nim_generate(self, system: str, user: str, temp: float,
                             max_tokens: int, pp: float, fp: float) -> str:
        response = await self.nim_client.chat.completions.create(
            model=self.nim_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
            max_tokens=max_tokens,
            presence_penalty=pp,
            frequency_penalty=fp,
        )
        return response.choices[0].message.content.strip()

    async def _openrouter_generate(self, system: str, user: str, temp: float,
                                    max_tokens: int, pp: float, fp: float) -> str:
        response = await self.openrouter_client.chat.completions.create(
            model=self.openrouter_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
            max_tokens=max_tokens,
            presence_penalty=pp,
            frequency_penalty=fp,
        )
        return response.choices[0].message.content.strip()

    async def _glm_generate(self, system: str, user: str, temp: float,
                             max_tokens: int, pp: float, fp: float) -> str:
        response = await self.glm_client.chat.completions.create(
            model=self.glm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
            max_tokens=max_tokens,
            presence_penalty=pp,
            frequency_penalty=fp,
        )
        return response.choices[0].message.content.strip()

    def get_available_providers(self) -> list[str]:
        providers = []
        if self.groq_client:
            providers.append("groq")
        if self.gemini_client:
            providers.append("gemini")
        if self.nim_client:
            providers.append("nim")
        if self.openrouter_client:
            providers.append("openrouter")
        if self.glm_client:
            providers.append("glm")
        return providers
