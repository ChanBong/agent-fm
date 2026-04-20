"""Model download and cache management for agent-fm.

Downloads Kokoro ONNX model files on first use and caches them
in ~/.agent-fm/models/. Total download is ~340MB (one-time).
"""

import sys
import urllib.request
from pathlib import Path

MODEL_DIR = Path.home() / ".agent-fm" / "models"

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

MODEL_FILENAME = "kokoro-v1.0.onnx"
VOICES_FILENAME = "voices-v1.0.bin"


def _download_file(url: str, destination: Path) -> None:
    """Download a file with progress reporting to stderr."""
    print(f"[agent-fm] Downloading {destination.name}...", file=sys.stderr)

    def progress_hook(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(
                f"\r[agent-fm]   {percent:.0f}% ({mb_done:.1f}/{mb_total:.1f} MB)",
                end="",
                flush=True,
                file=sys.stderr,
            )

    urllib.request.urlretrieve(url, str(destination), progress_hook)
    print(f"\n[agent-fm]   Done: {destination.name}", file=sys.stderr)


def ensure_models() -> tuple[Path, Path]:
    """Ensure Kokoro model files are downloaded and return their paths.

    Downloads models to ~/.agent-fm/models/ if not already present.
    This is a one-time ~340MB download.

    Returns:
        Tuple of (model_path, voices_path).
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODEL_DIR / MODEL_FILENAME
    voices_path = MODEL_DIR / VOICES_FILENAME

    if not model_path.exists():
        _download_file(MODEL_URL, model_path)

    if not voices_path.exists():
        _download_file(VOICES_URL, voices_path)

    return model_path, voices_path
