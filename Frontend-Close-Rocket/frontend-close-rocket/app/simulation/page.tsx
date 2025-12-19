"use client";

import { useEffect, useState } from "react";
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

interface SimulationResponse {
  id: string;
  trajectory: TrajectoryPoint[];
  error?: string;
}

export default function SimulationPage() {
  const searchParams = useSearchParams();
  const simulationId = searchParams.get("id") || "rocket_0001";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TrajectoryPoint[]>([]);
  const [simInfo, setSimInfo] = useState<{ id: string } | null>(null);

  useEffect(() => {
    const fetchSimulation = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`/api/simulations/${encodeURIComponent(simulationId)}`);
        
        if (!res.ok) {
          const errData = await res.json().catch(() => ({ error: "Erreur inconnue" }));
          throw new Error(errData.error || errData.details || `Erreur ${res.status}`);
        }

        const result: SimulationResponse = await res.json();
        
        if (result.error) {
          throw new Error(result.error);
        }

        setSimInfo({ id: result.id });
        setData(result.trajectory || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur lors du chargement de la simulation");
        // Données de démo en cas d'erreur pour tester l'affichage
        setData(generateDemoTrajectory());
        setSimInfo({ id: simulationId + " (démo)" });
      } finally {
        setLoading(false);
      }
    };

    fetchSimulation();
  }, [simulationId]);

  // Génère une trajectoire de démonstration
  function generateDemoTrajectory(): TrajectoryPoint[] {
    const points: TrajectoryPoint[] = [];
    for (let t = 0; t <= 60; t += 0.5) {
      // Simulation simplifiée d'une trajectoire de fusée
      const vz0 = 100; // vitesse initiale verticale m/s
      const g = 9.81;
      const burnTime = 10; // secondes de poussée
      
      let z: number;
      const vx = 5; // légère dérive horizontale
      
      if (t <= burnTime) {
        // Phase propulsée
        z = vz0 * t + 0.5 * 20 * t * t; // accélération de 20 m/s²
      } else {
        // Phase balistique
        const zAtBurnout = vz0 * burnTime + 0.5 * 20 * burnTime * burnTime;
        const vzAtBurnout = vz0 + 20 * burnTime;
        const dt = t - burnTime;
        z = zAtBurnout + vzAtBurnout * dt - 0.5 * g * dt * dt;
      }
      
      if (z < 0) z = 0;
      
      points.push({
        t: Math.round(t * 10) / 10,
        x: Math.round(vx * t * 10) / 10,
        y: Math.round(Math.sin(t * 0.1) * 10 * 10) / 10, // légère oscillation
        z: Math.round(z * 10) / 10,
      });
      
      if (z <= 0 && t > burnTime) break;
    }
    return points;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mb-4"></div>
          <p className="text-xl text-zinc-700 dark:text-zinc-300">Chargement de la simulation...</p>
          <p className="text-sm text-zinc-500 mt-2">ID: {simulationId}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black py-10">
      <main className="mx-auto w-full max-w-6xl rounded-xl bg-white dark:bg-zinc-900 p-8 shadow">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-black dark:text-white">
              Simulation de trajectoire
            </h1>
            <p className="text-sm text-zinc-500 mt-1">
              ID: {simInfo?.id || simulationId}
            </p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
          >
            ← Retour aux paramètres
          </Link>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 rounded-md border border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200">
            <p className="font-medium">⚠️ Mode démonstration</p>
            <p className="text-sm mt-1">{error}</p>
            <p className="text-sm mt-1">Affichage d&apos;une trajectoire simulée pour démonstration.</p>
          </div>
        )}

        {/* Stats summary */}
        {data.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Altitude max"
              value={`${Math.max(...data.map((p) => p.z)).toFixed(1)} m`}
            />
            <StatCard
              label="Distance X"
              value={`${Math.max(...data.map((p) => p.x)).toFixed(1)} m`}
            />
            <StatCard
              label="Durée vol"
              value={`${data[data.length - 1]?.t.toFixed(1) || 0} s`}
            />
            <StatCard
              label="Points"
              value={`${data.length}`}
            />
          </div>
        )}

        {/* Graphique Altitude vs Temps */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Altitude (Z) en fonction du temps
          </h2>
          <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="t"
                  label={{ value: "Temps (s)", position: "bottom", offset: 0 }}
                  stroke="#888"
                />
                <YAxis
                  label={{ value: "Altitude (m)", angle: -90, position: "insideLeft" }}
                  stroke="#888"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }}
                  labelStyle={{ color: "#fff" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="z"
                  name="Altitude Z"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Graphique Trajectoire XZ */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Trajectoire (X vs Z)
          </h2>
          <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="x"
                  label={{ value: "Distance X (m)", position: "bottom", offset: 0 }}
                  stroke="#888"
                />
                <YAxis
                  dataKey="z"
                  label={{ value: "Altitude Z (m)", angle: -90, position: "insideLeft" }}
                  stroke="#888"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }}
                  labelStyle={{ color: "#fff" }}
                />
                <Line
                  type="monotone"
                  dataKey="z"
                  name="Trajectoire"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Graphique toutes coordonnées */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Toutes les coordonnées (X, Y, Z) vs Temps
          </h2>
          <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="t"
                  label={{ value: "Temps (s)", position: "bottom", offset: 0 }}
                  stroke="#888"
                />
                <YAxis
                  label={{ value: "Position (m)", angle: -90, position: "insideLeft" }}
                  stroke="#888"
                />
                <Tooltip
                  contentStyle={{ backgroundColor: "#1f1f1f", border: "1px solid #333" }}
                  labelStyle={{ color: "#fff" }}
                />
                <Legend />
                <Line type="monotone" dataKey="x" name="X" stroke="#ef4444" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="y" name="Y" stroke="#f59e0b" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="z" name="Z" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Tableau de données */}
        <section>
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Données brutes (premiers 20 points)
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-zinc-100 dark:bg-zinc-800">
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">t (s)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">X (m)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">Y (m)</th>
                  <th className="border border-zinc-300 dark:border-zinc-700 px-3 py-2 text-left">Z (m)</th>
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 20).map((point, i) => (
                  <tr key={i} className="hover:bg-zinc-50 dark:hover:bg-zinc-800">
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.t}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.x}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.y}</td>
                    <td className="border border-zinc-300 dark:border-zinc-700 px-3 py-1">{point.z}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length > 20 && (
              <p className="text-sm text-zinc-500 mt-2">... et {data.length - 20} points supplémentaires</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-100 dark:bg-zinc-800 rounded-lg p-4 text-center">
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="text-xl font-bold text-black dark:text-white mt-1">{value}</p>
    </div>
  );
}
