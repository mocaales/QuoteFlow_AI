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
