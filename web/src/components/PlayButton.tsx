import React, { useState, useRef } from "react";
import { Play } from "./ui/Icons";
import { Button } from "./ui/Button";
import { appStore } from "@/lib/store";
import s from "./ui/Footer.module.css";

const IS_SAFARI = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
const IS_IOS = /iPad|iPhone|iPod/.test(navigator.userAgent);

const PlayingWaveform = ({
  audioLoaded,
  amplitudeLevels,
}: {
  audioLoaded: boolean;
  amplitudeLevels: number[];
}) => (
  <div className="w-[36px] h-[16px] relative left-[4px]">
    {amplitudeLevels.map((level, idx) => {
      const height = `${Math.min(Math.max(level * 30, 0.2), 1.9) * 100}%`;
      return (
        <div
          key={idx}
          className={`w-[2px] bg-white transition-all duration-150 rounded-[2px] absolute top-1/2 -translate-y-1/2 ${
            audioLoaded ? "opacity-100" : s["animate-wave"]
          }`}
          style={{
            height,
            animationDelay: `${idx * 0.15}s`,
            left: `${idx * 6}px`,
          }}
        />
      );
    })}
  </div>
);

// ---- Streaming playback via WebSocket + Web Audio API ----

function useStreamingPlayback() {
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const isActiveRef = useRef(false);

  const playChunk = (pcmBase64: string, sampleRate: number) => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new AudioContext({ sampleRate });
    }
    const ctx = audioCtxRef.current;

    const raw = atob(pcmBase64);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    const buffer = ctx.createBuffer(1, float32.length, sampleRate);
    buffer.getChannelData(0).set(float32);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    const startTime = Math.max(ctx.currentTime + 0.05, nextStartTimeRef.current);
    source.start(startTime);
    nextStartTimeRef.current = startTime + buffer.duration;

    return buffer.duration;
  };

  const start = (
    text: string,
    clonedVoice: string,
    onChunk: () => void,
    onDone: () => void,
    onError: (msg: string) => void
  ) => {
    stop();
    isActiveRef.current = true;
    nextStartTimeRef.current = 0;

    const ws = new WebSocket("ws://localhost:3002/ws/generate-stream");
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          text,
          voice_clone_path: clonedVoice || "",
        })
      );
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "chunk") {
        playChunk(data.audio, data.sample_rate);
        onChunk();
      } else if (data.type === "done") {
        // Wait for all audio to finish playing before signaling done
        const ctx = audioCtxRef.current;
        if (ctx && nextStartTimeRef.current > ctx.currentTime) {
          const remaining = (nextStartTimeRef.current - ctx.currentTime) * 1000;
          setTimeout(() => {
            isActiveRef.current = false;
            onDone();
          }, remaining + 100);
        } else {
          isActiveRef.current = false;
          onDone();
        }
      } else if (data.type === "error") {
        isActiveRef.current = false;
        onError(data.message);
      }
    };

    ws.onerror = () => {
      isActiveRef.current = false;
      onError("WebSocket connection failed. Is the Chatterbox server running?");
    };

    ws.onclose = () => {
      wsRef.current = null;
    };
  };

  const stop = () => {
    isActiveRef.current = false;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    nextStartTimeRef.current = 0;
  };

  return { start, stop, isActive: () => isActiveRef.current };
}

// ---- Main PlayButton component ----

export default function PlayButton() {
  const [audioLoading, setAudioLoading] = useState(false);
  const [audioLoaded, setAudioLoaded] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const [amplitudeLevels, setAmplitudeLevels] = useState<number[]>(
    new Array(5).fill(0)
  );
  const amplitudeIntervalRef = useRef<number | null>(null);
  const useStaticAnimation = IS_SAFARI || IS_IOS;

  const streaming = useStreamingPlayback();

  const generateRandomAmplitudes = () =>
    Array(5)
      .fill(0)
      .map(() => Math.random() * 0.06);

  const handleStop = () => {
    // Stop streaming
    streaming.stop();

    // Stop regular playback
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (amplitudeIntervalRef.current) {
      clearInterval(amplitudeIntervalRef.current);
      amplitudeIntervalRef.current = null;
    }
    setIsPlaying(false);
    setAudioLoaded(false);
    setAudioLoading(false);
  };

  const handleStreamingPlay = () => {
    const { input, clonedVoice } = appStore.getState();

    setAudioLoading(true);
    setAmplitudeLevels(new Array(5).fill(0));

    // Start waveform animation
    const animInterval = window.setInterval(() => {
      setAmplitudeLevels(generateRandomAmplitudes());
    }, 100);
    amplitudeIntervalRef.current = animInterval;

    streaming.start(
      input,
      clonedVoice,
      () => {
        // onChunk — first chunk arrived, we're playing
        setAudioLoading(false);
        setAudioLoaded(true);
        setIsPlaying(true);
      },
      () => {
        // onDone — all audio finished
        clearInterval(animInterval);
        amplitudeIntervalRef.current = null;
        setIsPlaying(false);
        setAudioLoaded(false);
        setAmplitudeLevels(new Array(5).fill(0));
      },
      (msg) => {
        // onError
        clearInterval(animInterval);
        amplitudeIntervalRef.current = null;
        setAudioLoading(false);
        setIsPlaying(false);
        alert(msg);
      }
    );
  };

  const handleRegularPlay = async () => {
    const { input, prompt, voice, engine, clonedVoice } = appStore.getState();

    setAudioLoading(true);
    appStore.setState({ latestAudioUrl: null });

    try {
      const url = new URL("/api/generate", window.location.origin);
      url.searchParams.append("input", input);
      url.searchParams.append("prompt", prompt);
      url.searchParams.append("voice", voice);
      url.searchParams.append("engine", engine);
      if (engine === "chatterbox" && clonedVoice) {
        url.searchParams.append("clone_path", clonedVoice);
      }
      url.searchParams.append("generation", crypto.randomUUID());
      const audioUrl = url.toString();
      appStore.setState({ latestAudioUrl: audioUrl });

      if (amplitudeIntervalRef.current !== null) {
        clearInterval(amplitudeIntervalRef.current);
        amplitudeIntervalRef.current = null;
      }

      const audio = new Audio();
      audio.preload = "none";
      audioRef.current = audio;

      if (!useStaticAnimation) {
        if (!audioContextRef.current) {
          audioContextRef.current = new AudioContext();
        }
        const ctx = audioContextRef.current;
        const source = ctx.createMediaElementSource(audio);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        analyser.connect(ctx.destination);
        analyserRef.current = analyser;
      }

      const sample = () => {
        if (useStaticAnimation) {
          setAmplitudeLevels(generateRandomAmplitudes());
          return;
        }
        if (!analyserRef.current) return;
        const data = new Uint8Array(analyserRef.current.fftSize);
        analyserRef.current.getByteTimeDomainData(data);
        const avg =
          data.reduce((sum, v) => sum + Math.abs(v - 128), 0) /
          analyserRef.current.fftSize;
        const amp = avg / 128;
        setAmplitudeLevels((prev) => [...prev.slice(1), amp]);
      };

      audio.onerror = () => {
        setAudioLoading(false);
        setAudioLoaded(false);
        setIsPlaying(false);
        alert("Error generating audio");
      };

      audio.onplay = () => {
        amplitudeIntervalRef.current = window.setInterval(sample, 100);
        setIsPlaying(true);
        setAudioLoaded(true);
        setAudioLoading(false);
      };

      const clearSampling = () => {
        audioRef.current = null;
        if (amplitudeIntervalRef.current !== null) {
          clearInterval(amplitudeIntervalRef.current);
          amplitudeIntervalRef.current = null;
        }
        setIsPlaying(false);
      };

      audio.onpause = clearSampling;
      audio.onended = clearSampling;
      audio.autoplay = true;
      audio.src = audioUrl;
    } catch (err) {
      console.error("Error generating speech:", err);
      setAudioLoading(false);
      setAudioLoaded(false);
      setIsPlaying(false);
    }
  };

  const handleSubmit = () => {
    if (audioLoading) return;

    // Toggle off if playing
    if (isPlaying || audioRef.current || streaming.isActive()) {
      handleStop();
      return;
    }

    const { engine, streaming: isStreaming } = appStore.getState();
    if (engine === "chatterbox" && isStreaming) {
      handleStreamingPlay();
    } else {
      handleRegularPlay();
    }
  };

  return (
    <Button
      color="primary"
      onClick={handleSubmit}
      selected={audioLoading || isPlaying}
      className="relative"
    >
      {isPlaying ? (
        <PlayingWaveform
          audioLoaded={audioLoaded}
          amplitudeLevels={amplitudeLevels}
        />
      ) : audioLoading ? (
        <PlayingWaveform
          audioLoaded={false}
          amplitudeLevels={[0.032, 0.032, 0.032, 0.032, 0.032]}
        />
      ) : (
        <Play />
      )}
      <span className="uppercase hidden md:inline pr-3">
        {isPlaying ? "Stop" : audioLoading ? "Busy" : "Play"}
      </span>
    </Button>
  );
}
