"""TTS engine for agent-fm.

Two-tier design:
  1. Kokoro (primary) — high-quality neural TTS via kokoro-onnx, runs on CPU
  2. System fallback — platform-native TTS when Kokoro is unavailable
"""

import asyncio
import platform
import shutil
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path

import numpy as np

from .models import ensure_models

# Voice metadata for Kokoro voices (subset — most useful for agent-fm)
VOICES = {
    # American English — Female
    "af_heart": {"language": "en-us", "gender": "female", "description": "Warm, friendly"},
    "af_bella": {"language": "en-us", "gender": "female", "description": "Clear, professional"},
    "af_nicole": {"language": "en-us", "gender": "female", "description": "Calm, measured"},
    "af_nova": {"language": "en-us", "gender": "female", "description": "Bright, energetic"},
    "af_sky": {"language": "en-us", "gender": "female", "description": "Light, airy"},
    "af_sarah": {"language": "en-us", "gender": "female", "description": "Warm, conversational"},
    "af_river": {"language": "en-us", "gender": "female", "description": "Smooth, flowing"},
    "af_alloy": {"language": "en-us", "gender": "female", "description": "Balanced, neutral"},
    "af_aoede": {"language": "en-us", "gender": "female", "description": "Musical, expressive"},
    "af_jessica": {"language": "en-us", "gender": "female", "description": "Friendly, casual"},
    "af_kore": {"language": "en-us", "gender": "female", "description": "Clear, precise"},
    # American English — Male
    "am_adam": {"language": "en-us", "gender": "male", "description": "Deep, confident"},
    "am_echo": {"language": "en-us", "gender": "male", "description": "Clear, resonant"},
    "am_eric": {"language": "en-us", "gender": "male", "description": "Warm, approachable"},
    "am_michael": {"language": "en-us", "gender": "male", "description": "Professional, steady"},
    "am_onyx": {"language": "en-us", "gender": "male", "description": "Rich, deep"},
    "am_fenrir": {"language": "en-us", "gender": "male", "description": "Strong, commanding"},
    "am_orion": {"language": "en-us", "gender": "male", "description": "Balanced, clear"},
    "am_rocket": {"language": "en-us", "gender": "male", "description": "Energetic, bright"},
    "am_thunder": {"language": "en-us", "gender": "male", "description": "Powerful, bold"},
    # British English — Female
    "bf_alice": {"language": "en-gb", "gender": "female", "description": "Gentle, refined"},
    "bf_emma": {"language": "en-gb", "gender": "female", "description": "Warm, articulate"},
    "bf_isabella": {"language": "en-gb", "gender": "female", "description": "Elegant, measured"},
    "bf_lily": {"language": "en-gb", "gender": "female", "description": "Sweet, clear"},
    # British English — Male
    "bm_daniel": {"language": "en-gb", "gender": "male", "description": "Authoritative, clear"},
    "bm_fable": {"language": "en-gb", "gender": "male", "description": "Storytelling, warm"},
    "bm_george": {"language": "en-gb", "gender": "male", "description": "Distinguished, deep"},
    "bm_lewis": {"language": "en-gb", "gender": "male", "description": "Friendly, casual"},
    # Spanish
    "ef_dora": {"language": "es", "gender": "female", "description": "Warm, expressive"},
    "em_alex": {"language": "es", "gender": "male", "description": "Clear, natural"},
    "em_santa": {"language": "es", "gender": "male", "description": "Cheerful, friendly"},
    # French
    "ff_siwis": {"language": "fr", "gender": "female", "description": "Elegant, smooth"},
    # Hindi
    "hf_alpha": {"language": "hi", "gender": "female", "description": "Clear, warm"},
    "hf_beta": {"language": "hi", "gender": "female", "description": "Soft, gentle"},
    "hm_omega": {"language": "hi", "gender": "male", "description": "Deep, steady"},
    "hm_psi": {"language": "hi", "gender": "male", "description": "Clear, confident"},
    # Italian
    "if_sara": {"language": "it", "gender": "female", "description": "Melodic, warm"},
    "im_nicola": {"language": "it", "gender": "male", "description": "Smooth, expressive"},
    # Japanese
    "jf_alpha": {"language": "ja", "gender": "female", "description": "Clear, polite"},
    "jf_gongitsune": {"language": "ja", "gender": "female", "description": "Gentle, storytelling"},
    "jf_nezumi": {"language": "ja", "gender": "female", "description": "Bright, youthful"},
    "jm_kumo": {"language": "ja", "gender": "male", "description": "Calm, measured"},
    "jm_takeru": {"language": "ja", "gender": "male", "description": "Strong, clear"},
    # Portuguese
    "pf_dora": {"language": "pt-br", "gender": "female", "description": "Warm, natural"},
    "pm_alex": {"language": "pt-br", "gender": "male", "description": "Clear, steady"},
    "pm_santa": {"language": "pt-br", "gender": "male", "description": "Friendly, warm"},
    # Mandarin Chinese
    "zf_xiaobei": {"language": "cmn", "gender": "female", "description": "Clear, bright"},
    "zf_xiaoni": {"language": "cmn", "gender": "female", "description": "Soft, gentle"},
    "zf_xiaoxiao": {"language": "cmn", "gender": "female", "description": "Youthful, lively"},
    "zf_xiaoyi": {"language": "cmn", "gender": "female", "description": "Warm, natural"},
    "zm_yunjian": {"language": "cmn", "gender": "male", "description": "Strong, clear"},
    "zm_yunxi": {"language": "cmn", "gender": "male", "description": "Warm, conversational"},
    "zm_yunxia": {"language": "cmn", "gender": "male", "description": "Balanced, steady"},
    "zm_yunyang": {"language": "cmn", "gender": "male", "description": "Deep, authoritative"},
}

SAMPLE_RATE = 24000
DEFAULT_VOICE = "am_fenrir"


class TTSEngine:
    """Two-tier TTS engine: Kokoro primary, system TTS fallback."""

    def __init__(self) -> None:
        self._kokoro = None  # Lazy-loaded Kokoro model
        self._kokoro_available: bool | None = None  # None = not checked yet
        self.default_voice: str = DEFAULT_VOICE
        self.default_speed: float = 1.0

    async def initialize(self) -> None:
        """Initialize the TTS engine. Downloads models on first run."""
        loop = asyncio.get_event_loop()
        try:
            model_path, voices_path = await loop.run_in_executor(None, ensure_models)
            from kokoro_onnx import Kokoro

            self._kokoro = await loop.run_in_executor(
                None, partial(Kokoro, str(model_path), str(voices_path))
            )
            self._kokoro_available = True
            print("[agent-fm] Kokoro TTS initialized", file=sys.stderr)
        except Exception as e:
            self._kokoro_available = False
            print(f"[agent-fm] Kokoro unavailable ({e}), using system TTS", file=sys.stderr)

    async def synthesize(
        self, text: str, voice: str = "", speed: float = 0.0
    ) -> tuple[np.ndarray, int]:
        """Synthesize speech from text.

        Args:
            text: Text to speak.
            voice: Voice ID (empty = use default).
            speed: Speech speed 0.5-2.0 (0 = use default).

        Returns:
            Tuple of (audio_array, sample_rate).
        """
        effective_voice = voice or self.default_voice
        effective_speed = speed if speed > 0 else self.default_speed

        if self._kokoro_available and self._kokoro is not None:
            return await self._synthesize_kokoro(text, effective_voice, effective_speed)
        return await self._synthesize_system(text)

    async def _synthesize_kokoro(
        self, text: str, voice: str, speed: float
    ) -> tuple[np.ndarray, int]:
        """Generate audio using Kokoro ONNX."""
        # Determine language from voice metadata
        meta = VOICES.get(voice, {})
        lang = meta.get("language", "en-us")

        loop = asyncio.get_event_loop()
        samples, sr = await loop.run_in_executor(
            None,
            partial(self._kokoro.create, text=text, voice=voice, speed=speed, lang=lang),
        )
        return samples.astype(np.float32), int(sr)

    async def _synthesize_system(self, text: str) -> tuple[np.ndarray, int]:
        """Fallback: use platform-native TTS."""
        system = platform.system()

        if system == "Darwin":
            return await self._tts_macos(text)
        elif system == "Windows":
            return await self._tts_windows(text)
        else:
            return await self._tts_linux(text)

    async def _tts_macos(self, text: str) -> tuple[np.ndarray, int]:
        """macOS fallback using 'say' command."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            proc = await asyncio.create_subprocess_exec(
                "say", "-o", tmp_path, "--data-format=LEF32@24000", text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            import soundfile as sf

            data, sr = sf.read(tmp_path, dtype="float32")
            return data, sr
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _tts_windows(self, text: str) -> tuple[np.ndarray, int]:
        """Windows fallback using PowerShell System.Speech or espeak-ng."""
        # Try espeak-ng first (better quality, already installed for Kokoro)
        espeak = shutil.which("espeak-ng")
        if espeak:
            return await self._tts_espeak(text)

        # Fallback to PowerShell System.Speech
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            # PowerShell script to save speech to WAV
            ps_script = (
                f"Add-Type -AssemblyName System.Speech;"
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                f"$synth.SetOutputToWaveFile('{tmp_path}');"
                f"$synth.Speak('{text.replace(chr(39), chr(39)+chr(39))}');"
                f"$synth.Dispose()"
            )
            proc = await asyncio.create_subprocess_exec(
                "powershell", "-NoProfile", "-Command", ps_script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            import soundfile as sf

            data, sr = sf.read(tmp_path, dtype="float32")
            return data, sr
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _tts_linux(self, text: str) -> tuple[np.ndarray, int]:
        """Linux fallback using espeak-ng."""
        return await self._tts_espeak(text)

    async def _tts_espeak(self, text: str) -> tuple[np.ndarray, int]:
        """Generate audio using espeak-ng."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            proc = await asyncio.create_subprocess_exec(
                "espeak-ng", "-w", tmp_path, text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            import soundfile as sf

            data, sr = sf.read(tmp_path, dtype="float32")
            return data, sr
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def get_voices(self, language: str = "") -> dict:
        """Get available voices, optionally filtered by language."""
        if not language:
            return VOICES
        return {k: v for k, v in VOICES.items() if v["language"] == language}

    def get_languages(self) -> list[str]:
        """Get list of available languages."""
        return sorted({v["language"] for v in VOICES.values()})
