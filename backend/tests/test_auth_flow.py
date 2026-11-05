"""Real HTTP/Auth contract against disposable LOCAL Supabase and a running API."""
import json
import os
from pathlib import Path
import secrets
import subprocess
from uuid import uuid4
from urllib.parse import urlsplit

import httpx
import psycopg
import pytest

pytestmark = pytest.mark.skipif(not os.getenv('TEST_AUTH_FLOW_URL'), reason='Requires local Auth and application')


def test_real_registration_roles_catalog_material_stock_and_revocation():
    api = os.environ['TEST_AUTH_FLOW_URL'].rstrip('/')
    assert urlsplit(api).hostname in ('localhost', '127.0.0.1')
    root = Path(__file__).resolve().parents[2]
    status = json.loads(subprocess.check_output(['supabase', 'status', '--output', 'json'], cwd=root,
                                               text=True, stderr=subprocess.DEVNULL))
    auth_url = status['API_URL'] + '/auth/v1'
    assert urlsplit(auth_url).hostname in ('localhost', '127.0.0.1')
    secret = status.get('SECRET_KEY') or status['SERVICE_ROLE_KEY']
    public = status.get('PUBLISHABLE_KEY') or status['ANON_KEY']
    auth_headers = {'apikey': secret, 'Authorization': 'Bearer ' + secret}
    suffix, password = uuid4().hex, secrets.token_urlsafe(24)
    users, companies = {}, []
    with httpx.Client(timeout=20) as h:
        def auth(method, path, **kwargs):
            return h.request(method, auth_url + path, headers=auth_headers, **kwargs)

        def login(name, pw=password):
            return h.post(auth_url + '/token?grant_type=password', headers={'apikey': public},
                          json={'email': f'{name}-{suffix}@example.test', 'password': pw})
        try:
            for name in ('admin', 'master', 'worker'):
                response = auth('POST', '/admin/users', json={
                    'email': f'{name}-{suffix}@example.test', 'password': password, 'email_confirm': True,
                    'user_metadata': {'ime': 'Test', 'priimek': 'HTTP', 'vloga': 'admin'}})
                assert response.status_code == 200, response.status_code
                users[name] = response.json()['id']
            with psycopg.connect(status['DB_URL']) as connection:
                connection.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'admin')", (users['admin'],))
            headers = {}
            for name in users:
                response = login(name)
                assert response.status_code == 200, response.status_code
                headers[name] = {'Authorization': 'Bearer ' + response.json()['access_token']}
            a, m, w = (headers[name] for name in ('admin', 'master', 'worker'))
            assert h.get(api + '/api/me').status_code == 401
            assert h.get(api + '/api/me', headers={'Authorization': 'Bearer invalid'}).status_code == 401
            assert login('worker', 'wrong-password').status_code == 400
            profile = h.get(api + '/api/me', headers=m)
            assert profile.status_code == 200
            assert profile.headers['cache-control'] == 'no-store'
            assert {role['vloga'] for role in profile.json()['vloge']} == {'stranka'}
            assert all(role['podjetje_id'] is None for role in profile.json()['vloge'])
            for owner in ('master', 'worker'):
                response = h.post(api + '/api/admin/podjetja', headers=a, json={
                    'lastnik_id': users[owner], 'naziv': 'HTTP ' + owner + suffix,
                    'maticna_stevilka': uuid4().hex[:30], 'naslov': 'Testna 1'})
                assert response.status_code == 201, response.text
                companies.append(response.json()['id'])
            company, other_company = companies
            base, foreign = (api + '/api/podjetja/' + c for c in companies)
            # Global stranka + company-scoped mojster and delavec coexist without leaking authority.
            payload = {'uporabnik_id': users['master'], 'podjetje_id': other_company, 'vloga': 'delavec'}
            response = h.post(api + '/api/admin/vloge', headers=a, json=payload)
            assert response.status_code == 200, response.text
            role_id = response.json()['id']
            assert h.post(api + '/api/admin/vloge', headers=a, json=payload).json()['id'] == role_id
            assert {role['vloga'] for role in h.get(api + '/api/me', headers=m).json()['vloge']} == {'stranka', 'mojster', 'delavec'}
            assert h.get(foreign, headers=m).status_code == 200
            assert h.get(foreign + '/cenik', headers=m).status_code == 403
            assert h.get(api + '/api/admin/uporabniki', headers=m).status_code == 403
            assert h.get(api + '/api/podjetja/' + str(uuid4()), headers=m).status_code == 404
            item = {'naziv': 'Rušenje estriha', 'opis': 'Odstranitev estriha', 'vrsta_dela': 'Rušenje',
                    'enota': 'm2', 'cena_na_enoto': '12.4500', 'stopnja_ddv': '0.22', 'aktivna': True}
            response = h.post(base + '/cenik', headers=m, json=item)
            assert response.status_code == 201, response.text
            item_id = response.json()['id']
            assert set(response.json()) == set(item) | {'id', 'podjetje_id'}
            assert h.put(base + '/cenik/' + item_id, headers=m, json=item | {'cena_na_enoto': '13'}).status_code == 200
            assert h.put(foreign + '/cenik/' + item_id, headers=w, json=item).status_code == 404
            assert h.get(base + '/cenik', headers=a).status_code == 403
            assert h.get(base + '/cenik', headers=w).status_code == 403
            assert h.post(base + '/pravila', headers=m, json={}).status_code == 404
            kind = h.post(base + '/vrste-materiala', headers=m, json={'naziv': 'Gradbeni materiali'})
            assert kind.status_code == 201, kind.text
            material_data = {'vrsta_materiala_id': kind.json()['id'], 'sifra': 'HTTP-1', 'naziv': 'Cement',
                             'enota': 'kg', 'cena_na_enoto': '2.1234', 'aktiven': True}
            material = h.post(base + '/materiali', headers=m, json=material_data)
            assert material.status_code == 201, material.text
            material_id = material.json()['id']
            stock_path = base + '/materiali/' + material_id + '/zaloga'
            assert h.get(stock_path, headers=m).json() == []
            for location, quantity in [('Maribor', '0'), ('Celje', '2.125')]:
                assert h.put(stock_path, headers=m, json={'lokacija': location, 'kolicina': quantity}).status_code == 200
            assert {r['lokacija']: float(r['kolicina']) for r in h.get(stock_path, headers=m).json()} == {'Celje': 2.125, 'Maribor': 0}
            assert h.put(stock_path, headers=m, json={'lokacija': 'Maribor', 'kolicina': '-1'}).status_code == 422
            assert h.get(foreign + '/materiali/' + material_id + '/zaloga', headers=w).status_code == 404
            assert h.put(foreign + '/materiali/' + material_id + '/zaloga', headers=w,
                         json={'lokacija': 'Vdor', 'kolicina': '99'}).status_code == 404
            assert h.delete(stock_path, headers=m, params={'lokacija': 'Maribor'}).status_code == 200
            assert [r['lokacija'] for r in h.get(stock_path, headers=m).json()] == ['Celje']
            assert h.patch(api + '/api/admin/vloge/' + role_id, headers=a, json={'aktivna': False}).status_code == 200
            assert h.get(foreign, headers=m).status_code == 404
            assert h.post(auth_url + '/logout', headers={'apikey': public} | m).status_code == 204
            assert h.get(api + '/api/me', headers=m).status_code == 401
            email = f'signup-{suffix}@example.test'
            response = h.post(auth_url + '/signup', headers={'apikey': public}, json={
                'email': email, 'password': password, 'data': {'vloga': 'admin', 'ime': 'Nova', 'priimek': 'Stranka'}})
            assert response.status_code == 200, response.status_code
            signed = response.json(); uid = signed.get('user', signed).get('id')
            assert uid
            users['signup'] = uid
            h.post(auth_url + '/signup', headers={'apikey': public}, json={'email': email, 'password': password})
            with psycopg.connect(status['DB_URL']) as connection:
                assert connection.execute('select count(*) from auth.users where email=%s', (email,)).fetchone()[0] == 1
                assert connection.execute('select vloga,podjetje_id from quoteflow.vloga_uporabnika where uporabnik_id=%s',
                                          (uid,)).fetchall() == [('stranka', None)]
        finally:
            if users:
                with psycopg.connect(status['DB_URL']) as connection:
                    connection.execute('set constraints all deferred')
                    if companies:
                        connection.execute('delete from quoteflow.zaloga where material_id in (select m.id from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where v.podjetje_id=any(%s::uuid[]))', (companies,))
                        connection.execute('delete from quoteflow.material where vrsta_materiala_id in (select id from quoteflow.vrsta_materiala where podjetje_id=any(%s::uuid[]))', (companies,))
                        connection.execute('delete from quoteflow.vrsta_materiala where podjetje_id=any(%s::uuid[])', (companies,))
                        connection.execute('delete from quoteflow.postavka_cenika where podjetje_id=any(%s::uuid[])', (companies,))
                    connection.execute('delete from quoteflow.vloga_uporabnika where uporabnik_id=any(%s::uuid[])', (list(users.values()),))
                    if companies:
                        connection.execute('delete from quoteflow.podjetje where id=any(%s::uuid[])', (companies,))
                    connection.execute('delete from quoteflow.uporabnik where id=any(%s::uuid[])', (list(users.values()),))
                for uid in users.values():
                    auth('DELETE', '/admin/users/' + uid)
