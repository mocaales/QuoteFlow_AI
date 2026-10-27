from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import psycopg
from app.identity import router as identity_router
from app.database import database_readiness
from app.pricing import CalculationInput, CalculationResult, calculate

app = FastAPI(title="QuoteFlow AI", version="0.2.0", description="Identiteta, podjetja in pravice. RFQ-proces še ni vključen.")

@app.get('/api/health')
def health():
    return {"status": "ok", "stage": "identity"}

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

app.include_router(identity_router, prefix='/api')

@app.exception_handler(psycopg.Error)
async def database_error(request: Request, error: psycopg.Error):
    if isinstance(error, psycopg.errors.InsufficientPrivilege):
        code, message = 403, 'Za to dejanje nimate pravice.'
    elif isinstance(error, psycopg.errors.NoDataFound):
        code, message = 404, 'Zapis ni na voljo.'
    elif isinstance(error, psycopg.IntegrityError):
        code, message = 422, 'Neveljavna povezava ali stanje podatkov. Osvežite seznam in preverite vnos.'
    else:
        code, message = 503, 'Podatkovna baza trenutno ni na voljo.'
    return JSONResponse(status_code=code, content={'detail':message})

@app.middleware('http')
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response
