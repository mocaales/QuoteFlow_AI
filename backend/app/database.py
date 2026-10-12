"""Connection readiness. Never returns credentials or driver error messages."""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict

# Docker injects environment variables; local runs read the project .env.
# Explicit environment values always win. No dependency on the working directory.
load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False, interpolate=False)

EXPECTED_TABLES = {
    'user_profiles', 'companies', 'company_members', 'platform_admins',
    'supplier_profiles', 'products', 'supplier_products', 'pricing_policies',
    'rfqs', 'rfq_items', 'rfq_recipients', 'agent_runs', 'quotes', 'quote_items',
    'quote_revisions', 'approvals', 'published_quotes', 'published_quote_items', 'audit_events',
}

class DatabaseConfigurationError(Exception):
    pass

def connection_options():
    url = os.getenv('DATABASE_URL', '')
    if not url:
        raise DatabaseConfigurationError('database_not_configured')
    try:
        options = conninfo_to_dict(url)
    except psycopg.Error:
        raise DatabaseConfigurationError('database_configuration_invalid') from None
    ref = os.getenv('SUPABASE_PROJECT_REF', '')
    host, user = options.get('host', ''), options.get('user', '')
    if ref and ref not in user + host:
        raise DatabaseConfigurationError('database_project_mismatch')
    # Never downgrade an explicitly configured certificate verification mode.
    if options.get('sslmode') not in ('require', 'verify-ca', 'verify-full'):
        options['sslmode'] = 'require'
    options['connect_timeout'] = 5
    options['application_name'] = 'quoteflow-api'
    options['prepare_threshold'] = None
    return options

def database_readiness():
    try:
        options = connection_options()
        with psycopg.connect(**options) as connection:
            if not connection.pgconn.ssl_in_use:
                return 'database_tls_required'
            role = connection.execute('''
                select current_user, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb
                from pg_roles where rolname=current_user
            ''').fetchone()
            if not role or role[0] != 'quoteflow_app' or any(role[1:]):
                return 'database_role_unsafe'
            connection.execute('set local statement_timeout = 5000')
            tables = connection.execute('''
                select c.relname, c.relrowsecurity, c.relforcerowsecurity
                from pg_class c join pg_namespace n on n.oid=c.relnamespace
                where n.nspname='quoteflow' and c.relkind='r'
            ''').fetchall()
            protected = {name for name, enabled, forced in tables if enabled and forced}
            if not EXPECTED_TABLES <= protected:
                return 'database_schema_not_ready'
            # No end-user identity is fabricated by this public health check.
            connection.execute('set local role authenticated')
            connection.execute("select set_config('request.jwt.claim.sub', '', true)")
            connection.execute("select set_config('request.jwt.claims', '{}', true)")
            if connection.execute('select count(*) from quoteflow.companies').fetchone()[0] != 0:
                return 'database_access_unsafe'
        return 'ok'
    except DatabaseConfigurationError as error:
        return str(error)
    except (psycopg.Error, ValueError):
        return 'database_unavailable'
