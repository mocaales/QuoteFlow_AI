"""The access boundary for every business request: verified token, active session, roles from PostgreSQL.

Routers depend on these instead of opening connections; tests/test_access.py fails when a route skips them.
"""
from functools import cache
import json
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException
import psycopg
from psycopg.rows import dict_row

from .auth import Principal, current_user
from .database import connection_options, DatabaseConfigurationError

def session_database(user: Principal = Depends(current_user)):
    try:
        options = connection_options()
    except DatabaseConfigurationError:
        raise HTTPException(503, 'Podatkovna baza ni nastavljena.') from None
    with psycopg.connect(**options, row_factory=dict_row) as connection:
        role = connection.execute('select current_user as name, rolsuper, rolbypassrls from pg_roles where rolname=current_user').fetchone()
        if role['name'] != 'quoteflow_app' or role['rolsuper'] or role['rolbypassrls']:
            raise HTTPException(503, 'Aplikacijska povezava ni pravilno nastavljena.')
        connection.execute('set local role authenticated')
        connection.execute("select set_config('request.jwt.claim.sub',%s,true), set_config('request.jwt.claims',%s,true)",
                           (str(user.id), json.dumps({'sub':str(user.id),'role':'authenticated','session_id':str(user.session_id)})))
        if not connection.execute('select quoteflow_private.aktivna_seja() as active').fetchone()['active']:
            raise HTTPException(401, 'Seja ni več aktivna. Prijavite se ponovno.')
        yield connection

def administrator(db=Depends(session_database)):
    if not db.execute('select quoteflow_private.administrator() as allowed').fetchone()['allowed']:
        raise HTTPException(403, 'Potrebna je vloga administratorja.')
    return db

def customer(db=Depends(session_database)):
    if not db.execute('select quoteflow_private.stranka() as allowed').fetchone()['allowed']:
        raise HTTPException(403, 'Za to dejanje nimate pravice.')
    return db

ROLE_NAMES = {'mojster': 'mojstra', 'delavec': 'delavca'}

@cache
def company_member(role: Literal['mojster', 'delavec']):
    """Guard for routes under /podjetja/{company_id}/: an active `role` at exactly that company."""
    def guard(company_id: UUID, db=Depends(session_database)):
        if not db.execute('select quoteflow_private.clan(%s,%s) as allowed', (company_id, role)).fetchone()['allowed']:
            raise HTTPException(403, f'Potrebna je aktivna vloga {ROLE_NAMES[role]} pri izbranem podjetju.')
        return db
    guard.company_role = role
    return guard
