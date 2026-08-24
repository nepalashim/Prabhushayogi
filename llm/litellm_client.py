"""LiteLLM routing: every LLM call in the app (generator, rewriter, judge)
goes through acompletion_with_fallback() so the "no API key configured"
check and the Groq dev/testing fallback are both handled in one place,
regardless of which provider (Gemini or Anthropic) is currently active in
config/settings.py's GENERATOR_MODEL/JUDGE_MODEL/REWRITE_MODEL slots.
"""

from __future__ import annotations

from typing import Any

import litellm

from config.settings import settings

# Maps a model string's LiteLLM provider prefix to (the env var it needs, a
# human-readable name, the URL to get a key). Add a row here if another
# provider slot is ever introduced - everything else in this file is generic.
_PROVIDER_KEY_INFO: dict[str, tuple[str, str, str]] = {
    "gemini/": ("GEMINI_API_KEY", "Google AI Studio", "https://aistudio.google.com/apikey"),
    "anthropic/": ("ANTHROPIC_API_KEY", "Anthropic Console", "https://console.anthropic.com/"),
    "groq/": ("GROQ_API_KEY", "Groq Console", "https://console.groq.com/"),
}


class MissingApiKeyError(RuntimeError):
    """Raised when `model` needs a provider API key that isn't set in .env.

    Deliberately NOT a pydantic validation error at Settings-load time (see
    config/settings.py's docstring) - this way indexing/retrieval/config work
    (Stages 1-3) never requires a key, and only an actual generation/judge/
    rewrite call fails, with a clear, actionable message.
    """


def _require_key_for(model: str) -> None:
    for prefix, (env_var, provider_name, url) in _PROVIDER_KEY_INFO.items():
        if model.startswith(prefix):
            if not getattr(settings, env_var):
                raise MissingApiKeyError(
                    f"{env_var} is not set in .env, but {model!r} needs it. "
                    f"Get a key from {provider_name} at {url} and add it as {env_var}=... in .env."
                )
            return
    # Unknown prefix: let LiteLLM itself raise its own authentication error
    # rather than guessing which env var an unrecognized provider needs.


async def acompletion_with_fallback(
    messages: list[dict[str, str]],
    model: str,
    **kwargs: Any,
) -> Any:
    """Call `model` via LiteLLM; if it errors and GROQ_API_KEY is set, retry
    once against settings.GROQ_FALLBACK_MODEL (dev/testing resilience if the
    primary provider has an outage or its free-tier quota is exhausted).

    Provider API keys are resolved by LiteLLM from the process environment -
    config/settings.py mirrors the .env values into os.environ once at import
    time so this works uniformly for both the primary call and LiteLLM's own
    internal fallback call.
    """
    _require_key_for(model)

    fallbacks = [settings.GROQ_FALLBACK_MODEL] if settings.GROQ_API_KEY else None

    return await litellm.acompletion(model=model, messages=messages, fallbacks=fallbacks, **kwargs)
