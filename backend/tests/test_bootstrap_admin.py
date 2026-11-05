"""First administrator uses a confirmed existing Auth identity, never a baked-in password."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('bootstrap_admin', ROOT / 'scripts/bootstrap_admin.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class Connection:
    def __init__(self, user):
        self.user = user
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, args):
        self.queries.append((sql, args))
        return self
    def fetchone(self): return self.user


def setup(monkeypatch, user):
    connection = Connection(user)
    monkeypatch.setattr(sys, 'argv', ['bootstrap_admin.py', ' ADMIN@example.test '])
    monkeypatch.setattr(bootstrap, 'dotenv_values', lambda *args, **kwargs: {'DATABASE_MIGRATION_URL': 'postgresql://postgres:fake@localhost/test'})
    monkeypatch.setattr(bootstrap.psycopg, 'connect', lambda **kwargs: connection)
    return connection


def test_admin_dodelitev_uporabi_potrjen_racun_in_ponovljiv_upsert(monkeypatch):
    connection = setup(monkeypatch, ('user-uuid',))
    bootstrap.main()
    lookup, write = connection.queries
    assert 'email_confirmed_at is not null' in lookup[0]
    assert lookup[1] == ('admin@example.test',)
    sql = write[0].lower()
    assert "'admin'" in sql and "'administrator'" not in sql
    assert 'on conflict' in sql and 'aktivna=true' in sql.replace(' ', '')
    assert write[1] == ('user-uuid',)
    assert not any('auth.users' in sql.lower() and 'insert' in sql.lower() for sql, _ in connection.queries)


def test_nepotrjen_racun_ne_dobi_admina(monkeypatch):
    connection = setup(monkeypatch, None)
    with pytest.raises(ValueError, match='potrjena'):
        bootstrap.main()
    assert len(connection.queries) == 1
