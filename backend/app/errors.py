"""Central mapping of database errors to HTTP responses."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
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
    'QFP09': 'Projekt že ima osnutek ponudbe.',
    'QFP10': 'Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.',
    'QFP11': 'O tej ponudbi ni več mogoče odločati.',
    'QFP12': 'Veljavnost ponudbe je potekla.',
    'QFP13': 'Ponudba mora imeti vsaj eno postavko.',
    'QFP14': 'Izvedbe ni mogoče zaključiti pred začetkom termina.',
    'QFP15': 'Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.',
    'QFP16': 'Neaktivne postavke cenika ni mogoče dodati v ponudbo.',
    'QFP17': 'Izvajalec trenutno ne posluje.',
    'QFP18': 'Termin se ne sme začeti v preteklosti.',
    'QFP20': 'Ponudba ima lahko največ 200 postavk.',
    'QFP21': 'Rok plačila ne sme biti pred datumom izdaje.',
    'QFP22': 'Skrbnik si ne more sam dodeliti vloge v podjetju.',
    'QFP23': 'Projekt ima največje dovoljeno število različic ponudbe.',
    'QFP24': 'Termin je bil danes spremenjen prevečkrat.',
    'QFP25': 'Izmere bi dale negativno količino.',
    'QFP26': 'Vsaka postavka mora imeti pozitivno količino izmer.',
    'QFP27': 'Mersko enoto lahko spremenite le, ko postavka nima izmer.',
    'QFP28': 'Postavka ima lahko največ 100 izmer.',
    'QFP29': 'Neaktivne vrste dela ni mogoče uporabiti.',
    'QFP30': 'Preveč poskusov dodajanja delavcev. Poskusite znova čez nekaj časa.',
    'QFP31': 'Podjetje ima lahko največ 500 vrst dela.',
    'QFP32': 'Vrsta dela ima lahko največ 50 materialov.',
    'QFP33': 'Lastniku podjetja ni mogoče odvzeti vloge mojster.',
    'QFP34': 'Povabila ni mogoče sprejeti.',
}

async def database_error(request: Request, error: psycopg.Error):
    if error.sqlstate in CONFLICTS:
        code, message = 409, CONFLICTS[error.sqlstate]
    elif isinstance(error, psycopg.errors.ObjectNotInPrerequisiteState):
        code, message = 409, 'Dokument je zaklenjen in ga ni mogoče spremeniti.'
    elif isinstance(error, (psycopg.errors.DeadlockDetected, psycopg.errors.SerializationFailure)):
        code, message = 409, 'Sočasna sprememba. Osvežite podatke in poskusite znova.'
    elif error.sqlstate in ('22023', '22004'):
        code, message = 422, 'Vnesena vrednost ni veljavna.'
    elif isinstance(error, psycopg.DataError):
        code, message = 422, 'Vrednost presega dovoljeno mejo.'
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
    detail = [{'loc': [str(p)[:60] for p in e.get('loc', ())[:6]], 'msg': str(e.get('msg', ''))[:200].encode('utf-8', 'replace').decode(), 'type': str(e.get('type', ''))[:60]} for e in error.errors()]
    return JSONResponse(status_code=422, content={'detail': detail})

async def recursion_error(request: Request, error: RecursionError):
    return JSONResponse(status_code=422, content={'detail': [{'loc': ['body'], 'msg': 'Vsebina zahtevka je neveljavna.', 'type': 'value_error'}]})

async def response_error(request: Request, error: ResponseValidationError):
    # Handled inside the middleware stack so even this 500 carries the API security headers; never echo the offending row.
    return JSONResponse(status_code=500, content={'detail': 'Odgovora ni mogoče pripraviti.'})

def register(app: FastAPI):
    app.exception_handler(ResponseValidationError)(response_error)
    app.exception_handler(RequestValidationError)(validation_error)
    app.exception_handler(RecursionError)(recursion_error)
    app.exception_handler(psycopg.Error)(database_error)
