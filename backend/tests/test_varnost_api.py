"""G6 pentest fixes: odzivne glave, oblika žetona, velikost telesa, kratek 422, strogi decimalni nizi, okno termina in nginx glave."""
import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import auth
from app.main import app
from app.routers.cenik import CatalogInput
from app.routers.materiali import StockInput
from test_izvedba_racun import Fake, GOOD, M, api, send  # noqa: F401
from v3_support import POSTAVKA_FORM, IZ_CENIKA_FORM, VRSTA

client = TestClient(app, raise_server_exceptions=False)
HEADERS = {'x-content-type-options': 'nosniff', 'x-frame-options': 'DENY', 'referrer-policy': 'strict-origin-when-cross-origin'}
ITEM = {'naziv': 'Rušenje', 'opis': 'Odvoz', 'vrsta_dela_id': str(VRSTA), 'enota': 'm2', 'cena_na_enoto': '12.45', 'stopnja_ddv': '0.22', 'aktivna': True}


# model v3: the old quote-line models moved to the project item routes; imported lazily so the unrelated tests in this file still run before they exist
def line_models():
    from app.routers.postavke import FromCatalogInput, PostavkaInput
    return PostavkaInput, FromCatalogInput


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://project.example'); monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test')


# W1
@pytest.mark.parametrize('path', ['/api/health', '/api/me'])
def test_w1_odgovori_api_nosijo_varnostne_glave(path):
    r = client.get(path)
    for k, v in HEADERS.items(): assert r.headers.get(k) == v, (path, k)


def test_w1_glave_so_tudi_na_napakah_413_in_422():
    assert client.post('/api/demo/calculate', json={'x': 1}).headers.get('x-frame-options') == 'DENY'
    assert client.post('/api/demo/calculate', content=b'x' * (300 * 1024), headers={'content-type': 'application/json'}).headers.get('x-content-type-options') == 'nosniff'


NGINX = Path(__file__).resolve().parents[2] / 'frontend' / 'nginx.conf'


def add_headers():
    return [l.strip() for l in NGINX.read_text().splitlines() if l.strip().startswith('add_header')]


@pytest.mark.parametrize('needle', ['Content-Security-Policy', "default-src 'self'", "frame-ancestors 'none'", "object-src 'none'", "base-uri 'none'"])
def test_w1_nginx_csp_vsebuje_zahtevane_direktive(needle):
    lines = [l for l in add_headers() if 'Content-Security-Policy' in l]; assert lines and needle in lines[0] and lines[0].rstrip(';').endswith('always')


@pytest.mark.parametrize('name,value', [('X-Frame-Options', 'DENY'), ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'strict-origin-when-cross-origin')])
def test_w1_nginx_glave_z_always(name, value):
    lines = [l for l in add_headers() if name in l]; assert lines and value in lines[0] and lines[0].rstrip(';').endswith('always'), name


def test_w1_nginx_omeji_velikost_telesa():
    assert re.search(r'^\s*client_max_body_size\s+\d+[kKmM]?;', NGINX.read_text(), re.M)


# F1
def forbid(*a, **k): raise AssertionError('Supabase ne sme biti poklican')


@pytest.mark.parametrize('token', ['a' * 4097, 'x.' * 3000 + 'y', 'forged', 'a.b', 'a.b.c.d', 'a..c', 'a.b.c!', 'a.b.c d', '.b.c', 'a.b.'])
def test_f1_napacen_zeton_je_401_brez_klica_supabase(monkeypatch, token):
    monkeypatch.setattr(auth.httpx, 'get', forbid)
    r = client.get('/api/me', headers={'Authorization': f'Bearer {token}'}); assert r.status_code == 401, token


def test_f1_veljavna_oblika_zetona_gre_se_naprej_k_supabase(monkeypatch):
    called = []
    monkeypatch.setattr(auth.httpx, 'get', lambda *a, **k: called.append(1) or httpx.Response(401))
    assert client.get('/api/me', headers={'Authorization': 'Bearer aaa-_1.bbb-_2.ccc-_3'}).status_code == 401 and called


# F2
@pytest.mark.parametrize('body', [GOOD | {'termin_od': 1893456000}, GOOD | {'termin_do': 1893456000}, GOOD | {'termin_od': 1893456000.5}, GOOD | {'termin_od': 0}, GOOD | {'termin_do': True}])
def test_f2_termin_kot_stevilo_je_422(api, body):
    fake = Fake([]); assert api(fake).put(f'{M}/termin', json=body).status_code == 422 and not fake.calls


# F8
@pytest.mark.parametrize('days', [367, 400, 3000])
def test_f8_zacetek_termina_cez_366_dni_je_422(api, days):
    od = date.today() + timedelta(days=days); fake = Fake([])
    r = api(fake).put(f'{M}/termin', json={'termin_od': f'{od}T08:00:00Z', 'termin_do': f'{od}T16:00:00Z'}); assert r.status_code == 422 and not fake.calls


# F3
def test_f3_telo_nad_256_kb_je_413():
    r = client.post('/api/demo/calculate', content=b'{"a":"' + b'x' * (257 * 1024) + b'"}', headers={'content-type': 'application/json'}); assert r.status_code == 413
    assert r.headers['cache-control'] == 'no-store'


def test_f3_telo_pod_mejo_ni_413():
    assert client.post('/api/demo/calculate', json={'x': 'y' * 1000}).status_code != 413


def test_f3_deklarirana_dolzina_nad_mejo_je_413_brez_branja():
    r = client.post('/api/demo/calculate', content=b'{}', headers={'content-type': 'application/json', 'content-length': str(257 * 1024)}); assert r.status_code in (413, 400)


# F4
def test_f4_422_z_ogromnim_neznanim_kljucem_je_kratek(api):
    r = api(Fake([])).put(f'{M}/termin', json=GOOD | {'k' * 100000: 1}); assert r.status_code == 422 and len(r.content) < 1024


def test_f4_422_z_ogromno_vrednostjo_je_kratek(api):
    r = api(Fake([])).put(f'{M}/termin', json={'termin_od': 'z' * 100000, 'termin_do': 'z' * 100000}); assert r.status_code == 422 and len(r.content) < 1024


# F5 / F6
BAD = ['1_000', '+5', ' 5 ', '1e6', '1E2', '٣', '５', '.5', '5.', '0x10', '-1', '1,5', 'NaN', 'Infinity', '']
GOOD_NUM = ['0', '1', '100', '0.22', '12.4500', '007']


@pytest.mark.parametrize('bad', BAD)
@pytest.mark.parametrize('field', ['cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'urna_postavka', 'stevilo_ur'])
def test_f5_postavka_projekta_sprejme_samo_navaden_decimalni_niz(field, bad):
    PostavkaInput, _ = line_models()
    PostavkaInput(**POSTAVKA_FORM)
    with pytest.raises(ValidationError): PostavkaInput(**(POSTAVKA_FORM | {field: bad}))


@pytest.mark.parametrize('bad', BAD)
@pytest.mark.parametrize('field', ['kolicina', 'popust'])
def test_f5_postavka_iz_cenika_sprejme_samo_navaden_decimalni_niz(field, bad):
    _, FromCatalogInput = line_models()
    FromCatalogInput(**IZ_CENIKA_FORM)
    with pytest.raises(ValidationError): FromCatalogInput(**(IZ_CENIKA_FORM | {field: bad}))


@pytest.mark.parametrize('bad', [x for x in BAD if x not in ('-1', 'NaN', 'Infinity', '')] + ['-0.5'])
def test_f6_cenik_in_zaloga_sprejmeta_samo_navaden_decimalni_niz(bad):
    for field in ('cena_na_enoto', 'stopnja_ddv'):
        with pytest.raises(ValidationError): CatalogInput(**(ITEM | {field: bad}))
    with pytest.raises(ValidationError): StockInput(lokacija='Skladisce', kolicina=bad)


@pytest.mark.parametrize('field', ['cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv'])
def test_f5_json_stevilo_je_422(field):
    PostavkaInput, _ = line_models()
    PostavkaInput(**POSTAVKA_FORM)
    for v in (0.22, 1, 5.5):
        with pytest.raises(ValidationError): PostavkaInput(**(POSTAVKA_FORM | {field: v}))


def test_f6_json_stevilo_za_ddv_v_ceniku_je_422():
    with pytest.raises(ValidationError): CatalogInput(**(ITEM | {'stopnja_ddv': 0.22}))


def test_f5_json_stevilo_0_22_za_ddv_postavke_je_422_prek_api(api):
    import json
    fake = Fake([]); r = api(fake).post(f'{M}/postavke', content=json.dumps(POSTAVKA_FORM | {'stopnja_ddv': 0.22}), headers={'content-type': 'application/json'}); assert r.status_code == 422 and not fake.calls


@pytest.mark.parametrize('good', GOOD_NUM)
def test_f5_navadni_nizi_se_vedno_veljajo(good):
    PostavkaInput, _ = line_models()
    assert PostavkaInput(**(POSTAVKA_FORM | {'cena_na_enoto': '1', 'kolicina': '1', 'popust': '0', 'stopnja_ddv': '0.22' if good == '0.22' else '0'})).stopnja_ddv >= 0
    assert CatalogInput(**(ITEM | {'cena_na_enoto': good if Decimal(good) < 1000 else '1'})).cena_na_enoto == Decimal(good)


# regression lock: PostgREST ne razkrije poslovnih shem
ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'
REST = 'http://127.0.0.1:54321/rest/v1'


@pytest.fixture(scope='module')
def rest():
    try: httpx.get(REST + '/', headers={'apikey': ANON}, timeout=2)
    except httpx.HTTPError: pytest.skip('Lokalni PostgREST ni dosegljiv')
    return {'apikey': ANON, 'Authorization': f'Bearer {ANON}'}


@pytest.mark.parametrize('schema', ['quoteflow', 'quoteflow_private'])
@pytest.mark.parametrize('table', ['projekt', 'ponudba', 'racun', 'podjetje', 'uporabnik', 'dogodek_dokumenta'])
def test_postgrest_anon_ne_vidi_tabel_poslovnih_shem(rest, schema, table):
    assert httpx.get(f'{REST}/{table}', headers=rest | {'Accept-Profile': schema}, timeout=5).status_code in (404, 406)


@pytest.mark.parametrize('fn', ['izdaj_racun', 'poslji_ponudbo', 'odgovori_ponudbo', 'dodeli_vlogo', 'ustvari_podjetje', 'doloci_termin'])
def test_postgrest_anon_ne_poklice_zasebnih_funkcij(rest, fn):
    for schema in ('quoteflow', 'quoteflow_private'):
        assert httpx.post(f'{REST}/rpc/{fn}', headers=rest | {'Content-Profile': schema}, json={}, timeout=5).status_code in (404, 406), (schema, fn)
    assert httpx.post(f'{REST}/rpc/{fn}', headers=rest, json={}, timeout=5).status_code == 404
