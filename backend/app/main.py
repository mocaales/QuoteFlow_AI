from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import identity, admin, prosnje, cenik, materiali, projekti
from app.database import database_readiness
from app.errors import register
from app.pricing import CalculationInput, CalculationResult, calculate

app = FastAPI(title="QuoteFlow AI", version="0.4.0", description="Uporabniki, podjetja, cenik storitev in materialne zaloge.")

@app.get('/api/health')
def health():
    return {"status": "ok", "stage": "company_projects"}

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

for module in (identity, admin, prosnje, cenik, materiali, projekti):
    app.include_router(module.router, prefix='/api')

register(app)

@app.middleware('http')
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response
