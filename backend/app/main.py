from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.routers import identity, admin, prosnje, cenik, materiali, projekti, ponudbe, racuni, vrste_dela, postavke, delavci, povabila
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

for module in (identity, admin, prosnje, cenik, materiali, projekti, ponudbe, racuni, vrste_dela, postavke, delavci, povabila):
    app.include_router(module.router, prefix='/api')

register(app)

MAX_BODY = 256 * 1024
SECURITY_HEADERS = [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'), (b'x-frame-options', b'DENY'), (b'referrer-policy', b'strict-origin-when-cross-origin')]

class TooLarge(Exception): pass

class ApiGuard:
    """Pure ASGI so chunked bodies are counted as they stream; adds the same headers to every /api response, errors included."""
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith('/api/'): return await self.app(scope, receive, send)
        started = False
        exceeded = False

        async def send_with_headers(message):
            nonlocal started
            if exceeded and not rejecting: return  # the framework may turn the abort into 400; drop its response
            if message['type'] == 'http.response.start':
                started = True
                names = {n for n, _ in SECURITY_HEADERS}
                message = message | {'headers': [(k, v) for k, v in message.get('headers', []) if k.lower() not in names] + SECURITY_HEADERS}
            await send(message)

        rejecting = False

        async def reject():
            nonlocal rejecting
            rejecting = True
            await JSONResponse(status_code=413, content={'detail': 'Zahtevek je prevelik.'})(scope, receive, send_with_headers)

        declared = dict(scope['headers']).get(b'content-length', b'')
        if declared.isdigit() and int(declared) > MAX_BODY: return await reject()
        size = 0

        async def counted():
            nonlocal size
            message = await receive()
            if message['type'] == 'http.request':
                size += len(message.get('body', b''))
                if size > MAX_BODY:
                    nonlocal exceeded
                    exceeded = True
                    raise TooLarge
            return message

        try: await self.app(scope, counted, send_with_headers)
        except TooLarge: pass
        if exceeded and not started: await reject()

app.add_middleware(ApiGuard)
