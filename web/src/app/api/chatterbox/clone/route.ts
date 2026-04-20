import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const res = await fetch("http://localhost:3002/api/clone", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch {
    return new Response("Chatterbox server offline on port 3002", { status: 503 });
  }
}
