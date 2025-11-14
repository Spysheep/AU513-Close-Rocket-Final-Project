from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import test

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def predict(x: float):
    result = test.z  # provient de backend-python/test.py
    return {"prediction": result}