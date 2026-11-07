"""US-04 osnutek ponudbe: API validation, status mapping and not-found handling with a fake connection.

Model v3: the draft is only a header (velja_do); line editing moved to the project (test_postavke.py), so the old line/iz-cenika cases were removed here.
"""
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, session_database
from app.auth import Principal, current_user
from app.main import app

VELJA = (datetime.now(ZoneInfo('Europe/Ljubljana')).date() + timedelta(days=30)).isoformat()
ME = Principal(uuid4(), uuid4(), 'ana@example.test')
COMPANY, PROJECT, QUOTE = uuid4(), uuid4(), uuid4()
M = f'/api/podjetja/{COMPANY}/projekti/{PROJECT}'
ROUTES = [('post', f'{M}/ponudbe', {}), ('put', f'{M}/ponudbe/{QUOTE}', {'velja_do': VELJA})]


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
        return TestClient(app, raise_server_exceptions=False)
    try: yield use
    finally: app.dependency_overrides.clear()


def send(client, method, path, body): return getattr(client, method)(path, json=body)


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_dodatna_polja_so_422(api, method, path, body):
    assert send(api(Fake([])), method, path, body | {'podjetje_id': str(uuid4())}).status_code == 422


def test_velja_do_mora_biti_datum(api):
    assert api(Fake([])).put(f'{M}/ponudbe/{QUOTE}', json={'velja_do': 'jutri'}).status_code == 422


def test_poslana_ponudba_je_409_in_ne_503(api):
    for error in (qfp('QFP10'), psycopg.errors.ObjectNotInPrerequisiteState()):
        r = api(Fake(error=error)).put(f'{M}/ponudbe/{QUOTE}', json={'velja_do': VELJA})
        assert r.status_code == 409 and r.json()['detail'] in ('Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.', 'Dokument je zaklenjen in ga ni mogoče spremeniti.')


def test_zapis_izven_meje_iz_baze_je_422_in_ne_503(api):
    r = api(Fake(error=psycopg.errors.NumericValueOutOfRange())).put(f'{M}/ponudbe/{QUOTE}', json={'velja_do': VELJA})
    assert r.status_code == 422 and r.json()['detail'] == 'Vrednost presega dovoljeno mejo.'


def test_nepoznana_ponudba_je_404_na_vseh_potih(api):
    for method, path, body in ROUTES:
        fake = Fake(error=psycopg.errors.NoDataFound()); r = send(api(fake), method, path, body) if body is not None else getattr(api(fake), method)(path)
        assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.' and fake.calls, path
    fake = Fake([]); assert api(fake).get(f'{M}/ponudbe/{uuid4()}').status_code == 404 and fake.calls


def test_ustvari_ponudbo_pokliče_funkcijo_s_podjetjem_projektom_in_datumom(api):
    fake = Fake([]); api(fake).post(f'{M}/ponudbe', json={'velja_do': VELJA})
    assert any('quoteflow_private.ustvari_ponudbo' in sql and COMPANY in p and PROJECT in p for sql, p in fake.calls)


def test_poti_brez_zetona_so_401():
    c = TestClient(app, raise_server_exceptions=False)
    for method, path, body in ROUTES + [('get', f'{M}/ponudbe', None), ('get', f'{M}/ponudbe/{QUOTE}', None)]:
        assert getattr(c, method)(path).status_code == 401, (method, path)


WRITES = [('put', f'{M}/ponudbe/{QUOTE}', {'velja_do': VELJA}, 'uredi_ponudbo'), ('post', f'{M}/ponudbe/{QUOTE}/poslji', None, 'poslji_ponudbo')]


@pytest.mark.parametrize('method,path,body,fn', WRITES)
def test_l1_vsaka_pisalna_funkcija_dobi_podjetje_projekt_in_ponudbo(api, method, path, body, fn):
    from re import search
    fake = Fake([{'id': uuid4()}]); c = api(fake); getattr(c, method)(path, **({'json': body} if body is not None else {}))
    call = next((x for x in fake.calls if f'quoteflow_private.{fn}(' in x[0]), None); assert call, fn
    sql, params = call; args = search(r'\(([^)]*)\)', sql[sql.index(fn):]).group(1).split(',')
    assert [str(p) for p in params[:3]] == [str(COMPANY), str(PROJECT), str(QUOTE)] and len(args) == len(params), (fn, params)


@pytest.mark.parametrize('method,path,body,fn', WRITES)
def test_l1_napacen_projekt_je_404_na_vseh_pisalnih_poteh(api, method, path, body, fn):
    c = api(Fake(error=psycopg.errors.NoDataFound())); r = getattr(c, method)(path, **({'json': body} if body is not None else {}))
    assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


@pytest.mark.parametrize('days', [-2, 368, 4000])
@pytest.mark.parametrize('method,path', [('post', f'{M}/ponudbe'), ('put', f'{M}/ponudbe/{QUOTE}')])
def test_l3_velja_do_izven_okna_je_422_brez_klica_baze(api, method, path, days):
    from datetime import date, timedelta
    fake = Fake([]); r = getattr(api(fake), method)(path, json={'velja_do': str(date.today() + timedelta(days=days))})
    assert r.status_code == 422 and not fake.calls


@pytest.mark.parametrize('days', [0, 1, 365])
def test_l3_velja_do_znotraj_okna_je_sprejet(api, days):
    from datetime import date, timedelta
    fake = Fake([]); api(fake).put(f'{M}/ponudbe/{QUOTE}', json={'velja_do': str(date.today() + timedelta(days=days))})
    assert any('uredi_ponudbo' in sql for sql, _ in fake.calls)


def test_l3_poslji_brez_velja_do_je_409_qfp12(api):
    r = api(Fake(error=qfp('QFP12'))).post(f'{M}/ponudbe/{QUOTE}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'Veljavnost ponudbe je potekla.'


@pytest.mark.parametrize('code,msg', [('QFP23', 'Projekt ima največje dovoljeno število različic ponudbe.')])
def test_l4_najvec_razlicic_je_409(api, code, msg):
    r = api(Fake(error=qfp(code))).post(f'{M}/ponudbe', json={}); assert r.status_code == 409 and r.json()['detail'] == msg


def test_l7_neveljavna_vrednost_iz_baze_je_422_s_sporocilom(api):
    for e in (psycopg.errors.InvalidParameterValue(), psycopg.errors.NullValueNotAllowed()):
        r = api(Fake(error=e)).post(f'{M}/ponudbe', json={}); assert r.status_code == 422 and r.json()['detail'] == 'Vnesena vrednost ni veljavna.'
