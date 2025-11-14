import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = "calculations.db"):
        """Initialise la connexion a la base de donnees SQLite"""
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Cree une connexion a la base de donnees"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Cree la table si elle n'existe pas"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Creation de la table 'calculations'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_number REAL NOT NULL,
                result REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def save_calculation(self, input_number: float, result: float) -> int:
        """
        Sauvegarde un calcul dans la base de donnees
        Retourne l'ID du calcul cree
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO calculations (input_number, result) VALUES (?, ?)",
            (input_number, result)
        )

        calculation_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return calculation_id

    def get_all_calculations(self, limit: int = 10) -> List[Dict]:
        """
        Recupere les derniers calculs (par defaut les 10 derniers)
        Retourne une liste de dictionnaires
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row  # Permet d'acceder aux colonnes par nom
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, input_number, result, created_at
            FROM calculations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        rows = cursor.fetchall()
        conn.close()

        # Convertir les resultats en liste de dictionnaires
        return [dict(row) for row in rows]

    def get_calculation_by_id(self, calculation_id: int) -> Optional[Dict]:
        """Recupere un calcul par son ID"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, input_number, result, created_at FROM calculations WHERE id = ?",
            (calculation_id,)
        )

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def delete_calculation(self, calculation_id: int) -> bool:
        """Supprime un calcul par son ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM calculations WHERE id = ?", (calculation_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted
