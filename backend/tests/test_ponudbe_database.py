"""US-04 osnutek ponudbe v modelu v3: osnutek je samo glava, postavke živijo na projektu in se posnamejo ob pošiljanju. Functions, numbering, locks, RLS and isolation on disposable local Supabase.
Quotes are built through v3_quotes (project items + izmere + ustvari_ponudbo); posnetek and formula A are pinned in test_postavke_database.py."""
import os
from datetime import date, timedelta
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user, catalog
from test_identity_database import api_client
from v3_quotes import P, add_item, bad, call, company_of, draft, env, fails, lines, new_project, quiet, raw_quote, send, sent, year  # noqa: F401
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
FORM = {'naziv': 'Prenova kopalnice', 'opis': 'Menjava ploščic', 'lokacija_izvedbe': 'Maribor'}
M_ZAKLENJENO = 'Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.'
REMOVED_FUNCTIONS = ('dodaj_postavko_cenika', 'shrani_postavko', 'odstrani_postavko')


def test_ustvari_ponudbo_stevilka_p_leto_nnn_po_podjetju(env, db):
    users, a, b, p, cat = env
    r = call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, None)
    assert r['stevilka'] == f'P-{year(db)}-001' and r['razlicica'] == 1 and r['stanje'] == 'osnutek' and r['projekt_id'] == p
    p2 = new_project(db, users, a); r2 = call(db, users, 'owner_a', 'ustvari_ponudbo', a, p2, None)
    assert r2['stevilka'] == f'P-{year(db)}-002'
    pb = new_project(db, users, b); assert call(db, users, 'owner_b', 'ustvari_ponudbo', b, pb, None)['stevilka'] == f'P-{year(db)}-001'


def test_osnutek_je_samo_glava_brez_lastnih_postavk_tudi_ko_projekt_ima_postavke(env, db):
    users, a, _, p, _ = env; add_item(db, p); q = draft(db, users, a, p)
    assert not lines(db, q) and db.execute('select count(*) as n from quoteflow.postavka_projekta where projekt_id=%s', (p,)).fetchone()['n'] == 1


def test_ustvari_ponudbo_ze_osnutek_je_qfp09(env, db):
    users, a, _, p, _ = env; draft(db, users, a, p)
    bad(db, users, 'owner_a', 'QFP09', 'ustvari_ponudbo', a, p, None)


def test_ustvari_ponudbo_v_neustrezni_fazi_ali_ob_sprejeti_je_qfp07(env, db):
    users, a, _, p, _ = env
    for faza in ('termin', 'izvedba', 'obracun', 'zakljucen'):
        pid = new_project(db, users, a); quiet(db, 'projekt', "update quoteflow.projekt set faza=%s, zakljuceno_ob=case when %s='zakljucen' then now() end where id=%s", (faza, faza, pid))
        bad(db, users, 'owner_a', 'QFP07', 'ustvari_ponudbo', a, pid, None)
    pid = new_project(db, users, a); quiet(db, 'ponudba', "insert into quoteflow.ponudba(projekt_id,stevilka,stanje,poslano_ob,odgovorjeno_ob) values(%s,'P-X','sprejeta',now(),now())", (pid,))
    bad(db, users, 'owner_a', 'QFP07', 'ustvari_ponudbo', a, pid, None)


def test_ustvari_ponudbo_v_fazah_ogled_in_ponudba_je_dovoljeno(env, db):
    users, a, _, p, _ = env
    db.execute("update quoteflow.projekt set faza='ogled' where id=%s", (p,)); assert draft(db, users, a, p)


def test_nova_razlicica_ohrani_stevilko_ne_kopira_postavk_in_posname_trenutne_postavke_projekta(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p); old = lines(db, q); assert len(old) == 1
    add_item(db, p, naziv='Dodatno', price=D(10), qty=D(1), discount=D(0))
    r = call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, None)
    assert r['stevilka'] == db.execute('select stevilka from quoteflow.ponudba where id=%s', (q,)).fetchone()['stevilka'] and r['razlicica'] == 2 and r['stanje'] == 'osnutek' and r['id'] != q
    assert not lines(db, r['id']) and lines(db, q) == old and db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'poslana'
    call(db, users, 'owner_a', 'uredi_ponudbo', a, p, r['id'], db.execute('select current_date+10 as d').fetchone()['d'])
    send(db, users, a, r['id']); new = lines(db, r['id'])
    assert [l['naziv'] for l in new] == ['Polaganje', 'Dodatno'] and not {x['id'] for x in new} & {x['id'] for x in old}


def test_razlicica_po_zavrnjeni_je_max_plus_ena(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    call(db, users, 'customer', 'odgovori_ponudbo', p, q, False)
    assert call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, None)['razlicica'] == 2


def test_uredi_ponudbo_nastavi_veljavnost_in_zavrne_poslano(env, db):
    users, a, _, p, _ = env; q = draft(db, users, a, p); d = db.execute('select current_date+30 as d').fetchone()['d']
    assert call(db, users, 'owner_a', 'uredi_ponudbo', a, p, q, d)['velja_do'] == d
    add_item(db, p); send(db, users, a, q)
    bad(db, users, 'owner_a', 'QFP10', 'uredi_ponudbo', a, P(db, q), q, None)


def test_funkcije_urejanja_vrstic_ponudbe_ne_obstajajo_vec(db):
    names = {r['proname'] for r in db.execute("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private'")}
    assert not names & set(REMOVED_FUNCTIONS)


def test_neposredni_zapis_v_poslano_je_55000(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    fails(db, "update quoteflow.postavka_ponudbe set kolicina=9 where ponudba_id=%s", (q,), '55000')


def test_tuje_podjetje_projekt_in_ponudba_so_not_found(env, db):
    users, a, b, p, cat = env; q = draft(db, users, a, p); add_item(db, p)
    bad(db, users, 'owner_b', 'P0002', 'ustvari_ponudbo', b, p, None)
    for name, args in [('uredi_ponudbo', (p, q, None)), ('poslji_ponudbo', (p, q))]:
        bad(db, users, 'owner_b', 'P0002', name, b, *args); bad(db, users, 'owner_b', '42501', name, a, *args)
    bad(db, users, 'owner_a', 'P0002', 'ustvari_ponudbo', a, uuid4(), None)
    pb = new_project(db, users, b); qb = draft(db, users, b, pb, 'owner_b')
    bad(db, users, 'owner_a', 'P0002', 'uredi_ponudbo', a, P(db, qb), qb, None); bad(db, users, 'owner_a', 'P0002', 'poslji_ponudbo', a, P(db, qb), qb)
    assert db.execute('select stanje from quoteflow.ponudba where id=%s', (qb,)).fetchone()['stanje'] == 'osnutek'


@pytest.mark.parametrize('who', ['worker', 'customer', 'outsider', 'admin'])
def test_nemojster_ne_sme_nobene_funkcije(env, db, who):
    users, a, _, p, _ = env; q = draft(db, users, a, p); add_item(db, p)
    for name, args in [('ustvari_ponudbo', (p, None)), ('uredi_ponudbo', (p, q, None)), ('poslji_ponudbo', (p, q))]:
        bad(db, users, who, '42501', name, a, *args)
    assert db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'osnutek'


def test_odvzeta_vloga_mojstra_ne_more_urejati(env, db):
    users, a, _, p, _ = env
    role = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a)).fetchone()['id']
    q = draft(db, users, a, p, 'outsider'); db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,))
    bad(db, users, 'outsider', '42501', 'poslji_ponudbo', a, P(db, q), q); bad(db, users, 'outsider', '42501', 'uredi_ponudbo', a, P(db, q), q, None)


def test_funkcije_niso_dosegljive_anonimnim_in_service_role(db):
    for f in ('ustvari_ponudbo(uuid,uuid,date)', 'uredi_ponudbo(uuid,uuid,uuid,date)', 'poslji_ponudbo(uuid,uuid,uuid)'):
        for role in ('anon', 'service_role', 'quoteflow_app', 'public'):
            assert not db.execute("select has_function_privilege(%s,%s,'execute') as p", (role, Q + f)).fetchone()['p'], (role, f)
        assert db.execute("select has_function_privilege('authenticated',%s,'execute') as p", (Q + f,)).fetchone()['p'], f


def test_osnutek_in_notranje_tabele_so_nevidni_stranki_delavcu_in_tujcem_stranka_vidi_poslano_brez_materialov_in_dela(env, db):
    users, a, _, p, cat = env; q = raw_quote(db, p)
    for who in ('customer', 'worker', 'outsider', 'owner_b', 'admin'):
        with as_user(db, users[who]):
            for t in ('ponudba', 'postavka_ponudbe', 'material_ponudbe', 'izmera_ponudbe', 'delo_ponudbe', 'postavka_projekta', 'izmera'): assert db.execute(f'select count(*) as n from quoteflow.{t}').fetchone()['n'] == 0, (who, t)
    send(db, users, a, q)
    with as_user(db, users['customer']):
        assert db.execute('select count(*) as n from quoteflow.ponudba').fetchone()['n'] == 1 and db.execute('select count(*) as n from quoteflow.postavka_ponudbe').fetchone()['n'] == 1
        assert db.execute('select count(*) as n from quoteflow.izmera_ponudbe').fetchone()['n'] == 1
        for t in ('material_ponudbe', 'delo_ponudbe', 'postavka_projekta', 'izmera', 'vrsta_dela'): assert db.execute(f'select count(*) as n from quoteflow.{t}').fetchone()['n'] == 0, t
    with as_user(db, users['worker']):
        for t in ('material_ponudbe', 'delo_ponudbe', 'izmera_ponudbe'): assert db.execute(f'select count(*) as n from quoteflow.{t}').fetchone()['n'] == 0, t
    with as_user(db, users['customer']): fails(db, "insert into quoteflow.postavka_ponudbe(ponudba_id,zaporedje,naziv,vrsta_dela,enota,cena_na_enoto,kolicina) values(%s,9,'X','G','m',1,1)", (q,), '42501')


# Step 0: scoped integrity triggers keep rejecting cross-company rows but no longer scan unrelated companies
def reject(db, sql, args=()):
    with pytest.raises(psycopg.Error):
        with db.transaction():
            db.execute(sql, args); db.execute('set constraints all immediate')


def test_ozki_sprozilci_se_vedno_zavrnejo_tuje_vrstice(env, db):
    users, a, b, p, cat = env; it = add_item(db, p)
    reject(db, 'update quoteflow.postavka_projekta set postavka_cenika_id=%s where id=%s', (cat[1][2], it))
    reject(db, 'update quoteflow.postavka_projekta set vrsta_dela_id=(select vrsta_dela_id from quoteflow.postavka_cenika where id=%s) where id=%s', (cat[1][2], it))
    reject(db, 'insert into quoteflow.material_vrste_dela(vrsta_dela_id,material_id,kolicina_na_enoto) select vrsta_dela_id,%s,2 from quoteflow.postavka_cenika where id=%s', (cat[1][1], cat[0][2]))
    team_b = db.execute("insert into quoteflow.ekipa(podjetje_id,naziv) values(%s,'B') returning id", (b,)).fetchone()['id']
    reject(db, 'insert into quoteflow.projekt_ekipa values(%s,%s)', (p, team_b))


def test_dokumenti_sprozilec_se_vedno_zavrne_sprejeto_brez_racuna_in_racun_brez_sprejete(env, db):
    users, a, _, p, _ = env; q = raw_quote(db, p)
    reject(db, "update quoteflow.ponudba set stanje='sprejeta', poslano_ob=now(), odgovorjeno_ob=now() where id=%s", (q,))
    reject(db, 'insert into quoteflow.racun(ponudba_id) values(%s)', (q,))


def test_celovitost_ne_pregleduje_nepovezanih_podjetij(env, db):
    users, a, b, p, cat = env; it = add_item(db, p)
    quiet(db, 'postavka_projekta', 'update quoteflow.postavka_projekta set postavka_cenika_id=%s where id=%s', (cat[1][2], it))
    db.execute("insert into quoteflow.ekipa(podjetje_id,naziv) values(%s,'Druga ekipa')", (b,)); db.execute('set constraints all immediate')


def test_dokumenti_ne_pregleduje_nepovezanih_projektov(env, db):
    users, a, b, p, _ = env; q = raw_quote(db, p)
    quiet(db, 'ponudba', "update quoteflow.ponudba set stanje='sprejeta', poslano_ob=now(), odgovorjeno_ob=now() where id=%s", (q,))
    new_project(db, users, b); db.execute('set constraints all immediate')


# D8: administrator cannot assign himself a company role
def test_skrbnik_si_ne_dodeli_vloge_v_podjetju_qfp22(env, db):
    users, a, _, _, _ = env
    for role in ('mojster', 'delavec'): bad(db, users, 'admin', 'QFP22', 'dodeli_vlogo', users['admin'][0], a, role)
    r = call(db, users, 'admin', 'dodeli_vlogo', users['outsider'][0], a, 'delavec'); assert r['uporabnik_id'] == users['outsider'][0] and r['vloga'] == 'delavec'


def test_skrbnik_api_dodelitev_sebi_je_409(env, api_client):
    client, selected = api_client; users, a, _, _, _ = env
    r = client.post('/api/admin/vloge', json={'uporabnik_id': str(users['admin'][0]), 'podjetje_id': str(a), 'vloga': 'mojster'})
    assert r.status_code == 409 and r.json()['detail'] == 'Skrbnik si ne more sam dodeliti vloge v podjetju.'
    assert client.post('/api/admin/vloge', json={'uporabnik_id': str(users['outsider'][0]), 'podjetje_id': str(a), 'vloga': 'delavec'}).status_code == 200


# D9: master cannot be his own customer
def mail(db, users, name): return db.execute('select e_posta from quoteflow.uporabnik where id=%s', (users[name][0],)).fetchone()['e_posta']


def refused(db, users, who, company, name):
    address = mail(db, users, name)
    with as_user(db, users[who]):
        try:
            with db.transaction(): r = db.execute(f'select (quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)).id as id', (company, address, 'N', 'O', 'L')).fetchone()
        except psycopg.Error as e:
            assert e.sqlstate == 'QFP06', e.sqlstate; return True
        return r['id'] is None


def test_mojster_ne_more_biti_svoja_stranka_ali_stranka_delavec_istega_podjetja(env, db):
    users, a, b, _, _ = env
    assert refused(db, users, 'owner_a', a, 'owner_a')
    assert refused(db, users, 'owner_a', a, 'worker')
    assert refused(db, users, 'owner_b', b, 'owner_a')
    assert not refused(db, users, 'owner_a', a, 'customer') and not refused(db, users, 'owner_a', a, 'owner_b')
    assert db.execute('select count(*) as n from quoteflow.projekt where podjetje_id=%s and stranka_id in (%s,%s,%s)', (a, users['owner_a'][0], users['worker'][0], users['owner_a'][0])).fetchone()['n'] == 0


def test_odvzeta_vloga_delavca_spet_dovoli_stranko(env, db):
    users, a, _, _, _ = env
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and podjetje_id=%s and vloga='delavec'", (users['worker'][0], a))
    assert not refused(db, users, 'owner_a', a, 'worker')


def test_api_projekt_zase_je_enak_409_kot_neznana_stranka(env, api_client, db):
    client, selected = api_client; users, a, _, _, _ = env; selected['name'] = 'owner_a'
    unknown = client.post(f'/api/podjetja/{a}/projekti', json=FORM | {'e_posta_stranke': 'ni-take@example.test'})
    for who in ('owner_a', 'worker'):
        r = client.post(f'/api/podjetja/{a}/projekti', json=FORM | {'e_posta_stranke': mail(db, users, who)})
        assert r.status_code == 409 and r.json() == unknown.json()


# API: master quote routes
def mk(client, M, velja=True):
    body = {'velja_do': (date.today() + timedelta(days=10)).isoformat()} if velja else {}
    r = client.post(M + '/ponudbe', json=body); assert r.status_code == 201, (r.status_code, r.text); return r.json()


@pytest.fixture
def master(env, api_client):
    client, selected = api_client; users, a, b, p, cat = env; selected['name'] = 'owner_a'
    return client, selected, f'/api/podjetja/{a}/projekti/{p}', users, cat


def test_api_ustvari_ponudbo_201_oblika_in_druga_je_409(master, db):
    client, _, M, users, _ = master
    r = client.post(M + '/ponudbe', json={}); assert r.status_code == 201, r.text
    q = r.json()
    assert {'id', 'stevilka', 'razlicica', 'stanje', 'poslano_ob', 'odgovorjeno_ob', 'velja_do', 'nadomescena', 'neto', 'ddv', 'skupaj', 'postavke', 'ddv_po_stopnjah'} <= set(q)
    assert q['stevilka'] == f'P-{year(db)}-001' and q['razlicica'] == 1 and q['stanje'] == 'osnutek' and q['postavke'] == [] and q['nadomescena'] is False and D(q['skupaj']) == 0
    r2 = client.post(M + '/ponudbe', json={}); assert r2.status_code == 409 and r2.json()['detail'] == 'Projekt že ima osnutek ponudbe.'
    assert client.post(M + '/ponudbe', json={'velja_do': (date.today() + timedelta(days=30)).isoformat(), 'x': 1}).status_code == 422
    assert client.post(M + '/ponudbe', json={'postavke': [{'naziv': 'x'}]}).status_code in (409, 422)


def test_api_ac2_predogled_osnutka_je_zivi_izracun_postavk_projekta_2x100_10_odstotkov_22_odstotkov(master, db):
    client, _, M, _, _ = master; p = M.rsplit('/', 1)[1]; add_item(db, p); q = mk(client, M)
    got = client.get(f"{M}/ponudbe/{q['id']}").json()
    assert (got['neto'], got['ddv'], got['skupaj']) == ('180.00', '39.60', '219.60') and len(got['postavke']) == 1 and len(got['ddv_po_stopnjah']) == 1 and got['stanje'] == 'osnutek'
    l = got['postavke'][0]; assert l['naziv'] == 'Polaganje' and D(l['kolicina']) == 2 and D(l['popust']) == D('0.1') and isinstance(l['cena_na_enoto'], str) and D(l['izmera_skupaj']) == 1
    assert not db.execute('select 1 from quoteflow.postavka_ponudbe where ponudba_id=%s', (q['id'],)).fetchall(), 'predogled ne posname'
    add_item(db, p, naziv='Dodatno', price=D(10), qty=D(1), discount=D(0), vat=D(0)); assert client.get(f"{M}/ponudbe/{q['id']}").json()['skupaj'] == '229.60', 'predogled sledi spremembam projekta'
    listed = client.get(M + '/ponudbe').json()
    assert [x['id'] for x in listed] == [q['id']] and set(listed[0]) == {'id', 'stevilka', 'razlicica', 'stanje', 'poslano_ob', 'odgovorjeno_ob', 'velja_do', 'nadomescena', 'neto', 'ddv', 'skupaj'}


def test_api_ponudba_ne_sprejme_vec_urejanja_vrstic(master, db):
    client, _, M, _, _ = master; p = M.rsplit('/', 1)[1]; add_item(db, p); q = mk(client, M); path = f"{M}/ponudbe/{q['id']}"
    for method, suffix in (('post', '/postavke'), ('post', '/postavke/iz-cenika'), ('put', f'/postavke/{uuid4()}'), ('delete', f'/postavke/{uuid4()}')):
        assert getattr(client, method)(path + suffix, **({'json': {'naziv': 'x'}} if method != 'delete' else {})).status_code in (404, 405), (method, suffix)


def test_api_veljavnost_se_uredi_in_poslana_ponudba_je_409_ne_503(master, db):
    client, _, M, _, _ = master; p = M.rsplit('/', 1)[1]; add_item(db, p); q = mk(client, M, velja=False); path = f"{M}/ponudbe/{q['id']}"
    assert client.put(path, json={'velja_do': (v := (date.today() + timedelta(days=60)).isoformat())}).json()['velja_do'] == v
    assert client.post(path + '/poslji').status_code == 200
    r = client.put(path, json={'velja_do': None}); assert r.status_code == 409 and r.json()['detail'] == M_ZAKLENJENO
    j = client.get(path).json(); assert j['stanje'] == 'poslana' and len(j['postavke']) == 1


def test_api_poslana_ponudba_ne_sledi_spremembam_projekta(master, db):
    client, _, M, _, _ = master; p = M.rsplit('/', 1)[1]; it = add_item(db, p); q = mk(client, M); path = f"{M}/ponudbe/{q['id']}"
    assert client.post(path + '/poslji').status_code == 200; before = client.get(path).json()
    add_item(db, p, naziv='Po pošiljanju', price=D(500)); assert client.get(path).json() == before and before['skupaj'] == '219.60'


def test_api_poslji_brez_postavk_projekta_je_409(master, db):
    client, _, M, _, _ = master; q = mk(client, M)
    r = client.post(f"{M}/ponudbe/{q['id']}/poslji"); assert r.status_code == 409 and r.json()['detail'] == 'Ponudba mora imeti vsaj eno postavko.'


def test_api_tujec_in_tuj_projekt_dobita_enak_404_kot_nakljucni_uuid(master, db, identities):
    client, selected, M, users, cat = master; _, a, b, _ = identities; p = M.rsplit('/', 1)[1]
    q = mk(client, M); selected['name'] = 'owner_b'
    foreign, rnd = f'/api/podjetja/{b}/projekti/{p}', f'/api/podjetja/{b}/projekti/{uuid4()}'
    for method, suffix, body in [('get', '/ponudbe', None), ('post', '/ponudbe', {}), ('get', f"/ponudbe/{q['id']}", None), ('put', f"/ponudbe/{q['id']}", {'velja_do': None}), ('post', f"/ponudbe/{q['id']}/poslji", None)]:
        args = {'json': body} if body is not None else {}
        f, r = getattr(client, method)(foreign + suffix, **args), getattr(client, method)(rnd + suffix.replace(q['id'], str(uuid4())), **args)
        assert f.status_code == 404 and f.json() == r.json(), (method, suffix, f.status_code)
    assert client.get(f'/api/podjetja/{a}/projekti/{p}/ponudbe').status_code == 403
    assert not db.execute('select * from quoteflow.ponudba where id<>%s', (q['id'],)).fetchall()


def test_api_stranka_delavec_in_skrbnik_nimajo_dostopa(master):
    client, selected, M, users, _ = master; q = mk(client, M)
    for who in ('customer', 'worker', 'admin', 'outsider'):
        selected['name'] = who
        assert client.get(M + '/ponudbe').status_code == 403 and client.post(M + '/ponudbe', json={}).status_code == 403 and client.get(f"{M}/ponudbe/{q['id']}").status_code == 403
        assert client.post(f"{M}/ponudbe/{q['id']}/poslji").status_code == 403
