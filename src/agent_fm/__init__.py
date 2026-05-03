"""agent-fm: Give your AI agent a voice.

An MCP server that lets AI coding agents speak to you via text-to-speech.
The agent decides when and what to say — like a colleague tapping your shoulder.
"""

__version__ = "0.1.0"

CLAUDE_MD_SNIPPET = """\
## Voice (agent-fm)

You have a `speak` tool. Use it to talk aloud — the user may not be watching the screen.

**When to speak:**
- Finished a task: `speak("Done with the auth refactor. All tests pass.")`
- Need input: `speak("Quick question — should I use Redis or an in-memory cache here?")`
- Found a problem: `speak("Heads up, there's a circular import in the payments module.")`
- About to do something big: `speak("Starting the full test suite, this'll take a minute.")`
- Made a design choice: `speak("I went with a factory pattern for the parsers — let me know if you'd prefer something else.")`

**Don't speak** for trivial ops, every step, or to repeat what's already on screen.
1-2 sentences max. Talk like a colleague, not a robot.
"""


def main() -> None:
    """Entry point for the agent-fm CLI."""
    import os
    import sys

    args = sys.argv[1:]

    if "--version" in args or "-V" in args:
        print(f"agent-fm {__version__}")
        return

    if "--help" in args or "-h" in args:
        _print_help()
        return

    if "warmup" in args:
        ci_mode = "--ci" in args or os.environ.get("CI") == "true"
        _warmup(ci=ci_mode)
        return

    # Default: run MCP server
    from .server import mcp

    mcp.run(transport="stdio")


def _print_help() -> None:
    print(f"agent-fm v{__version__} - Give your AI agent a voice")
    print()
    print("Usage:")
    print("  agent-fm              Run MCP server (stdio transport)")
    print("  agent-fm warmup       Download models + test setup")
    print("  agent-fm warmup --ci  Same, but skip audio playback")
    print("  agent-fm --version    Show version")
    print("  agent-fm --help       Show this help")


def _warmup(ci: bool = False) -> None:
    """Pre-download TTS models and verify the setup."""
    import platform
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    ok_count = 0
    warn_count = 0
    fail_count = 0

    def ok(msg: str) -> None:
        nonlocal ok_count
        ok_count += 1
        print(f"  [ok] {msg}")

    def warn(msg: str) -> None:
        nonlocal warn_count
        warn_count += 1
        print(f"  [!!] {msg}")

    def fail(msg: str) -> None:
        nonlocal fail_count
        fail_count += 1
        print(f"  [FAIL] {msg}")

    print(f"agent-fm v{__version__} - warmup")
    print()

    # ── 1. System dependencies ──────────────────────────────────────────
    print("1. System dependencies")
    system = platform.system()
    if system == "Linux":
        import ctypes.util
        if ctypes.util.find_library("portaudio"):
            ok("PortAudio found")
        else:
            fail("PortAudio not found - audio will not work")
            print("       Fix: sudo apt install libportaudio2")
    elif system == "Darwin":
        ok("macOS - no system dependencies needed")
    elif system == "Windows":
        ok("Windows - no system dependencies needed")
    print()

    # ── 2. TTS models ──────────────────────────────────────────────────
    print("2. TTS models (~340MB, one-time download)")
    from .models import ensure_models
    try:
        model_path, voices_path = ensure_models()
        ok(f"Model: {model_path}")
        ok(f"Voices: {voices_path}")
    except Exception as e:
        fail(f"Model download failed: {e}")
        print()
        print(f"Result: {ok_count} ok, {warn_count} warnings, {fail_count} failures")
        sys.exit(1)
    print()

    # ── 3. TTS synthesis ───────────────────────────────────────────────
    print("3. TTS synthesis")
    try:
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(str(model_path), str(voices_path))
        audio, sr = kokoro.create(
            "Agent FM is ready.", voice="am_fenrir", speed=1.0, lang="en-us"
        )
        ok(f"Generated {len(audio) / sr:.1f}s of audio at {sr}Hz")
    except Exception as e:
        fail(f"Synthesis failed: {e}")
        print()
        print(f"Result: {ok_count} ok, {warn_count} warnings, {fail_count} failures")
        sys.exit(1)
    print()

    # ── 4. Audio playback ──────────────────────────────────────────────
    print("4. Audio playback")
    if ci:
        ok("Skipped (CI mode)")
    else:
        try:
            import sounddevice as sd
            sd.play(audio, sr)
            sd.wait()
            ok("Playback works - you should have heard 'Agent FM is ready.'")
        except Exception as e:
            warn(f"Playback failed: {e}")
            if system == "Linux":
                print("       Fix: sudo apt install libportaudio2")
            else:
                print("       Check that an audio output device is connected.")
    print()

    # ── 5. MCP registration ────────────────────────────────────────────
    print("5. MCP registration")
    claude_bin = shutil.which("claude")
    if claude_bin:
        # Check if already registered
        try:
            result = subprocess.run(
                ["claude", "mcp", "list"], capture_output=True, text=True, timeout=10
            )
            if "agent-fm" in result.stdout:
                ok("Already registered with Claude Code")
            else:
                warn("Not registered yet")
                print("       Run one of:")
                print("         claude mcp add -s user agent-fm -- uvx agent-fm    # all projects")
                print("         claude mcp add agent-fm -- uvx agent-fm            # this project only")
        except Exception:
            warn("Could not check MCP status")
            print("       To register: claude mcp add -s user agent-fm -- uvx agent-fm")
    else:
        ok("Claude Code not found (skip - not required)")
        print("       When you install Claude Code, run:")
        print("         claude mcp add -s user agent-fm -- uvx agent-fm")
    print()

    # ── 6. Voice instructions ──────────────────────────────────────────
    print("6. Voice instructions (CLAUDE.md)")
    claude_md_global = Path.home() / ".claude" / "CLAUDE.md"
    claude_md_local = Path.cwd() / "CLAUDE.md"

    has_global = claude_md_global.exists() and "agent-fm" in claude_md_global.read_text(errors="ignore")
    has_local = claude_md_local.exists() and "agent-fm" in claude_md_local.read_text(errors="ignore")

    if has_global:
        ok(f"Found in {claude_md_global}")
    elif has_local:
        ok(f"Found in {claude_md_local}")
    else:
        warn("Not configured - your agent won't know when to speak")
        print("       Add to ~/.claude/CLAUDE.md (global) or ./CLAUDE.md (project):")
        print()
        for line in CLAUDE_MD_SNIPPET.strip().split("\n")[:6]:
            print(f"         {line}")
        print("         ...")
        print()
        print("       Full snippet: https://github.com/ChanBong/agent-fm#teaching-your-agent-when-to-speak")
    print()

    # ── Summary ────────────────────────────────────────────────────────
    print("-" * 50)
    if fail_count > 0:
        print(f"Result: {ok_count} ok, {warn_count} warnings, {fail_count} failures")
        print("Fix the failures above and run 'agent-fm warmup' again.")
        sys.exit(1)
    elif warn_count > 0:
        print(f"Result: {ok_count} ok, {warn_count} pending")
        print("agent-fm works! Complete the pending steps above.")
    else:
        print(f"Result: {ok_count} ok - fully configured!")
    print()

    # ── Uninstall ──────────────────────────────────────────────────────
    if not ci:
        print("To uninstall:")
        print("  claude mcp remove agent-fm && uv tool uninstall agent-fm && rm -rf ~/.agent-fm/")
        print()
