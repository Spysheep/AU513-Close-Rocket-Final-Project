from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import Database

app = FastAPI()
db = Database()  # Instance de la base de données

# Configuration CORS pour permettre au frontend de communiquer avec le backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL du frontend Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CalculateRequest(BaseModel):
    number: float

@app.get("/")
def read_root():
    return {"message": "Backend Close Rocket API"}

@app.post("/calculate")
def calculate(request: CalculateRequest):
    """
    Fonction qui calcule le carré d'un nombre et sauvegarde le résultat en base de données
    """
    result = request.number ** 2

    # Sauvegarde dans la base de données
    calculation_id = db.save_calculation(request.number, result)

    return {
        "id": calculation_id,
        "input": request.number,
        "result": result,
        "message": f"Le carré de {request.number} est {result}"
    }

@app.get("/history")
def get_history(limit: int = 10):
    """
    Récupère l'historique des calculs
    Par défaut, retourne les 10 derniers calculs
    """
    calculations = db.get_all_calculations(limit=limit)
    return {
        "count": len(calculations),
        "calculations": calculations
    }

@app.get("/history/{calculation_id}")
def get_calculation(calculation_id: int):
    """
    Récupère un calcul spécifique par son ID
    """
    calculation = db.get_calculation_by_id(calculation_id)
    if calculation:
        return calculation
    return {"error": "Calcul non trouvé"}

@app.delete("/history/{calculation_id}")
def delete_calculation(calculation_id: int):
    """
    Supprime un calcul de l'historique
    """
    success = db.delete_calculation(calculation_id)
    if success:
        return {"message": "Calcul supprimé avec succès"}
    return {"error": "Calcul non trouvé"}
