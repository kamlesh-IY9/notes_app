"""LLM client with Cerebras → Groq → Gemini → Together → OpenRouter → SambaNova → NIM → GLM → Ollama fallback chain."""

import asyncio
import logging
import os
from typing import Optional

from groq import AsyncGroq
from openai import AsyncOpenAI
import google.genai as genai

log = logging.getLogger(__name__)


class LLMClients:
    """Manages connections to all LLM providers with automatic fallback."""

    def __init__(self):
        self.groq_clients: list[AsyncGroq] = []
        self.groq_index = 0

        # Multiple clients for rotation
        self.gemini_clients: list = []
        self.gemini_index = 0
        self.nim_clients: list[AsyncOpenAI] = []
        self.nim_index = 0
        self.openrouter_clients: list[AsyncOpenAI] = []
        self.openrouter_index = 0
        self.together_clients: list[AsyncOpenAI] = []
        self.together_index = 0
        self.cerebras_clients: list[AsyncOpenAI] = []
        self.cerebras_index = 0
        self.sambanova_clients: list[AsyncOpenAI] = []
        self.sambanova_index = 0

        self.glm_client: Optional[AsyncOpenAI] = None
        self.ollama_client: Optional[AsyncOpenAI] = None

        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.nim_model = os.getenv("NIM_MODEL", "meta/llama-3.3-70b-instruct")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        self.glm_model = os.getenv("GLM_MODEL", "glm-4-flash")
        self.together_model = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")
        self.cerebras_model = os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
        self.sambanova_model = os.getenv("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

        # Initialize Groq (key rotation)
        groq_keys = [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")]
        for key in groq_keys:
            if key and not key.startswith("gsk_your"):
                self.groq_clients.append(AsyncGroq(api_key=key))
        if self.groq_clients:
            log.info("Groq initialized with %d keys", len(self.groq_clients))

        # Initialize Gemini (key rotation)
        gemini_keys = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
        for key in gemini_keys:
            if key:
                self.gemini_clients.append(genai.Client(api_key=key))
        if self.gemini_clients:
            log.info("Gemini initialized with %d keys", len(self.gemini_clients))

        # Cerebras Keys Rotation (fast free inference)
        cerebras_keys = [os.getenv("CEREBRAS_API_KEY"), os.getenv("CEREBRAS_API_KEY_2")]
        for key in cerebras_keys:
            if key:
                client = AsyncOpenAI(api_key=key, base_url="https://api.cerebras.ai/v1")
                self.cerebras_clients.append(client)
        if self.cerebras_clients:
            log.info("Cerebras initialized with %d keys", len(self.cerebras_clients))

        # Together.ai Keys Rotation (1M free tokens/month)
        together_keys = [os.getenv("TOGETHER_API_KEY"), os.getenv("TOGETHER_API_KEY_2")]
        for key in together_keys:
            if key:
                client = AsyncOpenAI(api_key=key, base_url="https://api.together.xyz/v1")
                self.together_clients.append(client)
        if self.together_clients:
            log.info("Together.ai initialized with %d keys", len(self.together_clients))

        # SambaNova Keys Rotation
        sambanova_keys = [os.getenv("SAMBANOVA_API_KEY"), os.getenv("SAMBANOVA_API_KEY_2")]
        for key in sambanova_keys:
            if key:
                client = AsyncOpenAI(api_key=key, base_url="https://api.sambanova.ai/v1")
                self.sambanova_clients.append(client)
        if self.sambanova_clients:
            log.info("SambaNova initialized with %d keys", len(self.sambanova_clients))

        # NIM Keys Rotation
        nim_keys = [os.getenv("NIM_API_KEY"), os.getenv("NIM_API_KEY_2")]
        for key in nim_keys:
            if key and not key.startswith("nvapi-your"):
                client = AsyncOpenAI(api_key=key, base_url="https://integrate.api.nvidia.com/v1")
                self.nim_clients.append(client)
        if self.nim_clients:
            log.info("NIM initialized with %d keys", len(self.nim_clients))

        # OpenRouter Keys Rotation
        or_keys = [os.getenv("OPENROUTER_API_KEY"), os.getenv("OPENROUTER_API_KEY_2"), os.getenv("OPENROUTER_API_KEY_3")]
        for key in or_keys:
            if key:
                client = AsyncOpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
                self.openrouter_clients.append(client)
        if self.openrouter_clients:
            log.info("OpenRouter initialized with %d keys", len(self.openrouter_clients))

        # GLM
        glm_key = os.getenv("GLM_API_KEY", "")
        if glm_key:
            self.glm_client = AsyncOpenAI(api_key=glm_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            log.info("GLM client initialized")

        # Ollama — local fallback, no key needed, just needs the daemon running
        ollama_enabled = os.getenv("OLLAMA_ENABLED", "true").lower() != "false"
        if ollama_enabled:
            self.ollama_client = AsyncOpenAI(api_key="ollama", base_url=self.ollama_base_url)
            log.info("Ollama client configured (model=%s, url=%s)", self.ollama_model, self.ollama_base_url)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 1.0,
        max_tokens: int = 800,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        provider: str = "auto",
        timeout: float = 150.0,
    ) -> str:
        """Generate text with provider fallback chain.

        Order (auto): Ollama → Cerebras → Groq → Gemini → Together → OpenRouter → SambaNova → NIM → GLM
        """
        attempts = []
        if provider == "auto":
            if self.ollama_client:
                attempts.append(("ollama", self._ollama_generate, (system_prompt, user_prompt, temperature, max_tokens)))
            if self.cerebras_clients:
                attempts.append(("cerebras", self._cerebras_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.groq_clients:
                attempts.append(("groq", self._groq_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.gemini_clients:
                attempts.append(("gemini", self._gemini_generate, (system_prompt, user_prompt, temperature, max_tokens)))
            if self.together_clients:
                attempts.append(("together", self._together_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.openrouter_clients:
                attempts.append(("openrouter", self._openrouter_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.sambanova_clients:
                attempts.append(("sambanova", self._sambanova_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.nim_clients:
                attempts.append(("nim", self._nim_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
            if self.glm_client:
                attempts.append(("glm", self._glm_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "gemini" and self.gemini_clients:
            attempts.append(("gemini", self._gemini_generate, (system_prompt, user_prompt, temperature, max_tokens)))
        elif provider == "groq" and self.groq_clients:
            attempts.append(("groq", self._groq_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "cerebras" and self.cerebras_clients:
            attempts.append(("cerebras", self._cerebras_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "together" and self.together_clients:
            attempts.append(("together", self._together_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "sambanova" and self.sambanova_clients:
            attempts.append(("sambanova", self._sambanova_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "openrouter" and self.openrouter_clients:
            attempts.append(("openrouter", self._openrouter_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "nim" and self.nim_clients:
            attempts.append(("nim", self._nim_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "glm" and self.glm_client:
            attempts.append(("glm", self._glm_generate, (system_prompt, user_prompt, temperature, max_tokens, presence_penalty, frequency_penalty)))
        elif provider == "ollama" and self.ollama_client:
            attempts.append(("ollama", self._ollama_generate, (system_prompt, user_prompt, temperature, max_tokens)))

        last_err = None
        for name, fn, args in attempts:
            # Ollama is CPU-only — give it much more time
            effective_timeout = 300.0 if name == "ollama" else timeout
            try:
                return await asyncio.wait_for(fn(*args), timeout=effective_timeout)
            except asyncio.TimeoutError as e:
                log.warning("%s timed out after %ds", name, effective_timeout)
                last_err = e
            except Exception as e:
                log.warning("%s failed: %s", name, e)
                last_err = e

        raise RuntimeError(f"All LLM providers failed or none configured: {last_err}")

    async def _groq_generate(self, system: str, user: str, temp: float,
                              max_tokens: int, pp: float, fp: float) -> str:
        client = self.groq_clients[self.groq_index]
        self.groq_index = (self.groq_index + 1) % len(self.groq_clients)
        response = await client.chat.completions.create(
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
        client = self.gemini_clients[self.gemini_index]
        self.gemini_index = (self.gemini_index + 1) % len(self.gemini_clients)
        combined_prompt = f"{system}\n\n---\n\n{user}"
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=self.gemini_model,
            contents=combined_prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temp,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text.strip()

    async def _cerebras_generate(self, system: str, user: str, temp: float,
                                  max_tokens: int, pp: float, fp: float) -> str:
        client = self.cerebras_clients[self.cerebras_index]
        self.cerebras_index = (self.cerebras_index + 1) % len(self.cerebras_clients)
        response = await client.chat.completions.create(
            model=self.cerebras_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=min(temp, 1.5),
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def _together_generate(self, system: str, user: str, temp: float,
                                  max_tokens: int, pp: float, fp: float) -> str:
        client = self.together_clients[self.together_index]
        self.together_index = (self.together_index + 1) % len(self.together_clients)
        response = await client.chat.completions.create(
            model=self.together_model,
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

    async def _sambanova_generate(self, system: str, user: str, temp: float,
                                   max_tokens: int, pp: float, fp: float) -> str:
        client = self.sambanova_clients[self.sambanova_index]
        self.sambanova_index = (self.sambanova_index + 1) % len(self.sambanova_clients)
        response = await client.chat.completions.create(
            model=self.sambanova_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def _nim_generate(self, system: str, user: str, temp: float,
                             max_tokens: int, pp: float, fp: float) -> str:
        client = self.nim_clients[self.nim_index]
        self.nim_index = (self.nim_index + 1) % len(self.nim_clients)
        response = await client.chat.completions.create(
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
        client = self.openrouter_clients[self.openrouter_index]
        self.openrouter_index = (self.openrouter_index + 1) % len(self.openrouter_clients)
        response = await client.chat.completions.create(
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

    async def _ollama_generate(self, system: str, user: str,
                                temp: float, max_tokens: int) -> str:
        response = await self.ollama_client.chat.completions.create(
            model=self.ollama_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=min(temp, 1.0),
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def get_available_providers(self) -> list[str]:
        providers = []
        if self.cerebras_clients:
            providers.append("cerebras")
        if self.groq_clients:
            providers.append("groq")
        if self.gemini_clients:
            providers.append("gemini")
        if self.together_clients:
            providers.append("together")
        if self.openrouter_clients:
            providers.append("openrouter")
        if self.sambanova_clients:
            providers.append("sambanova")
        if self.nim_clients:
            providers.append("nim")
        if self.glm_client:
            providers.append("glm")
        if self.ollama_client:
            providers.append("ollama")
        return providers
