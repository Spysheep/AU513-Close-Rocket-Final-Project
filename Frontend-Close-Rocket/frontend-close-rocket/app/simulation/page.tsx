"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface TrajectoryPoint {
  t: number;
  x: number;
  y: number;
  z: number;
}

interface TrajectoryData {
  trajectory: TrajectoryPoint[];
  parameters?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

interface SimulationResponse {
  id: string;
  source: string;
  trajectory?: TrajectoryPoint[];
  parameters?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  ml?: TrajectoryData;
  rocketpy?: TrajectoryData;
  error?: string;
}

type ViewMode = "ml" | "comparison";

export default function SimulationPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("id") || "rocket_0001";

  const [loading, setLoading] = useState(true);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("ml");
  
  // Data states
  const [mlData, setMlData] = useState<TrajectoryPoint[]>([]);
  const [rocketpyData, setRocketpyData] = useState<TrajectoryPoint[]>([]);
  const [simInfo, setSimInfo] = useState<{ id: string } | null>(null);

  // Génère une trajectoire de démonstration
  function generateDemoTrajectory(variation = 1): TrajectoryPoint[] {
    const points: TrajectoryPoint[] = [];
    for (let t = 0; t <= 60; t += 0.5) {
      const vz0 = 100 * variation;
      const g = 9.81;
      const burnTime = 10;
      
      let z: number;
      const vx = 5 * variation;
      
      if (t <= burnTime) {
        z = vz0 * t + 0.5 * 20 * t * t;
      } else {
        const zAtBurnout = vz0 * burnTime + 0.5 * 20 * burnTime * burnTime;
        const vzAtBurnout = vz0 + 20 * burnTime;
        const dt = t - burnTime;
        z = zAtBurnout + vzAtBurnout * dt - 0.5 * g * dt * dt;
      }
      
      if (z < 0) z = 0;
      
      points.push({
        t: Math.round(t * 10) / 10,
        x: Math.round(vx * t * 10) / 10,
        y: Math.round(Math.sin(t * 0.1) * 10 * variation * 10) / 10,
        z: Math.round(z * 10) / 10,
      });
      
      if (z <= 0 && t > burnTime) break;
    }
    return points;
  }

  // Fetch simulation data on mount
  // First try to load whatever is available (rocketpy by default for existing simulations)
  useEffect(() => {
    const fetchSimulation = async () => {
      setLoading(true);
      setError(null);

      try {
        // First, try to fetch both sources to see what's available
        const res = await fetch(`/api/simulations/${encodeURIComponent(simulationId)}?source=both`);
        
        if (!res.ok) {
          // If 'both' fails, try rocketpy only (for older simulations)
          const fallbackRes = await fetch(`/api/simulations/${encodeURIComponent(simulationId)}?source=rocketpy`);
          
          if (!fallbackRes.ok) {
            const errData = await fallbackRes.json().catch(() => ({ error: "Erreur inconnue" }));
            throw new Error(errData.error || errData.details || `Erreur ${fallbackRes.status}`);
          }
          
          const fallbackResult: SimulationResponse = await fallbackRes.json();
          setSimInfo({ id: fallbackResult.id });
          
          // Handle trajectory data
          const trajectory = fallbackResult.trajectory || [];
          setRocketpyData(trajectory);
          setMlData(trajectory); // Show same data in ML section for older simulations
          setViewMode("ml");
          return;
        }

        const result: SimulationResponse = await res.json();
        console.log("Simulation result:", result); // Debug log
        
        if (result.error) {
          throw new Error(result.error);
        }

        setSimInfo({ id: result.id });
        
        // Check what data is available - handle all cases
        const mlTrajectory = result.ml?.trajectory || [];
        const rocketpyTrajectory = result.rocketpy?.trajectory || [];
        const directTrajectory = result.trajectory || [];
        
        if (mlTrajectory.length > 0 && rocketpyTrajectory.length > 0) {
          // Both available - load both and show ML first
          setMlData(mlTrajectory);
          setRocketpyData(rocketpyTrajectory);
          setViewMode("ml");
        } else if (mlTrajectory.length > 0) {
          // Only ML available
          setMlData(mlTrajectory);
          setViewMode("ml");
        } else if (rocketpyTrajectory.length > 0) {
          // Only RocketPy available (older simulations)
          setRocketpyData(rocketpyTrajectory);
          setMlData(rocketpyTrajectory); // Show rocketpy data in ML section
          setViewMode("ml");
        } else if (directTrajectory.length > 0) {
          // Single source response (trajectory at root level)
          setMlData(directTrajectory);
          setViewMode("ml");
        } else {
          throw new Error("Aucune donnée de trajectoire trouvée");
        }
      } catch (err) {
        console.error("Fetch error:", err); // Debug log
        setError(err instanceof Error ? err.message : "Erreur lors du chargement de la simulation");
        // Données de démo en cas d'erreur
        setMlData(generateDemoTrajectory());
        setSimInfo({ id: simulationId + " (démo)" });
      } finally {
        setLoading(false);
      }
    };

    fetchSimulation();
  }, [simulationId]);

  // Fetch comparison data (both ML and RocketPy)
  const fetchComparison = useCallback(async () => {
    setLoadingComparison(true);
    
    try {
      const res = await fetch(`/api/simulations/${encodeURIComponent(simulationId)}?source=both`);
      
      if (!res.ok) {
        const errData = await res.json().catch(() => ({ error: "Erreur inconnue" }));
        throw new Error(errData.error || errData.details || `Erreur ${res.status}`);
      }

      const result: SimulationResponse = await res.json();
      
      if (result.ml && result.rocketpy) {
        setMlData(result.ml.trajectory);
        setRocketpyData(result.rocketpy.trajectory);
        setViewMode("comparison");
      } else {
        throw new Error("Données de comparaison incomplètes");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement de la comparaison");
      // Données de démo pour RocketPy
      setRocketpyData(generateDemoTrajectory(1.1)); // Légère variation
      setViewMode("comparison");
    } finally {
      setLoadingComparison(false);
    }
  }, [simulationId]);

  // Calculate stats from trajectory
  function getStats(data: TrajectoryPoint[]) {
    if (data.length === 0) return { maxAlt: 0, maxDist: 0, duration: 0, points: 0 };
    return {
      maxAlt: Math.max(...data.map((p) => p.z)),
      maxDist: Math.max(...data.map((p) => Math.sqrt(p.x * p.x + p.y * p.y))),
      duration: data[data.length - 1]?.t || 0,
      points: data.length,
    };
  }

  // Subsample data for chart performance (max ~1000 points)
  function subsampleForChart(data: TrajectoryPoint[], maxPoints = 1000): TrajectoryPoint[] {
    if (data.length <= maxPoints) return data;
    const step = Math.ceil(data.length / maxPoints);
    const sampled: TrajectoryPoint[] = [];
    for (let i = 0; i < data.length; i += step) {
      sampled.push(data[i]);
    }
    // Always include the last point
    if (sampled[sampled.length - 1] !== data[data.length - 1]) {
      sampled.push(data[data.length - 1]);
    }
    return sampled;
  }

  // Merge data for comparison charts (X, Y, Z for both ML and RocketPy)
  function mergeDataForComparison(): Array<{
    t: number; 
    ml_x: number; ml_y: number; ml_z: number; 
    rocketpy_x: number; rocketpy_y: number; rocketpy_z: number;
  }> {
    const mlSampled = subsampleForChart(mlData);
    const rpSampled = subsampleForChart(rocketpyData);
    const maxLen = Math.max(mlSampled.length, rpSampled.length);
    
    const merged: Array<{
      t: number; 
      ml_x: number; ml_y: number; ml_z: number; 
      rocketpy_x: number; rocketpy_y: number; rocketpy_z: number;
    }> = [];
    
    for (let i = 0; i < maxLen; i++) {
      const mlPoint = mlSampled[i] || { t: 0, x: 0, y: 0, z: 0 };
      const rpPoint = rpSampled[i] || { t: 0, x: 0, y: 0, z: 0 };
      merged.push({
        t: mlPoint.t || rpPoint.t,
        ml_x: mlPoint.x,
        ml_y: mlPoint.y,
        ml_z: mlPoint.z,
        rocketpy_x: rpPoint.x,
        rocketpy_y: rpPoint.y,
        rocketpy_z: rpPoint.z,
      });
    }
    return merged;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mb-4"></div>
          <p className="text-xl text-zinc-700 dark:text-zinc-300">Chargement de la prédiction ML...</p>
          <p className="text-sm text-zinc-500 mt-2">ID: {simulationId}</p>
        </div>
      </div>
    );
  }

  const mlStats = getStats(mlData);
  const rpStats = getStats(rocketpyData);
  
  // Subsample data for chart performance
  const mlDataChart = subsampleForChart(mlData);
  const rocketpyDataChart = subsampleForChart(rocketpyData);
  const comparisonData = viewMode === "comparison" ? mergeDataForComparison() : [];

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black py-10">
      <main className="mx-auto w-full max-w-7xl rounded-xl bg-white dark:bg-zinc-900 p-8 shadow">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-black dark:text-white">
              Résultats de Simulation
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              ID: {simInfo?.id || simulationId}
            </p>
          </div>
          <div className="flex gap-3">
            {viewMode === "ml" && (
              <button
                onClick={fetchComparison}
                disabled={loadingComparison}
                className="px-4 py-2 rounded-md bg-green-600 hover:bg-green-700 text-white disabled:bg-zinc-400 flex items-center gap-2"
              >
                {loadingComparison ? (
                  <>
                    <span className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></span>
                    Chargement...
                  </>
                ) : (
                  "🔬 Comparer avec RocketPy"
                )}
              </button>
            )}
            {viewMode === "comparison" && (
              <button
                onClick={() => setViewMode("ml")}
                className="px-4 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
              >
                ← Retour à ML seul
              </button>
            )}
            <Link
              href="/"
              className="px-4 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
            >
              🏠 Nouvelle simulation
            </Link>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 rounded-md border border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200">
            <p className="font-medium">⚠️ Mode démonstration</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        {/* ==================== ML PREDICTION SECTION ==================== */}
        <section className="mb-10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-4 h-4 rounded-full bg-blue-500"></div>
            <h2 className="text-xl font-semibold text-black dark:text-white">
              🤖 Prédiction ML
            </h2>
          </div>

          {/* Stats ML */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label="Altitude max" value={`${mlStats.maxAlt.toFixed(1)} m`} color="blue" />
            <StatCard label="Distance max" value={`${mlStats.maxDist.toFixed(1)} m`} color="blue" />
            <StatCard label="Durée vol" value={`${mlStats.duration.toFixed(1)} s`} color="blue" />
            <StatCard label="Points" value={`${mlStats.points}`} color="blue" />
          </div>

          {/* Graphiques ML - X, Y, Z en fonction du temps */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* X vs T */}
            <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
              <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position X vs Temps</h3>
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={mlDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis 
                    dataKey="t" 
                    type="number"
                    domain={[0, 200]} 
                    ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                    label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                    stroke="#888" 
                  />
                  <YAxis label={{ value: "X (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                  <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                  <Line type="monotone" dataKey="x" stroke="#3b82f6" strokeWidth={2} dot={false} name="X" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Y vs T */}
            <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
              <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position Y vs Temps</h3>
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={mlDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis 
                    dataKey="t" 
                    type="number"
                    domain={[0, 200]} 
                    ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                    label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                    stroke="#888" 
                  />
                  <YAxis label={{ value: "Y (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                  <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                  <Line type="monotone" dataKey="y" stroke="#10b981" strokeWidth={2} dot={false} name="Y" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Z vs T */}
            <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
              <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Altitude Z vs Temps</h3>
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={mlDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis 
                    dataKey="t" 
                    type="number"
                    domain={[0, 200]} 
                    ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                    label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                    stroke="#888" 
                  />
                  <YAxis label={{ value: "Z (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                  <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                  <Line type="monotone" dataKey="z" stroke="#f59e0b" strokeWidth={2} dot={false} name="Z" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Google Earth placeholder */}
          <div className="mt-6 bg-zinc-100 dark:bg-zinc-800 rounded-lg p-8 text-center border-2 border-dashed border-zinc-300 dark:border-zinc-600">
            <p className="text-zinc-500 dark:text-zinc-400 text-lg">🌍 Vue 3D Google Earth</p>
            <p className="text-sm text-zinc-400 mt-2">Configuration de l&apos;API Google Earth requise</p>
          </div>
        </section>

        {/* ==================== ROCKETPY SECTION (si comparison) ==================== */}
        {viewMode === "comparison" && rocketpyData.length > 0 && (
          <>
            <section className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-4 h-4 rounded-full bg-orange-500"></div>
                <h2 className="text-xl font-semibold text-black dark:text-white">
                  🚀 Simulation RocketPy
                </h2>
              </div>

              {/* Stats RocketPy */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <StatCard label="Altitude max" value={`${rpStats.maxAlt.toFixed(1)} m`} color="orange" />
                <StatCard label="Distance max" value={`${rpStats.maxDist.toFixed(1)} m`} color="orange" />
                <StatCard label="Durée vol" value={`${rpStats.duration.toFixed(1)} s`} color="orange" />
                <StatCard label="Points" value={`${rpStats.points}`} color="orange" />
              </div>

              {/* Graphiques RocketPy - X, Y, Z en fonction du temps */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* X vs T */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position X vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={rocketpyDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "X (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Line type="monotone" dataKey="x" stroke="#f97316" strokeWidth={2} dot={false} name="X" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Y vs T */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position Y vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={rocketpyDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "Y (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Line type="monotone" dataKey="y" stroke="#22c55e" strokeWidth={2} dot={false} name="Y" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Z vs T */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 300 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Altitude Z vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={rocketpyDataChart} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "Z (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Line type="monotone" dataKey="z" stroke="#ef4444" strokeWidth={2} dot={false} name="Z" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Google Earth placeholder */}
              <div className="mt-6 bg-zinc-100 dark:bg-zinc-800 rounded-lg p-8 text-center border-2 border-dashed border-zinc-300 dark:border-zinc-600">
                <p className="text-zinc-500 dark:text-zinc-400 text-lg">🌍 Vue 3D Google Earth</p>
                <p className="text-sm text-zinc-400 mt-2">Configuration de l&apos;API Google Earth requise</p>
              </div>
            </section>

            {/* ==================== COMPARISON SECTION ==================== */}
            <section className="mb-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-4 h-4 rounded-full bg-gradient-to-r from-blue-500 to-orange-500"></div>
                <h2 className="text-xl font-semibold text-black dark:text-white">
                  📊 Comparaison ML vs RocketPy
                </h2>
              </div>

              {/* Difference stats */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <StatCard 
                  label="Δ Altitude max" 
                  value={`${Math.abs(mlStats.maxAlt - rpStats.maxAlt).toFixed(1)} m`} 
                  color="purple" 
                />
                <StatCard 
                  label="Δ Durée" 
                  value={`${Math.abs(mlStats.duration - rpStats.duration).toFixed(2)} s`} 
                  color="purple" 
                />
                <StatCard 
                  label="Erreur relative altitude" 
                  value={`${rpStats.maxAlt > 0 ? (Math.abs(mlStats.maxAlt - rpStats.maxAlt) / rpStats.maxAlt * 100).toFixed(2) : 0} %`} 
                  color="purple" 
                />
              </div>

              {/* Graphiques de comparaison - X, Y, Z avec ML et RocketPy superposés */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* X vs T Comparison */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position X vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={comparisonData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "X (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Legend />
                      <Line type="monotone" dataKey="ml_x" stroke="#3b82f6" strokeWidth={2} dot={false} name="ML" />
                      <Line type="monotone" dataKey="rocketpy_x" stroke="#f97316" strokeWidth={2} dot={false} name="RocketPy" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Y vs T Comparison */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Position Y vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={comparisonData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "Y (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Legend />
                      <Line type="monotone" dataKey="ml_y" stroke="#3b82f6" strokeWidth={2} dot={false} name="ML" />
                      <Line type="monotone" dataKey="rocketpy_y" stroke="#f97316" strokeWidth={2} dot={false} name="RocketPy" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Z vs T Comparison */}
                <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
                  <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">Altitude Z vs Temps</h3>
                  <ResponsiveContainer width="100%" height="90%">
                    <LineChart data={comparisonData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                      <XAxis 
                        dataKey="t" 
                        type="number"
                        domain={[0, 200]} 
                        ticks={[0, 25, 50, 75, 100, 125, 150, 175, 200]}
                        label={{ value: "t (s)", position: "bottom", offset: 0 }} 
                        stroke="#888" 
                      />
                      <YAxis label={{ value: "Z (m)", angle: -90, position: "insideLeft" }} stroke="#888" />
                      <Tooltip contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }} />
                      <Legend />
                      <Line type="monotone" dataKey="ml_z" stroke="#3b82f6" strokeWidth={2} dot={false} name="ML" />
                      <Line type="monotone" dataKey="rocketpy_z" stroke="#f97316" strokeWidth={2} dot={false} name="RocketPy" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Google Earth comparison placeholder */}
              <div className="mt-6 bg-zinc-100 dark:bg-zinc-800 rounded-lg p-8 text-center border-2 border-dashed border-zinc-300 dark:border-zinc-600">
                <p className="text-zinc-500 dark:text-zinc-400 text-lg">🌍 Vue 3D Google Earth - Comparaison</p>
                <p className="text-sm text-zinc-400 mt-2">Trajectoires superposées (configuration API requise)</p>
              </div>
            </section>
          </>
        )}

        {/* Tableau de données brutes */}
        <section>
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            📋 Données brutes (premiers 15 points)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-zinc-100 dark:bg-zinc-800">
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">t (s)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">X (m)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">Y (m)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">Z (m)</th>
                  {viewMode === "comparison" && (
                    <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left bg-orange-100 dark:bg-orange-900/30">Z RocketPy (m)</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {mlData.slice(0, 15).map((point, i) => (
                  <tr key={i} className="hover:bg-zinc-50 dark:hover:bg-zinc-800">
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.t.toFixed(2)}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.x.toFixed(2)}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.y.toFixed(2)}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.z.toFixed(2)}</td>
                    {viewMode === "comparison" && rocketpyData[i] && (
                      <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1 bg-orange-50 dark:bg-orange-900/20">
                        {rocketpyData[i].z.toFixed(2)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {mlData.length > 15 && (
              <p className="text-sm text-zinc-500 mt-2">... et {mlData.length - 15} points supplémentaires</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value, color = "blue" }: { label: string; value: string; color?: "blue" | "orange" | "purple" }) {
  const colorClasses = {
    blue: "border-l-blue-500",
    orange: "border-l-orange-500",
    purple: "border-l-purple-500",
  };
  
  return (
    <div className={`bg-zinc-100 dark:bg-zinc-800 rounded-lg p-4 border-l-4 ${colorClasses[color]}`}>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="text-xl font-bold text-black dark:text-white mt-1">{value}</p>
    </div>
  );
}
