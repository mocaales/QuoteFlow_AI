"""US-06/US-07 termin, izvedba, račun: validacija, preslikava napak in zaščita poti s fake povezavo."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, customer, session_database
from app.auth import Principal, current_user
from app.main import app

TODAY = datetime.now(ZoneInfo('Europe/Ljubljana')).date()
DUE = (TODAY + timedelta(days=30)).isoformat()
START, BEFORE, END = (f'{(TODAY + timedelta(days=30 + n)).isoformat()}T{t}:00:00Z' for n, t in ((10, '08'), (9, '08'), (12, '16')))
ME = Principal(uuid4(), uuid4(), 'ana@example.test')
COMPANY, PROJECT = uuid4(), uuid4()
M = f'/api/podjetja/{COMPANY}/projekti/{PROJECT}'
OWN = f'/api/projekti/{PROJECT}/racun'
ISSUE = {'prejemnik_naziv': 'Ana Novak', 'prejemnik_naslov': 'Cesta 1, Maribor', 'zapade_dne': DUE}
GOOD = {'termin_od': START, 'termin_do': END}
MESSAGES = {'QFP07': 'V tej fazi projekta to dejanje ni dovoljeno.', 'QFP14': 'Izvedbe ni mogoče zaključiti pred začetkom termina.', 'QFP15': 'Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.',
            'QFP18': 'Termin se ne sme začeti v preteklosti.', 'QFP21': 'Rok plačila ne sme biti pred datumom izdaje.'}
ROUTES = [('put', f'{M}/termin', GOOD), ('post', f'{M}/izvedba', None), ('post', f'{M}/racun/izdaj', ISSUE), ('post', f'{M}/racun/placilo', None)]


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


def send(client, method, path, body): return getattr(client, method)(path, json=body) if body is not None else getattr(client, method)(path)


def test_termin_pokliče_funkcijo_s_podjetjem_projektom_in_casom(api):
    fake = Fake([]); api(fake).put(f'{M}/termin', json=GOOD)
    assert any('quoteflow_private.doloci_termin' in sql and COMPANY in p and PROJECT in p and len(p) == 4 for sql, p in fake.calls)


def test_izvedba_in_placilo_poklicete_funkciji_s_podjetjem_in_projektom(api):
    for path, fn in ((f'{M}/izvedba', 'zakljuci_izvedbo'), (f'{M}/racun/placilo', 'placaj_racun')):
        fake = Fake([]); api(fake).post(path); assert any(f'quoteflow_private.{fn}' in sql and COMPANY in p and PROJECT in p for sql, p in fake.calls), fn


def test_izdaja_poklice_funkcijo_s_prejemnikom_naslovom_in_rokom_placila(api):
    fake = Fake([]); api(fake).post(f'{M}/racun/izdaj', json=ISSUE | {'prejemnik_naziv': '  Ana Novak  '})
    assert any('quoteflow_private.izdaj_racun' in sql and sql.count('%s') == 5 and COMPANY in p and PROJECT in p and 'Ana Novak' in p and 'Cesta 1, Maribor' in p and any(str(x) == DUE for x in p) and len(p) == 5 for sql, p in fake.calls)


def test_konec_termina_mora_biti_po_zacetku(api):
    for do in (START, BEFORE):
        fake = Fake([]); r = api(fake).put(f'{M}/termin', json=GOOD | {'termin_do': do}); assert r.status_code == 422 and 'Konec termina mora biti po začetku.' in r.text and not fake.calls


@pytest.mark.parametrize('body', [{}, {'termin_od': START}, {'termin_od': START, 'termin_do': None}, {'termin_od': None, 'termin_do': START}, GOOD | {'termin_od': 'jutri'},
                                  GOOD | {'termin_od': 'infinity'}, GOOD | {'termin_do': 'infinity'}, GOOD | {'termin_do': '2032-01-01T00:00:00Z'}, GOOD | {'x': 1}, GOOD | {'faza': 'zakljucen'}])
def test_neveljaven_termin_je_422_brez_klica_baze(api, body):
    fake = Fake([]); assert api(fake).put(f'{M}/termin', json=body).status_code == 422 and not fake.calls


@pytest.mark.parametrize('change', [{'zapade_dne': None}, {'zapade_dne': 'jutri'}, {'zapade_dne': '2030-13-40'}, {'zapade_dne': 7}, {'stevilka': 'R-1'}, {'izdajatelj_naziv': 'X'}, {'prejemnik_e_posta': 'a@b.si'},
                                    {'prejemnik_naziv': ''}, {'prejemnik_naziv': '  '}, {'prejemnik_naziv': 'x' * 201}, {'prejemnik_naziv': None}, {'prejemnik_naziv': 5}, {'prejemnik_naslov': ''}, {'prejemnik_naslov': ' '},
                                    {'prejemnik_naslov': 'x' * 301}, {'prejemnik_naslov': None}, {'prejemnik_naziv': 'a\x00b'}])
def test_neveljavna_izdaja_je_422_brez_klica_baze(api, change):
    fake = Fake([]); assert api(fake).post(f'{M}/racun/izdaj', json=ISSUE | change).status_code == 422 and not fake.calls


@pytest.mark.parametrize('missing', ['prejemnik_naziv', 'prejemnik_naslov', 'zapade_dne'])
def test_izdaja_brez_obveznega_polja_je_422(api, missing):
    fake = Fake([]); body = dict(ISSUE); body.pop(missing); assert api(fake).post(f'{M}/racun/izdaj', json=body).status_code == 422 and not fake.calls
    assert api(Fake([])).post(f'{M}/racun/izdaj', json={}).status_code == 422


def test_najdaljsi_veljaven_prejemnik_je_sprejet(api):
    fake = Fake([]); api(fake).post(f'{M}/racun/izdaj', json=ISSUE | {'prejemnik_naziv': 'n' * 200, 'prejemnik_naslov': 'a' * 300})
    assert any('izdaj_racun' in sql for sql, _ in fake.calls)




@pytest.mark.parametrize('body', [{'znesek': '100'}, {'placano_ob': START}, {'stevilka': 'R-1'}])
def test_placilo_zavrne_telo_z_vsebino_422(api, body):
    fake = Fake([]); assert api(fake).post(f'{M}/racun/placilo', json=body).status_code == 422 and not fake.calls


def test_id_ni_uuid_je_422(api):
    c = api(Fake([]))
    for method, path, body in ((m, p.replace(str(PROJECT), 'ni-uuid'), b) for m, p, b in ROUTES): assert send(c, method, path, body).status_code == 422, path
    assert c.get('/api/projekti/ni-uuid/racun').status_code == 422


@pytest.mark.parametrize('method,path,body', ROUTES)
@pytest.mark.parametrize('code', ['QFP07', 'QFP14', 'QFP15', 'QFP18', 'QFP21'])
def test_poslovne_napake_so_409_s_slovenskim_sporocilom(api, method, path, body, code):
    r = send(api(Fake(error=qfp(code))), method, path, body); assert r.status_code == 409 and r.json()['detail'] == MESSAGES[code]


@pytest.mark.parametrize('method,path,body', ROUTES + [('get', f'{M}/racun', None)])
def test_neznan_zapis_je_404_brez_pravice_403(api, method, path, body):
    r = send(api(Fake(error=psycopg.errors.NoDataFound())), method, path, body); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert send(api(Fake(error=psycopg.errors.InsufficientPrivilege())), method, path, body).status_code == 403


def test_zaklenjen_racun_je_409_in_ne_503(api):
    r = send(api(Fake(error=psycopg.errors.ObjectNotInPrerequisiteState())), 'post', f'{M}/racun/placilo', None); assert r.status_code == 409 and r.json()['detail'] == 'Dokument je zaklenjen in ga ni mogoče spremeniti.'


def test_vrednost_izven_meje_iz_baze_je_422(api):
    r = send(api(Fake(error=psycopg.errors.DatetimeFieldOverflow())), 'put', f'{M}/termin', GOOD); assert r.status_code == 422 and r.json()['detail'] == 'Vrednost presega dovoljeno mejo.'


def test_racun_mojstra_brez_vrstic_je_404_in_filtrira_po_podjetju(api):
    fake = Fake([]); assert api(fake).get(f'{M}/racun').status_code == 404 and any(COMPANY in p and PROJECT in p for _, p in fake.calls)


def test_racun_stranke_brez_vrstic_je_404_in_filtrira_po_stranki(api):
    fake = Fake([]); r = api(fake).get(OWN); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert any(PROJECT in p and ME.id in p for _, p in fake.calls)


def test_nove_poti_brez_zetona_so_401():
    c = TestClient(app, raise_server_exceptions=False)
    for method, path, body in ROUTES + [('get', f'{M}/racun', None), ('get', OWN, None)]: assert send(c, method, path, body).status_code == 401, (method, path)
