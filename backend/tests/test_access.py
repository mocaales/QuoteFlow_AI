"""Every business route must pass the access boundary; a new endpoint cannot forget its guard."""
from fastapi.routing import APIRoute
from app.access import administrator, company_member, session_database
from app.auth import current_user
from app.main import app

PUBLIC={'/api/health','/api/ready','/api/config','/api/demo/calculate'}

def calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from calls(dep)

ROUTES=[(r.path,set(calls(r.dependant))) for r in app.routes if isinstance(r,APIRoute) and r.path.startswith('/api/')]

def test_business_routes_verify_token_session_and_database_role():
    for path,deps in ROUTES:
        if path in PUBLIC: continue
        assert current_user in deps and session_database in deps, path

def test_company_scoped_routes_check_membership_in_that_company():
    scoped=[(p,d) for p,d in ROUTES if p.startswith('/api/podjetja/{company_id}/')]
    assert scoped
    for path,deps in scoped:
        assert any(getattr(c,'company_role',None) for c in deps), path

def test_admin_routes_require_administrator():
    admin=[(p,d) for p,d in ROUTES if p.startswith('/api/admin/')]
    assert admin
    for path,deps in admin:
        assert administrator in deps, path

def test_company_member_guard_is_built_once_per_role():
    assert company_member('mojster') is company_member('mojster')
    assert company_member('mojster').company_role=='mojster'
    assert company_member('delavec').company_role=='delavec'


def test_company_routes_require_master_and_no_legacy_rules_endpoints():
    scoped = [(p, d) for p, d in ROUTES if p.startswith('/api/podjetja/{company_id}/')]
    for path, deps in scoped:
        assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps), path
    assert not any('/pravila' in path or '/potrditev' in path for path, _ in ROUTES)


def test_prosnje_mojstra_poti_obstajajo_in_so_zascitene():
    found = {(m, r.path.replace('{prosnja_id}', '{id}')) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    wanted = {('POST', '/api/prosnje'), ('GET', '/api/prosnje'), ('GET', '/api/admin/prosnje'), ('POST', '/api/admin/prosnje/{id}/odlocitev')}
    assert wanted <= found, wanted - found
    for path, deps in ROUTES:
        if path.startswith('/api/prosnje') or path.startswith('/api/admin/prosnje'): assert current_user in deps and session_database in deps and (administrator in deps) == path.startswith('/api/admin/'), path
