import type { NextRequest } from "next/server";

interface TrajectoryPoint {
  time: number;
  x: number;
  y: number;
  z: number;
  wind_velocity_x?: number;
  wind_velocity_y?: number;
}

interface SimulationData {
  rocket_parameters: Record<string, unknown>;
  trajectory: TrajectoryPoint[];
  metadata: Record<string, unknown>;
}

interface BackendSimulation {
  rocket_id: string;
  rocket_parameters?: Record<string, unknown>;
  trajectory?: TrajectoryPoint[];
  metadata?: Record<string, unknown>;
  rocketpy?: SimulationData;
  ml?: SimulationData;
}

function formatTrajectory(trajectory: TrajectoryPoint[]) {
  return trajectory.map((point) => ({
    t: point.time,
    x: point.x,
    y: point.y,
    z: point.z,
  }));
}

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
  const source = incoming.searchParams.get("source") || "rocketpy";
  backend.searchParams.set("source", source);

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
      const sim: BackendSimulation = data.simulations[0];
      
      // Handle source='both' - return both ML and RocketPy data if available
      if (source === "both") {
        const result: Record<string, unknown> = {
          id: sim.rocket_id,
          source: "both",
        };
        
        if (sim.rocketpy && sim.rocketpy.trajectory) {
          result.rocketpy = {
            trajectory: formatTrajectory(sim.rocketpy.trajectory),
            parameters: sim.rocketpy.rocket_parameters,
            metadata: sim.rocketpy.metadata,
          };
        }
        
        if (sim.ml && sim.ml.trajectory) {
          result.ml = {
            trajectory: formatTrajectory(sim.ml.trajectory),
            parameters: sim.ml.rocket_parameters,
            metadata: sim.ml.metadata,
          };
        }
        
        // If at least one source has data, return it
        if (result.rocketpy || result.ml) {
          return Response.json(result);
        }
      }
      
      // Handle single source (ml or rocketpy) - data at root level
      if (sim.trajectory) {
        return Response.json({
          id: sim.rocket_id,
          source: source,
          trajectory: formatTrajectory(sim.trajectory),
          parameters: sim.rocket_parameters,
          metadata: sim.metadata,
        });
      }
      
      // Fallback for nested data structure (when source=rocketpy but data is nested)
      if (sim.rocketpy && sim.rocketpy.trajectory) {
        return Response.json({
          id: sim.rocket_id,
          source: "rocketpy",
          trajectory: formatTrajectory(sim.rocketpy.trajectory),
          parameters: sim.rocketpy.rocket_parameters,
          metadata: sim.rocketpy.metadata,
        });
      }
      
      if (sim.ml && sim.ml.trajectory) {
        return Response.json({
          id: sim.rocket_id,
          source: "ml",
          trajectory: formatTrajectory(sim.ml.trajectory),
          parameters: sim.ml.rocket_parameters,
          metadata: sim.ml.metadata,
        });
      }
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
