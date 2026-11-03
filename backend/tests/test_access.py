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
    assert company_member('ponudnik') is company_member('ponudnik')
    assert company_member('ponudnik').company_role=='ponudnik'
    assert company_member('nabavnik').company_role=='nabavnik'
