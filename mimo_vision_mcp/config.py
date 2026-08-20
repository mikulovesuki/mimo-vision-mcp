"""Runtime configuration loaded from environment variables / .env file.

Priority: .env file > environment variable > default.

The .env file is re-read on every call so that changes made by the WebUI
(apply-to-mcp) are picked up live by the MCP server without a restart.
"""

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def _get(name: str, default: str) -> str:
    """Read a config value, preferring the .env file (re-read live) over
    environment variables, so WebUI edits to .env take effect immediately."""
    if ENV_FILE.exists():
        dot = dotenv_values(ENV_FILE)
        val = (dot.get(name) or "").strip()
        if val:
            return val
    val = (os.getenv(name) or "").strip()
    if val:
        return val
    return default


def get_api_key() -> str:
    """Return the API key (OpenCode Go / MiMo), falling back to OPENAI_API_KEY."""
    return _get("MIMO_API_KEY", "") or _get("OPENAI_API_KEY", "")


def get_provider() -> str:
    """Preferred provider id from the provider registry (see providers.py)."""
    return _get("MIMO_PROVIDER", "opencode-go")


def get_base_url() -> str:
    return _get("MIMO_BASE_URL", "https://opencode.ai/zen/go/v1")


def get_model() -> str:
    return _get("MIMO_MODEL", "mimo-v2.5")


def get_max_tokens() -> int:
    return int(_get("MIMO_MAX_TOKENS", "4096"))


def get_timeout() -> float:
    return float(_get("MIMO_TIMEOUT", "120"))


def get_webui_port() -> int:
    return int(_get("MIMO_WEBUI_PORT", "8000"))


def get_system_prompt() -> str:
    return _get(
        "MIMO_SYSTEM_PROMPT",
        "You are MiMo, an AI assistant developed by Xiaomi. "
        "Answer the user's question about the given image accurately and concisely.",
    )


def get_api_style() -> str:
    """API style for the configured model: 'responses' or 'chat'.

    OpenAI-style models (e.g. gpt-5.6-luna) served via the Responses API must
    use the /responses endpoint; OpenAI-compatible chat models (e.g. mimo-v2.5)
    use /chat/completions. Override with MIMO_API_STYLE=responses|chat.
    """
    style = _get("MIMO_API_STYLE", "").lower()
    if style in ("responses", "chat"):
        return style
    model = get_model().lower()
    return "responses" if model.startswith(("gpt", "grok")) else "chat"


def apply_active_config(
    provider: str,
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
    api_style: str | None = None,
) -> dict:
    """Write the selected provider/model into .env so the MCP server picks it up
    on its next tool call (config is re-read from .env every call, no restart).

    Empty/None values leave the existing .env entries untouched.
    Returns the resulting effective config.
    """
    if not ENV_FILE.exists():
        ENV_FILE.write_text("", encoding="utf-8")
    if provider:
        set_key(str(ENV_FILE), "MIMO_PROVIDER", provider, quote_mode="never")
    if model:
        set_key(str(ENV_FILE), "MIMO_MODEL", model, quote_mode="never")
    if base_url:
        set_key(str(ENV_FILE), "MIMO_BASE_URL", base_url, quote_mode="never")
    if api_style:
        set_key(str(ENV_FILE), "MIMO_API_STYLE", api_style, quote_mode="never")
    if api_key:
        set_key(str(ENV_FILE), "MIMO_API_KEY", api_key, quote_mode="never")
    return get_effective_config()


def get_effective_config() -> dict:
    """Return the currently effective configuration (what the MCP will use)."""
    return {
        "provider": get_provider(),
        "model": get_model(),
        "base_url": get_base_url(),
        "api_style": get_api_style(),
        "key_set": bool(get_api_key()),
        "key_source": "env/.env" if get_api_key() else "",
    }
