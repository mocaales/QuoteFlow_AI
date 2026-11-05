"""Central mapping of database errors to HTTP responses."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import psycopg

# Business conflicts raised by quoteflow_private functions with explicit SQLSTATEs.
CONFLICTS = {
    'QFP01': 'Prošnja je že obravnavana.',
    'QFP02': 'Že imate oddano prošnjo, ki čaka na odločitev.',
    'QFP03': 'Vlagatelj ne izpolnjuje pogojev za vlogo mojstra (potrjena e-pošta in aktivna vloga stranke ali delavca).',
    'QFP04': 'Podjetje ali oddana prošnja s to matično številko že obstaja.',
    'QFP05': 'Neaktivnega materiala ni mogoče dodati v sestavo.',
    'QFP06': 'Uporabnik s tem e-poštnim naslovom ni registrirana stranka.',
    'QFP07': 'V tej fazi projekta to dejanje ni dovoljeno.',
    'QFP08': 'Preveč poskusov ustvarjanja projektov. Poskusite znova čez nekaj časa.',
}

async def database_error(request: Request, error: psycopg.Error):
    if error.sqlstate in CONFLICTS:
        code, message = 409, CONFLICTS[error.sqlstate]
    elif isinstance(error, psycopg.errors.InsufficientPrivilege):
        code, message = 403, 'Za to dejanje nimate pravice.'
    elif isinstance(error, psycopg.errors.NoDataFound):
        code, message = 404, 'Zapis ni na voljo.'
    elif isinstance(error, psycopg.errors.ExclusionViolation):
        code, message = 409, 'Vnos se prekriva z obstoječim zapisom.'
    elif isinstance(error, psycopg.IntegrityError):
        code, message = 422, 'Neveljavna povezava ali stanje podatkov. Osvežite seznam in preverite vnos.'
    else:
        code, message = 503, 'Podatkovna baza trenutno ni na voljo.'
    return JSONResponse(status_code=code, content={'detail':message})

async def validation_error(request: Request, error: RequestValidationError):
    # Never echo input/ctx: they may hold NaN, surrogates or deep structures that break serialisation.
    detail = [{'loc': [str(p) for p in e.get('loc', ())], 'msg': str(e.get('msg', '')).encode('utf-8', 'replace').decode(), 'type': str(e.get('type', ''))} for e in error.errors()]
    return JSONResponse(status_code=422, content={'detail': detail})

async def recursion_error(request: Request, error: RecursionError):
    return JSONResponse(status_code=422, content={'detail': [{'loc': ['body'], 'msg': 'Vsebina zahtevka je neveljavna.', 'type': 'value_error'}]})

def register(app: FastAPI):
    app.exception_handler(RequestValidationError)(validation_error)
    app.exception_handler(RecursionError)(recursion_error)
    app.exception_handler(psycopg.Error)(database_error)
