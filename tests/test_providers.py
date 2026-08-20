import pytest

from mimo_vision_mcp.providers import (
    PROVIDER_REGISTRY,
    resolve_style,
)


def test_registry_has_opencode_go():
    assert "opencode-go" in PROVIDER_REGISTRY
    entry = PROVIDER_REGISTRY["opencode-go"]
    assert entry["base_url"] == "https://opencode.ai/zen/go/v1"
    assert entry["default_model"] == "mimo-v2.5"
    ids = [m["id"] for m in entry["models"]]
    assert "mimo-v2.5" in ids


def test_registry_models_have_style():
    for pid, entry in PROVIDER_REGISTRY.items():
        for m in entry["models"]:
            assert m["id"]
            assert m["style"] in ("chat", "responses")


@pytest.mark.parametrize(
    "model, override, expected",
    [
        ("mimo-v2.5", None, "chat"),
        ("mimo-v2.5-pro", None, "chat"),
        ("qwen3.7-max", None, "chat"),
        ("gpt-5.6-luna", None, "responses"),
        ("gpt-4o", None, "responses"),
        ("grok-4.5", None, "responses"),
        ("o3", None, "responses"),
        ("mimo-v2.5", "responses", "responses"),
        ("gpt-4o", "chat", "chat"),
        ("anything", "bogus", "chat"),
    ],
)
def test_resolve_style(model, override, expected):
    assert resolve_style(model, override) == expected


def test_call_vision_returns_missing_key_error():
    from mimo_vision_mcp import config

    # force no key for this call only
    original = config.get_api_key
    config.get_api_key = lambda: ""
    try:
        result = __import__("mimo_vision_mcp.providers", fromlist=["call_vision"]).call_vision(
            ["https://example.com/a.png"], "hi", provider="opencode-go"
        )
    finally:
        config.get_api_key = original
    assert result["error"]
    assert result["result"] == ""
