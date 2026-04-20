"use client";
import React, { useEffect, useRef, useState } from "react";
import { Block } from "./ui/Block";
import { Button, ButtonLED } from "./ui/Button";
import { appStore } from "@/lib/store";

interface ClonedVoice {
  name: string;
  filename: string;
  path: string;
  size_bytes: number;
}

const CHATTERBOX_API = "/api/chatterbox";

export default function ChatterboxVoices() {
  const clonedVoice = appStore.useState((s) => s.clonedVoice);
  const [voices, setVoices] = useState<ClonedVoice[]>([]);
  const [uploading, setUploading] = useState(false);
  const [newVoiceName, setNewVoiceName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState<{ loaded?: boolean; vram?: number; device?: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchVoices = async () => {
    try {
      const res = await fetch(`${CHATTERBOX_API}/voices`);
      const data = await res.json();
      setVoices(data.voices || []);
    } catch {
      setError("Can't reach Chatterbox server on port 3002");
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${CHATTERBOX_API}/health`);
      const data = await res.json();
      setStatus({
        loaded: data.model_loaded,
        vram: data.vram_allocated_mb,
        device: data.model_device,
      });
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => {
    fetchVoices();
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async () => {
    if (!newVoiceName.trim()) {
      setError("Enter a name for the voice first");
      return;
    }
    if (!selectedFile) {
      setError("Choose an audio file first");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("name", newVoiceName);
      formData.append("audio", selectedFile);
      const res = await fetch(`${CHATTERBOX_API}/clone`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      setNewVoiceName("");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchVoices();
    } catch (e) {
      setError(`Upload failed: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setUploading(false);
    }
  };

  const statusBadge = status ? (
    <span className="text-[10px] opacity-60 ml-auto">
      {status.loaded
        ? `loaded · ${status.device} · ${status.vram?.toFixed(0)}MB VRAM`
        : "not loaded (loads on first play)"}
    </span>
  ) : (
    <span className="text-[10px] opacity-60 ml-auto text-red-500">server offline</span>
  );

  const currentVoiceLabel = clonedVoice
    ? voices.find((v) => v.filename === clonedVoice)?.name || clonedVoice
    : "Default (built-in Chatterbox voice)";

  return (
    <Block title={
      <div className="flex items-center w-full gap-2">
        <span>Chatterbox Voice</span>
        <span className="text-[11px] text-primary font-semibold normal-case">→ {currentVoiceLabel}</span>
        {statusBadge}
      </div>
    }>
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {/* Default voice */}
          <Button
            block
            color="default"
            onClick={() => {
              appStore.setState((draft) => {
                draft.clonedVoice = "";
                draft.latestAudioUrl = null;
              });
            }}
            selected={clonedVoice === ""}
            className="aspect-4/3 sm:aspect-2/1 min-h-[60px] max-h-[100px] flex-col items-start justify-between relative"
          >
            <span className="text-[11px] font-semibold">Default</span>
            <div className="absolute left-[0.93rem] bottom-[0.93rem]">
              <ButtonLED />
            </div>
          </Button>

          {/* Cloned voices */}
          {voices.map((v) => (
            <Button
              key={v.filename}
              block
              color="default"
              onClick={() => {
                appStore.setState((draft) => {
                  draft.clonedVoice = v.filename;
                  draft.latestAudioUrl = null;
                });
              }}
              selected={clonedVoice === v.filename}
              className="aspect-4/3 sm:aspect-2/1 min-h-[60px] max-h-[100px] flex-col items-start justify-between relative"
            >
              <span className="text-[11px] break-words pr-1">{v.name}</span>
              <div className="absolute left-[0.93rem] bottom-[0.93rem]">
                <ButtonLED />
              </div>
            </Button>
          ))}
        </div>

        {/* Clone upload section */}
        <div className="bg-screen p-4 rounded-lg shadow-textarea flex flex-col gap-2">
          <div className="text-[11px] uppercase opacity-60">Clone a new voice</div>
          <div className="flex flex-col sm:flex-row gap-2 items-stretch">
            <input
              type="text"
              placeholder="Voice name (e.g., harsh)"
              value={newVoiceName}
              onChange={(e) => {
                setNewVoiceName(e.target.value);
                if (error) setError("");
              }}
              disabled={uploading}
              className="flex-1 px-3 py-2 bg-white rounded-md outline-none text-[13px]"
            />
            <input
              type="file"
              ref={fileInputRef}
              accept="audio/wav,audio/mpeg,audio/mp4,audio/x-m4a,audio/*"
              onChange={(e) => {
                const file = e.target.files?.[0] ?? null;
                setSelectedFile(file);
                if (error) setError("");
              }}
              disabled={uploading}
              className="text-[12px] flex-1"
            />
            <button
              onClick={handleUpload}
              disabled={uploading || !newVoiceName.trim() || !selectedFile}
              className="px-6 py-2 bg-primary text-white rounded-md text-[12px] uppercase font-semibold disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer hover:opacity-90 transition-opacity"
            >
              {uploading ? "Cloning..." : "Clone"}
            </button>
          </div>
          <div className="text-[10px] opacity-50">
            Upload a 5-30 second audio clip (WAV, MP3, or M4A) of the voice you want to clone. Clean audio works best.
          </div>
          {error && <div className="text-[11px] text-red-500">{error}</div>}
        </div>
      </div>
    </Block>
  );
}
