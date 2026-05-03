"""Tests for CLI commands: agent-fm config, agent-fm voices."""

import subprocess
import sys

import pytest

from agent_fm.config import DEFAULT_CONFIG, load_config, save_config


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Redirect config to temp directory."""
    config_dir = tmp_path / ".agent-fm"
    config_path = config_dir / "config.toml"
    monkeypatch.setattr("agent_fm.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("agent_fm.config.CONFIG_PATH", config_path)


def _config_path(tmp_path):
    return tmp_path / ".agent-fm" / "config.toml"


# ── Helper: run CLI via subprocess ─────────────────────────────────


def _run(*args, env_patch=None):
    """Run agent-fm CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "agent_fm", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


# ── _config_cmd (unit tests via direct function calls) ─────────────


class TestConfigCmdShow:
    def test_show_defaults_no_file(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd([])
        out = capsys.readouterr().out
        assert "am_fenrir" in out
        assert "1.0" in out
        assert "using defaults" in out

    def test_show_with_existing_config(self, tmp_path, capsys):
        save_config({"voice": "af_heart", "speed": 1.2})
        from agent_fm import _config_cmd

        _config_cmd([])
        out = capsys.readouterr().out
        assert "af_heart" in out
        assert "1.2" in out
        assert "using defaults" not in out


class TestConfigCmdSetVoice:
    def test_set_valid_voice(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd(["voice", "af_heart"])
        out = capsys.readouterr().out
        assert "af_heart" in out
        assert "am_fenrir" in out  # shows old value
        config = load_config()
        assert config["voice"] == "af_heart"

    def test_set_invalid_voice_exits(self, tmp_path):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit) as exc_info:
            _config_cmd(["voice", "nonexistent_voice"])
        assert exc_info.value.code == 1

    def test_show_voice_no_value(self, tmp_path, capsys):
        save_config({"voice": "bf_alice", "speed": 1.0})
        from agent_fm import _config_cmd

        _config_cmd(["voice"])
        out = capsys.readouterr().out
        assert "bf_alice" in out


class TestConfigCmdSetSpeed:
    def test_set_valid_speed(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd(["speed", "1.5"])
        out = capsys.readouterr().out
        assert "1.5" in out
        config = load_config()
        assert config["speed"] == 1.5

    def test_set_speed_lower_bound(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd(["speed", "0.5"])
        config = load_config()
        assert config["speed"] == 0.5

    def test_set_speed_upper_bound(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd(["speed", "2.0"])
        config = load_config()
        assert config["speed"] == 2.0

    def test_speed_too_high_exits(self, tmp_path):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit) as exc_info:
            _config_cmd(["speed", "3.0"])
        assert exc_info.value.code == 1

    def test_speed_too_low_exits(self, tmp_path):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit) as exc_info:
            _config_cmd(["speed", "0.1"])
        assert exc_info.value.code == 1

    def test_speed_not_a_number_exits(self, tmp_path):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit) as exc_info:
            _config_cmd(["speed", "fast"])
        assert exc_info.value.code == 1

    def test_show_speed_no_value(self, tmp_path, capsys):
        save_config({"voice": "am_fenrir", "speed": 1.8})
        from agent_fm import _config_cmd

        _config_cmd(["speed"])
        out = capsys.readouterr().out
        assert "1.8" in out


class TestConfigCmdReset:
    def test_reset_restores_defaults(self, tmp_path, capsys):
        save_config({"voice": "bf_alice", "speed": 0.6})
        from agent_fm import _config_cmd

        _config_cmd(["reset"])
        config = load_config()
        assert config["voice"] == DEFAULT_CONFIG["voice"]
        assert config["speed"] == DEFAULT_CONFIG["speed"]

    def test_reset_output(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        _config_cmd(["reset"])
        out = capsys.readouterr().out
        assert "reset to defaults" in out.lower()
        assert DEFAULT_CONFIG["voice"] in out


class TestConfigCmdUnknownKey:
    def test_unknown_key_exits(self, tmp_path):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit) as exc_info:
            _config_cmd(["engine", "chatterbox"])
        assert exc_info.value.code == 1

    def test_unknown_key_message(self, tmp_path, capsys):
        from agent_fm import _config_cmd

        with pytest.raises(SystemExit):
            _config_cmd(["badkey"])
        out = capsys.readouterr().out
        assert "Unknown config key" in out


# ── _voices_cmd ────────────────────────────────────────────────────


class TestVoicesCmd:
    def test_list_all_voices(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd([])
        out = capsys.readouterr().out
        assert "am_fenrir" in out
        assert "af_heart" in out
        assert "en-us" in out

    def test_filter_by_language(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd(["ja"])
        out = capsys.readouterr().out
        assert "jf_alpha" in out
        assert "jm_kumo" in out
        # Should not contain voices from other languages
        assert "am_fenrir" not in out

    def test_filter_by_nonexistent_language(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd(["klingon"])
        out = capsys.readouterr().out
        assert "No voices found" in out
        assert "Available languages" in out

    def test_voices_show_gender(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd(["en-gb"])
        out = capsys.readouterr().out
        assert "F" in out  # female voices
        assert "M" in out  # male voices

    def test_voices_show_count(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd(["ja"])
        out = capsys.readouterr().out
        assert "5 voices total" in out

    def test_all_voices_count(self, capsys):
        from agent_fm import _voices_cmd

        _voices_cmd([])
        out = capsys.readouterr().out
        assert "54 voices total" in out


# ── CLI integration (subprocess) ───────────────────────────────────


class TestCLIIntegration:
    def test_help_shows_config(self):
        rc, out, _ = _run("--help")
        assert rc == 0
        assert "config" in out
        assert "voices" in out

    def test_version(self):
        rc, out, _ = _run("--version")
        assert rc == 0
        assert "agent-fm" in out

    def test_voices_runs(self):
        rc, out, _ = _run("voices")
        assert rc == 0
        assert "am_fenrir" in out

    def test_voices_filter_runs(self):
        rc, out, _ = _run("voices", "hi")
        assert rc == 0
        assert "hf_alpha" in out

    def test_config_show_runs(self):
        rc, out, _ = _run("config")
        assert rc == 0
        assert "voice" in out
        assert "speed" in out

    def test_config_invalid_voice_fails(self):
        rc, out, _ = _run("config", "voice", "nope")
        assert rc == 1

    def test_config_invalid_speed_fails(self):
        rc, out, _ = _run("config", "speed", "999")
        assert rc == 1
