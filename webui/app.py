"""mimo-vision WebUI: interactive frontend for testing vision models across providers."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mimo_vision_mcp import config
from mimo_vision_mcp.providers import PROVIDER_REGISTRY, call_vision, fetch_models

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="mimo-vision WebUI")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class AnalyzeRequest(BaseModel):
    provider: str = "opencode-go"
    model: str = "mimo-v2.5"
    base_url: str | None = None
    api_key: str = ""
    api_style: str | None = None
    images: list[str]
    prompt: str = ""
    detail: str | None = None
    max_tokens: int | None = None


class ApplyRequest(BaseModel):
    provider: str = "opencode-go"
    model: str = "mimo-v2.5"
    base_url: str | None = None
    api_key: str = ""
    api_style: str | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/providers")
def get_providers() -> dict:
    data = {}
    for pid, entry in PROVIDER_REGISTRY.items():
        data[pid] = {
            "name": entry["name"],
            "base_url": entry["base_url"],
            "models_url": entry.get("models_url"),
            "default_model": entry.get("default_model"),
            "models": entry["models"],
        }
    return {
        "providers": data,
        "default_provider": config.get_provider(),
        "default_model": config.get_model(),
        "default_key_set": bool(config.get_api_key()),
    }


@app.get("/api/models")
def models(provider: str = "opencode-go", api_key: str = "") -> dict:
    entry = PROVIDER_REGISTRY.get(provider)
    if not entry or not entry.get("models_url"):
        raise HTTPException(status_code=400, detail="该供应商不支持动态拉取模型列表")
    key = api_key or config.get_api_key()
    if not key:
        raise HTTPException(status_code=400, detail="请先填写该供应商的 API Key")
    try:
        ids = fetch_models(entry["models_url"], key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"拉取模型列表失败: {exc}")
    return {"models": ids}


@app.get("/api/active-config")
def active_config() -> dict:
    """Current configuration that the MCP (CLI) will actually use."""
    return config.get_effective_config()


@app.post("/api/apply-to-mcp")
def apply_to_mcp(req: ApplyRequest) -> dict:
    """Persist the selected provider/model into .env so the CLI's MCP uses it
    on its next tool call (no restart needed)."""
    cfg = config.apply_active_config(
        provider=req.provider,
        model=req.model,
        base_url=req.base_url or None,
        api_key=req.api_key or None,
        api_style=req.api_style or None,
    )
    return {"ok": True, "message": "已同步到 MCP（.env），CLI 无需重启，下次调用即生效", "config": cfg}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest) -> dict:
    import time  # noqa: PLC0415

    t0 = time.time()
    payload = call_vision(
        req.images,
        req.prompt,
        req.detail,
        provider=req.provider,
        model=req.model,
        base_url=req.base_url,
        api_key=req.api_key or None,
        api_style=req.api_style,
        max_tokens=req.max_tokens,
    )
    payload["elapsed_ms"] = int((time.time() - t0) * 1000)
    return payload


def main() -> None:
    import uvicorn  # noqa: PLC0415

    uvicorn.run(app, host="127.0.0.1", port=config.get_webui_port(), log_level="info")


if __name__ == "__main__":
    main()
