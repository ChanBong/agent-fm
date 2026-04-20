export async function GET() {
  try {
    const res = await fetch("http://localhost:3002/api/health");
    if (!res.ok) {
      return new Response("Chatterbox server error", { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch {
    return new Response("Chatterbox server offline on port 3002", { status: 503 });
  }
}
