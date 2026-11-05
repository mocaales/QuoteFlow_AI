"""V2 catalogue/material/stock API and access isolation."""
import os
from uuid import uuid4
import pytest
from test_model_database import db, identities, as_user
from test_identity_database import api_client
from test_supplier import ITEM
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')

@pytest.fixture
def master_api(api_client, identities):
    client, selected = api_client; selected['name'] = 'owner_a'
    return client, selected, f'/api/podjetja/{identities[1]}'


def test_cenik_decimalne_cene_urejanje_in_deaktivacija(master_api):
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


def test_tuja_podjetja_delavec_stranka_admin_in_odvzeta_vloga(master_api, material, identities):
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
