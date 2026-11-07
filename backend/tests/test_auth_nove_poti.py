"""Auth and authorisation matrix over every new v3 / US-08 route: 401 (none, invalid, inactive session), 503 (Auth down), 403 (wrong role, other company), no-store."""
import base64
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from app import access, auth
from app.auth import current_user
from app.main import app
from v3_support import COMPANY, NEW_ROUTES, ME, Fake, call

ROUTES = [pytest.param(m, p, b, id=f'{m} {p.split("/api/podjetja/")[1][37:]}') for m, p, b, _ in NEW_ROUTES]


def token(**claims): return 'h.' + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=') + '.s'


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://project.example'); monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://quoteflow_app:x@127.0.0.1:5432/db'); monkeypatch.delenv('SUPABASE_PROJECT_REF', raising=False)
    yield
    app.dependency_overrides.clear()


client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_brez_zetona_je_401_in_no_store(method, path, body):
    r = call(client, method, path, body); assert r.status_code == 401 and r.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_neveljaven_zeton_je_401(monkeypatch, method, path, body):
    monkeypatch.setattr(auth.httpx, 'get', lambda *a, **k: httpx.Response(401))
    r = getattr(client, method)(path, headers={'Authorization': 'Bearer forged.token.value'}, **({'json': body} if body is not None else {}))
    assert r.status_code == 401 and r.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_nedosegljiv_auth_je_503_brez_uhajanja(monkeypatch, method, path, body):
    def down(*a, **k): raise httpx.ConnectError('DO-NOT-LEAK')
    monkeypatch.setattr(auth.httpx, 'get', down)
    r = getattr(client, method)(path, headers={'Authorization': 'Bearer a.b.c'}, **({'json': body} if body is not None else {}))
    assert r.status_code == 503 and 'DO-NOT-LEAK' not in r.text


class Session:
    """psycopg connection stand-in for access.session_database: valid role, but the auth.sessions row is gone."""
    def __init__(self, active): self.active, self.sql = active, []
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=()):
        self.sql.append(' '.join(sql.split())); out = self
        self.row = {'name': 'quoteflow_app', 'rolsuper': False, 'rolbypassrls': False} if 'pg_roles' in sql else {'active': self.active} if 'aktivna_seja' in sql else {'allowed': True}
        return out
    def fetchone(self): return self.row
    def fetchall(self): return []


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_veljaven_zeton_z_neaktivno_sejo_je_401_in_poslovna_poizvedba_se_ne_izvede(monkeypatch, method, path, body):
    uid, sid = uuid4(), uuid4(); conn = Session(False)
    monkeypatch.setattr(auth.httpx, 'get', lambda *a, **k: httpx.Response(200, json={'id': str(uid), 'email': 'ana@example.test'}))
    monkeypatch.setattr(access.psycopg, 'connect', lambda **k: conn)
    t = token(sub=str(uid), session_id=str(sid), role='authenticated')
    r = getattr(client, method)(path, headers={'Authorization': f'Bearer {t}'}, **({'json': body} if body is not None else {}))
    assert r.status_code == 401 and not any('quoteflow.' in s or 'quoteflow_private.' in s and 'aktivna_seja' not in s for s in conn.sql), conn.sql


def guarded(allowed):
    fake = Fake([{'allowed': allowed}])
    app.dependency_overrides[current_user] = lambda: ME; app.dependency_overrides[access.session_database] = lambda: fake
    return fake


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_nemojster_stranka_delavec_in_administrator_so_403_brez_poslovnih_poizvedb(method, path, body):
    fake = guarded(False); r = call(TestClient(app, raise_server_exceptions=False), method, path, body)
    assert r.status_code == 403 and r.headers['cache-control'] == 'no-store' and len(fake.calls) == 1 and fake.calls[0][1] == (COMPANY, 'mojster'), r.text


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_tuje_podjetje_v_poti_je_403_ker_se_clanstvo_preveri_za_to_podjetje(method, path, body):
    other = uuid4(); fake = guarded(False); r = call(TestClient(app, raise_server_exceptions=False), method, path.replace(str(COMPANY), str(other)), body)
    assert r.status_code == 403 and fake.calls[0][1] == (other, 'mojster')


@pytest.mark.parametrize('method,path,body', ROUTES)
def test_mojster_prestane_varovalo_in_odgovor_ima_no_store(method, path, body):
    fake = guarded(True); r = call(TestClient(app, raise_server_exceptions=False), method, path, body)
    assert fake.calls and fake.calls[0][1] == (COMPANY, 'mojster') and r.status_code not in (401, 403, 405) and r.headers['cache-control'] == 'no-store', (r.status_code, r.text[:200])
