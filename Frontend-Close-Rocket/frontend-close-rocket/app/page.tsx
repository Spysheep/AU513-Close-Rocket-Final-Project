'use client';

import { useState, useEffect } from 'react';

interface Calculation {
  id: number;
  input_number: number;
  result: number;
  created_at: string;
}

export default function Home() {
  const [number, setNumber] = useState<string>('');
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [history, setHistory] = useState<Calculation[]>([]);

  // Récupère l'historique au chargement de la page
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/history');
      if (response.ok) {
        const data = await response.json();
        setHistory(data.calculations);
      }
    } catch (err) {
      console.error('Erreur lors de la récupération de l\'historique:', err);
    }
  };

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

      // Rafraîchit l'historique après un nouveau calcul
      fetchHistory();
    } catch (err) {
      setError('Erreur : Impossible de se connecter au backend. Assurez-vous qu\'il est lancé sur le port 8000.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const response = await fetch(`http://localhost:8000/history/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Rafraîchit l'historique après suppression
        fetchHistory();
      }
    } catch (err) {
      console.error('Erreur lors de la suppression:', err);
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

        {/* Section Historique */}
        <div className="mt-8 border-t border-zinc-200 dark:border-zinc-700 pt-8">
          <h2 className="text-xl font-bold text-black dark:text-white mb-4">
            Historique des calculs
          </h2>

          {history.length === 0 ? (
            <p className="text-zinc-500 dark:text-zinc-400 text-sm text-center py-4">
              Aucun calcul dans l'historique
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {history.map((calc) => (
                <div
                  key={calc.id}
                  className="flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700"
                >
                  <div className="flex-1">
                    <p className="text-sm text-black dark:text-white">
                      <span className="font-medium">{calc.input_number}</span>² = {calc.result}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      {new Date(calc.created_at).toLocaleString('fr-FR')}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDelete(calc.id)}
                    className="ml-4 px-3 py-1 text-xs bg-red-500 hover:bg-red-600 text-white rounded transition-colors"
                  >
                    Supprimer
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
