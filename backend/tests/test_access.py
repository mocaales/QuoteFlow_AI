"""Every business route must pass the access boundary; a new endpoint cannot forget its guard."""
import re
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


def test_projekti_poti_obstajajo_in_so_zascitene():
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    base = '/api/podjetja/{company_id}'
    wanted = {('GET', base + '/projekti'), ('POST', base + '/projekti'), ('PUT', base + '/projekti/{projekt_id}'), ('POST', base + '/projekti/{projekt_id}/ogled'),
              ('GET', '/api/projekti'), ('GET', '/api/projekti/{projekt_id}')}
    assert wanted <= found, wanted - found
    for path, deps in ROUTES:
        if path.startswith(base + '/projekti'):
            assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps) and current_user in deps and session_database in deps, path
        if path.startswith('/api/projekti'):
            assert current_user in deps and session_database in deps and administrator not in deps and not any(getattr(c, 'company_role', None) for c in deps), path


# Model v3 replaces the per-catalogue-item composition (`/sestava`) and the per-quote line editing with vrste dela and project items.
# Reason these old assertions were replaced: ADR for model v3 (G1 decisions 1-12) removes both route families.
REMOVED_V3 = [('GET', '/cenik/{item_id}/sestava'), ('PUT', '/cenik/{item_id}/sestava/{material_id}'), ('DELETE', '/cenik/{item_id}/sestava/{material_id}'),
              ('POST', '/projekti/{projekt_id}/ponudbe/{ponudba_id}/postavke'), ('POST', '/projekti/{projekt_id}/ponudbe/{ponudba_id}/postavke/iz-cenika'),
              ('PUT', '/projekti/{projekt_id}/ponudbe/{ponudba_id}/postavke/{postavka_id}'), ('DELETE', '/projekti/{projekt_id}/ponudbe/{ponudba_id}/postavke/{postavka_id}')]
V3 = '/api/podjetja/{company_id}'
NEW_V3 = {('GET', '/vrste-dela'), ('POST', '/vrste-dela'), ('PUT', '/vrste-dela/{vid}'), ('PUT', '/vrste-dela/{vid}/materiali/{mid}'), ('DELETE', '/vrste-dela/{vid}/materiali/{mid}'),
          ('GET', '/projekti/{pid}/postavke'), ('POST', '/projekti/{pid}/postavke'), ('POST', '/projekti/{pid}/postavke/iz-cenika'), ('PUT', '/projekti/{pid}/postavke/{id}'), ('DELETE', '/projekti/{pid}/postavke/{id}'),
          ('POST', '/projekti/{pid}/postavke/{id}/izmere'), ('PUT', '/projekti/{pid}/postavke/{id}/izmere/{iid}'), ('DELETE', '/projekti/{pid}/postavke/{id}/izmere/{iid}'),
          ('GET', '/delavci'), ('GET', '/delavci/povabila'), ('POST', '/delavci/povabila'), ('POST', '/delavci/povabila/{pid}/preklic'), ('PATCH', '/delavci/{vid}')}
norm = lambda p: re.sub(r'\{[a-z_]+\}', '{}', p)


def test_v3_poti_obstajajo():
    found = {(m, norm(r.path)) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    missing = {w for w in NEW_V3 if (w[0], norm(V3 + w[1])) not in found}
    assert not missing, missing


def test_v3_odstranjene_poti_ne_obstajajo():
    found = {(m, norm(r.path)) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    assert not {w for w in REMOVED_V3 if (w[0], norm(V3 + w[1])) in found}
    assert not any('/sestava' in p or re.search(r'/ponudbe/\{[a-z_]+\}/postavke', p) for _, p in found)


def test_v3_poti_zahtevajo_zeton_sejo_in_aktivnega_mojstra_pri_tem_podjetju():
    wanted = {(m, norm(V3 + p)) for m, p in NEW_V3}
    checked = 0
    for r in app.routes:
        if not isinstance(r, APIRoute): continue
        for m in r.methods:
            if (m, norm(r.path)) not in wanted: continue
            deps = set(calls(r.dependant)); checked += 1
            assert current_user in deps and session_database in deps and administrator not in deps and access_customer() not in deps, (m, r.path)
            assert {getattr(c, 'company_role', None) for c in deps} - {None} == {'mojster'}, (m, r.path)
    assert checked == len(NEW_V3)


def access_customer():
    from app import access
    return access.customer


def test_delavci_poti_niso_dostopne_delavcu_in_stranki():
    for path, deps in ROUTES:
        if path.endswith('/delavci') or '/delavci/' in path: assert {getattr(c, 'company_role', None) for c in deps} - {None} == {'mojster'}, path


def test_nove_poti_brez_zetona_so_401():
    from uuid import uuid4
    from fastapi.testclient import TestClient
    c, u, m = TestClient(app, raise_server_exceptions=False), uuid4(), uuid4()
    base = f'/api/podjetja/{u}'
    for method, path in [('get', f'{base}/projekti'), ('post', f'{base}/projekti'), ('put', f'{base}/projekti/{m}'), ('post', f'{base}/projekti/{m}/ogled'),
                         ('get', '/api/projekti'), ('get', f'/api/projekti/{m}'), ('get', f'{base}/vrste-dela'), ('post', f'{base}/vrste-dela'), ('put', f'{base}/vrste-dela/{m}'),
                         ('put', f'{base}/vrste-dela/{m}/materiali/{m}'), ('delete', f'{base}/vrste-dela/{m}/materiali/{m}'),
                         ('get', f'{base}/projekti/{m}/postavke'), ('post', f'{base}/projekti/{m}/postavke'), ('post', f'{base}/projekti/{m}/postavke/iz-cenika'), ('put', f'{base}/projekti/{m}/postavke/{m}'),
                         ('delete', f'{base}/projekti/{m}/postavke/{m}'), ('post', f'{base}/projekti/{m}/postavke/{m}/izmere'), ('put', f'{base}/projekti/{m}/postavke/{m}/izmere/{m}'),
                         ('delete', f'{base}/projekti/{m}/postavke/{m}/izmere/{m}'), ('get', f'{base}/delavci'), ('get', f'{base}/delavci/povabila'), ('post', f'{base}/delavci/povabila'), ('post', f'{base}/delavci/povabila/{m}/preklic'),
                         ('patch', f'{base}/delavci/{m}'), ('get', '/api/povabila'), ('post', f'/api/povabila/{m}/odlocitev')]:
        assert getattr(c, method)(path).status_code == 401, (method, path)


def test_admin_poti_ostanejo_samo_za_administratorja_tudi_z_razsirjenim_seznamom_vlog():
    wanted = {('GET', '/api/admin/vloge'), ('POST', '/api/admin/vloge'), ('PATCH', '/api/admin/vloge/{role_id}'), ('GET', '/api/admin/uporabniki')}
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    assert wanted <= found
    for path, deps in ROUTES:
        if path.startswith('/api/admin/'): assert administrator in deps and not any(getattr(c, 'company_role', None) for c in deps), path


def test_lastni_projekti_zahtevajo_vlogo_stranka():
    from app import access
    customer = getattr(access, 'customer', None)
    assert customer is not None, 'app.access.customer manjka'
    for path, deps in ROUTES:
        if path.startswith('/api/projekti'): assert customer in deps and current_user in deps and session_database in deps, path


def test_ponudbe_mojstra_poti_obstajajo_in_so_zascitene():
    # v3: the draft is only a header; line editing routes are gone (see REMOVED_V3)
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    base = '/api/podjetja/{company_id}/projekti/{projekt_id}/ponudbe'
    wanted = {('GET', base), ('POST', base), ('GET', base + '/{ponudba_id}'), ('PUT', base + '/{ponudba_id}')}
    missing = {w for w in wanted if not any(m == w[0] and re.sub(r'\{[a-z_]+\}', '{}', p) == re.sub(r'\{[a-z_]+\}', '{}', w[1]) for m, p in found)}
    assert not missing, missing
    quote_routes = [(p, d) for p, d in ROUTES if p.startswith(base)]
    assert len(quote_routes) >= 5
    for path, deps in quote_routes: assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps) and current_user in deps and session_database in deps, path


def test_posiljanje_in_odlocitev_o_ponudbi_poti_obstajajo_in_so_zascitene():
    from app import access
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    send = '/api/podjetja/{company_id}/projekti/{projekt_id}/ponudbe/{ponudba_id}/poslji'
    wanted = {('POST', send), ('GET', '/api/projekti/{projekt_id}/ponudbe'), ('POST', '/api/projekti/{projekt_id}/ponudbe/{ponudba_id}/odlocitev')}
    norm = lambda p: re.sub(r'\{[a-z_]+\}', '{}', p)
    missing = {w for w in wanted if not any(m == w[0] and norm(p) == norm(w[1]) for m, p in found)}
    assert not missing, missing
    for path, deps in ROUTES:
        if norm(path) == norm(send): assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps) and current_user in deps and session_database in deps, path
        if norm(path) in (norm(w[1]) for w in wanted if w[1] != send):
            assert access.customer in deps and current_user in deps and session_database in deps and administrator not in deps and not any(getattr(c, 'company_role', None) for c in deps), path


def test_termin_izvedba_in_racun_poti_obstajajo_in_so_zascitene():
    from app import access
    found = {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    base = '/api/podjetja/{company_id}/projekti/{projekt_id}'
    wanted = {('PUT', base + '/termin'), ('POST', base + '/izvedba'), ('GET', base + '/racun'), ('POST', base + '/racun/izdaj'), ('POST', base + '/racun/placilo'), ('GET', '/api/projekti/{projekt_id}/racun')}
    norm = lambda p: re.sub(r'\{[a-z_]+\}', '{}', p)
    missing = {w for w in wanted if not any(m == w[0] and norm(p) == norm(w[1]) for m, p in found)}
    assert not missing, missing
    for path, deps in ROUTES:
        if norm(path).startswith(norm(base)) and norm(path).split('/{}/')[-1].split('/')[0] in ('termin', 'izvedba', 'racun'):
            assert any(getattr(c, 'company_role', None) == 'mojster' for c in deps) and current_user in deps and session_database in deps, path
        if norm(path) == norm('/api/projekti/{projekt_id}/racun'):
            assert access.customer in deps and current_user in deps and session_database in deps and administrator not in deps and not any(getattr(c, 'company_role', None) for c in deps), path


def test_stara_pot_dodaj_delavca_je_odstranjena():
    found = {(m, norm(r.path)) for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    assert ('POST', norm(V3 + '/delavci')) not in found


def test_povabila_prejemnika_zahtevajo_samo_zeton_in_sejo_brez_vloge():
    found = {(m, r.path): r for r in app.routes if isinstance(r, APIRoute) for m in r.methods}
    for key in (('GET', '/api/povabila'), ('POST', '/api/povabila/{povabilo_id}/odlocitev')):
        deps = set(calls(found[key].dependant)); assert current_user in deps and session_database in deps and administrator not in deps and access_customer() not in deps and not any(getattr(c, 'company_role', None) for c in deps), key
