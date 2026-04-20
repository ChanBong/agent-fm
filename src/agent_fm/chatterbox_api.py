"""FastAPI server for Chatterbox TTS exploration/development.

Separate from the Kokoro-based agent-fm server. Provides endpoints for
text-to-speech generation with voice cloning support using ChatterboxTTS.

Run: python -m agent_fm.chatterbox_api
"""

import asyncio
import base64
import io
import os
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torchaudio
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VOICES_DIR = Path.home() / ".agent-fm" / "voices"
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Lazy-loaded model singleton
# ---------------------------------------------------------------------------
_model = None
_model_device: Optional[str] = None
_model_load_time: Optional[float] = None


def _get_device() -> str:
    """Pick the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_model(device: Optional[str] = None, warmup: bool = True):
    """Load ChatterboxTurboTTS model onto the specified device.

    Applies bfloat16 for VRAM savings and runs a warmup generation
    to eliminate first-request latency.
    """
    global _model, _model_device, _model_load_time
    import sys
    from chatterbox.tts_turbo import ChatterboxTurboTTS

    device = device or _get_device()
    t0 = time.time()
    _model = ChatterboxTurboTTS.from_pretrained(device=device)

    # Apply bfloat16 to T3 backbone — saves ~0.8 GB VRAM on Ada GPUs
    if device == "cuda" and torch.cuda.is_bf16_supported():
        _model.t3.to(dtype=torch.bfloat16)
        if hasattr(_model.conds, "t3"):
            _model.conds.t3.to(dtype=torch.bfloat16)
        torch.cuda.empty_cache()
        print("[chatterbox] Applied bfloat16 to T3 backbone", file=sys.stderr)

    _model_load_time = time.time() - t0
    _model_device = device

    # Warmup: first generation is always slower due to CUDA kernel init
    if warmup and device == "cuda":
        print("[chatterbox] Warming up (first generation)...", file=sys.stderr)
        with torch.inference_mode():
            _ = _model.generate("Hello.")
        torch.cuda.synchronize()
        print("[chatterbox] Warmup complete", file=sys.stderr)


def _get_model():
    """Return the loaded model, loading it lazily on first call."""
    if _model is None:
        _load_model()
    return _model


def _unload_model():
    """Unload the model and free GPU memory."""
    global _model, _model_device, _model_load_time
    _model = None
    _model_device = None
    _model_load_time = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _gpu_info() -> dict:
    """Return GPU/VRAM info if CUDA is available."""
    if not torch.cuda.is_available():
        return {"gpu_available": False}

    return {
        "gpu_available": True,
        "gpu_name": torch.cuda.get_device_name(0),
        "vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1e6, 1),
        "vram_allocated_mb": round(torch.cuda.memory_allocated(0) / 1e6, 1),
        "vram_reserved_mb": round(torch.cuda.memory_reserved(0) / 1e6, 1),
    }


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Chatterbox TTS Playground", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_preload():
    """Pre-load model and warmup at server start for instant first requests."""
    import sys
    print("[chatterbox] Pre-loading model at startup...", file=sys.stderr)
    _load_model(warmup=True)
    print(f"[chatterbox] Ready! VRAM: {torch.cuda.memory_allocated() / 1024**3:.2f} GB", file=sys.stderr)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    text: str
    voice_clone_path: str = ""
    temperature: float = 0.8
    top_p: float = 0.95


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    """Health check with model and GPU status."""
    info = {
        "status": "ok",
        "model_loaded": _model is not None,
        "model_device": _model_device,
        "model_load_time_s": round(_model_load_time, 2) if _model_load_time else None,
        "sample_rate": _model.sr if _model else None,
    }
    info.update(_gpu_info())
    return info


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """Generate speech from text. Returns WAV audio binary."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    model = _get_model()

    # Build generation kwargs (Turbo-compatible)
    gen_kwargs = {
        "temperature": req.temperature,
        "top_p": req.top_p,
    }

    # Voice cloning: resolve path
    voice_path = None
    if req.voice_clone_path:
        voice_path = Path(req.voice_clone_path)
        if not voice_path.exists():
            # Try looking in the voices directory
            voice_path = VOICES_DIR / req.voice_clone_path
            if not voice_path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Voice file not found: {req.voice_clone_path}",
                )

    t0 = time.time()
    with torch.inference_mode():
        if voice_path:
            wav = model.generate(req.text, audio_prompt_path=str(voice_path), **gen_kwargs)
        else:
            wav = model.generate(req.text, **gen_kwargs)
    gen_time = time.time() - t0

    # Convert tensor to WAV bytes
    buf = io.BytesIO()
    # Ensure wav is 2D: (channels, samples)
    if wav.dim() == 1:
        wav = wav.unsqueeze(0)
    torchaudio.save(buf, wav.cpu(), model.sr, format="wav")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="audio/wav",
        headers={
            "X-Generation-Time": f"{gen_time:.2f}",
            "X-Audio-Duration": f"{wav.shape[-1] / model.sr:.2f}",
            "X-Sample-Rate": str(model.sr),
        },
    )


@app.post("/api/clone")
async def clone_voice(name: str = Form(...), audio: UploadFile = File(...)):
    """Upload an audio file for voice cloning.

    Accepts WAV, MP3, M4A, FLAC, OGG, etc. Converts to 24kHz mono WAV
    and saves to ~/.agent-fm/voices/.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="name must not be empty")

    # Sanitize filename
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip()
    if not safe_name:
        raise HTTPException(status_code=400, detail="name contains no valid characters")

    # Save raw upload to temp, then convert to 24kHz mono WAV
    import tempfile
    import soundfile as sf
    import librosa
    import numpy as np

    contents = await audio.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="uploaded file is empty")

    # Preserve original extension for the temp file so librosa can sniff format
    orig_ext = Path(audio.filename or "upload.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=orig_ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # librosa decodes virtually anything (m4a, mp3, wav, flac, ogg)
        samples, sr = librosa.load(tmp_path, sr=24000, mono=True)
        if len(samples) < 24000 * 5:  # less than 5 seconds
            raise HTTPException(
                status_code=400,
                detail=f"Audio too short: {len(samples) / 24000:.1f}s. Chatterbox Turbo needs at least 5 seconds.",
            )
        # Save as 24kHz mono WAV
        final_name = safe_name if safe_name.lower().endswith(".wav") else safe_name + ".wav"
        save_path = VOICES_DIR / final_name
        sf.write(save_path, samples, 24000, subtype="PCM_16")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not decode audio file: {e}. Try a different format (WAV/MP3/M4A).",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "status": "saved",
        "name": final_name,
        "path": str(save_path),
        "size_bytes": save_path.stat().st_size,
        "duration_s": round(len(samples) / 24000, 2),
    }


@app.get("/api/voices")
def list_voices():
    """List saved cloned voices from ~/.agent-fm/voices/."""
    voices = []
    for f in sorted(VOICES_DIR.iterdir()):
        if f.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg"):
            voices.append({
                "name": f.stem,
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size,
            })
    return {"voices_dir": str(VOICES_DIR), "voices": voices}


@app.post("/api/load")
def load_model():
    """Load the model into GPU/CPU memory."""
    if _model is not None:
        return {"status": "already_loaded", "device": _model_device}

    t0 = time.time()
    _load_model()
    elapsed = time.time() - t0

    return {
        "status": "loaded",
        "device": _model_device,
        "load_time_s": round(elapsed, 2),
    }


@app.post("/api/unload")
def unload_model():
    """Unload the model from memory."""
    was_loaded = _model is not None
    _unload_model()
    return {
        "status": "unloaded" if was_loaded else "already_unloaded",
    }


@app.websocket("/ws/generate-stream")
async def generate_stream(ws: WebSocket):
    """Stream TTS audio sentence-by-sentence over WebSocket.

    Client sends JSON: {text, voice_clone_path?, temperature?, top_p?}
    Server sends back: {type:"chunk", audio:<base64 PCM int16>, index, total, sample_rate}
    Then: {type:"done", total_time}
    """
    await ws.accept()
    try:
        data = await ws.receive_json()
        text = data.get("text", "").strip()
        if not text:
            await ws.send_json({"type": "error", "message": "text is empty"})
            await ws.close()
            return

        model = _get_model()

        # Resolve voice clone path
        voice_path = None
        clone_path = data.get("voice_clone_path", "")
        if clone_path:
            voice_path = Path(clone_path)
            if not voice_path.exists():
                voice_path = VOICES_DIR / clone_path
                if not voice_path.exists():
                    voice_path = None

        # Split into sentences
        from agent_fm.text_utils import split_sentences
        sentences = split_sentences(text)

        gen_kwargs = {
            "temperature": data.get("temperature", 0.8),
            "top_p": data.get("top_p", 0.95),
        }

        total_start = time.time()
        loop = asyncio.get_event_loop()

        for i, sentence in enumerate(sentences):
            def _generate_sentence(sent=sentence):
                with torch.inference_mode():
                    if voice_path:
                        return model.generate(sent, audio_prompt_path=str(voice_path), **gen_kwargs)
                    else:
                        return model.generate(sent, **gen_kwargs)

            wav = await loop.run_in_executor(None, _generate_sentence)

            # Convert to 16-bit PCM bytes, then base64
            pcm_float = wav.squeeze().cpu().numpy()
            pcm_int16 = (pcm_float * 32767).clip(-32768, 32767).astype(np.int16)
            pcm_b64 = base64.b64encode(pcm_int16.tobytes()).decode("ascii")

            await ws.send_json({
                "type": "chunk",
                "audio": pcm_b64,
                "index": i,
                "total": len(sentences),
                "sample_rate": model.sr,
                "sentence": sentence,
                "duration": len(pcm_int16) / model.sr,
            })

        total_time = time.time() - total_start
        await ws.send_json({"type": "done", "total_time": round(total_time, 2)})

    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    uvicorn.run(
        "agent_fm.chatterbox_api:app",
        host="0.0.0.0",
        port=3002,
        reload=False,
    )


if __name__ == "__main__":
    main()
