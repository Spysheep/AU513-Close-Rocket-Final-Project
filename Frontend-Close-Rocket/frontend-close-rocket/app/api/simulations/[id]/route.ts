import type { NextRequest } from "next/server";

// Proxy endpoint: /api/simulations/[id]
// Forwards the request to the backend at http://localhost:8000/simulations?ids={id}
// The backend expects a query parameter, not a path parameter
export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // Build backend URL - backend uses query param "ids" not path param
  const backend = new URL("http://localhost:8000/simulations");
  backend.searchParams.set("ids", id);
  
  // Forward any additional query params from the original request
  const incoming = new URL(req.url);
  for (const [k, v] of incoming.searchParams.entries()) {
    if (k !== "id") backend.searchParams.set(k, v);
  }

  try {
    const res = await fetch(backend.toString(), {
      headers: { Accept: "application/json" },
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
    
    // Backend returns { count, simulations: [...] }
    // Extract the first simulation and format for frontend
    if (data.simulations && data.simulations.length > 0) {
      const sim = data.simulations[0];
      return Response.json({
        id: sim.rocket_id,
        trajectory: sim.trajectory.map((point: { time: number; x: number; y: number; z: number }) => ({
          t: point.time,
          x: point.x,
          y: point.y,
          z: point.z,
        })),
        parameters: sim.rocket_parameters,
        metadata: sim.metadata,
      });
    }
    
    return Response.json(
      { error: "No simulation found", id },
      { status: 404 }
    );
  } catch (err: unknown) {
    return Response.json(
      { error: "Unable to reach backend at http://localhost:8000", details: String(err) },
      { status: 502 }
    );
  }
}
