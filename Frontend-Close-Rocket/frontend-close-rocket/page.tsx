"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";

interface RocketConfig {
  longueurOgive: string;
  longueurCorps: string;
  longueurAileron: string;
  poids: string;
  poussee: string;
  inclinaisonRampe: string;
  vent: string;
}

interface TrajectoryPoint {
  x: number;
  y: number;
  time: number;
}

export default function Simulation() {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [config, setConfig] = useState<RocketConfig | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [currentPoint, setCurrentPoint] = useState(0);
  const [maxHeight, setMaxHeight] = useState(0);
  const [maxDistance, setMaxDistance] = useState(0);
  const [flightTime, setFlightTime] = useState(0);

  useEffect(() => {
    // Récupérer la configuration depuis sessionStorage
    const storedConfig = sessionStorage.getItem("rocketConfig");
    if (!storedConfig) {
      router.push("/");
      return;
    }
    setConfig(JSON.parse(storedConfig));
  }, [router]);

  const calculateTrajectory = () => {
    if (!config) return;

    // Assurer que les valeurs sont bien parsées comme nombres
    const g = 9.81;
    const masse = Math.max(parseFloat(config.poids) || 1, 0.1);
    const poussee = Math.max(parseFloat(config.poussee) || 100, 10);
    const angle = Math.max(Math.min((parseFloat(config.inclinaisonRampe) || 45) * (Math.PI / 180), Math.PI / 2), 0);
    const vent = parseFloat(config.vent) || 0;

    console.log("Trajectoire calculée avec:", { masse, poussee, angle: angle * 180 / Math.PI, vent });

    // Calcul simplifié de la trajectoire (physique basique)
    const acceleration = (poussee / masse) - g;
    console.log("Accélération nette:", acceleration, "m/s²");
    
    // Vitesse initiale : si l'accélération est positive, utiliser la phase propulsée
    // Sinon, donner une vitesse initiale minimale pour avoir une trajectoire
    let v0 = 0;
    if (acceleration > 0) {
      v0 = Math.sqrt(2 * acceleration * 10); // Vitesse après 10m de poussée
    } else {
      // Si poussée insuffisante, donner une vitesse initiale pour voir quelque chose
      v0 = Math.sqrt(poussee * 2 / masse); // Vitesse équivalente à l'énergie de poussée
    }
    
    const vx = v0 * Math.cos(angle) - vent * 0.5;
    const vy = v0 * Math.sin(angle);
    console.log("Vitesse initiale v0:", v0, "Composantes: vx=", vx, "vy=", vy);

    const points: TrajectoryPoint[] = [];
    const dt = 0.1; // Pas de temps
    let t = 0;
    let x = 0;
    let y = 0;
    let vxCurrent = vx;
    let vyCurrent = vy;

    // Phase propulsée (2 secondes)
    while (t < 2) {
      x += vxCurrent * dt;
      y += vyCurrent * dt;
      vyCurrent += (acceleration - g) * dt;
      vxCurrent -= vent * 0.1 * dt;

      if (y >= 0) {
        points.push({ x, y, time: t });
      }
      t += dt;
    }

    // Phase balistique (limite de temps étendue à 300s = 5 minutes)
    while (y >= 0 && t < 300) {
      x += vxCurrent * dt;
      y += vyCurrent * dt;
      vyCurrent -= g * dt;
      vxCurrent -= vent * 0.05 * dt;

      if (y >= 0) {
        points.push({ x, y, time: t });
      }
      t += dt;
    }

    console.log(`Points calculés: ${points.length}`);

    // Si aucun point calculé, initialiser proprement et quitter
    if (points.length === 0) {
      setMaxHeight(0);
      setMaxDistance(0);
      setFlightTime(0);
      setTrajectory([]);
      return;
    }

    // Calculer les statistiques (sécurisé contre les tableaux vides)
    const heights = points.map((p) => p.y || 0);
    const distances = points.map((p) => p.x || 0);
    const computedMaxHeight = heights.length ? Math.max(...heights) : 0;
    const computedMaxDistance = distances.length ? Math.max(...distances) : 0;

    setMaxHeight(Number.isFinite(computedMaxHeight) ? computedMaxHeight : 0);
    setMaxDistance(Number.isFinite(computedMaxDistance) ? computedMaxDistance : 0);
    setFlightTime(Number.isFinite(points[points.length - 1]?.time) ? points[points.length - 1].time : 0);

    console.log("Stats finales:", { maxHeight: computedMaxHeight, maxDistance: computedMaxDistance, flightTime: points[points.length - 1]?.time });

    setTrajectory(points);
  };

  const startSimulation = () => {
    console.log("Config avant calcul:", config);
    calculateTrajectory();
    setIsSimulating(true);
    setCurrentPoint(0);
  };

  useEffect(() => {
    if (!isSimulating || currentPoint >= trajectory.length) return;

    const timer = setTimeout(() => {
      setCurrentPoint((prev) => prev + 1);
    }, 50);

    return () => clearTimeout(timer);
  }, [isSimulating, currentPoint, trajectory]);

  useEffect(() => {
    if (!canvasRef.current || trajectory.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Échelle (protéger contre division par zéro / valeurs non-finite)
    const scaleX = maxDistance > 0 && Number.isFinite(maxDistance) ? canvas.width / (maxDistance * 1.2) : 1;
    const scaleY = maxHeight > 0 && Number.isFinite(maxHeight) ? canvas.height / (maxHeight * 1.2) : 1;

    // Dessiner le sol
    ctx.strokeStyle = "#8B4513";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height);
    ctx.lineTo(canvas.width, canvas.height);
    ctx.stroke();

    // Dessiner la trajectoire
    ctx.strokeStyle = "#3B82F6";
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    for (let i = 0; i < Math.min(currentPoint, trajectory.length); i++) {
      const point = trajectory[i];
      const px = Number.isFinite(point.x) ? point.x : 0;
      const py = Number.isFinite(point.y) ? point.y : 0;
      const x = px * scaleX;
      const y = canvas.height - py * scaleY;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Dessiner la fusée
    if (currentPoint < trajectory.length) {
      const point = trajectory[currentPoint];
      const px = Number.isFinite(point.x) ? point.x : 0;
      const py = Number.isFinite(point.y) ? point.y : 0;
      const x = px * scaleX;
      const y = canvas.height - py * scaleY;

      // Angle de la fusée
      let angle = 0;
      if (currentPoint > 0) {
        const prevPoint = trajectory[currentPoint - 1];
        const pyPrev = Number.isFinite(prevPoint.y) ? prevPoint.y : 0;
        const pxPrev = Number.isFinite(prevPoint.x) ? prevPoint.x : 0;
        angle = Math.atan2(point.y - pyPrev, point.x - pxPrev);
      }

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(angle);

      // Dessiner la fusée simplifiée
      ctx.fillStyle = "#EF4444";
      ctx.beginPath();
      ctx.moveTo(-10, 0);
      ctx.lineTo(10, 0);
      ctx.lineTo(0, -30);
      ctx.closePath();
      ctx.fill();

      // Flammes (seulement pendant les 2 premières secondes)
      if (trajectory[currentPoint].time < 2) {
        ctx.fillStyle = "#FFA500";
        ctx.beginPath();
        ctx.moveTo(-5, 0);
        ctx.lineTo(5, 0);
        ctx.lineTo(0, 15);
        ctx.closePath();
        ctx.fill();
      }

      ctx.restore();
    }

    // Grille et axes
    ctx.strokeStyle = "#E5E7EB";
    ctx.lineWidth = 1;
    for (let i = 0; i < 10; i++) {
      // Lignes horizontales
      const y = (canvas.height / 10) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();

      // Lignes verticales
      const x = (canvas.width / 10) * i;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
  }, [trajectory, currentPoint, maxHeight, maxDistance]);

  const handleBack = () => {
    router.push("/");
  };

  const handleRestart = () => {
    setIsSimulating(false);
    setCurrentPoint(0);
    setTrajectory([]);
  };

  if (!config) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl">Chargement...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* En-tête */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800">
            Simulation de Vol de Fusée
          </h1>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {/* Panneau de contrôle */}
          <div className="col-span-1 space-y-6">
            {/* Statistiques */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold mb-4">Statistiques</h2>
              <div className="space-y-3">
                <div className="p-3 bg-blue-50 rounded">
                  <div className="text-sm text-gray-600">Altitude Max</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {maxHeight.toFixed(1)} m
                  </div>
                </div>
                <div className="p-3 bg-green-50 rounded">
                  <div className="text-sm text-gray-600">Distance Max</div>
                  <div className="text-2xl font-bold text-green-600">
                    {maxDistance.toFixed(1)} m
                  </div>
                </div>
                <div className="p-3 bg-purple-50 rounded">
                  <div className="text-sm text-gray-600">Temps de Vol</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {flightTime.toFixed(1)} s
                  </div>
                </div>
                {trajectory.length > 0 && currentPoint < trajectory.length && (
                  <div className="p-3 bg-orange-50 rounded">
                    <div className="text-sm text-gray-600">Temps Actuel</div>
                    <div className="text-2xl font-bold text-orange-600">
                      {trajectory[currentPoint]?.time.toFixed(1)} s
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Configuration */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold mb-4">Configuration</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Poids:</span>
                  <span className="font-semibold">{config.poids} kg</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Poussée:</span>
                  <span className="font-semibold">{config.poussee} N</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Angle:</span>
                  <span className="font-semibold">{config.inclinaisonRampe}°</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Vent:</span>
                  <span className="font-semibold">{config.vent} m/s</span>
                </div>
              </div>
            </div>

            {/* Contrôles */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="space-y-3">
                {!isSimulating ? (
                  <button
                    onClick={startSimulation}
                    className="w-full px-4 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors"
                  >
                    ▶ Démarrer la Simulation
                  </button>
                ) : (
                  <button
                    onClick={handleRestart}
                    className="w-full px-4 py-3 bg-orange-600 text-white rounded-lg font-semibold hover:bg-orange-700 transition-colors"
                  >
                    🔄 Recommencer
                  </button>
                )}
                <button
                  onClick={handleBack}
                  className="w-full px-4 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
                >
                  ← Retour à la Configuration
                </button>
              </div>
            </div>
          </div>

          {/* Zone de simulation */}
          <div className="col-span-3 bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4">Trajectoire de la Fusée</h2>
            <div className="relative">
              <canvas
                ref={canvasRef}
                width={900}
                height={600}
                className="border-2 border-gray-300 rounded-lg w-full"
              />
              {!isSimulating && trajectory.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-50 bg-opacity-75 rounded-lg">
                  <div className="text-center">
                    <p className="text-2xl text-gray-600 mb-4">
                      Prêt à démarrer la simulation
                    </p>
                    <p className="text-gray-500">
                      Cliquez sur "Démarrer la Simulation" pour lancer
                    </p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Légende */}
            <div className="mt-4 flex gap-6 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-blue-500 rounded"></div>
                <span>Trajectoire</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-red-500 rounded"></div>
                <span>Fusée</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-orange-500 rounded"></div>
                <span>Propulsion active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
