'use client';

import { useState } from 'react';

export default function Home() {
  const [number, setNumber] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleCalculate = async () => {
    setLoading(true);
    setError('');
    setResult('');

    try {
      const response = await fetch('http://localhost:8000/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          number: parseFloat(number),
        }),
      });

      if (!response.ok) {
        throw new Error('Erreur lors de l\'appel au backend');
      }

      const data = await response.json();
      setResult(data.message);
    } catch (err) {
      setError('Erreur : Impossible de se connecter au backend. Assurez-vous qu\'il est lancé sur le port 8000.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-md flex-col gap-8 p-8 bg-white dark:bg-zinc-900 rounded-lg shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-black dark:text-white mb-2">
            Close Rocket Calculator
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Calculateur simple connecté au backend
          </p>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label htmlFor="number" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Entrez un nombre
            </label>
            <input
              id="number"
              type="number"
              value={number}
              onChange={(e) => setNumber(e.target.value)}
              placeholder="Ex: 5"
              className="px-4 py-2 border border-zinc-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleCalculate}
            disabled={loading || !number}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-400 text-white font-medium rounded-lg transition-colors"
          >
            {loading ? 'Calcul en cours...' : 'Calculer le carré'}
          </button>

          {result && (
            <div className="p-4 bg-green-100 dark:bg-green-900 border border-green-300 dark:border-green-700 rounded-lg">
              <p className="text-green-800 dark:text-green-100 font-medium">
                {result}
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 rounded-lg">
              <p className="text-red-800 dark:text-red-100 text-sm">
                {error}
              </p>
            </div>
          )}
        </div>

        <div className="text-center text-xs text-zinc-500 dark:text-zinc-500">
          Backend API: http://localhost:8000
        </div>
      </main>
    </div>
  );
}
