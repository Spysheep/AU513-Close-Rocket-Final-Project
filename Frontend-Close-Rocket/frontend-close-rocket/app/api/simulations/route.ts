import type { NextRequest } from "next/server";

// Proxy endpoint: /api/simulations/[id]
// Forwards the request to the backend at http://localhost:8000/simulations/%7Bid%7D
// Keeps any query parameters and returns the backend JSON as-is.
export async function GET(req: NextRequest, context: { params: { id: string } }) {
  const { id } = context.params;

  // Build backend URL and forward any query params from the original request
  const incoming = new URL(req.url);
  const backend = new URL('http://localhost:8000/simulations/${encodeURIComponent(id)}');
  for (const [k, v] of incoming.searchParams.entries()) backend.searchParams.set(k, v);

  try {
    const res = await fetch(backend.toString(), {
      // Forward GET only; add headers as needed
      headers: { Accept: "application/json" },
      // You can set cache: "no-store" to always hit backend
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      return Response.json(
        { error: "Backend /simulations call failed", status: res.status, details: text },
        { status: res.status }
      );
    }

    const data = await res.json();
    return Response.json(data);
  } catch (err: unknown) {
    return Response.json(
      { error: "Unable to reach backend at http://localhost:8000/", details: String(err) },
      { status: 502 }
    );
  }
}