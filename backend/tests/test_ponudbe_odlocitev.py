"""US-05 pošiljanje in odločitev o ponudbi: validacija, preslikava napak in zaščita poti s fake povezavo."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, customer, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'ana@example.test')
COMPANY, PROJECT, QUOTE = uuid4(), uuid4(), uuid4()
SEND = f'/api/podjetja/{COMPANY}/projekti/{PROJECT}/ponudbe/{QUOTE}/poslji'
DECIDE = f'/api/projekti/{PROJECT}/ponudbe/{QUOTE}/odlocitev'
LIST = f'/api/projekti/{PROJECT}/ponudbe'
MESSAGES = {'QFP07': 'V tej fazi projekta to dejanje ni dovoljeno.', 'QFP10': 'Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.', 'QFP11': 'O tej ponudbi ni več mogoče odločati.',
            'QFP12': 'Veljavnost ponudbe je potekla.', 'QFP13': 'Ponudba mora imeti vsaj eno postavko.', 'QFP17': 'Izvajalec trenutno ne posluje.'}


class Cursor:
    def __init__(self, rows): self.rows = rows
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Fake:
    def __init__(self, rows=(), error=None): self.rows, self.error, self.calls = list(rows), error, []
    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))
        if self.error: raise self.error
        return Cursor(self.rows)


def qfp(code):
    class Custom(psycopg.DatabaseError): sqlstate = code
    return Custom()


@pytest.fixture
def api():
    def use(fake):
        app.dependency_overrides[current_user] = lambda: ME
        app.dependency_overrides[session_database] = lambda: fake
        app.dependency_overrides[company_member('mojster')] = lambda: fake
        app.dependency_overrides[customer] = lambda: fake
        return TestClient(app, raise_server_exceptions=False)
    try: yield use
    finally: app.dependency_overrides.clear()


def test_poslji_pokliče_funkcijo_s_podjetjem_in_ponudbo(api):
    fake = Fake([]); api(fake).post(SEND)
    assert any('quoteflow_private.poslji_ponudbo' in sql and COMPANY in p and QUOTE in p for sql, p in fake.calls)


@pytest.mark.parametrize('code', ['QFP07', 'QFP10', 'QFP12', 'QFP13'])
def test_poslji_poslovne_napake_so_409(api, code):
    r = api(Fake(error=qfp(code))).post(SEND); assert r.status_code == 409 and r.json()['detail'] == MESSAGES[code]


def test_poslji_neznana_ponudba_je_404_in_stara_zaklenitev_409(api):
    r = api(Fake(error=psycopg.errors.NoDataFound())).post(SEND); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert api(Fake(error=psycopg.errors.DeadlockDetected())).post(SEND).status_code == 409


def test_odlocitev_pokliče_funkcijo_s_projektom_ponudbo_in_izbiro(api):
    for choice in (True, False):
        fake = Fake([]); api(fake).post(DECIDE, json={'sprejmi': choice})
        assert any('quoteflow_private.odgovori_ponudbo' in sql and PROJECT in p and QUOTE in p and choice in p for sql, p in fake.calls), choice


@pytest.mark.parametrize('body', [{}, {'sprejmi': None}, {'sprejmi': 'da'}, {'sprejmi': 2}, {'sprejmi': True, 'x': 1}, {'sprejmi': [True]}])
def test_odlocitev_zahteva_natancno_bool_sprejmi(api, body):
    fake = Fake([]); assert api(fake).post(DECIDE, json=body).status_code == 422 and not fake.calls


def test_odlocitev_id_ni_uuid_je_422(api):
    assert api(Fake([])).post(f'/api/projekti/ni-uuid/ponudbe/{QUOTE}/odlocitev', json={'sprejmi': True}).status_code == 422


@pytest.mark.parametrize('code', ['QFP11', 'QFP12', 'QFP17', 'QFP07'])
def test_odlocitev_poslovne_napake_so_409(api, code):
    r = api(Fake(error=qfp(code))).post(DECIDE, json={'sprejmi': True}); assert r.status_code == 409 and r.json()['detail'] == MESSAGES[code]


def test_odlocitev_tujec_je_404_brez_pravice_403(api):
    r = api(Fake(error=psycopg.errors.NoDataFound())).post(DECIDE, json={'sprejmi': True}); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert api(Fake(error=psycopg.errors.InsufficientPrivilege())).post(DECIDE, json={'sprejmi': True}).status_code == 403


def test_seznam_ponudb_stranke_filtrira_po_lastni_stranki(api):
    fake = Fake([]); api(fake).get(LIST)
    assert fake.calls and any(PROJECT in p and ME.id in p for _, p in fake.calls)


def test_nove_poti_brez_zetona_so_401():
    c = TestClient(app, raise_server_exceptions=False)
    assert c.post(SEND).status_code == 401 and c.get(LIST).status_code == 401 and c.post(DECIDE, json={'sprejmi': True}).status_code == 401
