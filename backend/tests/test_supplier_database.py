"""Katalog (cenik z vrsto dela), materiali, zaloga in vrste dela z materiali: API in izolacija na disposable local Supabase (model v3)."""
import os
from uuid import uuid4
import pytest
from test_model_database import db, identities, as_user
from test_identity_database import api_client
from test_supplier import ITEM as ITEM_V3
from app.errors import CONFLICTS
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')

VRSTA = {'naziv': 'Polaganje ploščic', 'opis': 'Keramika', 'urna_postavka': '25', 'stevilo_ur': '8', 'stevilo_delavcev': 2, 'aktivna': True}


@pytest.fixture
def master_api(api_client, identities):
    client, selected = api_client; selected['name'] = 'owner_a'
    return client, selected, f'/api/podjetja/{identities[1]}'


def make_vrsta(client, base, **change):
    r = client.post(base + '/vrste-dela', json=VRSTA | change); assert r.status_code == 201, r.text; return r.json()


@pytest.fixture
def vrsta_a(master_api): return make_vrsta(master_api[0], master_api[2])


@pytest.fixture
def ITEM(vrsta_a): return ITEM_V3 | {'vrsta_dela_id': vrsta_a['id']}


def test_cenik_decimalne_cene_urejanje_in_deaktivacija(master_api, ITEM):
    client, _, base = master_api
    response = client.post(base + '/cenik', json=ITEM); assert response.status_code == 201, response.text
    item = response.json()
    assert float(item['cena_na_enoto']) == 12.45 and float(item['stopnja_ddv']) == .22
    assert 'strosek_na_enoto' not in item and 'potrjeno_ob' not in item
    path = base + '/cenik/' + item['id']
    response = client.put(path, json=ITEM | {'cena_na_enoto': '25.125', 'aktivna': False})
    assert response.status_code == 200 and response.json()['aktivna'] is False
    assert float(client.get(base + '/cenik').json()[0]['cena_na_enoto']) == 25.125
    assert client.put(base + '/cenik/' + str(uuid4()), json=ITEM).status_code == 404
    assert client.post(base + '/pravila', json={}).status_code == 404
    assert client.post(path + '/potrditev').status_code == 404

@pytest.fixture
def material(master_api):
    client, _, base = master_api
    response = client.post(base + '/vrste-materiala', json={'naziv': 'Lepila'}); assert response.status_code == 201, response.text
    payload = {'vrsta_materiala_id': response.json()['id'], 'sifra': 'LEP-1', 'naziv': 'Lepilo', 'enota': 'kg', 'cena_na_enoto': '2.1234', 'aktiven': True}
    response = client.post(base + '/materiali', json=payload); assert response.status_code == 201, response.text
    return response.json(), payload


def test_zaloga_po_lokacijah_locuje_nic_in_nevodenje(master_api, material):
    client, _, base = master_api; item, _ = material
    path = base + '/materiali/' + item['id'] + '/zaloga'
    assert client.get(path).json() == []
    assert client.put(path, json={'lokacija': 'Maribor', 'kolicina': '0'}).status_code == 200
    assert client.put(path, json={'lokacija': 'Celje', 'kolicina': '2.125'}).status_code == 200
    assert {r['lokacija']: float(r['kolicina']) for r in client.get(path).json()} == {'Celje': 2.125, 'Maribor': 0}
    assert client.delete(path, params={'lokacija': 'Maribor'}).status_code == 200
    assert [r['lokacija'] for r in client.get(path).json()] == ['Celje']
    assert client.put(path, json={'lokacija': 'Celje', 'kolicina': '-1'}).status_code == 422


def test_material_ne_spremeni_enote_in_podvojene_sifre(master_api, material):
    client, _, base = master_api; item, payload = material
    assert client.post(base + '/materiali', json=payload).status_code in (409, 422)
    assert client.put(base + '/materiali/' + item['id'], json=payload | {'enota': 'm'}).status_code in (409, 422)
    assert client.put(base + '/materiali/' + item['id'], json=payload | {'cena_na_enoto': '3'}).status_code == 200


def test_tuja_podjetja_delavec_stranka_admin_in_odvzeta_vloga(master_api, material, identities, ITEM):
    client, selected, base = master_api; users, a, b, _ = identities
    item, payload = material; own_item = client.post(base + '/cenik', json=ITEM).json()
    foreign = f'/api/podjetja/{b}'
    for actor in ('owner_b', 'worker', 'customer', 'admin', 'outsider'):
        selected['name'] = actor
        assert client.get(base + '/cenik').status_code == 403
        assert client.put(base + '/cenik/' + own_item['id'], json=ITEM).status_code == 403
        assert client.put(base + '/materiali/' + item['id'] + '/zaloga', json={'lokacija': 'X', 'kolicina': '100'}).status_code == 403
    selected['name'] = 'owner_a'
    assert client.get(foreign + '/cenik').status_code == 403
    selected['name'] = 'owner_b'
    assert client.put(foreign + '/materiali/' + item['id'], json=payload).status_code in (403, 404, 422)
    assert client.get(foreign + '/materiali/' + item['id'] + '/zaloga').status_code == 404
    assert client.get(foreign + '/materiali/' + str(uuid4()) + '/zaloga').status_code == 404
    selected['name'] = 'admin'
    role = client.post('/api/admin/vloge', json={'uporabnik_id': str(users['worker'][0]), 'podjetje_id': str(a), 'vloga': 'mojster'}).json()
    selected['name'] = 'worker'; assert client.get(base + '/cenik').status_code == 200
    selected['name'] = 'admin'; assert client.patch('/api/admin/vloge/' + role['id'], json={'aktivna': False}).status_code == 200
    selected['name'] = 'worker'; assert client.get(base + '/cenik').status_code == 403


def test_vrsta_dela_cena_dela_je_izpeljana_in_seznam_ima_materiale(master_api, vrsta_a, material):
    client, _, base = master_api; vid = vrsta_a['id']; mat = material[0]['id']
    assert vrsta_a['cena_dela'] == '400.00' and vrsta_a.get('materiali', []) == [] and vrsta_a['stevilo_delavcev'] == 2
    assert client.put(f'{base}/vrste-dela/{vid}/materiali/{mat}', json={'kolicina_na_enoto': '1.25'}).status_code in (200, 201)
    listed = next(v for v in client.get(base + '/vrste-dela').json() if v['id'] == vid)
    assert [(m['material_id'], m['sifra'] if 'sifra' in m else 'LEP-1', m['enota'], float(m['kolicina_na_enoto'])) for m in listed['materiali']] == [(mat, 'LEP-1', 'kg', 1.25)]
    assert client.put(f'{base}/vrste-dela/{vid}', json=VRSTA | {'urna_postavka': '30', 'stevilo_ur': '1', 'stevilo_delavcev': 1}).json()['cena_dela'] == '30.00'


def test_vrsta_dela_material_dodaj_spremeni_odstrani_in_decimalna_kolicina(master_api, vrsta_a, material):
    client, _, base = master_api; path = f"{base}/vrste-dela/{vrsta_a['id']}/materiali/{material[0]['id']}"
    assert client.put(path, json={'kolicina_na_enoto': '1.25'}).status_code in (200, 201) and client.put(path, json={'kolicina_na_enoto': '0.0001'}).status_code in (200, 201)
    row = next(v for v in client.get(base + '/vrste-dela').json() if v['id'] == vrsta_a['id']); assert len(row['materiali']) == 1 and float(row['materiali'][0]['kolicina_na_enoto']) == 0.0001
    assert client.delete(path).status_code == 204
    assert next(v for v in client.get(base + '/vrste-dela').json() if v['id'] == vrsta_a['id'])['materiali'] == []


@pytest.mark.parametrize('value', ['0', '-1', '1.23456'])
def test_vrsta_dela_material_neveljavna_kolicina_je_422(master_api, vrsta_a, material, value):
    client, _, base = master_api
    assert client.put(f"{base}/vrste-dela/{vrsta_a['id']}/materiali/{material[0]['id']}", json={'kolicina_na_enoto': value}).status_code == 422


def test_vrsta_dela_neaktiven_material_ne_gre_v_vrsto_a_se_odstrani(master_api, vrsta_a, material):
    client, _, base = master_api; mat = material[0]['id']; path = f"{base}/vrste-dela/{vrsta_a['id']}/materiali/{mat}"
    assert client.put(path, json={'kolicina_na_enoto': '2'}).status_code in (200, 201)
    assert client.put(f'{base}/materiali/{mat}', json=material[1] | {'aktiven': False}).status_code == 200
    r = client.put(path, json={'kolicina_na_enoto': '3'}); assert r.status_code == 409 and r.json()['detail'] == CONFLICTS['QFP05']
    row = next(v for v in client.get(base + '/vrste-dela').json() if v['id'] == vrsta_a['id']); assert row['materiali'][0]['aktiven'] is False and float(row['materiali'][0]['kolicina_na_enoto']) == 2
    assert client.delete(path).status_code == 204


def test_cenik_z_neaktivno_vrsto_dela_je_409_qfp29_in_s_tujo_404(master_api, vrsta_a, ITEM, identities):
    client, selected, base = master_api; _, a, b, _ = identities
    assert client.put(f"{base}/vrste-dela/{vrsta_a['id']}", json=VRSTA | {'aktivna': False}).status_code == 200
    r = client.post(base + '/cenik', json=ITEM); assert r.status_code == 409 and r.json()['detail'] == CONFLICTS['QFP29']
    selected['name'] = 'owner_b'; foreign = make_vrsta(client, f'/api/podjetja/{b}')
    selected['name'] = 'owner_a'
    r = client.post(base + '/cenik', json=ITEM_V3 | {'vrsta_dela_id': foreign['id']}); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert client.post(base + '/cenik', json=ITEM_V3 | {'vrsta_dela_id': str(uuid4())}).json() == r.json()


def test_vrste_dela_tuje_podjetje_delavec_stranka_admin(master_api, vrsta_a, material, identities):
    client, selected, base = master_api; _, a, b, _ = identities; vid, mat = vrsta_a['id'], material[0]['id']; path = f'{base}/vrste-dela/{vid}/materiali/{mat}'
    for actor in ('owner_b', 'worker', 'customer', 'admin', 'outsider'):
        selected['name'] = actor
        assert client.get(base + '/vrste-dela').status_code == 403 and client.post(base + '/vrste-dela', json=VRSTA).status_code == 403 and client.put(f'{base}/vrste-dela/{vid}', json=VRSTA).status_code == 403
        assert client.put(path, json={'kolicina_na_enoto': '1'}).status_code == 403 and client.delete(path).status_code == 403, actor
    selected['name'] = 'owner_b'; foreign = f'/api/podjetja/{b}'
    for r in (client.put(f'{foreign}/vrste-dela/{vid}', json=VRSTA), client.put(f'{foreign}/vrste-dela/{vid}/materiali/{mat}', json={'kolicina_na_enoto': '1'}), client.delete(f'{foreign}/vrste-dela/{vid}/materiali/{mat}')):
        assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    assert client.put(f'{foreign}/vrste-dela/{uuid4()}', json=VRSTA).json() == r.json()
    selected['name'] = 'owner_a'; assert next(v for v in client.get(base + '/vrste-dela').json() if v['id'] == vid)['materiali'] == []


@pytest.mark.parametrize('method,suffix', [('get', '/sestava'), ('put', '/sestava/{mat}'), ('delete', '/sestava/{mat}')])
def test_stare_poti_sestave_ne_obstajajo(master_api, material, ITEM, method, suffix):
    client, _, base = master_api; item = client.post(base + '/cenik', json=ITEM).json()['id']
    r = getattr(client, method)(f"{base}/cenik/{item}" + suffix.format(mat=material[0]['id']), **({'json': {'kolicina_na_enoto': '1'}} if method == 'put' else {})); assert r.status_code in (404, 405)
