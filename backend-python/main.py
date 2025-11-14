from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
