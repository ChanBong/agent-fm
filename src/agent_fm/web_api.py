"""Lightweight FastAPI server for agent-fm TTS.

Provides a simple HTTP API for generating speech audio from text
using kokoro-onnx. Designed for local development with the web app.
"""

import io
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from agent_fm.models import ensure_models
from agent_fm.tts import DEFAULT_VOICE, VOICES

# ---------------------------------------------------------------------------
# Lazy-loaded model singleton
# ---------------------------------------------------------------------------
_kokoro = None


def _get_model():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro

        model_path, voices_path = ensure_models()
        _kokoro = Kokoro(str(model_path), str(voices_path))
    return _kokoro


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="agent-fm TTS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    speed: float = 1.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/voices")
def voices():
    return VOICES


@app.post("/api/generate")
def generate(req: GenerateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    if req.voice not in VOICES:
        raise HTTPException(status_code=400, detail=f"unknown voice: {req.voice}")

    lang = VOICES[req.voice]["language"]
    model = _get_model()
    samples, sr = model.create(
        text=req.text, voice=req.voice, speed=req.speed, lang=lang
    )

    # Convert to WAV bytes
    buf = io.BytesIO()
    sf.write(buf, samples.astype(np.float32), 24000, format="WAV")
    buf.seek(0)

    return Response(content=buf.read(), media_type="audio/wav")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
