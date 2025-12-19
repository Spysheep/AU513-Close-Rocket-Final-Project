"use client";

import { useState } from "react";
import RocketPreview from "./components/RocketPreview";

type AileronType = "trapezoidale" | "elliptique" | "diamant";

interface BackendResponse {
  message: string;
  summary?: Record<string, unknown>;
  computed?: { thrust_to_weight_ratio: number };
}

interface FormData {
  geometry: {
    coiffe: { shape_param: string; diameter_mm: string; length_mm: string };
    tube: { diameter_mm: string; length_mm: string };
    aileron: {
      type: AileronType;
      number: string;
      // Params per type (French labels kept in form; mapped in preview)
      trapezoid?: { hauteur: string; longueur: string; emplanture: string; sweep_angle_deg: string };
      elliptique?: { hauteur: string; emplanture: string; segments?: string };
      diamant?: { hauteur: string; longueur: string; emplanture: string; sweep_angle_deg: string };
    };
  };
  cg: { x: string; y: string; z: string };
  weight_kg: string;
  thrust_N: string;
  wind: { x: string; y: string; z: string; groundSpeed_kms: string };
  ramp_inclination: { theta_xy: string; phi_xz: string };
}

const initialForm: FormData = {
  geometry: {
    coiffe: { shape_param: "0.5", diameter_mm: "60", length_mm: "150" },
    tube: { diameter_mm: "60", length_mm: "300" },
    aileron: {
      type: "trapezoidale",
      number: "3",
      trapezoid: { hauteur: "80", longueur: "60", emplanture: "90", sweep_angle_deg: "20" },
      elliptique: { hauteur: "80", emplanture: "90", segments: "48" },
      diamant: { hauteur: "80", longueur: "60", emplanture: "90", sweep_angle_deg: "15" },
    },
  },
  cg: { x: "", y: "", z: "" },
  weight_kg: "",
  thrust_N: "",
  wind: { x: "", y: "", z: "", groundSpeed_kms: "" },
  ramp_inclination: { theta_xy: "", phi_xz: "" },
};

export default function Home() {
  const [form, setForm] = useState<FormData>(initialForm);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<BackendResponse | null>(null);

  const clearForm = () => {
    setForm(initialForm);
    setError("");
    setResult(null);
  };

  const validateClient = (): string | null => {
    const sp = parseFloat(form.geometry.coiffe.shape_param);
    const nb = parseInt(form.geometry.aileron.number);
    if (isNaN(sp) || sp < 0 || sp > 1) return "Paramètre de forme (coiffe) doit être entre 0 et 1.";
    if (isNaN(nb) || nb < 3) return "Nombre d'ailerons doit être au minimum 3.";
    return null;
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    const clientError = validateClient();
    if (clientError) {
      setLoading(false);
      setError(clientError);
      return;
    }

    try {
      const payload = {
        geometry: {
          coiffe: {
            shape_param: parseFloat(form.geometry.coiffe.shape_param),
            diameter_mm: parseFloat(form.geometry.coiffe.diameter_mm),
            length_mm: parseFloat(form.geometry.coiffe.length_mm),
          },
          tube: {
            diameter_mm: parseFloat(form.geometry.tube.diameter_mm),
            length_mm: parseFloat(form.geometry.tube.length_mm),
          },
          aileron: {
            type: form.geometry.aileron.type,
            number: parseInt(form.geometry.aileron.number),
            // Backend expects an inclination; only diamant has sweep angle now
            inclination_deg:
              form.geometry.aileron.type === "diamant"
                ? parseFloat(form.geometry.aileron.diamant?.sweep_angle_deg || "0")
                : 0,
          },
        },
        cg: {
          x: parseFloat(form.cg.x),
          y: parseFloat(form.cg.y),
          z: parseFloat(form.cg.z),
        },
        weight_kg: parseFloat(form.weight_kg),
        thrust_N: parseFloat(form.thrust_N),
        wind: {
          x: parseFloat(form.wind.x),
          y: parseFloat(form.wind.y),
          z: parseFloat(form.wind.z),
          groundSpeed_kms: parseFloat(form.wind.groundSpeed_kms),
        },
        ramp_inclination: {
          theta_xy: parseFloat(form.ramp_inclination.theta_xy),
          phi_xz: parseFloat(form.ramp_inclination.phi_xz),
        },
      };

      const response = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const txt = await response.text();
        throw new Error(txt || "Erreur lors de l'envoi des paramètres");
      }
      const data = await response.json();
      setResult(data);
    } catch (e: unknown) {
      setError(
        "Erreur : Impossible de se connecter au backend ou données invalides. Assurez-vous que le backend est lancé sur le port 8000."
      );
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black py-10">
      <main className="mx-auto w-full max-w-6xl rounded-xl bg-white dark:bg-zinc-900 p-8 shadow">
        <header className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl md:text-3xl font-bold text-black dark:text-white">Close Rocket — Input</h1>
          <div className="text-xs text-zinc-500">Backend: http://localhost:8000</div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: form (two columns width) */}
          <div className="lg:col-span-2">
        {/* Geometry */}
        <section>
          <h2 className="text-xl font-semibold text-black dark:text-white">Géométrie</h2>
          <hr className="my-4 border-zinc-200 dark:border-zinc-800" />

          {/* Coiffe */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="col-span-1 md:col-span-3 font-medium text-zinc-700 dark:text-zinc-300">Coiffe</div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-zinc-700 dark:text-zinc-300">Paramètre de forme (0-1)</label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <input
                  type="number"
                  value={form.geometry.coiffe.shape_param}
                  onChange={(e)=>{
                    const v = e.target.value;
                    setForm({
                      ...form,
                      geometry: { ...form.geometry, coiffe: { ...form.geometry.coiffe, shape_param: v } }
                    });
                  }}
                  min={0}
                  max={1}
                  step="0.01"
                  className="px-3 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={parseFloat(form.geometry.coiffe.shape_param || "0")}
                  onChange={(e)=>{
                    const v = e.target.value;
                    setForm({
                      ...form,
                      geometry: { ...form.geometry, coiffe: { ...form.geometry.coiffe, shape_param: v } }
                    });
                  }}
                />
              </div>
            </div>
            <InputNumber label="Diamètre (mm)" value={form.geometry.coiffe.diameter_mm} onChange={(v)=>setForm({
              ...form, geometry: { ...form.geometry, coiffe: { ...form.geometry.coiffe, diameter_mm: v }, tube: { ...form.geometry.tube, diameter_mm: v } }
            })} />
            <InputNumber label="Longueur (mm)" value={form.geometry.coiffe.length_mm} onChange={(v)=>setForm({
              ...form, geometry: { ...form.geometry, coiffe: { ...form.geometry.coiffe, length_mm: v } }
            })} />
          </div>

          {/* Tube */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="col-span-1 md:col-span-2 font-medium text-zinc-700 dark:text-zinc-300">Tube</div>
            <InputNumber label="Diamètre (mm)" value={form.geometry.tube.diameter_mm} onChange={(v)=>setForm({
              ...form, geometry: { ...form.geometry, tube: { ...form.geometry.tube, diameter_mm: v }, coiffe: { ...form.geometry.coiffe, diameter_mm: v } }
            })} />
            <InputNumber label="Longueur (mm)" value={form.geometry.tube.length_mm} onChange={(v)=>setForm({
              ...form, geometry: { ...form.geometry, tube: { ...form.geometry.tube, length_mm: v } }
            })} />
          </div>

          {/* Aileron */}
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="col-span-1 md:col-span-3 font-medium text-zinc-700 dark:text-zinc-300">Aileron</div>
            <div className="flex flex-col gap-1">
              <label className="text-sm text-zinc-700 dark:text-zinc-300">Type</label>
              <select
                value={form.geometry.aileron.type}
                onChange={(e) => setForm({
                  ...form,
                  geometry: { ...form.geometry, aileron: { ...form.geometry.aileron, type: e.target.value as AileronType } },
                })}
                className="px-3 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-black dark:text-white"
              >
                <option value="trapezoidale">Trapezoïdale</option>
                <option value="elliptique">Elliptique</option>
                <option value="diamant">Diamant</option>
              </select>
            </div>
            <InputNumber label="Nombre (min 3)" value={form.geometry.aileron.number} onChange={(v)=>setForm({
              ...form, geometry: { ...form.geometry, aileron: { ...form.geometry.aileron, number: v } }
            })} min={3} step="1" />
            {/* Sub-params per aileron type */}
            {form.geometry.aileron.type === "trapezoidale" && (
              <div className="col-span-1 md:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                <InputNumber label="Hauteur (mm)" value={form.geometry.aileron.trapezoid?.hauteur || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      trapezoid: { ...(form.geometry.aileron.trapezoid||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), hauteur: v },
                    },
                  },
                })} />
                <InputNumber label="Longueur du bord supérieur (mm)" value={form.geometry.aileron.trapezoid?.longueur || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      trapezoid: { ...(form.geometry.aileron.trapezoid||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), longueur: v },
                    },
                  },
                })} />
                <InputNumber label="Emplanture (mm)" value={form.geometry.aileron.trapezoid?.emplanture || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      trapezoid: { ...(form.geometry.aileron.trapezoid||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), emplanture: v },
                    },
                  },
                })} />
              </div>
            )}

            {form.geometry.aileron.type === "elliptique" && (
              <div className="col-span-1 md:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                <InputNumber label="Hauteur (mm)" value={form.geometry.aileron.elliptique?.hauteur || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      elliptique: { ...(form.geometry.aileron.elliptique||{ hauteur:"", emplanture:"" }), hauteur: v },
                    },
                  },
                })} />
                <InputNumber label="Emplanture (mm)" value={form.geometry.aileron.elliptique?.emplanture || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      elliptique: { ...(form.geometry.aileron.elliptique||{ hauteur:"", emplanture:"" }), emplanture: v },
                    },
                  },
                })} />
                <InputNumber label="Segments (N)" value={form.geometry.aileron.elliptique?.segments || "48"} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      elliptique: { ...(form.geometry.aileron.elliptique||{ hauteur:"", emplanture:"", segments:"" }), segments: v },
                    },
                  },
                })} />
              </div>
            )}

            {form.geometry.aileron.type === "diamant" && (
              <div className="col-span-1 md:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                <InputNumber label="Hauteur (mm)" value={form.geometry.aileron.diamant?.hauteur || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      diamant: { ...(form.geometry.aileron.diamant||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), hauteur: v },
                    },
                  },
                })} />
                <InputNumber label="Longueur du bord supérieur (mm)" value={form.geometry.aileron.diamant?.longueur || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      diamant: { ...(form.geometry.aileron.diamant||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), longueur: v },
                    },
                  },
                })} />
                <InputNumber label="Emplanture (mm)" value={form.geometry.aileron.diamant?.emplanture || ""} onChange={(v)=>setForm({
                  ...form,
                  geometry: {
                    ...form.geometry,
                    aileron: {
                      ...form.geometry.aileron,
                      diamant: { ...(form.geometry.aileron.diamant||{ hauteur:"", longueur:"", emplanture:"", sweep_angle_deg:"" }), emplanture: v },
                    },
                  },
                })} />
              </div>
            )}
          </div>
        </section>

        {/* Paramètres de vol */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold text-black dark:text-white">Paramètres de vol</h2>
          <hr className="my-4 border-zinc-200 dark:border-zinc-800" />

          {/* CG */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="col-span-1 md:col-span-3 font-medium text-zinc-700 dark:text-zinc-300">Centre de gravité (x, y, z)</div>
            <InputNumber label="x" value={form.cg.x} onChange={(v)=>setForm({ ...form, cg: { ...form.cg, x: v } })} />
            <InputNumber label="y" value={form.cg.y} onChange={(v)=>setForm({ ...form, cg: { ...form.cg, y: v } })} />
            <InputNumber label="z" value={form.cg.z} onChange={(v)=>setForm({ ...form, cg: { ...form.cg, z: v } })} />
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <InputNumber label="Poids (kg)" value={form.weight_kg} onChange={(v)=>setForm({ ...form, weight_kg: v })} />
            <InputNumber label="Poussée (N)" value={form.thrust_N} onChange={(v)=>setForm({ ...form, thrust_N: v })} />
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="col-span-1 md:col-span-4 font-medium text-zinc-700 dark:text-zinc-300">Inclinaison de la rampe</div>
            <InputNumber label="θ (x·y) °" value={form.ramp_inclination.theta_xy} onChange={(v)=>setForm({ ...form, ramp_inclination: { ...form.ramp_inclination, theta_xy: v } })} />
            <InputNumber label="φ (x·z) °" value={form.ramp_inclination.phi_xz} onChange={(v)=>setForm({ ...form, ramp_inclination: { ...form.ramp_inclination, phi_xz: v } })} />
          </div>
        </section>

        {/* Paramètres météo */}
        <section className="mt-8">
          <h2 className="text-xl font-semibold text-black dark:text-white">Paramètres météo</h2>
          <hr className="my-4 border-zinc-200 dark:border-zinc-800" />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="col-span-1 md:col-span-4 font-medium text-zinc-700 dark:text-zinc-300">Vent w (x, y, z)</div>
            <InputNumber label="wₓ" value={form.wind.x} onChange={(v)=>setForm({ ...form, wind: { ...form.wind, x: v } })} />
            <InputNumber label="wᵧ" value={form.wind.y} onChange={(v)=>setForm({ ...form, wind: { ...form.wind, y: v } })} />
            <InputNumber label="wᶻ" value={form.wind.z} onChange={(v)=>setForm({ ...form, wind: { ...form.wind, z: v } })} /> 
            <InputNumber label="Vent sol (km/s)" value={form.wind.groundSpeed_kms} onChange={(v)=>setForm({ ...form, wind: { ...form.wind, groundSpeed_kms: v } })} />
          </div>
        </section>

        {/* Actions */}
        <section className="mt-10 flex items-center gap-4">
          <button
            onClick={clearForm}
            className="px-6 py-3 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-700"
          >
            Clear
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="px-6 py-3 rounded-md bg-blue-600 hover:bg-blue-700 text-white disabled:bg-zinc-400"
          >
            {loading ? "Validation…" : "Valider"}
          </button>
        </section>

        {/* Results & errors */}
        <section className="mt-6">
          {error && (
            <div className="p-3 rounded-md border border-red-300 bg-red-100 text-red-800 text-sm">{error}</div>
          )}
          {result && (
            <div className="mt-3 p-4 rounded-md border border-green-300 bg-green-100 text-green-900">
              <div className="font-semibold mb-2">Réponse du backend</div>
              <pre className="text-xs overflow-x-auto whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </section>
          </div>

          {/* Right: rocket preview */}
          <aside className="lg:col-span-1">
            <div className="sticky top-6">
              <div className="mb-3 font-medium text-zinc-700 dark:text-zinc-300">Prévisualisation</div>
              <RocketPreview
                coiffe={{
                  shape_param: parseFloat(form.geometry.coiffe.shape_param),
                  diameter_mm: parseFloat(form.geometry.coiffe.diameter_mm),
                  length_mm: parseFloat(form.geometry.coiffe.length_mm),
                }}
                tube={{
                  diameter_mm: parseFloat(form.geometry.tube.diameter_mm),
                  length_mm: parseFloat(form.geometry.tube.length_mm),
                }}
                aileron={{
                  type: form.geometry.aileron.type,
                  number: parseInt(form.geometry.aileron.number),
                  trapezoid: {
                    height: parseFloat(form.geometry.aileron.trapezoid?.hauteur || "0"),
                    length: parseFloat(form.geometry.aileron.trapezoid?.longueur || "0"),
                    root_chord: parseFloat(form.geometry.aileron.trapezoid?.emplanture || "0"),
                    sweep_angle_deg: parseFloat(form.geometry.aileron.trapezoid?.sweep_angle_deg || "0"),
                  },
                  elliptique: {
                    height: parseFloat(form.geometry.aileron.elliptique?.hauteur || "0"),
                    root_chord: parseFloat(form.geometry.aileron.elliptique?.emplanture || "0"),
                    segments: parseInt(form.geometry.aileron.elliptique?.segments || "48"),
                  },
                  diamant: {
                    height: parseFloat(form.geometry.aileron.diamant?.hauteur || "0"),
                    length: parseFloat(form.geometry.aileron.diamant?.longueur || "0"),
                    root_chord: parseFloat(form.geometry.aileron.diamant?.emplanture || "0"),
                    sweep_angle_deg: parseFloat(form.geometry.aileron.diamant?.sweep_angle_deg || "0"),
                  },
                }}
                rampInclinationDeg={parseFloat(form.ramp_inclination.theta_xy)}
              />
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

function InputNumber({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  min?: number;
  max?: number;
  step?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm text-zinc-700 dark:text-zinc-300">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        min={min}
        max={max}
        step={step}
        className="px-3 py-2 rounded-md border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}