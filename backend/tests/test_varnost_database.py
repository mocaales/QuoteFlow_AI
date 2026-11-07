"""G6 popravki na disposable local Supabase: M-2 skrbnik, L-1 projekt v pisalnih funkcijah, L-2..L-5 meje, L-9 posnetki, I-1 sočasnost, I-2 404 namesto []."""
import os
import threading
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from psycopg.rows import dict_row
from test_model_database import db, identities, as_user, catalog
from test_identity_database import api_client
from v3_quotes import P, env, call, bad, fails, quiet, new_project, draft, year, raw_quote, send, sent, decide, add_item, as_owner, LJ  # noqa: F401
from test_ponudbe_database import master, mk
from test_ponudbe_odlocitev_database import api as odl_api
from test_izvedba_database import one, accepted, in_izvedba, project, audit, term, bad_term, ts, TODAY
from test_racun_database import ready, issue, REC, invoice
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
QFP22 = 'Skrbnik si ne more sam dodeliti vloge v podjetju.'
M07 = 'V tej fazi projekta to dejanje ni dovoljeno.'


# M-2
def own_role(db, users, a, vloga='mojster'):
    return db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga,aktivna) values(%s,%s,%s,false) returning id", (users['admin'][0], a, vloga)).fetchone()['id']


@pytest.mark.parametrize('vloga', ['mojster', 'delavec'])
def test_m2_skrbnik_si_ne_aktivira_lastne_vloge_v_podjetju(db, identities, vloga):
    users, a, _, _ = identities; role = own_role(db, users, a, vloga)
    with as_user(db, users['admin']): fails(db, f'select * from {Q}aktiviraj_vlogo(%s,true)', (role,), 'QFP22')
    assert db.execute('select aktivna from quoteflow.vloga_uporabnika where id=%s', (role,)).fetchone()['aktivna'] is False


def test_m2_skrbnik_aktivira_tuji_vlogi_se_vedno(db, identities):
    users, a, _, role = identities
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,))
    with as_user(db, users['admin']): assert db.execute(f'select * from {Q}aktiviraj_vlogo(%s,true)', (role,)).fetchone()['aktivna'] is True


def test_m2_ustvari_podjetje_z_lastnikom_skrbnikom_je_qfp22_tuj_lastnik_je_ok(db, identities):
    users, _, _, _ = identities
    with as_user(db, users['admin']):
        fails(db, f'select * from {Q}ustvari_podjetje(%s,%s,%s,%s,%s)', (users['admin'][0], 'Moje', uuid4().hex[:30], None, 'Naslov'), 'QFP22')
        assert db.execute(f'select * from {Q}ustvari_podjetje(%s,%s,%s,%s,%s)', (users['outsider'][0], 'Tuje', uuid4().hex[:30], None, 'Naslov')).fetchone()['lastnik_id'] == users['outsider'][0]
    assert not db.execute('select 1 from quoteflow.podjetje where naziv=%s', ('Moje',)).fetchall()


def test_m2_skrbnik_ne_odobri_lastne_prosnje_qfp22(db, identities):
    users, _, _, _ = identities
    with as_user(db, users['admin']):
        pid = db.execute(f'select * from {Q}oddaj_prosnjo(%s,%s,%s,%s)', ('Moje', uuid4().hex[:30], None, 'Naslov')).fetchone()['id']
        fails(db, f'select * from {Q}odloci_prosnjo(%s,true)', (pid,), 'QFP22')
        assert db.execute(f'select * from {Q}odloci_prosnjo(%s,false)', (pid,)).fetchone()['stanje'] == 'zavrnjena'
    assert not db.execute("select 1 from quoteflow.podjetje where naziv='Moje'").fetchall()


def test_m2_skrbnik_odobri_tujo_prosnjo(db, identities):
    users, _, _, _ = identities
    with as_user(db, users['outsider']): pid = db.execute(f'select * from {Q}oddaj_prosnjo(%s,%s,%s,%s)', ('Tuje', uuid4().hex[:30], None, 'Naslov')).fetchone()['id']
    with as_user(db, users['admin']): assert db.execute(f'select * from {Q}odloci_prosnjo(%s,true)', (pid,)).fetchone()['stanje'] == 'odobrena'


def test_m2_api_aktivacija_lastne_vloge_je_409(api_client, db, identities):
    client, selected = api_client; users, a, _, _ = identities; role = own_role(db, users, a)
    r = client.patch(f'/api/admin/vloge/{role}', json={'aktivna': True}); assert r.status_code == 409 and r.json()['detail'] == QFP22


def test_m2_api_ustvari_podjetje_zase_je_409_za_druge_201(api_client, identities):
    client, selected = api_client; users, _, _, _ = identities
    own = {'lastnik_id': str(users['admin'][0]), 'naziv': 'Moje', 'maticna_stevilka': uuid4().hex[:30], 'naslov': 'Naslov 1'}
    r = client.post('/api/admin/podjetja', json=own); assert r.status_code == 409 and r.json()['detail'] == QFP22
    assert client.post('/api/admin/podjetja', json=own | {'lastnik_id': str(users['outsider'][0]), 'maticna_stevilka': uuid4().hex[:30]}).status_code == 201


def test_m2_api_odobritev_lastne_prosnje_je_409_zavrnitev_ok(api_client, identities):
    client, selected = api_client; users, _, _, _ = identities
    form = {'naziv_podjetja': 'Moje', 'maticna_stevilka': uuid4().hex[:30], 'davcna_stevilka': None, 'naslov_podjetja': 'Cesta 1'}
    r = client.post('/api/prosnje', json=form); assert r.status_code == 201, r.text; pid = r.json()['id']
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}); assert r.status_code == 409 and r.json()['detail'] == QFP22
    assert client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': False}).status_code == 200


# L-1
def snapshot(db, p):
    return (db.execute('select * from quoteflow.ponudba where projekt_id=%s order by razlicica', (p,)).fetchall(),
            db.execute('select * from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id where q.projekt_id=%s order by l.id', (p,)).fetchall(),
            db.execute('select * from quoteflow.postavka_projekta where projekt_id=%s order by id', (p,)).fetchall(),
            db.execute('select count(*) as n from quoteflow_private.dogodek_dokumenta where projekt_id=%s', (p,)).fetchone())


def test_l1_napacen_projekt_istega_podjetja_je_not_found_in_baza_je_nespremenjena(env, db):
    users, a, _, p, cat = env; it = add_item(db, p); q = draft(db, users, a, p); p2 = new_project(db, users, a)
    before = snapshot(db, p), snapshot(db, p2)
    for name, args in [('uredi_ponudbo', (p2, q, None)), ('poslji_ponudbo', (p2, q))]: bad(db, users, 'owner_a', 'P0002', name, a, *args)
    bad(db, users, 'owner_a', 'P0002', 'odstrani_postavko_projekta', podjetje=a, projekt=p2, postavka=it)
    bad(db, users, 'owner_a', 'P0002', 'shrani_izmero', podjetje=a, projekt=p2, postavka=it, izmera=None, odstej=False, kosi=D(1), dolzina=D(1), visina=D(1), sirina=None)
    assert (snapshot(db, p), snapshot(db, p2)) == before


def test_l1_pravilni_projekt_deluje_za_vse_funkcije(env, db):
    users, a, _, p, cat = env; add_item(db, p); q = draft(db, users, a, p)
    call(db, users, 'owner_a', 'uredi_ponudbo', a, p, q, db.execute('select current_date+5 as d').fetchone()['d'])
    assert call(db, users, 'owner_a', 'poslji_ponudbo', a, p, q)['stanje'] == 'poslana'
    assert len(db.execute('select 1 from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchall()) == 1


def test_l1_poslji_z_napacnim_projektom_ostane_osnutek(env, db):
    users, a, _, p, _ = env; add_item(db, p); q = draft(db, users, a, p); p2 = new_project(db, users, a)
    bad(db, users, 'owner_a', 'P0002', 'poslji_ponudbo', a, p2, q); assert db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'osnutek'
    db.execute('update quoteflow.ponudba set velja_do=current_date+10 where id=%s', (q,))
    assert call(db, users, 'owner_a', 'poslji_ponudbo', a, p, q)['stanje'] == 'poslana'


def test_l1_api_napacen_projekt_je_404_na_vseh_pisalnih_poteh(master, db):
    client, selected, M, users, cat = master; p = M.rsplit('/', 1)[1]; add_item(db, p)
    q = mk(client, M)
    p2 = new_project(db, users, db.execute('select podjetje_id from quoteflow.projekt where id=%s', (p,)).fetchone()['podjetje_id']); W = M.rsplit('/', 1)[0] + f'/{p2}/ponudbe/{q["id"]}'
    before = snapshot(db, p)
    for method, path, body in [('put', W, {'velja_do': None}), ('post', W + '/poslji', None), ('get', W, None)]:
        r = getattr(client, method)(path, **({'json': body} if body is not None else {})); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.', (method, path, r.status_code)
    assert snapshot(db, p) == before


# L-2
def test_l2_po_sprejeti_v1_je_urejanje_osnutka_v2_in_postavk_projekta_qfp07(env, db):
    users, a, _, p, cat = env; q1 = sent(db, users, a, p); q2 = call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, None)['id']; it = db.execute('select id from quoteflow.postavka_projekta where projekt_id=%s', (p,)).fetchone()['id']
    decide(db, users, p, q1, True); before = snapshot(db, p)
    for name, args in [('uredi_ponudbo', (a, p, q2, None)), ('poslji_ponudbo', (a, p, q2))]: bad(db, users, 'owner_a', 'QFP07', name, *args)
    bad(db, users, 'owner_a', 'QFP07', 'odstrani_postavko_projekta', podjetje=a, projekt=p, postavka=it)
    bad(db, users, 'owner_a', 'QFP07', 'dodaj_postavko_iz_cenika', podjetje=a, projekt=p, postavka_cenika=cat[0][2], kolicina=D(1), popust=D(0))
    assert snapshot(db, p) == before


# L-3
@pytest.mark.parametrize('expr', [f'{LJ}-1', f'{LJ}+367', f'{LJ}+4000'])
def test_l3_velja_do_izven_okna_je_22023(env, db, expr):
    users, a, _, p, _ = env; d = one(db, f'select {expr} as d')['d']
    bad(db, users, 'owner_a', '22023', 'ustvari_ponudbo', a, p, d); assert not db.execute('select 1 from quoteflow.ponudba where projekt_id=%s', (p,)).fetchall()
    q = draft(db, users, a, p); bad(db, users, 'owner_a', '22023', 'uredi_ponudbo', a, p, q, d)


@pytest.mark.parametrize('expr', [LJ, f'{LJ}+1', f'{LJ}+366'])
def test_l3_velja_do_znotraj_okna_je_ok(env, db, expr):
    users, a, _, p, _ = env; d = one(db, f'select {expr} as d')['d']
    assert call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, d)['velja_do'] == d


def test_l3_poslji_brez_velja_do_je_qfp12(env, db):
    users, a, _, p, _ = env; add_item(db, p); q = draft(db, users, a, p)
    bad(db, users, 'owner_a', 'QFP12', 'poslji_ponudbo', a, p, q); assert db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'osnutek'


def test_l3_zapade_cez_366_dni_je_22023_in_366_je_ok(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p)
    bad(db, users, 'owner_a', '22023', 'izdaj_racun', a, p, *REC, one(db, f'select {LJ}+367 as d')['d'])
    assert invoice(db, r)['stanje_dokumenta'] == 'osnutek'
    assert issue(db, users, a, p, one(db, f'select {LJ}+366 as d')['d'])['stanje_dokumenta'] == 'izdan'


# L-4
def test_l4_50_razlicic_je_dovoljenih_51_je_qfp23(env, db):
    users, a, _, p, _ = env
    quiet(db, 'ponudba', "insert into quoteflow.ponudba(projekt_id,stevilka,razlicica,stanje,poslano_ob,odgovorjeno_ob,velja_do) select %s,'P-X-001',g,'zavrnjena',now(),now(),current_date+10 from generate_series(1,49) g", (p,))
    r = call(db, users, 'owner_a', 'ustvari_ponudbo', a, p, None); assert r['razlicica'] == 50
    add_item(db, p); call(db, users, 'owner_a', 'uredi_ponudbo', a, p, r['id'], one(db, 'select current_date+10 as d')['d']); send(db, users, a, r['id']); decide(db, users, p, r['id'], False)
    bad(db, users, 'owner_a', 'QFP23', 'ustvari_ponudbo', a, p, None)
    assert one(db, 'select count(*) as n from quoteflow.ponudba where projekt_id=%s', (p,))['n'] == 50


def test_l4_enajsta_sprememba_termina_na_dan_je_qfp24(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    for _ in range(10): term(db, users, a, p)
    bad_term(db, users, 'QFP24', a, p); assert one(db, "select count(*) as n from quoteflow_private.dogodek_dokumenta where projekt_id=%s and dejanje='termin'", (p,))['n'] == 10


def test_l4_omejitev_termina_je_po_projektu(env, db):
    users, a, _, p, _ = env; p2 = new_project(db, users, a); accepted(db, p); accepted(db, p2, number='P-2026-002')
    for _ in range(10): term(db, users, a, p)
    assert term(db, users, a, p2)['faza'] == 'izvedba'


# L-5
def test_l5_termin_ob_0030_po_ljubljanskem_casu_danes_je_sprejet_ceprav_je_utc_se_vceraj(env, db):
    users, a, _, p, _ = env; accepted(db, p); db.execute("set local timezone='UTC'")
    od = "((date_trunc('day', now() at time zone 'Europe/Ljubljana') + interval '30 minutes') at time zone 'Europe/Ljubljana')"
    assert term(db, users, a, p, od=od, do=f"{od}+interval '2 hours'")['faza'] == 'izvedba'


# L-9
def test_l9_brisanje_auth_uporabnika_stranke_ne_spremeni_posnetkov_racuna_in_ponudbe(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p); i = issue(db, users, a, p); before = (invoice(db, r), one(db, 'select * from quoteflow.ponudba where id=%s', (q,)), project(db, p))
    try:
        with db.transaction(): db.execute('delete from auth.users where id=%s', (users['customer'][0],))
    except psycopg.Error as e: assert e.sqlstate in ('23503', '55000'), e.sqlstate  # blokirano z RESTRICT
    assert (invoice(db, r), one(db, 'select * from quoteflow.ponudba where id=%s', (q,)), project(db, p)) == before
    assert invoice(db, r)['stevilka'] == i['stevilka'] and invoice(db, r)['prejemnik_naziv'] == 'Ime Priimek'


def test_l9_trenutni_tuji_kljuci_uporabnika_so_restrict_ali_no_action(db):
    rows = db.execute("select conrelid::regclass::text as t, confdeltype as d from pg_constraint where contype='f' and confrelid in ('auth.users'::regclass,'quoteflow.uporabnik'::regclass) and conrelid::regclass::text like 'quoteflow.%%'").fetchall()
    assert rows and all(x['d'] in ('r', 'a', 'n') for x in rows), rows  # nikoli cascade na poslovne zapise


# I-2
def test_i2_master_ponudbe_neznanega_ali_tujega_projekta_so_404(master, db, identities):
    client, selected, M, users, _ = master; _, a, b, _ = identities; p = M.rsplit('/', 1)[1]
    for path in (f'/api/podjetja/{a}/projekti/{uuid4()}/ponudbe', f'/api/podjetja/{b}/projekti/{p}/ponudbe'):
        selected['name'] = 'owner_a' if '/podjetja/' + str(a) in path else 'owner_b'
        r = client.get(path); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.', path
    selected['name'] = 'owner_a'; r = client.get(M + '/ponudbe'); assert r.status_code == 200 and r.json() == []


def test_i2_stranka_ponudbe_neznanega_tujega_projekta_so_404_lastni_prazen_je_seznam(odl_api, db):
    client, selected, users, a, _, p, M = odl_api; selected['name'] = 'customer'
    r = client.get(f'/api/projekti/{uuid4()}/ponudbe'); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    selected['name'] = 'outsider'; f = client.get(f'/api/projekti/{p}/ponudbe'); assert f.status_code == 404 and f.json() == r.json()
    selected['name'] = 'customer'; ok = client.get(f'/api/projekti/{p}/ponudbe'); assert ok.status_code == 200 and ok.json() == []


# I-1: prava sočasnost z dvema potrjenima povezavama; vsak test ima lastno podjetje in jo po sebi počisti
URL = lambda: os.environ['TEST_DATABASE_URL']


class World:
    def __init__(self):
        self.users, self.sessions, self.company, self.projects = {}, {}, None, []
        self.conn = psycopg.connect(URL(), row_factory=dict_row, autocommit=True)

    def setup(self):
        c = self.conn
        with c.transaction():
            for name in ('owner', 'customer'):
                uid, sid = uuid4(), uuid4()
                c.execute('insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at) values(%s,%s,%s::jsonb,now())', (uid, f'{name}-{uid}@example.test', '{"ime":"Ime","priimek":"Priimek"}'))
                c.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid)); self.users[name] = (uid, sid)
            self.company = c.execute("insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(%s,'Socasno',%s,'Naslov 1','SI12345678') returning id", (self.users['owner'][0], uuid4().hex[:30])).fetchone()['id']
            c.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (self.users['owner'][0], self.company))
            self.vrsta = c.execute("insert into quoteflow.vrsta_dela(podjetje_id,naziv,opis,urna_postavka,stevilo_ur,stevilo_delavcev) values(%s,'Gradnja','',0,0,1) returning id", (self.company,)).fetchone()['id']

    def project(self, n=1):
        c = self.conn
        with c.transaction():
            p = c.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','O','Maribor') returning id", (self.company, self.users['customer'][0])).fetchone()['id']
        self.projects.append(p); return p

    def fn(self, who, sql, args):
        with self.conn.transaction():
            with as_user(self.conn, self.users[who]): return self.conn.execute(sql, args).fetchone()

    def items(self, p):
        """One default item (1 m2 x 2 x 100 EUR, popust 10 %, DDV 22 %) built through the v3 functions."""
        it = self.fn('owner', f'select * from {Q}shrani_postavko_projekta(podjetje => %s, projekt => %s, postavka => null, vrsta_dela => %s, naziv => %s, opis => %s, enota => %s, cena => %s, kolicina => %s, popust => %s, stopnja_ddv => %s, urna_postavka => 0, stevilo_ur => 0, stevilo_delavcev => 1)',
                     (self.company, p, self.vrsta, 'Polaganje', 'K', 'm2', D(100), D(2), D('0.1'), D('0.22')))['id']
        self.fn('owner', f'select * from {Q}shrani_izmero(podjetje => %s, projekt => %s, postavka => %s, izmera => null, odstej => false, kosi => 1, dolzina => 1, visina => 1, sirina => null)', (self.company, p, it))

    def draft(self, p): return self.fn('owner', f'select * from {Q}ustvari_ponudbo(podjetje => %s, projekt => %s, velja_do => current_date+10)', (self.company, p))['id']
    def send(self, p, q): self.fn('owner', f'select * from {Q}poslji_ponudbo(%s,%s,%s)', (self.company, p, q))

    def sent_pair(self):
        """(projekt, v1 poslana, v2 osnutek)"""
        p = self.project(); self.items(p); v1 = self.draft(p); self.send(p, v1); return p, v1, self.draft(p)

    def finished_project(self, number=None):
        p = self.project(); self.items(p); q = self.draft(p); self.send(p, q); self.fn('customer', f'select * from {Q}odgovori_ponudbo(%s,%s,true)', (p, q)); c = self.conn
        with c.transaction():
            c.execute('set local session_replication_role=replica')
            c.execute("update quoteflow.projekt set faza='izvedba', termin_od=date_trunc('day',now()), termin_do=date_trunc('day',now())+interval '2 days', izvedba_koncana_ob=now() where id=%s", (p,))
            c.execute('set local session_replication_role=origin')
        return p

    def run(self, jobs):
        """jobs: [(who, sql, args)] started together; returns list of ('ok', row) or ('err', sqlstate)."""
        barrier, out = threading.Barrier(len(jobs)), [None] * len(jobs)
        def work(i, who, sql, args):
            with psycopg.connect(URL(), row_factory=dict_row) as c:
                try:
                    with c.transaction():
                        with as_user(c, self.users[who]):
                            barrier.wait(10); out[i] = ('ok', c.execute(sql, args).fetchone())
                except psycopg.Error as e: out[i] = ('err', e.sqlstate)
        threads = [threading.Thread(target=work, args=(i, *j)) for i, j in enumerate(jobs)]
        [t.start() for t in threads]; [t.join(30) for t in threads]
        return out

    def cleanup(self):
        c = self.conn
        try:
            with c.transaction():
                c.execute('set local session_replication_role=replica')
                ids = [u for u, _ in self.users.values()]  # registration audits the stranka grant; replica mode would leave orphans
                c.execute('delete from quoteflow_private.dogodek_vloge where izvajalec_id = any(%s) or uporabnik_id = any(%s) or podjetje_id = %s', (ids, ids, self.company))
                if self.company:
                    own = 'select l.id from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=%(c)s'
                    for sql in ('delete from quoteflow_private.dogodek_dokumenta where podjetje_id=%(c)s',
                                'delete from quoteflow_private.preverjeno_podjetje where podjetje_id=%(c)s',
                                f'delete from quoteflow.izmera_ponudbe where postavka_ponudbe_id in ({own})', f'delete from quoteflow.delo_ponudbe where postavka_ponudbe_id in ({own})',
                                'delete from quoteflow.material_ponudbe where postavka_ponudbe_id in (select l.id from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=%(c)s)',
                                'delete from quoteflow.postavka_ponudbe where ponudba_id in (select q.id from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=%(c)s)',
                                'delete from quoteflow.racun where ponudba_id in (select q.id from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=%(c)s)',
                                'delete from quoteflow.ponudba where projekt_id in (select id from quoteflow.projekt where podjetje_id=%(c)s)',
                                'delete from quoteflow.izmera where postavka_projekta_id in (select i.id from quoteflow.postavka_projekta i join quoteflow.projekt p on p.id=i.projekt_id where p.podjetje_id=%(c)s)',
                                'delete from quoteflow.postavka_projekta where projekt_id in (select id from quoteflow.projekt where podjetje_id=%(c)s)',
                                'delete from quoteflow.projekt where podjetje_id=%(c)s', 'delete from quoteflow.material_vrste_dela where vrsta_dela_id in (select id from quoteflow.vrsta_dela where podjetje_id=%(c)s)',
                                'delete from quoteflow.vrsta_dela where podjetje_id=%(c)s', 'delete from quoteflow.vloga_uporabnika where podjetje_id=%(c)s', 'delete from quoteflow.podjetje where id=%(c)s'):
                        c.execute(sql, {'c': self.company})
                ids = [u for u, _ in self.users.values()]
                c.execute('delete from quoteflow.vloga_uporabnika where uporabnik_id = any(%s)', (ids,)); c.execute('delete from quoteflow.uporabnik where id = any(%s)', (ids,))
                c.execute('delete from auth.sessions where user_id = any(%s)', (ids,)); c.execute('delete from auth.users where id = any(%s)', (ids,))
        finally: c.close()


@pytest.fixture
def world():
    w = World()
    try: w.setup(); yield w
    finally: w.cleanup()


def test_i1a_poslji_v2_proti_sprejemu_v1_brez_smrtnega_objema(world):
    seen = []
    for _ in range(8):
        p, v1, v2 = world.sent_pair()
        res = world.run([('owner', f'select * from {Q}poslji_ponudbo(%s,%s,%s)', (world.company, p, v2)), ('customer', f'select * from {Q}odgovori_ponudbo(%s,%s,%s)', (p, v1, True))])
        seen += res
    states = [r[1] for r in seen if r[0] == 'err']
    assert None not in seen and '40P01' not in states, states
    assert set(states) <= {'QFP07', 'QFP10', 'QFP11'}, states


def test_i1b_socasni_izdaji_racunov_v_enem_podjetju_dobita_razlicni_zaporedni_stevilki(world):
    p1, p2 = world.finished_project('P-2026-001'), world.finished_project('P-2026-002')
    res = world.run([('owner', f'select * from {Q}izdaj_racun(%s,%s,%s,%s,%s)', (world.company, p, 'Ime Priimek', 'Maribor', one_day())) for p in (p1, p2)])
    assert [r[0] for r in res] == ['ok', 'ok'], res
    y = world.conn.execute('select extract(year from current_date)::int as y').fetchone()['y']
    nums = sorted(r[1]['stevilka'] for r in res); assert nums == [f'R-{y}-001', f'R-{y}-002']
    stored = sorted(x['stevilka'] for x in world.conn.execute('select r.stevilka from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=%s', (world.company,)).fetchall())
    assert stored == nums


def one_day():
    from datetime import date, timedelta
    return date.today() + timedelta(days=8)
