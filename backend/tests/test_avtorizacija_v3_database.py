"""G6 avtorizacija (model v3 + US-08 povabila): HTTP-level IDOR, povabila, pogled stranke, admin, odvzete vloge in dve dirki. Pravi FastAPI TestClient nad disposable LOCAL Supabase.
Vsak zahtevek gre skozi pravi guard (company_member / customer / administrator) in pravo sejo; samo token je nadomeščen z izbiro uporabnika."""
import json
import os
import threading
from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4
import psycopg
import pytest
from psycopg.rows import dict_row
from test_model_database import db, identities, as_user, catalog, vrsta_of  # noqa: F401
from test_identity_database import api_client  # noqa: F401
from test_postavke_socasnost_database import live, prepared, new_draft, meas_kw, run  # noqa: F401
from v3_quotes import add_item, raw_quote, send, new_project, vrsta, call  # noqa: F401
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
NF = {'detail': 'Zapis ni na voljo.'}
GENERIC = 'Povabila ni mogoče sprejeti.'
INTERNAL = {'urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'cena_dela', 'cena_materiala', 'vrsta_dela_id', 'postavka_cenika_id', 'materiali', 'material_id', 'kolicina_na_enoto', 'kolicina_skupaj', 'nabavna_cena', 'marza', 'strosek_na_enoto'}
SNAPSHOT_TABLES = ['quoteflow.vrsta_dela', 'quoteflow.material_vrste_dela', 'quoteflow.postavka_cenika', 'quoteflow.material', 'quoteflow.projekt', 'quoteflow.postavka_projekta', 'quoteflow.izmera', 'quoteflow.ponudba',
                   'quoteflow.postavka_ponudbe', 'quoteflow.izmera_ponudbe', 'quoteflow.delo_ponudbe', 'quoteflow.racun', 'quoteflow.vloga_uporabnika', 'quoteflow_private.povabilo_delavca']


def keys(value):
    if isinstance(value, dict): return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list): return {k for v in value for k in keys(v)}
    return set()


def fingerprint(db):
    return {t: db.execute(f'select count(*) as n, md5(coalesce(string_agg(x::text, \'|\' order by x::text), \'\')) as h from {t} x').fetchone() for t in SNAPSHOT_TABLES}


def new_user(db, users, name, confirmed=True):
    uid, sid = uuid4(), uuid4(); email = f'{name}-{uid}@example.test'
    db.execute('insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at) values(%s,%s,%s::jsonb,%s)', (uid, email, json.dumps({'ime': 'Ime', 'priimek': name}), 'now()' if confirmed else None))
    db.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid)); users[name] = (uid, sid)
    db.execute('set constraints all immediate'); db.execute('set constraints all deferred')
    return email


def email_of(db, who): return db.execute('select email from auth.users where id=%s', (who[0],)).fetchone()['email']


@pytest.fixture
def w(db, identities, catalog, api_client):
    client, selected = api_client; users, a, b, role_a = identities; (ka, ma, ca), (kb, mb, cb) = catalog
    pa1, pa2, pb1 = new_project(db, users, a, 'customer'), new_project(db, users, a, 'outsider'), new_project(db, users, b, 'customer')
    ia1, ia2, ib1 = add_item(db, pa1), add_item(db, pa2), add_item(db, pb1)
    one = lambda sql, *args: db.execute(sql, args).fetchone()['id']
    za1, za2, zb1 = (one('select id from quoteflow.izmera where postavka_projekta_id=%s', i) for i in (ia1, ia2, ib1))
    qa1 = raw_quote(db, pa1); send(db, users, a, qa1); qa2, qb1 = raw_quote(db, pa2), raw_quote(db, pb1)
    new_user(db, users, 'invitee_a'); new_user(db, users, 'invitee_b')
    inv_a = call(db, users, 'owner_a', 'povabi_delavca', podjetje=a, e_posta=email_of(db, users['invitee_a']))['id']
    inv_b = call(db, users, 'owner_b', 'povabi_delavca', podjetje=b, e_posta=email_of(db, users['invitee_b']))['id']
    role_b = one("select id from quoteflow.vloga_uporabnika where podjetje_id=%s and vloga='delavec'", b)
    return SimpleNamespace(c=client, sel=selected, db=db, users=users, a=a, b=b, pa1=pa1, pa2=pa2, pb1=pb1, ia1=ia1, ia2=ia2, ib1=ib1, za1=za1, za2=za2, zb1=zb1, qa1=qa1, qa2=qa2, qb1=qb1, ka=ka, ma=ma, ca=ca, kb=kb, mb=mb, cb=cb,
                           va=vrsta_of(db, ca), vb=vrsta_of(db, cb), inv_a=inv_a, inv_b=inv_b, role_a=role_a, role_b=role_b)


def R(w, who, method, path, body=None):
    w.sel['name'] = who
    r = getattr(w.c, method)(path, **({'json': body} if body is not None else {}))
    if path.startswith('/api'): assert r.headers.get('cache-control') == 'no-store', (method, path)
    return r


def item_body(vrsta_id, **o): return {'naziv': 'Polaganje', 'opis': '', 'vrsta_dela_id': str(vrsta_id), 'enota': 'm2', 'cena_na_enoto': '10', 'kolicina': '1', 'popust': '0', 'stopnja_ddv': '0.22', 'urna_postavka': '25', 'stevilo_ur': '8', 'stevilo_delavcev': 2} | o


def routes(c, p, it, iz, vr, mat, cat, q, role, inv, vr_body):
    """Every new or changed route that carries a foreign-able id, parameterised by the ids the caller smuggles in. c = company in the path."""
    A, P = f'/api/podjetja/{c}', f'/api/podjetja/{c}/projekti/{p}'
    return [
        ('put', f'{A}/vrste-dela/{vr}', {'naziv': 'X', 'opis': '', 'urna_postavka': '1', 'stevilo_ur': '1', 'stevilo_delavcev': 1, 'aktivna': True}),
        ('put', f'{A}/vrste-dela/{vr}/materiali/{mat}', {'kolicina_na_enoto': '1.5'}), ('delete', f'{A}/vrste-dela/{vr}/materiali/{mat}', None),
        ('put', f'{A}/cenik/{cat}', {'naziv': 'X', 'opis': 'Opis', 'vrsta_dela_id': str(vr), 'enota': 'm2', 'cena_na_enoto': '1', 'stopnja_ddv': '0.22', 'aktivna': True}),
        ('get', f'{P}/postavke', None), ('post', f'{P}/postavke', item_body(vr)), ('post', f'{P}/postavke/iz-cenika', {'postavka_cenika_id': str(cat), 'kolicina': '1', 'popust': '0'}),
        ('put', f'{P}/postavke/{it}', item_body(vr)), ('delete', f'{P}/postavke/{it}', None),
        ('post', f'{P}/postavke/{it}/izmere', {'kosi': '1', 'dolzina': '2', 'visina': '3'}), ('put', f'{P}/postavke/{it}/izmere/{iz}', {'kosi': '9', 'dolzina': '2', 'visina': '3'}), ('delete', f'{P}/postavke/{it}/izmere/{iz}', None),
        ('get', f'{P}/ponudbe', None), ('post', f'{P}/ponudbe', {}), ('get', f'{P}/ponudbe/{q}', None), ('put', f'{P}/ponudbe/{q}', {}), ('post', f'{P}/ponudbe/{q}/poslji', None),
        ('get', f'{P}/racun', None), ('post', f'{P}/racun/izdaj', {'prejemnik_naziv': 'X', 'prejemnik_naslov': 'Y', 'zapade_dne': str(date.today() + timedelta(days=10))}), ('post', f'{P}/racun/placilo', None),
        ('patch', f'{A}/delavci/{role}', {'aktivna': False}), ('post', f'{A}/delavci/povabila/{inv}/preklic', None)]


def test_tuje_podjetje_vsaka_nova_pot_je_403_in_nic_se_ne_spremeni(w):
    before = fingerprint(w.db)
    for m, path, body in routes(w.a, w.pa1, w.ia1, w.za1, w.va, w.ma, w.ca, w.qa1, w.role_a, w.inv_a, None) + [('get', f'/api/podjetja/{w.a}/vrste-dela', None), ('get', f'/api/podjetja/{w.a}/delavci', None), ('get', f'/api/podjetja/{w.a}/delavci/povabila', None),
                                                                                                                  ('post', f'/api/podjetja/{w.a}/delavci/povabila', {'e_posta': 'x@example.test'}), ('post', f'/api/podjetja/{w.a}/vrste-dela', item_body(w.va) | {'vrsta_dela_id': None})]:
        r = R(w, 'owner_b', m, path, body); assert r.status_code == 403 and r.json() == {'detail': 'Potrebna je aktivna vloga mojstra pri izbranem podjetju.'}, (m, path, r.status_code, r.text)
    assert fingerprint(w.db) == before


def test_tuji_id_pod_lastnim_podjetjem_je_povsod_enak_404(w):
    """Mojster B, pot pod podjetjem B, vsi id-ji iz podjetja A."""
    before = fingerprint(w.db)
    cases = routes(w.b, w.pa1, w.ia1, w.za1, w.va, w.ma, w.ca, w.qa1, w.role_a, w.inv_a, None)
    cases += [('put', f'/api/podjetja/{w.b}/vrste-dela/{w.va}/materiali/{w.mb}', {'kolicina_na_enoto': '1'}), ('put', f'/api/podjetja/{w.b}/vrste-dela/{w.vb}/materiali/{w.ma}', {'kolicina_na_enoto': '1'}),
              ('delete', f'/api/podjetja/{w.b}/vrste-dela/{w.vb}/materiali/{w.ma}', None),
              # own project, foreign catalogue / work type / item / measurement / quote
              ('post', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke', item_body(w.va)), ('post', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/iz-cenika', {'postavka_cenika_id': str(w.ca), 'kolicina': '1', 'popust': '0'}),
              ('put', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/{w.ia1}', item_body(w.vb)), ('delete', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/{w.ia1}', None),
              ('post', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/{w.ia1}/izmere', {'kosi': '1', 'dolzina': '2', 'visina': '3'}), ('put', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/{w.ib1}/izmere/{w.za1}', {'kosi': '9', 'dolzina': '2', 'visina': '3'}),
              ('delete', f'/api/podjetja/{w.b}/projekti/{w.pb1}/postavke/{w.ib1}/izmere/{w.za1}', None), ('get', f'/api/podjetja/{w.b}/projekti/{w.pb1}/ponudbe/{w.qa1}', None),
              ('post', f'/api/podjetja/{w.b}/projekti/{w.pb1}/ponudbe/{w.qa2}/poslji', None), ('put', f'/api/podjetja/{w.b}/vrste-dela/{w.vb}/materiali/{w.ma}', {'kolicina_na_enoto': '1'})]
    for m, path, body in cases:
        r = R(w, 'owner_b', m, path, body); assert r.status_code == 404 and (r.json() == NF if r.content else True), (m, path, r.status_code, r.text)
    assert fingerprint(w.db) == before


def test_id_iz_drugega_projekta_ali_podjetja_pod_lastnim_projektom_je_404(w):
    """Mojster A, projekt pa1: postavka/ponudba projekta pa2, vse iz B."""
    before = fingerprint(w.db)
    p1, p2 = f'/api/podjetja/{w.a}/projekti/{w.pa1}', f'/api/podjetja/{w.a}/projekti/{w.pa2}'
    cases = [('put', f'{p1}/postavke/{w.ia2}', item_body(w.va)), ('delete', f'{p1}/postavke/{w.ia2}', None), ('post', f'{p1}/postavke/{w.ia2}/izmere', {'kosi': '1', 'dolzina': '2', 'visina': '3'}),
             ('put', f'{p1}/postavke/{w.ia1}/izmere/{w.za2}', {'kosi': '9', 'dolzina': '2', 'visina': '3'}), ('delete', f'{p1}/postavke/{w.ia1}/izmere/{w.za2}', None),
             ('put', f'{p1}/postavke/{w.ia2}/izmere/{w.za2}', {'kosi': '9', 'dolzina': '2', 'visina': '3'}),
             ('get', f'{p1}/ponudbe/{w.qa2}', None), ('put', f'{p1}/ponudbe/{w.qa2}', {}), ('post', f'{p1}/ponudbe/{w.qa2}/poslji', None), ('get', f'{p2}/ponudbe/{w.qa1}', None), ('post', f'{p2}/ponudbe/{w.qa1}/poslji', None),
             # B's ids under A's own project and company
             ('post', f'{p1}/postavke', item_body(w.vb)), ('put', f'{p1}/postavke/{w.ia1}', item_body(w.vb)), ('post', f'{p1}/postavke/iz-cenika', {'postavka_cenika_id': str(w.cb), 'kolicina': '1', 'popust': '0'}),
             ('get', f'{p1}/ponudbe/{w.qb1}', None), ('post', f'{p1}/ponudbe/{w.qb1}/poslji', None), ('put', f'/api/podjetja/{w.a}/vrste-dela/{w.vb}', {'naziv': 'X', 'opis': '', 'urna_postavka': '1', 'stevilo_ur': '1', 'stevilo_delavcev': 1, 'aktivna': True}),
             ('put', f'/api/podjetja/{w.a}/vrste-dela/{w.va}/materiali/{w.mb}', {'kolicina_na_enoto': '1'}), ('put', f'/api/podjetja/{w.a}/vrste-dela/{w.vb}/materiali/{w.ma}', {'kolicina_na_enoto': '1'}),
             ('delete', f'/api/podjetja/{w.a}/vrste-dela/{w.va}/materiali/{w.mb}', None), ('put', f'/api/podjetja/{w.a}/cenik/{w.cb}', {'naziv': 'X', 'opis': 'Opis', 'vrsta_dela_id': str(w.va), 'enota': 'm2', 'cena_na_enoto': '1', 'stopnja_ddv': '0.22', 'aktivna': True}),
             ('patch', f'/api/podjetja/{w.a}/delavci/{w.role_b}', {'aktivna': False}), ('post', f'/api/podjetja/{w.a}/delavci/povabila/{w.inv_b}/preklic', None),
             ('post', f'/api/podjetja/{w.a}/delavci/povabila/{uuid4()}/preklic', None), ('patch', f'/api/podjetja/{w.a}/delavci/{uuid4()}', {'aktivna': False}),
             ('get', f'/api/podjetja/{w.a}/projekti/{w.pb1}/postavke', None), ('get', f'/api/podjetja/{w.a}/projekti/{uuid4()}/ponudbe', None), ('get', f'/api/podjetja/{w.a}/projekti/{w.pb1}/racun', None)]
    for m, path, body in cases:
        r = R(w, 'owner_a', m, path, body); assert r.status_code == 404 and (r.json() == NF if r.content else True), (m, path, r.status_code, r.text)
    assert fingerprint(w.db) == before


@pytest.mark.parametrize('who', ['worker', 'customer', 'outsider', 'admin'])
def test_napacna_vloga_je_403_na_novih_mojstrskih_poteh(w, who):
    before = fingerprint(w.db)
    for m, path, body in routes(w.a, w.pa1, w.ia1, w.za1, w.va, w.ma, w.ca, w.qa1, w.role_a, w.inv_a, None) + [('get', f'/api/podjetja/{w.a}/vrste-dela', None), ('get', f'/api/podjetja/{w.a}/delavci', None)]:
        r = R(w, who, m, path, body); assert r.status_code == 403, (who, m, path, r.status_code, r.text)
    assert fingerprint(w.db) == before


# --- povabila ---
def invite(w, who, mail, company=None): return R(w, who, 'post', f'/api/podjetja/{company or w.a}/delavci/povabila', {'e_posta': mail})


def test_povabilo_sprejme_in_vidi_samo_uporabnik_s_potrjenim_naslovom(w):
    assert [x['id'] for x in R(w, 'invitee_a', 'get', '/api/povabila').json()] == [str(w.inv_a)]
    for who in ('invitee_b', 'owner_b', 'owner_a', 'worker', 'customer', 'admin'):
        assert str(w.inv_a) not in [x['id'] for x in R(w, who, 'get', '/api/povabila').json()]
        before = fingerprint(w.db)
        r = R(w, who, 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': True}); assert r.status_code == 404 and r.json() == NF, (who, r.text)
        r = R(w, who, 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': False}); assert r.status_code == 404 and r.json() == NF, (who, r.text)
        assert fingerprint(w.db) == before
    assert R(w, 'invitee_a', 'post', f'/api/povabila/{uuid4()}/odlocitev', {'sprejmi': True}).json() == NF
    r = R(w, 'invitee_a', 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': True}); assert r.status_code == 200 and r.json() == {'id': str(w.inv_a), 'stanje': 'sprejeto'}, r.text
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga='delavec' and aktivna", (w.users['invitee_a'][0], w.a)).fetchone()['n'] == 1
    r = R(w, 'invitee_a', 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': True}); assert r.status_code in (404, 409), r.text   # second submit is refused, no duplicate role
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga='delavec'", (w.users['invitee_a'][0], w.a)).fetchone()['n'] == 1


def test_nepotrjen_naslov_ne_vidi_in_ne_sprejme_povabila(w):
    mail = new_user(w.db, w.users, 'unconfirmed', confirmed=False)
    inv = invite(w, 'owner_a', mail); assert inv.status_code == 201, inv.text
    assert R(w, 'unconfirmed', 'get', '/api/povabila').json() == []
    r = R(w, 'unconfirmed', 'post', f'/api/povabila/{inv.json()["id"]}/odlocitev', {'sprejmi': True}); assert r.status_code in (404, 409), r.text
    assert w.db.execute('select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga=%s', (w.users['unconfirmed'][0], 'delavec')).fetchone()['n'] == 0


def test_stranka_odprtega_projekta_podjetja_ne_sprejme_povabila_d19(w):
    inv = invite(w, 'owner_a', email_of(w.db, w.users['customer'])); assert inv.status_code == 201
    assert invite(w, 'owner_a', 'neznan-' + uuid4().hex + '@example.test').json().keys() == inv.json().keys()   # identical shape for strangers
    r = R(w, 'customer', 'post', f'/api/povabila/{inv.json()["id"]}/odlocitev', {'sprejmi': True}); assert r.status_code == 409 and r.json() == {'detail': GENERIC}, r.text
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga='delavec'", (w.users['customer'][0], w.a)).fetchone()['n'] == 0


def test_poteklo_povabilo_se_ne_sprejme_in_ni_na_seznamu(w):
    w.db.execute("update quoteflow_private.povabilo_delavca set poslano_ob=now()-interval '15 days' where id=%s", (w.inv_a,))
    assert R(w, 'invitee_a', 'get', '/api/povabila').json() == []
    r = R(w, 'invitee_a', 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': True}); assert r.status_code == 409 and r.json() == {'detail': GENERIC}, r.text
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='delavec' and podjetje_id=%s", (w.users['invitee_a'][0], w.a)).fetchone()['n'] == 0


def test_preklicano_povabilo_ni_vec_sprejemljivo_in_tuj_mojster_ga_ne_more_preklicati(w):
    path = f'/api/podjetja/{w.a}/delavci/povabila/{w.inv_a}/preklic'
    assert R(w, 'owner_b', 'post', path).status_code == 403
    assert R(w, 'owner_b', 'post', f'/api/podjetja/{w.b}/delavci/povabila/{w.inv_a}/preklic').json() == NF
    for who in ('worker', 'customer', 'invitee_a'): assert R(w, who, 'post', path).status_code == 403
    assert w.db.execute('select stanje from quoteflow_private.povabilo_delavca where id=%s', (w.inv_a,)).fetchone()['stanje'] == 'povabljen'
    r = R(w, 'owner_a', 'post', path); assert r.status_code == 200 and r.json()['stanje'] == 'preklicano', r.text
    assert R(w, 'owner_a', 'post', path).status_code in (404, 409)   # double cancel
    assert R(w, 'invitee_a', 'get', '/api/povabila').json() == []
    r = R(w, 'invitee_a', 'post', f'/api/povabila/{w.inv_a}/odlocitev', {'sprejmi': True}); assert r.status_code in (404, 409), r.text
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='delavec'", (w.users['invitee_a'][0],)).fetchone()['n'] == 0


def test_povabilo_ne_razkrije_obstoja_uporabnika_in_ne_ustvari_vloge(w):
    shapes = []
    for mail in (email_of(w.db, w.users['outsider']), email_of(w.db, w.users['admin']), 'nihce-' + uuid4().hex + '@example.test', email_of(w.db, w.users['owner_b'])):
        r = invite(w, 'owner_a', mail); assert r.status_code == 201, r.text
        assert set(r.json()) == {'id', 'e_posta', 'stanje', 'poslano_ob'} and r.json()['stanje'] == 'povabljen'; shapes.append(r.json()['e_posta'] == mail)
    assert all(shapes)
    assert w.db.execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga in ('delavec','mojster') and podjetje_id=%s", (w.users['outsider'][0], w.a)).fetchone()['n'] == 0
    assert set(R(w, 'owner_a', 'get', f'/api/podjetja/{w.a}/delavci/povabila').json()[0]) == {'id', 'e_posta', 'stanje', 'poslano_ob', 'odloceno_ob'}
    assert R(w, 'owner_a', 'post', f'/api/podjetja/{w.a}/delavci', {'e_posta': 'a@example.test'}).status_code in (404, 405)   # direct grant removed


# --- pogled stranke ---
def test_stranka_vidi_samo_poslane_verzije_svojih_projektov_brez_notranjih_polj(w):
    path = f'/api/projekti/{w.pa1}/ponudbe'
    first = R(w, 'customer', 'get', path); assert first.status_code == 200 and [q['id'] for q in first.json()] == [str(w.qa1)]
    draft = raw_quote(w.db, w.pa1)   # v2 is a draft: invisible
    assert [q['id'] for q in R(w, 'customer', 'get', path).json()] == [str(w.qa1)]
    r = R(w, 'customer', 'post', f'{path}/{draft}/odlocitev', {'sprejmi': True}); assert r.status_code in (404, 409) and r.status_code != 200, r.text
    assert w.db.execute('select stanje from quoteflow.ponudba where id=%s', (draft,)).fetchone()['stanje'] == 'osnutek'
    # v2 gets another measurement and is sent: only the latest version carries izmere
    as_owner_izmera = call(w.db, w.users, 'owner_a', 'shrani_izmero', podjetje=w.a, projekt=w.pa1, postavka=w.ia1, izmera=None, odstej=False, kosi=3, dolzina=2, visina=2, sirina=None)
    assert as_owner_izmera['id']
    send(w.db, w.users, w.a, draft)
    rows = R(w, 'customer', 'get', path).json(); assert [q['id'] for q in rows] == [str(draft), str(w.qa1)]
    n = lambda q: [len(l['izmere']) for l in q['postavke']]
    assert n(rows[0]) == [2] and n(rows[1]) == [0]
    allowed_line = {'zaporedje', 'naziv', 'opis', 'vrsta_dela', 'enota', 'cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'izmera_skupaj', 'neto', 'ddv', 'koncna_cena', 'izmere'}
    for q in rows:
        assert set(q) == {'id', 'stevilka', 'razlicica', 'stanje', 'poslano_ob', 'odgovorjeno_ob', 'velja_do', 'nadomescena', 'neto', 'ddv', 'skupaj', 'postavke', 'ddv_po_stopnjah', 'podjetje_naziv'}
        assert all(set(l) == allowed_line for l in q['postavke']) and not keys(q) & INTERNAL, keys(q) & INTERNAL
    # decision on an older version: refused, or the answer holds only that version's (empty) izmere
    r = R(w, 'customer', 'post', f'{path}/{w.qa1}/odlocitev', {'sprejmi': False})
    if r.status_code == 200: assert r.json()['id'] == str(w.qa1) and n(r.json()) == [0] and not keys(r.json()) & INTERNAL
    else: assert r.status_code in (404, 409), r.text
    r = R(w, 'customer', 'post', f'{path}/{draft}/odlocitev', {'sprejmi': False}); assert r.status_code == 200 and n(r.json()) == [2] and r.json()['stanje'] == 'zavrnjena' and not keys(r.json()) & INTERNAL, r.text
    assert R(w, 'customer', 'post', f'{path}/{draft}/odlocitev', {'sprejmi': True}).status_code in (404, 409)   # double submit


def test_stranka_ne_vidi_tujih_projektov_in_tujih_odlocitev(w):
    send(w.db, w.users, w.a, w.qa2); before = fingerprint(w.db)
    assert [p['id'] for p in R(w, 'customer', 'get', '/api/projekti').json()] == sorted([str(w.pa1), str(w.pb1)], key=lambda x: [p['id'] for p in R(w, 'customer', 'get', '/api/projekti').json()].index(x))
    assert str(w.pa2) not in [p['id'] for p in R(w, 'customer', 'get', '/api/projekti').json()]
    for m, path, body in [('get', f'/api/projekti/{w.pa2}/ponudbe', None), ('post', f'/api/projekti/{w.pa2}/ponudbe/{w.qa2}/odlocitev', {'sprejmi': True}), ('get', f'/api/projekti/{w.pa2}/racun', None), ('get', f'/api/projekti/{w.pa2}', None),
                          ('post', f'/api/projekti/{w.pa1}/ponudbe/{w.qa2}/odlocitev', {'sprejmi': True}), ('post', f'/api/projekti/{w.pa1}/ponudbe/{w.qb1}/odlocitev', {'sprejmi': True})]:
        r = R(w, 'customer', m, path, body); assert r.status_code == 404 and r.json() == NF, (path, r.status_code, r.text)
    for who in ('owner_a', 'owner_b', 'worker'):   # masters and workers decide nothing
        r = R(w, who, 'post', f'/api/projekti/{w.pa2}/ponudbe/{w.qa2}/odlocitev', {'sprejmi': True}); assert r.status_code in (403, 404), (who, r.status_code)
    assert fingerprint(w.db) == before


def test_uporabnik_ki_je_stranka_projekta_in_delavec_podjetja_dobi_404_pri_odlocitvi_d9(w):
    p = new_project(w.db, w.users, w.a, 'worker')   # worker: delavec of A
    qid = raw_quote(w.db, p); send(w.db, w.users, w.a, qid); before = fingerprint(w.db)
    r = R(w, 'worker', 'post', f'/api/projekti/{p}/ponudbe/{qid}/odlocitev', {'sprejmi': True}); assert r.status_code == 404 and r.json() == NF, r.text
    assert fingerprint(w.db) == before


def test_racun_stranke_ne_vsebuje_notranjih_polj_in_ne_tujega_projekta(w):
    r = R(w, 'customer', 'post', f'/api/projekti/{w.pa1}/ponudbe/{w.qa1}/odlocitev', {'sprejmi': True}); assert r.status_code == 200, r.text
    assert R(w, 'customer', 'get', f'/api/projekti/{w.pa1}/racun').status_code == 404   # draft invoice is not for the buyer
    assert R(w, 'owner_a', 'post', f'/api/podjetja/{w.a}/projekti/{w.pa1}/racun/izdaj', {'prejemnik_naziv': 'X', 'prejemnik_naslov': 'Y', 'zapade_dne': str(date.today() + timedelta(days=10))}).status_code in (200, 409, 422)
    r = R(w, 'customer', 'get', f'/api/projekti/{w.pa1}/racun')
    if r.status_code == 200: assert not keys(r.json()) & INTERNAL and 'id' not in r.json()
    assert R(w, 'outsider', 'get', f'/api/projekti/{w.pa1}/racun').json() == NF


# --- admin ---
ADMIN = lambda w: [('get', '/api/admin/uporabniki', None), ('get', '/api/admin/vloge', None), ('get', '/api/admin/prosnje', None),
                   ('post', '/api/admin/podjetja', {'lastnik_id': str(w.users['outsider'][0]), 'naziv': 'N', 'maticna_stevilka': uuid4().hex[:20], 'naslov': 'x'}),
                   ('put', f'/api/admin/podjetja/{w.a}', {'naziv': 'N', 'maticna_stevilka': '1', 'naslov': 'x', 'aktivno': False}), ('post', '/api/admin/vloge', {'uporabnik_id': str(w.users['outsider'][0]), 'podjetje_id': str(w.a), 'vloga': 'delavec'}),
                   ('patch', f'/api/admin/vloge/{w.role_a}', {'aktivna': False}), ('post', f'/api/admin/prosnje/{uuid4()}/odlocitev', {'odobri': True})]


@pytest.mark.parametrize('who', ['owner_a', 'worker', 'customer', 'outsider'])
def test_admin_poti_so_403_za_vse_neadministratorje(w, who):
    before = fingerprint(w.db)
    for m, path, body in ADMIN(w):
        r = R(w, who, m, path, body); assert r.status_code == 403 and r.json() == {'detail': 'Potrebna je vloga administratorja.'}, (who, m, path, r.status_code, r.text)
    assert fingerprint(w.db) == before


def grants(w, who, role='delavec', company=None): return R(w, 'admin', 'post', '/api/admin/vloge', {'uporabnik_id': str(w.users[who][0]), 'podjetje_id': str(company or w.a), 'vloga': role})


@pytest.mark.parametrize('role', ['delavec', 'mojster'])
def test_admin_ne_dodeli_vloge_stranki_odprtega_projekta_in_nepotrjenemu_d19(w, role):
    mail = new_user(w.db, w.users, 'unconfirmed', confirmed=False); before = fingerprint(w.db)
    for who in ('customer', 'unconfirmed'):
        r = grants(w, who, role); assert 400 <= r.status_code < 500 and r.status_code != 404, (who, r.status_code, r.text)
        assert isinstance(r.json()['detail'], str) and mail not in r.text and str(w.users[who][0]) not in r.text and 'postgres' not in r.text.lower(), r.text
    assert fingerprint(w.db) == before


def test_admin_uporabniki_potrjen_ustreza_auth_email_confirmed_at(w):
    new_user(w.db, w.users, 'unconfirmed', confirmed=False)
    rows = {r['id']: r for r in R(w, 'admin', 'get', '/api/admin/uporabniki').json()}
    truth = {str(r['id']): r['c'] for r in w.db.execute('select id, email_confirmed_at is not null as c from auth.users').fetchall()}
    assert rows and all(set(r) == {'id', 'e_posta', 'ime', 'priimek', 'potrjen'} for r in rows.values())
    assert all(rows[i]['potrjen'] is truth[i] for i in rows) and rows[str(w.users['unconfirmed'][0])]['potrjen'] is False and rows[str(w.users['owner_a'][0])]['potrjen'] is True


# --- odvzete vloge ---
def test_odvzeti_mojster_dobi_403_z_istim_zetonom_na_novih_poteh(w):
    mail = new_user(w.db, w.users, 'second')
    r = grants(w, 'second', 'mojster'); assert r.status_code == 200, r.text; role = r.json()['id']
    probes = [('get', f'/api/podjetja/{w.a}/vrste-dela', None), ('get', f'/api/podjetja/{w.a}/delavci', None), ('get', f'/api/podjetja/{w.a}/delavci/povabila', None), ('get', f'/api/podjetja/{w.a}/projekti/{w.pa1}/postavke', None),
              ('get', f'/api/podjetja/{w.a}/projekti/{w.pa1}/ponudbe', None), ('post', f'/api/podjetja/{w.a}/delavci/povabila', {'e_posta': 'n-' + uuid4().hex + '@example.test'}),
              ('post', f'/api/podjetja/{w.a}/projekti/{w.pa1}/postavke', item_body(w.va))]
    assert all(R(w, 'second', m, p, b).status_code in (200, 201) for m, p, b in probes)
    assert R(w, 'admin', 'patch', f'/api/admin/vloge/{role}', {'aktivna': False}).status_code == 200
    before = fingerprint(w.db)
    for m, p, b in probes: assert R(w, 'second', m, p, b).status_code == 403, (m, p)
    assert fingerprint(w.db) == before
    assert R(w, 'admin', 'patch', f'/api/admin/vloge/{role}', {'aktivna': True}).status_code == 200 and R(w, 'second', 'get', f'/api/podjetja/{w.a}/vrste-dela').status_code == 200


def test_odvzeti_delavec_izgubi_dostop_takoj_in_nima_mojstrskih_poti(w):
    assert R(w, 'worker', 'get', f'/api/podjetja/{w.a}').status_code == 200
    assert R(w, 'worker', 'get', f'/api/podjetja/{w.a}/vrste-dela').status_code == 403
    assert R(w, 'owner_a', 'patch', f'/api/podjetja/{w.a}/delavci/{w.role_a}', {'aktivna': False}).status_code == 200
    assert R(w, 'worker', 'get', f'/api/podjetja/{w.a}').status_code == 404
    for p in ('vrste-dela', 'delavci', 'delavci/povabila', f'projekti/{w.pa1}/ponudbe', f'projekti/{w.pa1}/postavke'): assert R(w, 'worker', 'get', f'/api/podjetja/{w.a}/{p}').status_code == 403, p


# --- dirke (prave povezave s commitom, vsak zahtevek svoja povezava) ---
@pytest.fixture
def http(live):
    from fastapi import Request
    from fastapi.testclient import TestClient
    from app.access import session_database
    from app.auth import Principal, current_user
    from app.main import app
    env = live; people = {'owner': env['owner'], 'customer': env['customer'], 'worker': env['worker']}
    def principal(request: Request):
        uid, sid = people[request.headers['x-test-user']]; return Principal(uid, sid, 'x@example.test')
    def connection(request: Request):
        with psycopg.connect(env['url'], row_factory=dict_row) as c:
            with as_user(c, people[request.headers['x-test-user']]):
                if not c.execute('select quoteflow_private.aktivna_seja() as active').fetchone()['active']: raise RuntimeError('session')
                yield c
    app.dependency_overrides[current_user] = principal; app.dependency_overrides[session_database] = connection
    try: yield env, lambda: TestClient(app, raise_server_exceptions=False, headers={'x-test-user': 'owner'})
    finally: app.dependency_overrides.clear()


def together(*calls):
    barrier, out = threading.Barrier(len(calls)), [None] * len(calls)
    def go(i, f): barrier.wait(10); out[i] = f()
    threads = [threading.Thread(target=go, args=(i, f), daemon=True) for i, f in enumerate(calls)]
    [t.start() for t in threads]; [t.join(40) for t in threads]
    assert not any(t.is_alive() for t in threads), 'zahtevek ni končal'
    return out


def test_http_posiljanje_proti_dodajanju_izmere_da_skladen_posnetek_brez_500(prepared, http):
    env, make = http; admin = env['admin']; P = f'/api/podjetja/{env["a"]}/projekti/{env["p"]}'
    for round_ in range(5):
        q = new_draft(env); c1, c2 = make(), make()
        send_r, add_r = together(lambda: c1.post(f'{P}/ponudbe/{q}/poslji'), lambda: c2.post(f'{P}/postavke/{env["item"]}/izmere', json={'kosi': '5'}))
        assert send_r.status_code == 200 and add_r.status_code == 201, (round_, send_r.status_code, send_r.text, add_r.status_code, add_r.text)
        snap = admin.execute('select id, izmera_skupaj as s from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone()
        parts = admin.execute('select coalesce(sum(case when odstej then -vrednost else vrednost end),0) as s from quoteflow.izmera_ponudbe where postavka_ponudbe_id=%s', (snap['id'],)).fetchone()['s']
        live_total = admin.execute('select izmera_skupaj as s from quoteflow.postavka_projekta where id=%s', (env['item'],)).fetchone()['s']
        assert snap['s'] == parts and snap['s'] <= live_total and (live_total - snap['s']) in (0, 5), (round_, snap, parts, live_total)
        assert admin.execute("select count(*) as n from quoteflow_private.dogodek_dokumenta where ponudba_id=%s and dejanje='poslana'", (q,)).fetchone()['n'] == 1


def test_http_sociasni_povabili_istega_naslova_dasta_eno_odprto_povabilo(live, http):
    env, make = http; path = f'/api/podjetja/{env["a"]}/delavci/povabila'; c1, c2 = make(), make()
    r1, r2 = together(lambda: c1.post(path, json={'e_posta': env['worker_mail']}), lambda: c2.post(path, json={'e_posta': ' ' + env['worker_mail'].upper() + ' '}))
    assert r1.status_code == 201 and r2.status_code == 201 and r1.json()['id'] == r2.json()['id'], (r1.text, r2.text)
    assert env['admin'].execute("select count(*) as n from quoteflow_private.povabilo_delavca where podjetje_id=%s and stanje='povabljen'", (env['a'],)).fetchone()['n'] == 1
