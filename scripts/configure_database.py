"""Provision the restricted runtime login using a local admin connection.

Run from the project root: backend/.venv/bin/python scripts/configure_database.py
Secrets are never printed. The original administrative URL stays in .env only.
"""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote, parse_qsl, urlencode
import secrets
import sys
import psycopg
from psycopg import sql
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]

def main():
    env = ROOT / '.env'
    values = dotenv_values(env, interpolate=False)
    original = values.get('DATABASE_URL') or ''
    ref = values.get('SUPABASE_PROJECT_REF')
    parts = urlsplit(original)
    if not ref or not parts.hostname or ref not in (parts.username or '') + parts.hostname:
        raise ValueError('Connection does not identify the configured project')
    if (parts.username or '').split('.')[0] == 'quoteflow_app':
        with psycopg.connect(original, connect_timeout=8, sslmode='require', prepare_threshold=None) as conn:
            assert conn.pgconn.ssl_in_use
            assert conn.execute('select current_user').fetchone()[0] == 'quoteflow_app'
        print('Existing runtime connection verified; no password rotation performed.')
        return
    if (parts.username or '').split('.')[0] != 'postgres':
        raise ValueError('Expected the project administrator for initial provisioning')
    password = secrets.token_urlsafe(48)
    query = dict(parse_qsl(parts.query))
    query['sslmode'] = 'require'
    admin_url = urlunsplit(parts._replace(query=urlencode(query)))
    with psycopg.connect(admin_url, connect_timeout=8, prepare_threshold=None) as admin:
        role = admin.execute("select rolcanlogin, rolbypassrls from pg_roles where rolname='quoteflow_app'").fetchone()
        if role != (True, False):
            raise ValueError('Apply the application login migration first')
        admin.execute(sql.SQL('alter role quoteflow_app password {}').format(sql.Literal(password)))
    username = f'quoteflow_app.{ref}' if '.pooler.supabase.com' in parts.hostname else 'quoteflow_app'
    host = parts.hostname + (f':{parts.port}' if parts.port else '')
    runtime_url = urlunsplit(parts._replace(netloc=f'{quote(username)}:{quote(password)}@{host}',query=urlencode(query)))
    # Save before probing so a transient network error cannot lose the new credential.
    set_key(env, 'MIGRATION_DATABASE_URL', admin_url)
    set_key(env, 'DATABASE_URL', runtime_url)
    env.chmod(0o600)
    with psycopg.connect(runtime_url, connect_timeout=8, prepare_threshold=None) as conn:
        assert conn.pgconn.ssl_in_use
        assert conn.execute('select current_user').fetchone()[0] == 'quoteflow_app'
        conn.execute('set local role authenticated')
        assert conn.execute('select count(*) from quoteflow.companies').fetchone()[0] == 0
    print('Restricted login configured; TLS active; no user identity means no business rows.')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Configuration failed ({type(exc).__name__}); credential details suppressed.', file=sys.stderr)
        sys.exit(1)
