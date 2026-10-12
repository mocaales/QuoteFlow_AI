"""Opt-in tests against the actual runtime login; no persistent writes."""
import os
import pytest
import psycopg
from app.database import connection_options, database_readiness

pytestmark = pytest.mark.skipif(os.getenv('RUN_DATABASE_TESTS') != '1', reason='Set RUN_DATABASE_TESTS=1 for live database checks')

def test_runtime_tls_schema_and_rls():
    assert database_readiness() == 'ok'

def test_runtime_cannot_escalate_or_write():
    with psycopg.connect(**connection_options()) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute('set local role postgres')
        with conn.transaction():
            conn.execute('set local role authenticated')
            assert conn.execute('select count(*) from quoteflow.quotes').fetchone()[0] == 0
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute("insert into quoteflow.companies(name) values ('MUST NOT BE INSERTED')")
