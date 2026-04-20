"""Audio playback queue for agent-fm.

Manages sequential, non-blocking audio playback through the system speakers.
Multiple speak() calls are queued and played one at a time — no overlap.
"""

import asyncio
import sys
import threading
from queue import Empty, Queue

import numpy as np
import sounddevice as sd


class AudioQueue:
    """Sequential audio playback queue.

    Audio arrays are enqueued and played one at a time in FIFO order.
    Playback runs in a background thread — enqueue() returns immediately.
    """

    def __init__(self, sample_rate: int = 24000) -> None:
        self._sample_rate = sample_rate
        self._queue: Queue[np.ndarray | None] = Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the playback thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()
        print("[agent-fm] Audio playback started", file=sys.stderr)

    def enqueue(self, audio: np.ndarray, sample_rate: int = 0) -> None:
        """Add audio to the playback queue. Returns immediately.

        Args:
            audio: Float32 numpy array of audio samples.
            sample_rate: Sample rate (0 = use default).
        """
        if not self._running:
            self.start()

        # Store sample rate with audio if different from default
        if sample_rate and sample_rate != self._sample_rate:
            # Resample by storing the rate — playback loop handles it
            self._queue.put((audio, sample_rate))
        else:
            self._queue.put(audio)

    def _playback_loop(self) -> None:
        """Background thread: pull from queue, play sequentially."""
        while self._running:
            try:
                item = self._queue.get(timeout=1.0)
            except Empty:
                continue

            if item is None:
                # Poison pill — shutdown signal
                break

            # Unpack audio and optional sample rate
            if isinstance(item, tuple):
                audio, sr = item
            else:
                audio = item
                sr = self._sample_rate

            try:
                # Ensure float32, mono
                audio = np.asarray(audio, dtype=np.float32)
                if audio.ndim > 1:
                    audio = audio[:, 0]

                # Play and block until done
                sd.play(audio, samplerate=sr)
                sd.wait()
            except Exception as e:
                print(f"[agent-fm] Playback error: {e}", file=sys.stderr)
            finally:
                self._queue.task_done()

    def stop(self) -> None:
        """Stop playback and drain the queue."""
        self._running = False
        # Send poison pill
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        print("[agent-fm] Audio playback stopped", file=sys.stderr)

    @property
    def pending(self) -> int:
        """Number of audio items waiting to be played."""
        return self._queue.qsize()
