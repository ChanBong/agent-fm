"""User configuration for agent-fm.

Persistent config stored at ~/.agent-fm/config.toml.
Lets users set default voice, speed, and (future) engine preferences
that survive across sessions.
"""

import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".agent-fm"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_VOICE = "am_fenrir"
DEFAULT_SPEED = 1.0

DEFAULT_CONFIG = {
    "voice": DEFAULT_VOICE,
    "speed": DEFAULT_SPEED,
}

_CONFIG_TEMPLATE = """\
# agent-fm configuration
# Docs: https://github.com/ChanBong/agent-fm#configuration

# Voice ID (list all: agent-fm voices)
voice = "{voice}"

# Speech speed: 0.5 (slow) to 2.0 (fast)
speed = {speed}
"""


def _parse_toml_simple(text: str) -> dict:
    """Minimal TOML parser for flat key=value configs (Python 3.10 fallback)."""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            result[key] = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            result[key] = value[1:-1]
        else:
            try:
                result[key] = float(value) if "." in value else int(value)
            except ValueError:
                result[key] = value
    return result


def _read_toml(path: Path) -> dict:
    """Read a TOML file, using tomllib (3.11+) or fallback parser."""
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib

        return tomllib.loads(text)
    except ImportError:
        return _parse_toml_simple(text)


def load_config() -> dict:
    """Load config from ~/.agent-fm/config.toml, merged with defaults.

    Missing keys get default values. Missing file returns all defaults.
    """
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            user = _read_toml(CONFIG_PATH)
            if "voice" in user and isinstance(user["voice"], str):
                config["voice"] = user["voice"]
            if "speed" in user:
                config["speed"] = float(user["speed"])
        except Exception as e:
            print(f"[agent-fm] Warning: could not read config ({e})", file=sys.stderr)
    return config


def save_config(config: dict) -> Path:
    """Write config to ~/.agent-fm/config.toml. Returns the path."""
    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        _CONFIG_TEMPLATE.format(voice=merged["voice"], speed=merged["speed"]),
        encoding="utf-8",
    )
    return CONFIG_PATH


def ensure_config() -> Path:
    """Create default config if it doesn't exist. Returns the path."""
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
    return CONFIG_PATH
