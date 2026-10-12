from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.database import database_readiness
from app.pricing import CalculationInput, CalculationResult, calculate

app = FastAPI(title="QuoteFlow AI", version="0.1.0", description="Razvojno ogrodje. Poslovni postopki še niso vključeni.")

@app.get('/api/health')
def health():
    return {"status": "ok", "stage": "scaffold"}

@app.get('/api/ready')
def ready():
    status = database_readiness()
    if status != 'ok':
        return JSONResponse(status_code=503, content={"status": status})
    return {"status": "ok", "database": "connected"}

@app.post('/api/demo/calculate', response_model=CalculationResult)
def demo_calculate(data: CalculationInput):
    # Public demonstration endpoint: inputs are not trusted supplier records.
    return calculate(data)
