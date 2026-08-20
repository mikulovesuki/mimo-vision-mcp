"""Provider registry + OpenAI-compatible vision API call logic.

Shared by the MCP server (tools exposed to LLMs) and the WebUI (interactive
frontend). Both call `call_vision`, which transparently supports both the
Chat Completions API (chat) and the Responses API (responses).
"""

import time
from typing import Any

import httpx
from openai import OpenAI
from openai import APIConnectionError, APITimeoutError

from . import config
from .image_loader import build_image_part, build_responses_image_part, normalize_input

# Provider registry.
# Each entry:
#   name          - display name
#   base_url      - OpenAI-compatible base url
#   models_url    - optional endpoint that returns the full model list
#   default_model - default selection
#   models        - curated vision-capable models [{id, style}]
PROVIDER_REGISTRY: dict[str, dict[str, Any]] = {
    "opencode-go": {
        "name": "OpenCode Go",
        "base_url": "https://opencode.ai/zen/go/v1",
        "models_url": "https://opencode.ai/zen/go/v1/models",
        "default_model": "mimo-v2.5",
        "models": [
            {"id": "mimo-v2.5", "style": "chat"},
            {"id": "mimo-v2.5-pro", "style": "chat"},
            {"id": "qwen3.7-max", "style": "chat"},
            {"id": "qwen3.7-plus", "style": "chat"},
            {"id": "qwen3.6-plus", "style": "chat"},
            {"id": "gpt-5.6-luna", "style": "responses"},
            {"id": "grok-4.5", "style": "responses"},
        ],
    },
}


def resolve_style(model: str, override: str | None = None) -> str:
    """Determine API style ('chat' or 'responses') for a model id.

    OpenAI Responses-API models (gpt/grok/o-series) use /responses; everything
    else defaults to the OpenAI-compatible /chat/completions.
    """
    if override in ("chat", "responses"):
        return override
    m = model.lower()
    return "responses" if m.startswith(("gpt", "grok", "o1", "o3")) else "chat"


def _registry_base_url(provider: str | None) -> str:
    if provider:
        entry = PROVIDER_REGISTRY.get(provider)
        if entry and entry.get("base_url"):
            return entry["base_url"]
    return ""


def call_vision(
    images: list[str],
    prompt: str,
    detail: str | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_style: str | None = None,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Normalize images, call the vision model, and return a result dict.

    Returns: {"result", "error", "model", "usage"}.
    """
    model = model or config.get_model()
    base_url = base_url or config.get_base_url() or _registry_base_url(provider)
    api_key = api_key or config.get_api_key()
    style = resolve_style(model, api_style)
    max_tokens = max_tokens or config.get_max_tokens()
    timeout = timeout if timeout is not None else config.get_timeout()

    if not api_key:
        return {
            "error": "未配置 API Key。请设置环境变量 MIMO_API_KEY（或 OPENAI_API_KEY），或在本项目根目录创建 .env 文件（参考 .env.example）。",
            "result": "",
        }

    parts: list[dict[str, Any]] = []
    errors: list[str] = []
    for img in images:
        try:
            normalized = normalize_input(img)
            parts.append(
                build_responses_image_part(normalized, detail)
                if style == "responses"
                else build_image_part(normalized, detail)
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))
    if errors:
        return {"error": "; ".join(errors), "result": ""}
    if not parts:
        return {"error": "没有可用的图片输入", "result": ""}

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    system = config.get_system_prompt()

    # Transient network errors (connection drop / timeout) are retried a couple
    # of times, because upstreams like opencode.ai can be intermittently flaky.
    max_attempts = max(1, config.get_max_retries())
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            payload = _do_call(client, system, style, model, parts, prompt, max_tokens)
            return payload
        except (APIConnectionError, APITimeoutError, httpx.TransportError) as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                time.sleep(0.5 * (attempt + 1))
        except Exception as exc:  # noqa: BLE001 - non-transient error
            return {"error": f"调用视觉模型失败: {exc}", "result": ""}

    return {"error": f"调用视觉模型失败（网络重试 {max_attempts} 次仍失败）: {last_error}", "result": ""}


def _do_call(
    client: OpenAI,
    system: str,
    style: str,
    model: str,
    parts: list[dict[str, Any]],
    prompt: str,
    max_tokens: int,
) -> dict[str, Any]:
    if style == "responses":
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": parts + [{"type": "input_text", "text": prompt}]},
            ],
            max_output_tokens=max_tokens,
            stream=False,
        )
        result = getattr(response, "output_text", None) or ""
        usage = getattr(response, "usage", None)
        usage_map = {
            "prompt_tokens": getattr(usage, "input_tokens", None),
            "completion_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else None
    else:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": parts + [{"type": "text", "text": prompt}]},
            ],
            max_completion_tokens=max_tokens,
            temperature=0.3,
            stream=False,
        )
        result = completion.choices[0].message.content or ""
        usage = getattr(completion, "usage", None)
        usage_map = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else None

    return {"error": "", "result": result, "model": model, "usage": usage_map}


def fetch_models(base_url: str, api_key: str) -> list[str]:
    """Fetch the model list from an OpenAI-compatible /models endpoint."""
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
    data = client.models.list()
    return [m.id for m in data.data]
