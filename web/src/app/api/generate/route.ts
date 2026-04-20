import { NextRequest } from "next/server";

const MAX_INPUT_LENGTH = 1000;

// Engine configs
const ENGINES: Record<string, { url: string; buildBody: (input: string, voice: string, speed: string, clonePath: string) => string }> = {
  kokoro: {
    url: "http://localhost:3001/api/generate",
    buildBody: (input, voice, speed) =>
      JSON.stringify({ text: input, voice, speed: parseFloat(speed) }),
  },
  chatterbox: {
    url: "http://localhost:3002/api/generate",
    buildBody: (input, _voice, _speed, clonePath) =>
      JSON.stringify({ text: input, voice_clone_path: clonePath || "" }),
  },
};

async function handleGenerate(
  input: string,
  voice: string,
  speed: string,
  vibe: string,
  engine: string,
  clonePath: string
) {
  input = input.slice(0, MAX_INPUT_LENGTH);
  const eng = ENGINES[engine] || ENGINES.kokoro;

  try {
    const apiResponse = await fetch(eng.url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: eng.buildBody(input, voice, speed, clonePath),
    });

    if (!apiResponse.ok) {
      const errText = await apiResponse.text().catch(() => "Unknown error");
      return new Response(`Error generating audio: ${errText}`, {
        status: apiResponse.status,
      });
    }

    const filename = `agent-fm-${engine}-${voice || "default"}-${vibe}.wav`;
    return new Response(apiResponse.body, {
      headers: {
        "Content-Type": "audio/wav",
        "Content-Disposition": `inline; filename="${filename}"`,
        "Cache-Control": "no-cache",
        "X-Engine": engine,
      },
    });
  } catch (err) {
    console.error(`Error generating speech (${engine}):`, err);
    return new Response(
      `Error generating speech. Make sure the ${engine} TTS server is running.`,
      { status: 500 }
    );
  }
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  return handleGenerate(
    searchParams.get("input") || "",
    searchParams.get("voice") || "",
    searchParams.get("speed") || "1.0",
    searchParams.get("vibe") || "audio",
    searchParams.get("engine") || "kokoro",
    searchParams.get("clone_path") || ""
  );
}

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  return handleGenerate(
    formData.get("input")?.toString() || "",
    formData.get("voice")?.toString() || "",
    formData.get("speed")?.toString() || "1.0",
    formData.get("vibe")?.toString() || "audio",
    formData.get("engine")?.toString() || "kokoro",
    formData.get("clone_path")?.toString() || ""
  );
}
