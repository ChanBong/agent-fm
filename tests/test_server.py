"""Tests for MCP server set_voice persist behavior.

Uses a mock TTSEngine to avoid downloading models.
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent_fm.config import load_config, save_config
from agent_fm.tts import VOICES


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Redirect config to temp directory."""
    config_dir = tmp_path / ".agent-fm"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr("agent_fm.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("agent_fm.config.CONFIG_PATH", config_path)


@pytest.fixture(autouse=True)
def _reset_server_state():
    """Reset the lazy-initialized server globals between tests."""
    import agent_fm.server as srv

    old_engine, old_audio = srv._engine, srv._audio
    srv._engine = None
    srv._audio = None
    yield
    srv._engine = old_engine
    srv._audio = old_audio


class FakeEngine:
    """Minimal TTSEngine stand-in that doesn't need models."""

    def __init__(self):
        self.default_voice = "am_fenrir"
        self.default_speed = 1.0

    async def initialize(self):
        pass

    def get_voices(self, language=""):
        if not language:
            return VOICES
        return {k: v for k, v in VOICES.items() if v["language"] == language}

    def get_languages(self):
        return sorted({v["language"] for v in VOICES.values()})


class FakeAudio:
    """Minimal AudioQueue stand-in."""

    pending = 0

    def start(self):
        pass

    def enqueue(self, data, sr):
        self.pending += 1


async def _fake_ensure():
    import agent_fm.server as srv

    if srv._engine is None:
        srv._engine = FakeEngine()
        srv._audio = FakeAudio()
    return srv._engine, srv._audio


@pytest.fixture(autouse=True)
def _mock_ensure(monkeypatch):
    """Replace _ensure_initialized with our fake."""
    monkeypatch.setattr("agent_fm.server._ensure_initialized", _fake_ensure)


# ── set_voice without persist ──────────────────────────────────────


class TestSetVoiceSession:
    @pytest.mark.asyncio
    async def test_change_voice_session_only(self):
        from agent_fm.server import set_voice

        result = await set_voice(voice="af_heart")
        assert result["status"] == "ok"
        assert result["default_voice"] == "af_heart"
        assert result["persisted"] is False
        assert "hint" in result

    @pytest.mark.asyncio
    async def test_change_speed_session_only(self):
        from agent_fm.server import set_voice

        result = await set_voice(speed=1.5)
        assert result["status"] == "ok"
        assert result["default_speed"] == 1.5
        assert result["persisted"] is False

    @pytest.mark.asyncio
    async def test_hint_mentions_persist(self):
        from agent_fm.server import set_voice

        result = await set_voice(voice="af_heart")
        assert "persist" in result["hint"].lower()

    @pytest.mark.asyncio
    async def test_no_change_returns_current(self):
        from agent_fm.server import set_voice

        result = await set_voice()
        assert result["status"] == "ok"
        assert result["default_voice"] == "am_fenrir"
        assert result["default_speed"] == 1.0


# ── set_voice with persist ─────────────────────────────────────────


class TestSetVoicePersist:
    @pytest.mark.asyncio
    async def test_persist_writes_config(self, tmp_path):
        from agent_fm.server import set_voice

        result = await set_voice(voice="bf_alice", speed=0.8, persist=True)
        assert result["status"] == "ok"
        assert result["persisted"] is True
        assert "hint" not in result

        config = load_config()
        assert config["voice"] == "bf_alice"
        assert config["speed"] == 0.8

    @pytest.mark.asyncio
    async def test_persist_voice_only(self, tmp_path):
        from agent_fm.server import set_voice

        result = await set_voice(voice="af_heart", persist=True)
        assert result["persisted"] is True

        config = load_config()
        assert config["voice"] == "af_heart"
        assert config["speed"] == 1.0  # default preserved

    @pytest.mark.asyncio
    async def test_persist_speed_only(self, tmp_path):
        from agent_fm.server import set_voice

        result = await set_voice(speed=1.8, persist=True)
        assert result["persisted"] is True

        config = load_config()
        assert config["voice"] == "am_fenrir"  # default preserved
        assert config["speed"] == 1.8

    @pytest.mark.asyncio
    async def test_persist_no_change(self, tmp_path):
        from agent_fm.server import set_voice

        result = await set_voice(persist=True)
        assert result["persisted"] is True

        config = load_config()
        assert config["voice"] == "am_fenrir"
        assert config["speed"] == 1.0

    @pytest.mark.asyncio
    async def test_persist_overwrites_previous(self, tmp_path):
        from agent_fm.server import set_voice

        save_config({"voice": "jf_alpha", "speed": 0.5})
        await set_voice(voice="af_heart", speed=1.3, persist=True)

        config = load_config()
        assert config["voice"] == "af_heart"
        assert config["speed"] == 1.3


# ── set_voice validation ──────────────────────────────────────────


class TestSetVoiceValidation:
    @pytest.mark.asyncio
    async def test_invalid_voice_returns_error(self):
        from agent_fm.server import set_voice

        result = await set_voice(voice="nonexistent_voice")
        assert result["status"] == "error"
        assert "Unknown voice" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_voice_does_not_persist(self, tmp_path):
        from agent_fm.server import set_voice

        save_config({"voice": "am_fenrir", "speed": 1.0})
        result = await set_voice(voice="nonexistent", persist=True)
        assert result["status"] == "error"

        config = load_config()
        assert config["voice"] == "am_fenrir"

    @pytest.mark.asyncio
    async def test_speed_too_high(self):
        from agent_fm.server import set_voice

        result = await set_voice(speed=3.0)
        assert result["status"] == "error"
        assert "0.5 and 2.0" in result["error"]

    @pytest.mark.asyncio
    async def test_speed_too_low(self):
        from agent_fm.server import set_voice

        result = await set_voice(speed=0.1)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_speed_at_boundaries(self):
        from agent_fm.server import set_voice

        result_low = await set_voice(speed=0.5)
        assert result_low["status"] == "ok"
        assert result_low["default_speed"] == 0.5

        result_high = await set_voice(speed=2.0)
        assert result_high["status"] == "ok"
        assert result_high["default_speed"] == 2.0


# ── TTSEngine config integration ──────────────────────────────────


class TestTTSEngineConfig:
    def test_engine_reads_config_defaults(self, tmp_path):
        save_config({"voice": "bf_alice", "speed": 0.7})
        from agent_fm.tts import TTSEngine

        engine = TTSEngine()
        assert engine.default_voice == "bf_alice"
        assert engine.default_speed == 0.7

    def test_engine_falls_back_on_invalid_voice(self, tmp_path):
        save_config({"voice": "nonexistent", "speed": 1.0})
        from agent_fm.tts import TTSEngine

        engine = TTSEngine()
        assert engine.default_voice == "am_fenrir"

    def test_engine_uses_defaults_no_config(self, tmp_path):
        from agent_fm.tts import TTSEngine

        engine = TTSEngine()
        assert engine.default_voice == "am_fenrir"
        assert engine.default_speed == 1.0

    def test_engine_reads_custom_speed(self, tmp_path):
        save_config({"voice": "am_fenrir", "speed": 1.8})
        from agent_fm.tts import TTSEngine

        engine = TTSEngine()
        assert engine.default_speed == 1.8
