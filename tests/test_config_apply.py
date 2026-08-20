import pytest

from mimo_vision_mcp import config

_MIMO_ENV_KEYS = (
    "MIMO_PROVIDER",
    "MIMO_MODEL",
    "MIMO_BASE_URL",
    "MIMO_API_STYLE",
    "MIMO_API_KEY",
    "MIMO_MAX_TOKENS",
    "MIMO_TIMEOUT",
    "MIMO_SYSTEM_PROMPT",
    "OPENAI_API_KEY",
)


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    # isolate from any env vars that load_dotenv may have injected at import
    for k in _MIMO_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    f = tmp_path / ".env"
    f.write_text(
        "MIMO_PROVIDER=opencode-go\nMIMO_MODEL=mimo-v2.5\nMIMO_BASE_URL=https://opencode.ai/zen/go/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "ENV_FILE", f)
    return f


def test_apply_writes_and_live_reads(env_file):
    config.apply_active_config("opencode-go", "gpt-5.6-luna")
    assert config.get_model() == "gpt-5.6-luna"
    eff = config.get_effective_config()
    assert eff["provider"] == "opencode-go"
    assert eff["model"] == "gpt-5.6-luna"


def test_apply_base_url_and_style(env_file):
    config.apply_active_config("custom", "my-model", base_url="https://x.com/v1", api_style="responses")
    assert config.get_base_url() == "https://x.com/v1"
    assert config.get_api_style() == "responses"


def test_apply_empty_does_not_overwrite(env_file):
    config.apply_active_config("opencode-go", "qwen3.7-max")
    config.apply_active_config("", "", base_url=None, api_key="", api_style=None)
    assert config.get_model() == "qwen3.7-max"
    assert config.get_base_url() == "https://opencode.ai/zen/go/v1"


def test_apply_writes_key_to_file(env_file):
    config.apply_active_config("opencode-go", "mimo-v2.5", api_key="sk-test")
    content = env_file.read_text(encoding="utf-8")
    assert "MIMO_API_KEY=sk-test" in content


def test_effective_config_shape(env_file):
    eff = config.get_effective_config()
    assert set(eff) >= {"provider", "model", "base_url", "api_style", "key_set"}
