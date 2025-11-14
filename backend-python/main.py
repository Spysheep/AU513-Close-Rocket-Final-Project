from fastapi import FastAPI
import your_model

app = FastAPI()

@app.get("/predict")
def predict(x: float):
    result = your_model.inference(x)
    return {"prediction": result}
