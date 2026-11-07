import psycopg
from app import database
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_tls_enforced_and_certificate_verification_preserved(monkeypatch):
    monkeypatch.setenv('SUPABASE_PROJECT_REF', 'testref')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://quoteflow_app.testref:secret@pool.example/db?sslmode=disable')
    assert database.connection_options()['sslmode'] == 'require'
    monkeypatch.setenv('DATABASE_URL', 'postgresql://quoteflow_app.testref:secret@pool.example/db?sslmode=verify-full')
    assert database.connection_options()['sslmode'] == 'verify-full'

def test_wrong_project_is_rejected_before_connect(monkeypatch):
    monkeypatch.setenv('SUPABASE_PROJECT_REF', 'expectedref')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:secret@different.example/db')
    assert database.database_readiness() == 'database_project_mismatch'

def test_connection_error_never_exposes_credentials(monkeypatch):
    monkeypatch.setenv('SUPABASE_PROJECT_REF', '')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:DO-NOT-LEAK@db.example/db')
    def fail(**kwargs):
        raise psycopg.OperationalError('password DO-NOT-LEAK for user at db.example')
    monkeypatch.setattr(database.psycopg, 'connect', fail)
    response = client.get('/api/ready')
    assert response.status_code == 503
    assert response.json() == {'status': 'database_unavailable'}
    assert 'DO-NOT-LEAK' not in response.text

class FakeConnection:
    class pgconn:
        ssl_in_use = True
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, query): return self
    def fetchone(self): return ('postgres', False, True, True, True)

def test_administrator_connection_is_not_ready(monkeypatch):
    monkeypatch.setenv('SUPABASE_PROJECT_REF', '')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://postgres:secret@db.example/db')
    monkeypatch.setattr(database.psycopg, 'connect', lambda **kwargs: FakeConnection())
    assert client.get('/api/ready').json() == {'status': 'database_role_unsafe'}


def test_pogodba_pripravljenosti_ima_22_tabel_modela_v3():
    old = {'uporabnik', 'podjetje', 'vloga_uporabnika', 'prosnja_mojstra', 'projekt', 'ekipa', 'clan_ekipe', 'projekt_ekipa', 'postavka_cenika', 'vrsta_materiala', 'material', 'zaloga',
           'sestava_cenika', 'ponudba', 'postavka_ponudbe', 'material_ponudbe', 'racun'}
    new = database.EXPECTED_TABLES - old
    assert len(database.EXPECTED_TABLES) == 22 and 'sestava_cenika' not in database.EXPECTED_TABLES and old - database.EXPECTED_TABLES == {'sestava_cenika'}
    assert {'vrsta_dela', 'material_vrste_dela', 'postavka_projekta', 'izmera', 'izmera_ponudbe'} <= new and len(new) == 6  # 6th = mojster-only labour snapshot table (security M2)

def fake_connection(tables):
    class Result:
        def __init__(self, rows): self.rows = rows
        def fetchone(self): return self.rows[0]
        def fetchall(self): return self.rows
    class Connection:
        pgconn = type('P', (), {'ssl_in_use': True})()
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=()):
            if 'pg_roles' in sql: return Result([('quoteflow_app', False, False, False, False)])
            if 'pg_class' in sql: return Result(tables)
            return Result([(0,)])
    return Connection()

def test_pripravljenost_zahteva_forsiran_rls_tudi_na_zasebnih_tabelah(monkeypatch):
    monkeypatch.setenv('SUPABASE_PROJECT_REF', ''); monkeypatch.setenv('DATABASE_URL', 'postgresql://quoteflow_app:x@db.example/db')
    ok = [(n, True, True) for n in database.EXPECTED_TABLES | database.PRIVATE_TABLES]
    monkeypatch.setattr(database.psycopg, 'connect', lambda **k: fake_connection(ok))
    assert database.database_readiness() == 'ok'
    for missing in sorted(database.PRIVATE_TABLES):
        for flags in ((True, False), (False, False)):
            tables = [t for t in ok if t[0] != missing] + [(missing, *flags)]
            monkeypatch.setattr(database.psycopg, 'connect', lambda **k: fake_connection(tables))
            assert database.database_readiness() == 'database_schema_not_ready'
