"""Step 0: central mapping of database errors (new SQLSTATEs and business conflicts QFP09-QFP24)."""
import asyncio
import json
import psycopg
import pytest
from app.errors import CONFLICTS, database_error

M = {
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
    'QFP33': 'Lastniku podjetja ni mogoče odvzeti vloge mojster.',
}


def qfp(code):
    class Custom(psycopg.DatabaseError): sqlstate = code
    return Custom()


def run(error):
    r = asyncio.run(database_error(None, error)); return r.status_code, json.loads(r.body)['detail']


@pytest.mark.parametrize('code', sorted(M))
def test_nov_poslovni_konflikt_je_409_s_slovenskim_sporocilom(code):
    assert CONFLICTS.get(code) == M[code]
    assert run(qfp(code)) == (409, M[code])


def test_zaklenjen_dokument_55000_je_409_ne_503():
    assert run(psycopg.errors.ObjectNotInPrerequisiteState()) == (409, 'Dokument je zaklenjen in ga ni mogoče spremeniti.')


def test_vrednost_izven_meje_22003_in_data_error_sta_422():
    assert run(psycopg.errors.NumericValueOutOfRange()) == (422, 'Vrednost presega dovoljeno mejo.')
    assert run(psycopg.DataError()) == (422, 'Vrednost presega dovoljeno mejo.')


def test_smrtni_objem_in_serializacija_sta_409():
    for error in (psycopg.errors.DeadlockDetected(), psycopg.errors.SerializationFailure()):
        assert run(error) == (409, 'Sočasna sprememba. Osvežite podatke in poskusite znova.')


def test_obstojece_preslikave_ostane_nespremenjen():
    assert run(psycopg.errors.InsufficientPrivilege()) == (403, 'Za to dejanje nimate pravice.')
    assert run(psycopg.errors.NoDataFound())[0] == 404 and run(psycopg.errors.CheckViolation())[0] == 422
    assert run(psycopg.OperationalError())[0] == 503


def test_qfp19_ni_vec_poslovni_konflikt():
    assert 'QFP19' not in CONFLICTS


@pytest.mark.parametrize('error', [psycopg.errors.InvalidParameterValue(), psycopg.errors.NullValueNotAllowed()])
def test_22023_in_22004_sta_422_z_jasnim_sporocilom(error):
    assert run(error) == (422, 'Vnesena vrednost ni veljavna.')


def test_22003_obdrzi_sporocilo_o_meji():
    assert run(psycopg.errors.NumericValueOutOfRange()) == (422, 'Vrednost presega dovoljeno mejo.')
