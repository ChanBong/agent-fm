"""MCP server for agent-fm.

Exposes tools that let AI agents speak to the developer via text-to-speech.
The agent decides when and what to say — like a colleague tapping your shoulder.
"""

from mcp.server.fastmcp import FastMCP

from .audio import AudioQueue
from .tts import TTSEngine

mcp = FastMCP(
    name="agent-fm",
    instructions=(
        "You have a speak tool that lets you talk to the developer out loud. "
        "The developer may not be looking at the screen — they could be in another "
        "window, wearing headphones, or away from their desk. Use speak() like a "
        "colleague tapping their shoulder: after completing significant work, when "
        "you need a decision, when you hit a blocking error, or when you find "
        "something surprising. Keep messages to 1-2 sentences. Be conversational, "
        "not robotic. Do NOT speak for trivial operations or narrate every step."
    ),
)

# Lazy-initialized global state
_engine: TTSEngine | None = None
_audio: AudioQueue | None = None


async def _ensure_initialized() -> tuple[TTSEngine, AudioQueue]:
    """Lazy initialization of TTS engine and audio queue."""
    global _engine, _audio
    if _engine is None:
        _engine = TTSEngine()
        await _engine.initialize()
        _audio = AudioQueue()
        _audio.start()
    return _engine, _audio


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "openWorldHint": True,
    }
)
async def speak(
    message: str,
    urgency: str = "info",
    voice: str = "",
    speed: float = 0.0,
) -> dict:
    """Speak a message aloud to the developer via text-to-speech.

    Call this when you complete a significant task, need a design decision,
    encounter a blocking error, or want to provide a status update.
    The developer may not be looking at the screen. Keep messages brief
    and conversational — like a colleague tapping their shoulder.

    Args:
        message: What to say. Keep to 1-2 sentences.
        urgency: Priority level — "info" (normal), "warning" (important),
                 or "critical" (urgent, needs immediate attention).
        voice: Voice ID override. Leave empty to use the session default.
               Use list_voices to see available voices.
        speed: Speech speed override (0.5-2.0). 0 = use session default.
    """
    engine, audio = await _ensure_initialized()

    # Adjust speed based on urgency
    effective_speed = speed if speed > 0 else engine.default_speed
    if urgency == "critical" and speed <= 0:
        effective_speed = max(0.9, effective_speed - 0.1)  # Slightly slower for emphasis
    elif urgency == "warning" and speed <= 0:
        effective_speed = effective_speed  # Normal speed

    effective_voice = voice or engine.default_voice

    # Validate voice
    if effective_voice not in engine.get_voices():
        return {
            "status": "error",
            "error": f"Unknown voice: {effective_voice}. Use list_voices to see available voices.",
        }

    # Synthesize
    try:
        audio_data, sample_rate = await engine.synthesize(
            text=message, voice=effective_voice, speed=effective_speed
        )
    except Exception as e:
        return {"status": "error", "error": f"TTS failed: {e}"}

    # Queue for playback (non-blocking)
    audio.enqueue(audio_data, sample_rate)

    return {
        "status": "speaking",
        "message": message,
        "voice": effective_voice,
        "urgency": urgency,
        "queued_items": audio.pending,
    }


@mcp.tool(annotations={"readOnlyHint": True})
async def list_voices(language: str = "") -> dict:
    """List available TTS voices, optionally filtered by language.

    Args:
        language: Filter by language code (e.g., "en-us", "ja", "es").
                  Leave empty to list all voices.
    """
    engine, _ = await _ensure_initialized()

    voices = engine.get_voices(language)
    languages = engine.get_languages()

    return {
        "voices": {
            vid: {
                "language": meta["language"],
                "gender": meta["gender"],
                "description": meta["description"],
            }
            for vid, meta in voices.items()
        },
        "total": len(voices),
        "languages": languages,
        "current_default": engine.default_voice,
    }


@mcp.tool(annotations={"readOnlyHint": False})
async def set_voice(
    voice: str = "", speed: float = 0.0, persist: bool = False
) -> dict:
    """Set the default voice and/or speed for this session.

    Args:
        voice: Voice ID to use as default. Leave empty to keep current.
        speed: Default speech speed (0.5-2.0). 0 = keep current.
        persist: If true, save as the default for all future sessions
                 (writes to ~/.agent-fm/config.toml).
    """
    engine, _ = await _ensure_initialized()

    if voice:
        if voice not in engine.get_voices():
            return {
                "status": "error",
                "error": f"Unknown voice: {voice}. Use list_voices to see options.",
            }
        engine.default_voice = voice

    if speed > 0:
        if not 0.5 <= speed <= 2.0:
            return {"status": "error", "error": "Speed must be between 0.5 and 2.0"}
        engine.default_speed = speed

    result = {
        "status": "ok",
        "default_voice": engine.default_voice,
        "default_speed": engine.default_speed,
    }

    if persist:
        from .config import save_config

        save_config({"voice": engine.default_voice, "speed": engine.default_speed})
        result["persisted"] = True
    else:
        result["persisted"] = False
        result["hint"] = (
            "This change is for this session only. "
            "To make it your default across sessions, "
            "call set_voice with persist=true."
        )

    return result
