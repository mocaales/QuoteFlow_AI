"""Populated V1 -> V2 migration regression in a disposable LOCAL database.

Run: backend/.venv/bin/python supabase/tests/v1_to_v2_upgrade.py
Uses the existing local Supabase PostgreSQL on 127.0.0.1:54322 only.
Auth tables implement the identity/session columns needed by these migrations;
actual GoTrue HTTP/session behavior is covered separately by the backend tests.
"""
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
LOCAL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
name = f"quoteflow_upgrade_test_{uuid4().hex}"
users = [uuid4() for _ in range(3)]
companies = [uuid4() for _ in range(2)]
admin_role = uuid4()

with psycopg.connect(LOCAL, autocommit=True) as control:
    control.execute(sql.SQL("create database {} template template0").format(sql.Identifier(name)))
    try:
        with psycopg.connect(LOCAL, dbname=name) as db:
            db.execute("""
                create schema extensions;
                create schema auth;
                create table auth.users (
                    id uuid primary key, email text, email_confirmed_at timestamptz,
                    raw_user_meta_data jsonb not null default '{}'
                );
                create table auth.sessions (
                    id uuid primary key, user_id uuid references auth.users(id), not_after timestamptz
                );
                create function auth.uid() returns uuid language sql stable as $$
                    select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
                $$;
            """)
            for migration in (
                "20261027161706_identity_and_permissions.sql",
                "20261029195006_supplier_catalog_stock_rules.sql",
            ):
                db.execute((ROOT / "supabase/migrations" / migration).read_text())
            for index, user in enumerate(users):
                db.execute(
                    "insert into auth.users(id,email,email_confirmed_at) values(%s,%s,now())",
                    (user, f"upgrade-{index}@example.test"),
                )
            for index, company in enumerate(companies):
                db.execute("insert into quoteflow.podjetje(id,naziv) values(%s,%s)", (company, f"V1 {index}"))
            db.execute(
                "insert into quoteflow.vloga_uporabnika(id,uporabnik_id,vloga) values(%s,%s,'administrator')",
                (admin_role, users[0]),
            )
            db.execute(
                "insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'ponudnik')",
                (users[1], companies[0]),
            )
            db.commit()
            migration = (ROOT / "supabase/migrations/20261103211654_v2_projects_roles_catalog.sql").read_text()
            db.execute(migration)
            db.commit()
            assert db.execute("select count(*) from auth.users").fetchone()[0] == 3
            assert db.execute("select count(*) from quoteflow.uporabnik").fetchone()[0] == 3
            assert db.execute("select count(*) from quoteflow.vloga_uporabnika where vloga='stranka' and aktivna").fetchone()[0] == 3
            assert db.execute(
                "select id,uporabnik_id,aktivna from quoteflow.vloga_uporabnika where vloga='admin'"
            ).fetchall() == [(admin_role, users[0], True)]
            assert db.execute("select count(*) from quoteflow_legacy_20261103.podjetje").fetchone()[0] == 2
            assert db.execute("select count(*) from quoteflow.podjetje").fetchone()[0] == 0
            # Frozen 17-table smoke: tenant_isolation.sql asserts the current model, which these V2-only migrations do not create.
            db.execute((ROOT / "supabase/tests/v2_upgrade_smoke.sql").read_text())
            print("PASS: populated V1 -> V2; 3 identities, 1 admin and 3 customers preserved; 2 V1 companies archived; 17-table RLS smoke green.")
    finally:
        control.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(name)))
