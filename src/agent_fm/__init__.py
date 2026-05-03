"""agent-fm: Give your AI agent a voice.

An MCP server that lets AI coding agents speak to you via text-to-speech.
The agent decides when and what to say — like a colleague tapping your shoulder.
"""

__version__ = "0.1.0"


def main() -> None:
    """Entry point for the agent-fm CLI."""
    import os
    import sys

    args = sys.argv[1:]

    if "--version" in args or "-V" in args:
        print(f"agent-fm {__version__}")
        return

    if "warmup" in args:
        ci_mode = "--ci" in args or os.environ.get("CI") == "true"
        _warmup(ci=ci_mode)
        return

    # Default: run MCP server
    from .server import mcp

    mcp.run(transport="stdio")


def _warmup(ci: bool = False) -> None:
    """Pre-download TTS models and verify the setup."""
    import platform
    import sys

    print(f"agent-fm v{__version__} — warmup")
    print()

    # 1. Check platform-specific deps
    system = platform.system()
    if system == "Linux":
        # Check for PortAudio (required by sounddevice on Linux)
        import ctypes.util

        if ctypes.util.find_library("portaudio"):
            print("[ok] PortAudio found")
        else:
            print("[!!] PortAudio not found — audio playback will fail")
            print("     Install it: sudo apt install libportaudio2")
            print()
    elif system == "Darwin":
        print("[ok] macOS — no system dependencies needed")
    elif system == "Windows":
        print("[ok] Windows — no system dependencies needed")

    # 2. Download models
    print()
    print("Downloading Kokoro TTS models (~340MB, one-time)...")
    from .models import ensure_models

    model_path, voices_path = ensure_models()
    print(f"[ok] Model: {model_path}")
    print(f"[ok] Voices: {voices_path}")

    # 3. Test synthesis
    print()
    print("Testing TTS synthesis...")
    try:
        from kokoro_onnx import Kokoro

        kokoro = Kokoro(str(model_path), str(voices_path))
        audio, sr = kokoro.create(
            "Agent FM is ready.", voice="am_fenrir", speed=1.0, lang="en-us"
        )
        print(f"[ok] Generated {len(audio) / sr:.1f}s of audio at {sr}Hz")
    except Exception as e:
        print(f"[!!] TTS test failed: {e}")
        sys.exit(1)

    # 4. Test audio playback
    if ci:
        print()
        print("[skip] Audio playback skipped (CI mode)")
    else:
        print()
        print("Testing audio playback...")
        try:
            import sounddevice as sd

            sd.play(audio, sr)
            sd.wait()
            print("[ok] Audio playback works — you should have heard 'Agent FM is ready.'")
        except Exception as e:
            print(f"[!!] Audio playback failed: {e}")
            if system == "Linux":
                print("     Try: sudo apt install libportaudio2")
            else:
                print("     Make sure you have an audio output device connected.")

    print()
    print("Warmup complete! Add to Claude Code:")
    print()
    print("  claude mcp add agent-fm -- uvx agent-fm")
    print()
    print("To uninstall later:")
    print("  claude mcp remove agent-fm")
    print("  uv tool uninstall agent-fm")
    print("  rm -rf ~/.agent-fm/")
    print()
