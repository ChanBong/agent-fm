"""Tests for agent_fm.config — load, save, parse, ensure."""

import textwrap

import pytest

from agent_fm.config import (
    DEFAULT_CONFIG,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    _parse_toml_simple,
    ensure_config,
    load_config,
    save_config,
)


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR and CONFIG_PATH to a temp directory for every test."""
    config_dir = tmp_path / ".agent-fm"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr("agent_fm.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("agent_fm.config.CONFIG_PATH", config_path)


def _config_path(tmp_path):
    return tmp_path / ".agent-fm" / "config.toml"


# ── _parse_toml_simple ─────────────────────────────────────────────


class TestParseTomlSimple:
    def test_double_quoted_string(self):
        assert _parse_toml_simple('voice = "af_heart"') == {"voice": "af_heart"}

    def test_single_quoted_string(self):
        assert _parse_toml_simple("voice = 'af_heart'") == {"voice": "af_heart"}

    def test_float_value(self):
        assert _parse_toml_simple("speed = 1.3") == {"speed": 1.3}

    def test_integer_value(self):
        assert _parse_toml_simple("count = 5") == {"count": 5}

    def test_unquoted_string(self):
        result = _parse_toml_simple("engine = kokoro")
        assert result == {"engine": "kokoro"}

    def test_comments_ignored(self):
        text = '# this is a comment\nvoice = "af_heart"\n# another comment'
        assert _parse_toml_simple(text) == {"voice": "af_heart"}

    def test_blank_lines_ignored(self):
        text = '\n\nvoice = "af_heart"\n\n\nspeed = 1.0\n\n'
        assert _parse_toml_simple(text) == {"voice": "af_heart", "speed": 1.0}

    def test_empty_string(self):
        assert _parse_toml_simple("") == {}

    def test_comments_only(self):
        assert _parse_toml_simple("# just comments\n# nothing else") == {}

    def test_whitespace_around_equals(self):
        assert _parse_toml_simple('voice  =  "af_heart"') == {"voice": "af_heart"}

    def test_no_equals_line_skipped(self):
        text = 'voice = "af_heart"\ngarbage line\nspeed = 1.0'
        assert _parse_toml_simple(text) == {"voice": "af_heart", "speed": 1.0}

    def test_multiple_keys(self):
        text = 'voice = "bf_alice"\nspeed = 0.8'
        result = _parse_toml_simple(text)
        assert result == {"voice": "bf_alice", "speed": 0.8}

    def test_value_with_equals_in_it(self):
        text = 'url = "https://example.com?a=1"'
        assert _parse_toml_simple(text) == {"url": "https://example.com?a=1"}

    def test_invalid_float_becomes_string(self):
        result = _parse_toml_simple("speed = notanumber")
        assert result["speed"] == "notanumber"


# ── load_config ────────────────────────────────────────────────────


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path):
        config = load_config()
        assert config["voice"] == DEFAULT_VOICE
        assert config["speed"] == DEFAULT_SPEED

    def test_reads_voice_from_file(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text('voice = "bf_alice"\nspeed = 1.0', encoding="utf-8")
        config = load_config()
        assert config["voice"] == "bf_alice"

    def test_reads_speed_from_file(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text('voice = "am_fenrir"\nspeed = 1.5', encoding="utf-8")
        config = load_config()
        assert config["speed"] == 1.5

    def test_partial_config_fills_defaults(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text('voice = "af_heart"', encoding="utf-8")
        config = load_config()
        assert config["voice"] == "af_heart"
        assert config["speed"] == DEFAULT_SPEED

    def test_speed_only_config(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text("speed = 0.7", encoding="utf-8")
        config = load_config()
        assert config["voice"] == DEFAULT_VOICE
        assert config["speed"] == 0.7

    def test_extra_keys_ignored(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text(
            'voice = "am_fenrir"\nspeed = 1.0\nengine = "chatterbox"\nfoo = "bar"',
            encoding="utf-8",
        )
        config = load_config()
        assert config["voice"] == "am_fenrir"
        assert config["speed"] == 1.0
        assert "engine" not in config
        assert "foo" not in config

    def test_empty_file_returns_defaults(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text("", encoding="utf-8")
        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_comments_only_file_returns_defaults(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text("# just a comment\n# another one", encoding="utf-8")
        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_corrupt_file_returns_defaults(self, tmp_path, capsys):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\x00\x01\x02\xff\xfe")
        config = load_config()
        assert config["voice"] == DEFAULT_VOICE
        assert config["speed"] == DEFAULT_SPEED

    def test_non_string_voice_ignored(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text("voice = 123\nspeed = 1.0", encoding="utf-8")
        config = load_config()
        assert config["voice"] == DEFAULT_VOICE

    def test_integer_speed_converted_to_float(self, tmp_path):
        path = _config_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text('voice = "am_fenrir"\nspeed = 2', encoding="utf-8")
        config = load_config()
        assert config["speed"] == 2.0
        assert isinstance(config["speed"], float)

    def test_full_template_file(self, tmp_path):
        """The file produced by save_config should be parseable by load_config."""
        save_config({"voice": "jf_alpha", "speed": 0.8})
        config = load_config()
        assert config["voice"] == "jf_alpha"
        assert config["speed"] == 0.8


# ── save_config ────────────────────────────────────────────────────


class TestSaveConfig:
    def test_creates_directory_and_file(self, tmp_path):
        path = save_config({"voice": "af_heart", "speed": 1.2})
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert 'voice = "af_heart"' in content
        assert "speed = 1.2" in content

    def test_creates_parent_directories(self, tmp_path):
        path = _config_path(tmp_path)
        assert not path.parent.exists()
        save_config(DEFAULT_CONFIG)
        assert path.exists()

    def test_overwrites_existing(self, tmp_path):
        save_config({"voice": "am_fenrir", "speed": 1.0})
        save_config({"voice": "bf_alice", "speed": 0.5})
        config = load_config()
        assert config["voice"] == "bf_alice"
        assert config["speed"] == 0.5

    def test_merges_with_defaults(self, tmp_path):
        path = save_config({"voice": "af_heart"})
        content = path.read_text(encoding="utf-8")
        assert 'voice = "af_heart"' in content
        assert f"speed = {DEFAULT_SPEED}" in content

    def test_file_contains_comments(self, tmp_path):
        path = save_config(DEFAULT_CONFIG)
        content = path.read_text(encoding="utf-8")
        assert "# agent-fm configuration" in content
        assert "# Voice ID" in content
        assert "# Speech speed" in content

    def test_returns_path(self, tmp_path):
        path = save_config(DEFAULT_CONFIG)
        assert path == _config_path(tmp_path)


# ── ensure_config ──────────────────────────────────────────────────


class TestEnsureConfig:
    def test_creates_when_missing(self, tmp_path):
        path = ensure_config()
        assert path.exists()
        config = load_config()
        assert config == DEFAULT_CONFIG

    def test_does_not_overwrite_existing(self, tmp_path):
        save_config({"voice": "bf_alice", "speed": 0.6})
        ensure_config()
        config = load_config()
        assert config["voice"] == "bf_alice"
        assert config["speed"] == 0.6

    def test_returns_path(self, tmp_path):
        path = ensure_config()
        assert path == _config_path(tmp_path)

    def test_idempotent(self, tmp_path):
        path1 = ensure_config()
        path2 = ensure_config()
        assert path1 == path2
        config = load_config()
        assert config == DEFAULT_CONFIG


# ── Round-trip ─────────────────────────────────────────────────────


class TestRoundTrip:
    @pytest.mark.parametrize(
        "voice,speed",
        [
            ("am_fenrir", 1.0),
            ("af_heart", 0.5),
            ("jf_alpha", 2.0),
            ("bf_alice", 1.3),
        ],
    )
    def test_save_then_load(self, tmp_path, voice, speed):
        save_config({"voice": voice, "speed": speed})
        config = load_config()
        assert config["voice"] == voice
        assert config["speed"] == speed

    def test_multiple_save_load_cycles(self, tmp_path):
        for voice, speed in [("af_heart", 0.8), ("am_echo", 1.5), ("bf_lily", 1.0)]:
            save_config({"voice": voice, "speed": speed})
            config = load_config()
            assert config["voice"] == voice
            assert config["speed"] == speed
