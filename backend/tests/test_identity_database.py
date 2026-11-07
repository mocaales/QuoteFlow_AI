"""Identity API against V2 on disposable local Supabase."""
import os
from uuid import uuid4
import pytest
from test_model_database import db, identities, as_user
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')

@pytest.fixture
def api_client(db, identities):
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import Principal, current_user
    from app.access import session_database
    users, _, _, _ = identities
    selected = {'name': 'admin'}
    def principal():
        uid, sid = users[selected['name']]
        return Principal(uid, sid, selected['name'] + '@example.test')
    def connection():
        with db.transaction():
            with as_user(db, users[selected['name']]):
                if not db.execute('select quoteflow_private.aktivna_seja() as active').fetchone()['active']:
                    raise HTTPException(401, 'Seja ni več aktivna.')
                yield db
    app.dependency_overrides[current_user] = principal
    app.dependency_overrides[session_database] = connection
    try:
        with TestClient(app) as client: yield client, selected
    finally: app.dependency_overrides.clear()


def test_admin_api_lastnistvo_dodelitev_in_takojsen_odvzem(api_client, db, identities):
    client, selected = api_client; users, _, _, _ = identities
    payload = {'lastnik_id': str(users['outsider'][0]), 'naziv': ' Novo podjetje ', 'maticna_stevilka': uuid4().hex[:30], 'naslov': 'Naslov 1'}
    response = client.post('/api/admin/podjetja', json=payload)
    assert response.status_code == 201, response.text
    company = response.json()
    assert company['naziv'] == 'Novo podjetje' and company['lastnik_id'] == str(users['outsider'][0])
    role_data = {'uporabnik_id': str(users['worker'][0]), 'podjetje_id': company['id'], 'vloga': 'delavec'}
    response = client.post('/api/admin/vloge', json=role_data); assert response.status_code == 200, response.text
    role = response.json()
    assert client.post('/api/admin/vloge', json=role_data).json()['id'] == role['id']
    for obsolete in ('administrator', 'nabavnik', 'ponudnik', 'admin'):
        assert client.post('/api/admin/vloge', json=role_data | {'vloga': obsolete}).status_code == 422
    selected['name'] = 'worker'
    assert client.get('/api/podjetja/' + company['id']).status_code == 200
    assert client.get('/api/admin/uporabniki').status_code == 403
    assert client.get('/api/me').json()['ime'] == 'Ime'
    selected['name'] = 'admin'
    assert client.patch('/api/admin/vloge/' + role['id'], json={'aktivna': False}).status_code == 200
    selected['name'] = 'worker'
    assert client.get('/api/podjetja/' + company['id']).status_code == 404
    assert not any(v['id'] == role['id'] for v in client.get('/api/me').json()['vloge'])


def test_admin_deaktivacija_in_tuja_pot(api_client, identities):
    client, selected = api_client; _, a, b, _ = identities
    selected['name'] = 'owner_b'
    assert client.get('/api/podjetja/' + str(b)).status_code == 200
    assert client.get('/api/podjetja/' + str(a)).status_code == 404
    selected['name'] = 'admin'
    company = client.get('/api/podjetja/' + str(b)).json()
    update = {key: company[key] for key in ('naziv', 'maticna_stevilka', 'davcna_stevilka', 'naslov')}
    assert client.put('/api/admin/podjetja/' + str(b), json=update | {'aktivno': False}).status_code == 200
    assert client.put('/api/admin/podjetja/' + str(uuid4()), json=update | {'aktivno': True}).status_code == 404
    selected['name'] = 'owner_b'
    assert client.get('/api/podjetja/' + str(b)).status_code == 404
    assert client.get('/api/podjetja/' + str(b) + '/cenik').status_code == 403


def test_preklic_seje_prepreci_api_z_obstojecim_zetonom(api_client, db, identities):
    client, _ = api_client; users, _, _, _ = identities
    assert client.get('/api/me').status_code == 200
    db.execute('delete from auth.sessions where id=%s', (users['admin'][1],))
    assert client.get('/api/me').status_code == 401


def test_lastnikove_vloge_ni_mogoce_odvzeti_v_api(api_client, identities):
    client, _ = api_client; users, _, _, _ = identities
    master = next(v for v in client.get('/api/admin/vloge').json() if v['uporabnik_id'] == str(users['owner_a'][0]) and v['vloga'] == 'mojster')
    response = client.patch('/api/admin/vloge/' + master['id'], json={'aktivna': False})
    assert response.status_code == 409 and response.json()['detail'] == 'Lastniku podjetja ni mogoče odvzeti vloge mojster.', response.text
    assert next(v for v in client.get('/api/admin/vloge').json() if v['id'] == master['id'])['aktivna'] is True
