"""US-02 materialna sestava postavke cenika: API validation, status mapping and guards with a fake connection."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'mojster@example.test')
COMPANY, ITEM, MATERIAL = uuid4(), uuid4(), uuid4()
BASE = f'/api/podjetja/{COMPANY}/cenik/{ITEM}/sestava'


def row(**change):
    return {'material_id': MATERIAL, 'sifra': 'LEP-1', 'naziv': 'Lepilo', 'enota': 'kg', 'aktiven': True, 'kolicina_na_enoto': '1.2500'} | change


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


def test_seznam_sestave_vrne_material_in_kolicino_kot_niz(api):
    fake = Fake([row(), row(material_id=uuid4(), sifra='CEM-1', naziv='Cement', aktiven=False, kolicina_na_enoto='0.5000')])
    r = api(fake).get(BASE)
    assert r.status_code == 200 and len(r.json()) == 2
    assert set(r.json()[0]) == {'material_id', 'sifra', 'naziv', 'enota', 'aktiven', 'kolicina_na_enoto'}
    assert isinstance(r.json()[0]['kolicina_na_enoto'], str) and r.json()[1]['aktiven'] is False
    assert any('sestava_cenika' in sql and ITEM in p for sql, p in fake.calls if p)


def test_shrani_sestavo_poklice_funkcijo_in_vrne_vrstico(api):
    fake = Fake([row()])
    r = api(fake).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1.25'})
    assert r.status_code == 200 and r.json()['material_id'] == str(MATERIAL) and r.json()['kolicina_na_enoto'] == '1.2500'
    assert any('quoteflow_private.shrani_sestavo' in sql for sql, _ in fake.calls)
    assert any(COMPANY in p and ITEM in p and MATERIAL in p for _, p in fake.calls if p)


@pytest.mark.parametrize('value', ['0', '-1', '-0.0001', '1.23456', 'NaN', 'Infinity', '', None, 'abc'])
def test_neveljavna_kolicina_je_422_in_ne_doseze_baze(api, value):
    fake = Fake([row()])
    assert api(fake).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': value}).status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize('body', [{}, {'kolicina_na_enoto': '1', 'material_id': str(uuid4())}, {'kolicina_na_enoto': '1', 'podjetje_id': str(uuid4())}])
def test_manjkajoca_ali_dodatna_polja_so_422(api, body):
    fake = Fake([row()])
    assert api(fake).put(f'{BASE}/{MATERIAL}', json=body).status_code == 422 and fake.calls == []


def test_stirje_decimalke_so_dovoljene(api):
    assert api(Fake([row()])).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '0.0001'}).status_code == 200


def test_neaktiven_material_je_409_s_slovenskim_sporocilom(api):
    r = api(Fake(error=qfp('QFP05'))).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1'})
    assert r.status_code == 409 and r.json()['detail'] == 'Neaktivnega materiala ni mogoče dodati v sestavo.'


def test_tuja_postavka_ali_material_je_404(api):
    assert api(Fake(error=psycopg.errors.NoDataFound())).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1'}).status_code == 404
    assert api(Fake(error=psycopg.errors.NoDataFound())).delete(f'{BASE}/{MATERIAL}').status_code == 404


def test_brez_pravice_v_funkciji_je_403(api):
    assert api(Fake(error=psycopg.errors.InsufficientPrivilege())).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1'}).status_code == 403


def test_odstrani_sestavo_vrne_204_brez_telesa(api):
    fake = Fake([])
    r = api(fake).delete(f'{BASE}/{MATERIAL}')
    assert r.status_code == 204 and r.content == b''
    assert any('quoteflow_private.odstrani_sestavo' in sql and COMPANY in p and ITEM in p and MATERIAL in p for sql, p in fake.calls)


def test_nemojster_dobi_403_na_vseh_poteh_sestave():
    fake = Fake([{'allowed': False}])
    app.dependency_overrides[current_user] = lambda: ME
    app.dependency_overrides[session_database] = lambda: fake
    try:
        c = TestClient(app, raise_server_exceptions=False)
        assert c.get(BASE).status_code == 403
        assert c.put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1'}).status_code == 403
        assert c.delete(f'{BASE}/{MATERIAL}').status_code == 403
        assert not any('sestav' in sql for sql, _ in fake.calls)
    finally: app.dependency_overrides.clear()


def test_sestava_tuje_ali_neobstojece_postavke_je_404(api):
    r = api(Fake([])).get(f'/api/podjetja/{COMPANY}/cenik/{uuid4()}/sestava')
    assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


@pytest.mark.parametrize('field', ['naziv', 'opis', 'vrsta_dela', 'enota'])
def test_nul_znak_v_ceniku_je_422(api, field):
    fake = Fake([row()])
    body = {'naziv': 'Ploščice', 'opis': 'Polaganje', 'vrsta_dela': 'Keramika', 'enota': 'm2', 'cena_na_enoto': '10', 'stopnja_ddv': '0.22'} | {field: 'a\x00b'}
    assert api(fake).post(f'/api/podjetja/{COMPANY}/cenik', json=body).status_code == 422 and fake.calls == []


def test_nul_znak_v_sestavi_je_422(api):
    fake = Fake([row()])
    assert api(fake).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': '1\x00'}).status_code == 422 and fake.calls == []


@pytest.mark.parametrize('value', ['1_0', '１２', '1e2', '+1', '.5', '5.', '1.', '123456789012345'])
def test_kolicina_samo_navadno_decimalno_stevilo_422(api, value):
    fake = Fake([row()])
    assert api(fake).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': value}).status_code == 422 and fake.calls == []


@pytest.mark.parametrize('value', ['1', '0.5', '12.3456'])
def test_kolicina_navadno_decimalno_stevilo_je_sprejeto(api, value):
    assert api(Fake([row()])).put(f'{BASE}/{MATERIAL}', json={'kolicina_na_enoto': value}).status_code == 200
