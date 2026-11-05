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


def test_sestava_in_projekti_poti_obstajajo_in_so_zascitene():
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    base = '/api/podjetja/{company_id}'
    wanted = {('GET', base + '/cenik/{item_id}/sestava'), ('PUT', base + '/cenik/{item_id}/sestava/{material_id}'), ('DELETE', base + '/cenik/{item_id}/sestava/{material_id}'),
              ('GET', base + '/projekti'), ('POST', base + '/projekti'), ('PUT', base + '/projekti/{projekt_id}'), ('POST', base + '/projekti/{projekt_id}/ogled'),
              ('GET', '/api/projekti'), ('GET', '/api/projekti/{projekt_id}')}
    assert wanted <= found, wanted - found
    for path, deps in ROUTES:
        if '/sestava' in path or path.startswith(base + '/projekti'):
            assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps) and current_user in deps and session_database in deps, path
        if path.startswith('/api/projekti'):
            assert current_user in deps and session_database in deps and administrator not in deps and not any(getattr(c, 'company_role', None) for c in deps), path


def test_nove_poti_brez_zetona_so_401():
    from uuid import uuid4
    from fastapi.testclient import TestClient
    c, u, m = TestClient(app, raise_server_exceptions=False), uuid4(), uuid4()
    base = f'/api/podjetja/{u}'
    for method, path in [('get', f'{base}/cenik/{u}/sestava'), ('put', f'{base}/cenik/{u}/sestava/{m}'), ('delete', f'{base}/cenik/{u}/sestava/{m}'),
                         ('get', f'{base}/projekti'), ('post', f'{base}/projekti'), ('put', f'{base}/projekti/{m}'), ('post', f'{base}/projekti/{m}/ogled'),
                         ('get', '/api/projekti'), ('get', f'/api/projekti/{m}')]:
        assert getattr(c, method)(path).status_code == 401, (method, path)


def test_lastni_projekti_zahtevajo_vlogo_stranka():
    from app import access
    customer = getattr(access, 'customer', None)
    assert customer is not None, 'app.access.customer manjka'
    for path, deps in ROUTES:
        if path.startswith('/api/projekti'): assert customer in deps and current_user in deps and session_database in deps, path
