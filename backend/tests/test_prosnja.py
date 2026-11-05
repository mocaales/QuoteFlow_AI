"""US-01 prošnja mojstra: API validation, status mapping and own-only filter with a fake connection."""
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import administrator, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'ana@example.test')
FORM = {'naziv_podjetja': 'Mojster Novak d.o.o.', 'maticna_stevilka': '1234567000', 'davcna_stevilka': 'SI12345678', 'naslov_podjetja': 'Cesta 1, Maribor'}


def row(**change):
    return {'id': uuid4(), 'uporabnik_id': ME.id, 'naziv_podjetja': 'Mojster Novak d.o.o.', 'maticna_stevilka': '1234567000', 'davcna_stevilka': None,
            'naslov_podjetja': 'Cesta 1, Maribor', 'stanje': 'oddana', 'podjetje_id': None, 'oddano_ob': datetime.now(timezone.utc), 'odloceno_ob': None} | change


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


@pytest.fixture
def api():
    def use(fake, admin=False):
        app.dependency_overrides[current_user] = lambda: ME
        app.dependency_overrides[session_database] = lambda: fake
        if admin: app.dependency_overrides[administrator] = lambda: fake
        return TestClient(app, raise_server_exceptions=False)
    try: yield use
    finally: app.dependency_overrides.clear()


def test_oddaja_prosnje_vrne_201_in_prirezane_podatke(api):
    fake = Fake([row(davcna_stevilka='SI12345678')])
    r = api(fake).post('/api/prosnje', json=FORM | {'naziv_podjetja': '  Mojster Novak d.o.o.  '})
    assert r.status_code == 201, r.text
    assert r.json()['stanje'] == 'oddana' and r.json()['naziv_podjetja'] == 'Mojster Novak d.o.o.'
    assert any('Mojster Novak d.o.o.' in map(str, p) and '  Mojster Novak d.o.o.  ' not in map(str, p) for _, p in fake.calls if p)


def test_davcna_stevilka_je_neobvezna(api):
    assert api(Fake([row()])).post('/api/prosnje', json={k: v for k, v in FORM.items() if k != 'davcna_stevilka'}).status_code == 201
    assert api(Fake([row()])).post('/api/prosnje', json=FORM | {'davcna_stevilka': None}).status_code == 201


@pytest.mark.parametrize('change', [
    {'naziv_podjetja': ' '}, {'maticna_stevilka': ''}, {'naslov_podjetja': '   '}, {'naziv_podjetja': None},
    {'stanje': 'odobrena'}, {'uporabnik_id': str(uuid4())}, {'podjetje_id': str(uuid4())},
])
def test_neveljavna_prosnja_je_422_in_ne_doseze_baze(api, change):
    fake = Fake([row()])
    assert api(fake).post('/api/prosnje', json=FORM | change).status_code == 422
    assert fake.calls == []


def qfp(code):
    # psycopg exposes unknown SQLSTATEs as a generic DatabaseError whose `sqlstate` is the code
    class Custom(psycopg.DatabaseError): sqlstate = code
    return Custom()


M_OBRAVNAVANA, M_ODDANA = 'Prošnja je že obravnavana.', 'Že imate oddano prošnjo, ki čaka na odločitev.'
M_POGOJI = 'Vlagatelj ne izpolnjuje pogojev za vlogo mojstra (potrjena e-pošta in aktivna vloga stranke ali delavca).'
M_MATICNA = 'Podjetje ali oddana prošnja s to matično številko že obstaja.'


def test_obstojeca_maticna_je_409_s_slovenskim_sporocilom(api):
    r = api(Fake(error=qfp('QFP04'))).post('/api/prosnje', json=FORM)
    assert r.status_code == 409 and r.json()['detail'] == M_MATICNA


def test_ze_oddana_prosnja_je_409_s_slovenskim_sporocilom(api):
    r = api(Fake(error=qfp('QFP02'))).post('/api/prosnje', json=FORM)
    assert r.status_code == 409 and r.json()['detail'] == M_ODDANA


@pytest.mark.parametrize('error', [psycopg.errors.UniqueViolation, psycopg.errors.ObjectNotInPrerequisiteState])
def test_splosne_napake_oddaje_niso_vec_409_iz_poti(api, error):
    r = api(Fake(error=error())).post('/api/prosnje', json=FORM)
    assert r.status_code != 409 and 'matično' not in r.json()['detail'] and 'oddano prošnjo' not in r.json()['detail']


def test_brez_pravice_za_oddajo_je_403(api):
    assert api(Fake(error=psycopg.errors.InsufficientPrivilege())).post('/api/prosnje', json=FORM).status_code == 403


def test_seznam_vrne_samo_lastne_prosnje_najnovejse_prve(api):
    fake = Fake([row(), row(stanje='zavrnjena')])
    r = api(fake).get('/api/prosnje')
    assert r.status_code == 200 and len(r.json()) == 2
    sql, params = fake.calls[-1]
    assert 'prosnja_mojstra' in sql and 'uporabnik_id' in sql and 'oddano_ob desc' in sql.lower()
    assert ME.id in params or str(ME.id) in map(str, params)


def test_admin_seznam_vsebuje_podatke_vlagatelja(api):
    fake = Fake([row() | {'e_posta': 'ana@example.test', 'ime': 'Ana', 'priimek': 'Novak'}])
    r = api(fake, admin=True).get('/api/admin/prosnje')
    assert r.status_code == 200
    assert {'e_posta', 'ime', 'priimek'} <= r.json()[0].keys()
    sql = fake.calls[-1][0].lower()
    assert "stanje='oddana'" in sql.replace(' ', '') or "stanje = 'oddana'" in sql


@pytest.mark.parametrize('odobri', [True, False])
def test_odlocitev_poklice_funkcijo_z_id_in_odlocitvijo(api, odobri):
    pid = uuid4(); fake = Fake([row(id=pid, stanje='odobrena' if odobri else 'zavrnjena')])
    r = api(fake, admin=True).post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': odobri})
    assert r.status_code == 200, r.text
    sql, params = fake.calls[-1]
    assert 'odloci_prosnjo' in sql and pid in params and odobri in params


@pytest.mark.parametrize('body', [{}, {'odobri': 'da'}, {'odobri': 1}, {'odobri': True, 'x': 1}])
def test_odlocitev_zahteva_strog_bool(api, body):
    assert api(Fake([row()]), admin=True).post(f'/api/admin/prosnje/{uuid4()}/odlocitev', json=body).status_code == 422


def decide(api, error):
    return api(Fake(error=error), admin=True).post(f'/api/admin/prosnje/{uuid4()}/odlocitev', json={'odobri': True})


def test_ze_obravnavana_prosnja_je_409(api):
    r = decide(api, qfp('QFP01')); assert r.status_code == 409 and r.json()['detail'] == M_OBRAVNAVANA


def test_neupravicen_vlagatelj_je_409_z_razlogom(api):
    r = decide(api, qfp('QFP03')); assert r.status_code == 409 and r.json()['detail'] == M_POGOJI


def test_odobritev_z_zasedeno_maticno_je_409(api):
    r = decide(api, qfp('QFP04')); assert r.status_code == 409 and r.json()['detail'] == M_MATICNA


def test_navadna_check_violation_pri_odlocitvi_je_422_ne_obravnavana(api):
    r = decide(api, psycopg.errors.CheckViolation()); assert r.status_code == 422 and r.json()['detail'] != M_OBRAVNAVANA


@pytest.mark.parametrize('error', [psycopg.errors.UniqueViolation, psycopg.errors.ObjectNotInPrerequisiteState])
def test_odlocitev_ne_mapira_splosnih_napak_v_409_prosnje(api, error):
    assert decide(api, error()).json()['detail'] not in (M_POGOJI, M_OBRAVNAVANA, M_MATICNA)


@pytest.mark.parametrize('code, message', [('QFP01', M_OBRAVNAVANA), ('QFP02', M_ODDANA), ('QFP03', M_POGOJI), ('QFP04', M_MATICNA)])
def test_osrednji_handler_preslika_qfp_na_kateri_koli_poti(api, code, message):
    r = api(Fake(error=qfp(code))).get(f'/api/podjetja/{uuid4()}/cenik')
    assert r.status_code == 409 and r.json()['detail'] == message


def test_neznan_sqlstate_ni_409(api):
    assert api(Fake(error=qfp('QFP99'))).get(f'/api/podjetja/{uuid4()}/cenik').status_code == 503


def test_neobstojeca_prosnja_je_404(api):
    assert api(Fake(error=psycopg.errors.NoDataFound()), admin=True).post(f'/api/admin/prosnje/{uuid4()}/odlocitev', json={'odobri': False}).status_code == 404


def test_odlocitev_neveljavnega_id_je_422(api):
    assert api(Fake(), admin=True).post('/api/admin/prosnje/ni-uuid/odlocitev', json={'odobri': True}).status_code == 422
