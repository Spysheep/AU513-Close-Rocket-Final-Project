"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
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

interface SimulationData {
  trajectory: TrajectoryPoint[];
  parameters?: any;
  metadata?: any;
}

interface SimulationResponse {
  id: string;
  source: string;
  trajectory?: TrajectoryPoint[];
  parameters?: any;
  metadata?: any;
  rocketpy?: SimulationData;
  ml?: SimulationData;
  error?: string;
}

// Fonction pour convertir XY (mètres) en lat/lon (degrés)
// Approximation: 1 degré ≈ 111 km à l'équateur
function convertXYToLatLon(x: number, y: number, originLat: number, originLon: number): { lat: number; lon: number } {
  const metersPerDegree = 111000; // approximation
  const lat = originLat + (y / metersPerDegree);
  const lon = originLon + (x / (metersPerDegree * Math.cos(originLat * Math.PI / 180)));
  return { lat, lon };
}

// Génère un fichier KML pour Google Earth
function generateKML(trajectory: TrajectoryPoint[], name: string, originLat: number = 45.0, originLon: number = 5.0): string {
  const coordinates = trajectory
    .map((p) => {
      const { lat, lon } = convertXYToLatLon(p.x, p.y, originLat, originLon);
      return `${lon},${lat},${p.z}`;
    })
    .join("\n            ");

  return `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${name}</name>
    <Style id="trajectory">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
    </Style>
    <Placemark>
      <name>Trajectoire ${name}</name>
      <styleUrl>#trajectory</styleUrl>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>
            ${coordinates}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>`;
}

// Télécharge un fichier KML
function downloadKML(trajectory: TrajectoryPoint[], filename: string) {
  const kmlContent = generateKML(trajectory, filename);
  const blob = new Blob([kmlContent], { type: "application/vnd.google-earth.kml+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.kml`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function SimulationPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const simulationId = searchParams.get("id") || "rocket_0001";
  const source = searchParams.get("source") || "ml";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SimulationResponse | null>(null);

  useEffect(() => {
    const fetchSimulation = async () => {
      setLoading(true);
      setError(null);

      try {
        const res = await fetch(`/api/simulations/${encodeURIComponent(simulationId)}?source=${source}`);

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ error: "Erreur inconnue" }));
          throw new Error(errData.error || errData.details || `Erreur ${res.status}`);
        }

        const result: SimulationResponse = await res.json();

        if (result.error) {
          throw new Error(result.error);
        }

        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur lors du chargement de la simulation");
        // Ne pas charger de données de démo - laisser data à null pour afficher l'erreur
      } finally {
        setLoading(false);
      }
    };

    fetchSimulation();
  }, [simulationId, source]);

  const handleCompareWithRocketPy = () => {
    router.push(`/simulations?id=${encodeURIComponent(simulationId)}&source=both`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mb-4"></div>
          <p className="text-xl text-zinc-700 dark:text-zinc-300">Chargement de la simulation...</p>
          <p className="text-sm text-zinc-500 mt-2">ID: {simulationId}</p>
          <p className="text-sm text-zinc-500">Source: {source}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black py-10">
        <main className="mx-auto w-full max-w-6xl rounded-xl bg-white dark:bg-zinc-900 p-8 shadow">
          <div className="mb-6 p-4 rounded-md border border-red-300 bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200">
            <p className="font-medium">❌ Erreur</p>
            <p className="text-sm mt-1">{error || "Données introuvables"}</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
          >
            ← Retour aux paramètres
          </Link>
        </main>
      </div>
    );
  }

  const isBothMode = data.source === "both" && data.rocketpy && data.ml;
  const mlData = isBothMode ? data.ml!.trajectory : (data.trajectory || []);
  const rocketpyData = isBothMode ? data.rocketpy!.trajectory : [];

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
              ID: {data.id}
            </p>
            <p className="text-sm text-zinc-500">
              Source: {isBothMode ? "ML + RocketPy (Comparaison)" : data.source === "ml" ? "ML Prediction" : "RocketPy Simulation"}
            </p>
          </div>
          <div className="flex gap-3 flex-wrap">
            {source === "ml" && (
              <button
                onClick={handleCompareWithRocketPy}
                className="px-4 py-2 rounded-md bg-green-600 hover:bg-green-700 text-white"
              >
                Comparer avec RocketPy
              </button>
            )}
            {!isBothMode && mlData.length > 0 && (
              <button
                onClick={() => downloadKML(mlData, `${data.id}_${data.source}`)}
                className="px-4 py-2 rounded-md bg-purple-600 hover:bg-purple-700 text-white"
              >
                📥 Télécharger KML
              </button>
            )}
            {isBothMode && mlData.length > 0 && rocketpyData.length > 0 && (
              <>
                <button
                  onClick={() => downloadKML(mlData, `${data.id}_ML`)}
                  className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white"
                >
                  📥 KML (ML)
                </button>
                <button
                  onClick={() => downloadKML(rocketpyData, `${data.id}_RocketPy`)}
                  className="px-4 py-2 rounded-md bg-red-600 hover:bg-red-700 text-white"
                >
                  📥 KML (RocketPy)
                </button>
              </>
            )}
            <Link
              href="/"
              className="px-4 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
            >
              ← Retour aux paramètres
            </Link>
          </div>
        </div>

        {/* Stats summary */}
        {mlData.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              label={isBothMode ? "Altitude max (ML)" : "Altitude max"}
              value={`${Math.max(...mlData.map((p) => p.z)).toFixed(1)} m`}
            />
            {isBothMode && rocketpyData.length > 0 && (
              <StatCard
                label="Altitude max (RocketPy)"
                value={`${Math.max(...rocketpyData.map((p) => p.z)).toFixed(1)} m`}
              />
            )}
            <StatCard
              label={isBothMode ? "Durée vol (ML)" : "Durée vol"}
              value={`${mlData[mlData.length - 1]?.t.toFixed(1) || 0} s`}
            />
            {isBothMode && rocketpyData.length > 0 && (
              <StatCard
                label="Durée vol (RocketPy)"
                value={`${rocketpyData[rocketpyData.length - 1]?.t.toFixed(1) || 0} s`}
              />
            )}
            <StatCard
              label="Points (ML)"
              value={`${mlData.length}`}
            />
            {isBothMode && rocketpyData.length > 0 && (
              <StatCard
                label="Points (RocketPy)"
                value={`${rocketpyData.length}`}
              />
            )}
          </div>
        )}

        {/* Graphique Altitude vs Temps */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Altitude (Z) en fonction du temps
          </h2>
          <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={['dataMin', 'dataMax']}
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
                  data={mlData}
                  type="monotone"
                  dataKey="z"
                  name="ML Prediction"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                {isBothMode && rocketpyData.length > 0 && (
                  <Line
                    data={rocketpyData}
                    type="monotone"
                    dataKey="z"
                    name="RocketPy Simulation"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
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
              <LineChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="x"
                  type="number"
                  domain={['dataMin', 'dataMax']}
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
                <Legend />
                <Line
                  data={mlData}
                  type="monotone"
                  dataKey="z"
                  name="ML Prediction"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
                {isBothMode && rocketpyData.length > 0 && (
                  <Line
                    data={rocketpyData}
                    type="monotone"
                    dataKey="z"
                    name="RocketPy Simulation"
                    stroke="#f97316"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Graphique toutes coordonnées */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
            Toutes les coordonnées vs Temps
          </h2>
          <div className="bg-zinc-50 dark:bg-zinc-800 rounded-lg p-4" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={['dataMin', 'dataMax']}
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
                {!isBothMode && (
                  <>
                    <Line
                      data={mlData}
                      type="monotone"
                      dataKey="x"
                      name="X"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      data={mlData}
                      type="monotone"
                      dataKey="y"
                      name="Y"
                      stroke="#f97316"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      data={mlData}
                      type="monotone"
                      dataKey="z"
                      name="Z"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </>
                )}
                {isBothMode && (
                  <>
                    <Line
                      data={mlData}
                      type="monotone"
                      dataKey="z"
                      name="Z (ML)"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      data={rocketpyData}
                      type="monotone"
                      dataKey="z"
                      name="Z (RocketPy)"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={false}
                    />
                  </>
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Raw Data Table - Only show for single source */}
        {!isBothMode && mlData.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
              Données brutes (premiers points)
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left text-zinc-700 dark:text-zinc-300">
                <thead className="text-xs uppercase bg-zinc-100 dark:bg-zinc-800">
                  <tr>
                    <th className="px-4 py-2">Temps (s)</th>
                    <th className="px-4 py-2">X (m)</th>
                    <th className="px-4 py-2">Y (m)</th>
                    <th className="px-4 py-2">Z (m)</th>
                  </tr>
                </thead>
                <tbody>
                  {mlData.slice(0, 20).map((p, i) => (
                    <tr key={i} className="border-b dark:border-zinc-700">
                      <td className="px-4 py-2">{p.t.toFixed(2)}</td>
                      <td className="px-4 py-2">{p.x.toFixed(2)}</td>
                      <td className="px-4 py-2">{p.y.toFixed(2)}</td>
                      <td className="px-4 py-2">{p.z.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {mlData.length > 20 && (
              <p className="text-sm text-zinc-500 mt-2">
                ... et {mlData.length - 20} points supplémentaires
              </p>
            )}
          </section>
        )}

        {/* Comparison Stats for both mode */}
        {isBothMode && rocketpyData.length > 0 && (
          <section className="mt-8">
            <h2 className="text-lg font-semibold text-black dark:text-white mb-4">
              Comparaison ML vs RocketPy
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ComparisonCard
                label="Différence altitude max"
                value={`${Math.abs(
                  Math.max(...mlData.map(p => p.z)) - Math.max(...rocketpyData.map(p => p.z))
                ).toFixed(1)} m`}
              />
              <ComparisonCard
                label="Différence durée vol"
                value={`${Math.abs(
                  (mlData[mlData.length - 1]?.t || 0) - (rocketpyData[rocketpyData.length - 1]?.t || 0)
                ).toFixed(1)} s`}
              />
              <ComparisonCard
                label="Ratio points de données"
                value={`${(mlData.length / rocketpyData.length).toFixed(2)}x`}
              />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 rounded-md bg-zinc-100 dark:bg-zinc-800">
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{label}</p>
      <p className="text-xl font-semibold text-black dark:text-white mt-1">{value}</p>
    </div>
  );
}

function ComparisonCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 rounded-md border-2 border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20">
      <p className="text-sm text-blue-700 dark:text-blue-300">{label}</p>
      <p className="text-xl font-semibold text-blue-900 dark:text-blue-100 mt-1">{value}</p>
    </div>
  );
}
