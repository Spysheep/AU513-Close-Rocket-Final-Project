from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

app = FastAPI()

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

# ----- Domain models for the input page -----
class NoseCone(BaseModel):
    # paramètre de forme entre 0 et 1
    shape_param: float = Field(..., ge=0.0, le=1.0)
    diameter_mm: float = Field(..., gt=0)
    length_mm: float = Field(..., gt=0)

class Tube(BaseModel):
    diameter_mm: float = Field(..., gt=0)
    length_mm: float = Field(..., gt=0)

class Aileron(BaseModel):
    type: Literal["trapezoidale", "elliptique", "diamant"]
    number: int = Field(..., ge=3)
    inclination_deg: float = Field(..., ge=0)

class Geometry(BaseModel):
    coiffe: NoseCone
    tube: Tube
    aileron: Aileron

class CenterOfGravity(BaseModel):
    x: float
    y: float
    z: float

class Wind(BaseModel):
    x: float
    y: float
    z: float
    groundSpeed_kms: float = Field(..., ge=0)

class RampInclination(BaseModel):
    theta_xy: float  # degrés
    phi_xz: float    # degrés

class RocketInputs(BaseModel):
    geometry: Geometry
    cg: CenterOfGravity
    weight_kg: float = Field(..., gt=0)
    thrust_N: float = Field(..., gt=0)
    wind: Wind
    ramp_inclination: RampInclination

@app.get("/")
def read_root():
    return {"message": "Backend Close Rocket API"}

@app.post("/calculate")
def calculate(request: CalculateRequest):
    """
    Fonction simple qui prend un nombre et retourne son carré
    """
    result = request.number ** 2
    return {
        "input": request.number,
        "result": result,
        "message": f"Le carré de {request.number} est {result}"
    }


@app.post("/inputs")
def submit_inputs(inputs: RocketInputs):
    """
    Endpoint qui reçoit tous les paramètres de l'interface Input.
    Pour l'instant, on valide et on renvoie un récapitulatif.
    """

    # validation supplémentaire : le diamètre du tube doit être lié à la coiffe (<= coiffe)
    if inputs.geometry.tube.diameter_mm > inputs.geometry.coiffe.diameter_mm:
        raise HTTPException(
            status_code=400,
            detail="Le diamètre du tube doit être inférieur ou égal au diamètre de la coiffe."
        )

    summary = {
        "geometry": inputs.geometry.model_dump(),
        "cg": inputs.cg.model_dump(),
        "weight_kg": inputs.weight_kg,
        "thrust_N": inputs.thrust_N,
        "wind": inputs.wind.model_dump(),
        "ramp_inclination": inputs.ramp_inclination.model_dump(),
    }

    # Exemple de calcul rapide: rapport poussée/poids
    twr = inputs.thrust_N / (inputs.weight_kg * 9.80665)

    return {
        "message": "Paramètres reçus avec succès",
        "summary": summary,
        "computed": {
            "thrust_to_weight_ratio": twr
        }
    }