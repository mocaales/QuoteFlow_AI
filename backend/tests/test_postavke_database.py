"""Model v3 (G1 2026-11-07): vrste dela, postavke projekta, izmere, formula A, posnetek ob pošiljanju. Disposable local Supabase only.
Function contract (named arguments, order is free): shrani_vrsto_dela(podjetje,vrsta,naziv,opis,urna_postavka,stevilo_ur,stevilo_delavcev,aktivna) ·
shrani_material_vrste(podjetje,vrsta,material,kolicina) · odstrani_material_vrste(podjetje,vrsta,material) ·
shrani_cenik(podjetje,target,ime,opis_v,vrsta_dela_v,enota_v,cena,ddv,aktivna_v) ·
shrani_postavko_projekta(podjetje,projekt,postavka,vrsta_dela,naziv,opis,enota,cena,kolicina,popust,stopnja_ddv,urna_postavka,stevilo_ur,stevilo_delavcev) ·
dodaj_postavko_iz_cenika(podjetje,projekt,postavka_cenika,kolicina,popust) · odstrani_postavko_projekta(podjetje,projekt,postavka) ·
shrani_izmero(podjetje,projekt,postavka,izmera,odstej,kosi,dolzina,visina,sirina) · odstrani_izmero(podjetje,projekt,postavka,izmera)."""
import os
from datetime import timedelta
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
NEW_TABLES = ['vrsta_dela', 'material_vrste_dela', 'postavka_projekta', 'izmera', 'izmera_ponudbe', 'delo_ponudbe']
LIVE = ['vrsta_dela', 'material_vrste_dela', 'postavka_projekta', 'izmera']
FUNCTIONS = ['shrani_vrsto_dela', 'shrani_material_vrste', 'odstrani_material_vrste', 'shrani_postavko_projekta', 'dodaj_postavko_iz_cenika', 'odstrani_postavko_projekta', 'shrani_izmero', 'odstrani_izmero']
VRSTA = dict(vrsta=None, naziv='Polaganje ploščic', opis='Keramika', urna_postavka=D(25), stevilo_ur=D(8), stevilo_delavcev=2, aktivna=True)


def stmt(name, kw): return f"select * from {Q}{name}({','.join(f'{k} => %s' for k in kw)})", tuple(kw.values())


def fails(db, sql, args, state, text=None):
    states = {state} if isinstance(state, str) else set(state)
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): db.execute(sql, args)
    assert e.value.sqlstate in states, f'{e.value.sqlstate}: {e.value}'
    return e.value


INTEGRITY = {'23514', '23503', '23505', '55000', 'P0002', 'QFP27'}


def reject(db, sql, args=(), states=INTEGRITY):
    # Only constraint-style SQLSTATEs count: an undefined table or column must not look like a rejection.
    with pytest.raises(psycopg.Error) as err:
        with db.transaction(): db.execute(sql, args); db.execute('set constraints all immediate')
    assert err.value.sqlstate in states, f'{err.value.sqlstate}: {err.value}'


def call(db, users, who, name, **kw):
    s, a = stmt(name, kw)
    with as_user(db, users[who]): return db.execute(s, a).fetchone()


def bad(db, users, who, state, name, **kw):
    s, a = stmt(name, kw)
    with as_user(db, users[who]): return fails(db, s, a, state)


def quiet(db, table, sql, args=()):
    db.execute('set constraints all immediate'); db.execute(f'alter table quoteflow.{table} disable trigger user'); db.execute(sql, args)
    db.execute(f'alter table quoteflow.{table} enable trigger user'); db.execute('set constraints all deferred')


class E:
    def __init__(s, **k): s.__dict__.update(k)


def project(db, users, company, customer='customer'):
    return db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (company, users[customer][0])).fetchone()['id']


@pytest.fixture
def e(db, identities):
    users, a, b, _ = identities; mats = {}
    for c, tag in ((a, 'a'), (b, 'b')):
        kind = db.execute("insert into quoteflow.vrsta_materiala(podjetje_id,naziv) values(%s,'Lepila') returning id", (c,)).fetchone()['id']
        mats[tag] = db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'LEP-1','Lepilo','kg',0.8) returning id", (kind,)).fetchone()['id']
    va = call(db, users, 'owner_a', 'shrani_vrsto_dela', podjetje=a, **VRSTA)['id']
    vb = call(db, users, 'owner_b', 'shrani_vrsto_dela', podjetje=b, **VRSTA)['id']
    call(db, users, 'owner_a', 'shrani_material_vrste', podjetje=a, vrsta=va, material=mats['a'], kolicina=D(5))
    cat = lambda who, c, v: call(db, users, who, 'shrani_cenik', podjetje=c, target=None, ime='Polaganje', opis_v='Opis', vrsta_dela_v=v, enota_v='m2', cena=D(25), ddv=D('0.22'), aktivna_v=True)['id']
    today = db.execute('select quoteflow_private.danes() as d').fetchone()['d']
    return E(db=db, users=users, a=a, b=b, ma=mats['a'], mb=mats['b'], va=va, vb=vb, ca=cat('owner_a', a, va), cb=cat('owner_b', b, vb),
             pa=project(db, users, a), pb=project(db, users, b, 'outsider'), today=today)


def put(e, who='owner_a', **o):
    kw = dict(podjetje=e.a, projekt=e.pa, postavka=None, vrsta_dela=e.va, naziv='Polaganje', opis='Keramika', enota='m2', cena=D(10), kolicina=D(1), popust=D('0.1'), stopnja_ddv=D('0.22'),
              urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None) | o
    return call(e.db, e.users, who, 'shrani_postavko_projekta', **kw)


def meas(e, item, who='owner_a', **o):
    kw = dict(podjetje=e.a, projekt=e.pa, postavka=item, izmera=None, odstej=False, kosi=D(1), dolzina=None, visina=None, sirina=None) | o
    return call(e.db, e.users, who, 'shrani_izmero', **kw)


def bad_meas(e, state, item, who='owner_a', **o):
    kw = dict(podjetje=e.a, projekt=e.pa, postavka=item, izmera=None, odstej=False, kosi=D(1), dolzina=None, visina=None, sirina=None) | o
    return bad(e.db, e.users, who, state, 'shrani_izmero', **kw)


def row(db, table, id_, key='id'): return db.execute(f'select * from quoteflow.{table} where {key}=%s', (id_,)).fetchone()
def total(db, item): return db.execute('select izmera_skupaj as s from quoteflow.postavka_projekta where id=%s', (item,)).fetchone()['s']
def summed(db, item): return db.execute('select coalesce(sum(case when odstej then -vrednost else vrednost end),0) as s from quoteflow.izmera where postavka_projekta_id=%s', (item,)).fetchone()['s']
def count(db, table, where='true', args=()): return db.execute(f'select count(*) as n from quoteflow.{table} where {where}', args).fetchone()['n']


def worked(e, **o):
    """Odločitev 1: 5x4 + 2x1 - 1x2 = 20 m2, 20 x 1 x 10 EUR + 25 EUR x 8 h x 2 delavca, popust 10 %, DDV 22 % -> 540,00 / 118,80 / 658,80."""
    it = put(e, **o)['id']
    meas(e, it, dolzina=D(5), visina=D(4)); meas(e, it, dolzina=D(2), visina=D(1)); meas(e, it, odstej=True, dolzina=D(1), visina=D(2))
    return it


def clear(e):
    for r in e.db.execute('select id from quoteflow.postavka_projekta where projekt_id=%s', (e.pa,)).fetchall(): call(e.db, e.users, 'owner_a', 'odstrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=r['id'])


def draft(e, who='owner_a', company=None, proj=None):
    return call(e.db, e.users, who, 'ustvari_ponudbo', podjetje=company or e.a, projekt=proj or e.pa, velja_do=e.today + timedelta(days=10))['id']


def send(e, q, who='owner_a'): return call(e.db, e.users, who, 'poslji_ponudbo', podjetje=e.a, projekt=e.pa, ponudba=q)


def lines(db, q): return db.execute('select * from quoteflow.postavka_ponudbe where ponudba_id=%s order by zaporedje', (q,)).fetchall()


def frozen(db, q):
    ids = "(select id from quoteflow.postavka_ponudbe where ponudba_id=%s)"
    return (lines(db, q), db.execute(f'select * from quoteflow.izmera_ponudbe where postavka_ponudbe_id in {ids} order by postavka_ponudbe_id,zaporedje', (q,)).fetchall(),
            db.execute(f'select * from quoteflow.material_ponudbe where postavka_ponudbe_id in {ids} order by postavka_ponudbe_id,material_id', (q,)).fetchall(),
            db.execute(f'select * from quoteflow.delo_ponudbe where postavka_ponudbe_id in {ids} order by postavka_ponudbe_id', (q,)).fetchall())


def unreadable(db, users, who, table):
    """True when RLS hides every row or the table is not granted at all."""
    with as_user(db, users[who]):
        try:
            with db.transaction(): return db.execute(f'select count(*) as n from quoteflow.{table}').fetchone()['n'] == 0
        except psycopg.errors.InsufficientPrivilege: return True


# --- contract: tables, columns, grants (X2, X3, X5, M2, M6)
def test_nove_tabele_obstajajo_s_prisiljenim_rls_brez_sestave_cenika(db):
    names = {r['tablename'] for r in db.execute("select tablename from pg_tables where schemaname='quoteflow'")}
    assert set(NEW_TABLES) <= names and 'sestava_cenika' not in names
    for t in NEW_TABLES:
        assert db.execute("select relrowsecurity and relforcerowsecurity as ok from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow' and relname=%s", (t,)).fetchone()['ok'], t


def test_stare_funkcije_in_stolpec_vrsta_dela_besedilo_so_odstranjeni(db):
    gone = {'shrani_sestavo', 'odstrani_sestavo', 'dodaj_postavko_cenika', 'shrani_postavko', 'odstrani_postavko'}
    assert not {r['proname'] for r in db.execute("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private'")} & gone
    cols = {r['column_name']: r for r in db.execute("select column_name,data_type,is_nullable from information_schema.columns where table_schema='quoteflow' and table_name='postavka_cenika'")}
    assert 'vrsta_dela' not in cols and cols['vrsta_dela_id']['data_type'] == 'uuid' and cols['vrsta_dela_id']['is_nullable'] == 'NO'


def test_posnetek_ponudbe_nima_stolpcev_dela_in_vsote_so_navadni_stolpci(db):
    cols = {r['column_name']: r['is_generated'] for r in db.execute("select column_name,is_generated from information_schema.columns where table_schema='quoteflow' and table_name='postavka_ponudbe'")}
    assert not {'urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'cena_dela'} & set(cols), 'M2: delo je samo v delo_ponudbe'
    assert {'izmera_skupaj', 'neto', 'koncna_cena'} <= set(cols) and all(cols[c] == 'NEVER' for c in ('izmera_skupaj', 'neto', 'koncna_cena')), 'M6: vsote se zapišejo enkrat ob pošiljanju'
    live = {r['column_name']: r['is_generated'] for r in db.execute("select column_name,is_generated from information_schema.columns where table_schema='quoteflow' and table_name='postavka_projekta'")}
    assert {'izmera_skupaj', 'cena_dela', 'neto', 'koncna_cena', 'urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'vrsta_dela_id', 'enota'} <= set(live)
    assert all(live[c] == 'ALWAYS' for c in ('cena_dela', 'neto', 'koncna_cena'))


def test_pravice_novih_tabel_anon_nic_authenticated_samo_select(db):
    for t in NEW_TABLES:
        for role in ('anon', 'service_role', 'quoteflow_app'):
            assert not [p for p in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE') if db.execute('select has_table_privilege(%s,%s,%s) as y', (role, 'quoteflow.' + t, p)).fetchone()['y']], (t, role)
        assert db.execute('select has_table_privilege(%s,%s,%s) as y', ('authenticated', 'quoteflow.' + t, 'SELECT')).fetchone()['y'], t
        for p in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'): assert not db.execute('select has_table_privilege(%s,%s,%s) as y', ('authenticated', 'quoteflow.' + t, p)).fetchone()['y'], (t, p)


def test_nove_funkcije_anon_ne_sme_authenticated_sme(db):
    for name in FUNCTIONS:
        procs = db.execute("select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private' and proname=%s", (name,)).fetchall()
        assert len(procs) == 1, name
        assert db.execute("select has_function_privilege('authenticated',%s,'execute') as y", (procs[0]['oid'],)).fetchone()['y'], name
        for role in ('anon', 'service_role', 'quoteflow_app'): assert not db.execute("select has_function_privilege(%s,%s,'execute') as y", (role, procs[0]['oid'])).fetchone()['y'], (name, role)


def test_sprozilci_celovitosti_pokrivajo_nove_tabele_in_ne_omenjajo_sestave(db):
    for t in LIVE + ['izmera_ponudbe', 'delo_ponudbe']:
        names = {r['tgname'] for r in db.execute("select tgname from pg_trigger where tgrelid=('quoteflow.'||%s)::regclass and not tgisinternal", (t,))}
        assert 'a_zakleni_podjetje' in names and 'celovitost' in names, (t, names)
    for fn in ('preveri_celovitost', 'zakleni_podjetje', 'zakleni_postavko'):
        assert 'sestava_cenika' not in db.execute("select pg_get_functiondef(p.oid) as d from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private' and proname=%s", (fn,)).fetchone()['d'], fn
    for t in ('postavka_projekta', 'izmera'):
        assert db.execute("select count(*) as n from pg_trigger where tgrelid=('quoteflow.'||%s)::regclass and tgname='zakleni_reference'", (t,)).fetchone()['n'] == 1, t


def test_app_vloga_ima_statement_timeout(db):
    assert any(c.startswith('statement_timeout=') for c in db.execute("select rolconfig from pg_roles where rolname='quoteflow_app'").fetchone()['rolconfig'])


# --- vrste dela
def test_vrsta_dela_cena_dela_je_izpeljana_in_material_ni_obvezen(e):
    r = row(e.db, 'vrsta_dela', e.va)
    assert (r['naziv'], r['urna_postavka'], r['stevilo_ur'], r['stevilo_delavcev'], r['cena_dela'], r['aktivna'], r['podjetje_id']) == ('Polaganje ploščic', D(25), D(8), 2, D(400), True, e.a)
    assert count(e.db, 'material_vrste_dela', 'vrsta_dela_id=%s', (e.va,)) == 1 and count(e.db, 'material_vrste_dela', 'vrsta_dela_id=%s', (e.vb,)) == 0
    upd = call(e.db, e.users, 'owner_a', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(vrsta=e.va, urna_postavka=D('33.33'), stevilo_ur=D('1.5'), stevilo_delavcev=3)))
    assert upd['id'] == e.va and upd['cena_dela'] == D('149.99')


def test_vrsta_dela_nic_eden_ali_vec_materialov_z_odstranitvijo(e):
    call(e.db, e.users, 'owner_a', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=e.ma, kolicina=D('2.5'))
    assert row(e.db, 'material_vrste_dela', e.va, 'vrsta_dela_id')['kolicina_na_enoto'] == D('2.5')
    kind = e.db.execute("select vrsta_materiala_id as k from quoteflow.material where id=%s", (e.ma,)).fetchone()['k']
    m2 = e.db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'LEP-2','Fuga','kg',1) returning id", (kind,)).fetchone()['id']
    call(e.db, e.users, 'owner_a', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=m2, kolicina=D(1)); assert count(e.db, 'material_vrste_dela', 'vrsta_dela_id=%s', (e.va,)) == 2
    for ok in (D(0), D(-1)): bad(e.db, e.users, 'owner_a', '23514', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=m2, kolicina=ok)
    call(e.db, e.users, 'owner_a', 'odstrani_material_vrste', podjetje=e.a, vrsta=e.va, material=e.ma); call(e.db, e.users, 'owner_a', 'odstrani_material_vrste', podjetje=e.a, vrsta=e.va, material=m2)
    assert count(e.db, 'material_vrste_dela', 'vrsta_dela_id=%s', (e.va,)) == 0
    bad(e.db, e.users, 'owner_a', 'P0002', 'odstrani_material_vrste', podjetje=e.a, vrsta=e.va, material=m2)


def test_neaktiven_material_v_vrsti_dela_je_qfp05(e):
    e.db.execute('update quoteflow.material set aktiven=false where id=%s', (e.ma,))
    bad(e.db, e.users, 'owner_a', 'QFP05', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=e.ma, kolicina=D(1))


@pytest.mark.parametrize('field,value', [('urna_postavka', D('10000.01')), ('urna_postavka', D(-1)), ('stevilo_ur', D('100000.01')), ('stevilo_ur', D(-1)), ('stevilo_delavcev', 0), ('stevilo_delavcev', 1001),
                                          ('urna_postavka', D('NaN')), ('stevilo_ur', D('NaN')), ('naziv', ''), ('naziv', '  '), ('naziv', 'x' * 201)])
def test_vrsta_dela_meje_m7(e, field, value):
    bad(e.db, e.users, 'owner_a', {'22003', '23514', '22023'}, 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | {field: value}))
    assert count(e.db, 'vrsta_dela', 'podjetje_id=%s', (e.a,)) == 1


def test_vrsta_dela_najvecja_dovoljena_vrednost_deluje(e):
    r = call(e.db, e.users, 'owner_a', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(naziv='Meja', urna_postavka=D(10000), stevilo_ur=D(100000), stevilo_delavcev=1000, opis='')))
    assert r['id'] and r['cena_dela'] == D(10000) * D(100000) * D(1000)


def test_vrsta_dela_vloge_in_tujina(e):
    users, db = e.users, e.db
    for who in ('worker', 'customer', 'outsider', 'admin'): bad(db, users, who, '42501', 'shrani_vrsto_dela', podjetje=e.a, **VRSTA)
    bad(db, users, 'owner_b', '42501', 'shrani_vrsto_dela', podjetje=e.a, **VRSTA)
    bad(db, users, 'owner_b', 'P0002', 'shrani_vrsto_dela', podjetje=e.b, **(VRSTA | dict(vrsta=e.va)))
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (users['worker'][0], e.a))
    assert call(db, users, 'worker', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(naziv='Druga')))['id']
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='mojster'", (users['worker'][0],))
    bad(db, users, 'worker', '42501', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(naziv='Tretja')))


@pytest.mark.parametrize('who', ['owner_b', 'worker', 'customer', 'outsider', 'admin'])
def test_vrste_dela_materiali_postavke_in_izmere_so_samo_za_mojstra_podjetja(e, who):
    it = worked(e); q = draft(e); send(e, q)
    for t in LIVE + ['izmera_ponudbe', 'delo_ponudbe', 'material_vrste_dela']:
        if who == 'owner_b' and t == 'vrsta_dela':  # his own vrsta (fixture vb) is legitimately readable, A's must not be
            with as_user(e.db, e.users[who]): assert [r['id'] for r in e.db.execute('select id from quoteflow.vrsta_dela').fetchall()] == [e.vb]
            continue
        assert unreadable(e.db, e.users, who, t) or who == 'customer' and t == 'izmera_ponudbe', (who, t)


def test_stranka_vidi_izmere_poslane_ponudbe_ne_pa_dela_in_materialov(e):
    it = worked(e); q = draft(e); send(e, q)
    with as_user(e.db, e.users['customer']):
        assert count(e.db, 'izmera_ponudbe') == 3 and count(e.db, 'postavka_ponudbe') == 1
    with as_user(e.db, e.users['outsider']): assert count(e.db, 'izmera_ponudbe') == 0
    with as_user(e.db, e.users['owner_a']): assert (count(e.db, 'izmera_ponudbe'), count(e.db, 'delo_ponudbe'), count(e.db, 'material_ponudbe')) == (3, 1, 1)
    for t in ('delo_ponudbe', 'material_ponudbe', 'postavka_projekta', 'izmera', 'vrsta_dela', 'material_vrste_dela'): assert unreadable(e.db, e.users, 'customer', t), t
    assert unreadable(e.db, e.users, 'owner_b', 'izmera_ponudbe') and unreadable(e.db, e.users, 'worker', 'izmera_ponudbe')


def test_authenticated_ne_more_neposredno_pisati_vsote(e):
    it = worked(e)
    for sql in ('update quoteflow.postavka_projekta set izmera_skupaj=99', 'update quoteflow.izmera set kosi=5', "insert into quoteflow.izmera(postavka_projekta_id,enota,zaporedje,kosi) select id,enota,9,1 from quoteflow.postavka_projekta",
                'delete from quoteflow.postavka_projekta', 'update quoteflow.vrsta_dela set urna_postavka=0'):
        with as_user(e.db, e.users['owner_a']): fails(e.db, sql, (), '42501')
    assert total(e.db, it) == 20


# --- cenik s tipizirano vrsto dela in enoto
@pytest.mark.parametrize('unit', ['m', 'm2', 'm3', 'kos'])
def test_cenik_sprejme_stiri_enote_in_vrsto_dela_podjetja(e, unit):
    r = call(e.db, e.users, 'owner_a', 'shrani_cenik', podjetje=e.a, target=None, ime='X', opis_v='', vrsta_dela_v=e.va, enota_v=unit, cena=D(5), ddv=D('0.22'), aktivna_v=True)
    assert r['enota'] == unit and r['vrsta_dela_id'] == e.va


@pytest.mark.parametrize('unit', ['m²', 'cm', 'ura', 'M2', '', 'kg'])
def test_cenik_zavrne_neznano_enoto(e, unit):
    bad(e.db, e.users, 'owner_a', {'23514', '22023'}, 'shrani_cenik', podjetje=e.a, target=None, ime='X', opis_v='', vrsta_dela_v=e.va, enota_v=unit, cena=D(5), ddv=D('0.22'), aktivna_v=True)


def test_neaktivna_vrsta_dela_je_qfp29_v_ceniku_postavki_in_iz_cenika(e):
    call(e.db, e.users, 'owner_a', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(vrsta=e.va, aktivna=False)))
    bad(e.db, e.users, 'owner_a', 'QFP29', 'shrani_cenik', podjetje=e.a, target=None, ime='X', opis_v='', vrsta_dela_v=e.va, enota_v='m', cena=D(5), ddv=D('0.22'), aktivna_v=True)
    bad(e.db, e.users, 'owner_a', 'QFP29', 'shrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=None, vrsta_dela=e.va, naziv='X', opis='', enota='m', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)
    bad(e.db, e.users, 'owner_a', 'QFP29', 'dodaj_postavko_iz_cenika', podjetje=e.a, projekt=e.pa, postavka_cenika=e.ca, kolicina=D(1), popust=D(0))
    assert count(e.db, 'postavka_projekta') == 0


def test_neaktivna_postavka_cenika_je_qfp16(e):
    e.db.execute('update quoteflow.postavka_cenika set aktivna=false where id=%s', (e.ca,))
    bad(e.db, e.users, 'owner_a', 'QFP16', 'dodaj_postavko_iz_cenika', podjetje=e.a, projekt=e.pa, postavka_cenika=e.ca, kolicina=D(1), popust=D(0))


# --- postavke projekta
def test_postavka_kopira_delo_iz_vrste_dela_in_ga_je_mogoce_urediti(e):
    r = put(e); assert (r['urna_postavka'], r['stevilo_ur'], r['stevilo_delavcev'], r['vrsta_dela_id'], r['zaporedje'], r['izmera_skupaj']) == (D(25), D(8), 2, e.va, 1, 0)
    own = put(e, urna_postavka=D(40), stevilo_ur=D(3), stevilo_delavcev=4); assert (own['urna_postavka'], own['stevilo_ur'], own['stevilo_delavcev'], own['zaporedje']) == (D(40), D(3), 4, 2)
    call(e.db, e.users, 'owner_a', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(vrsta=e.va, urna_postavka=D(99))))
    assert row(e.db, 'postavka_projekta', r['id'])['urna_postavka'] == D(25), 'kopija, ne referenca'
    up = put(e, postavka=r['id'], naziv='Preimenovana', stevilo_ur=D(1)); assert up['id'] == r['id'] and up['naziv'] == 'Preimenovana' and up['stevilo_ur'] == D(1)


def test_dodaj_postavko_iz_cenika_je_kopija_s_podatki_dela(e):
    r = call(e.db, e.users, 'owner_a', 'dodaj_postavko_iz_cenika', podjetje=e.a, projekt=e.pa, postavka_cenika=e.ca, kolicina=D(2), popust=D('0.05'))
    assert (r['postavka_cenika_id'], r['naziv'], r['opis'], r['enota'], r['cena_na_enoto'], r['stopnja_ddv'], r['kolicina'], r['popust'], r['vrsta_dela_id'], r['urna_postavka'], r['stevilo_ur'], r['stevilo_delavcev']) == \
        (e.ca, 'Polaganje', 'Opis', 'm2', D(25), D('0.22'), D(2), D('0.05'), e.va, D(25), D(8), 2)
    e.db.execute('update quoteflow.postavka_cenika set cena_na_enoto=999 where id=%s', (e.ca,)); assert row(e.db, 'postavka_projekta', r['id'])['cena_na_enoto'] == D(25)


def test_formula_a_primer_540_11880_65880(e):
    it = worked(e); r = row(e.db, 'postavka_projekta', it)
    assert (r['izmera_skupaj'], r['cena_dela'], r['neto'], r['koncna_cena'] - r['neto'], r['koncna_cena']) == (D(20), D(400), D('540.00'), D('118.80'), D('658.80'))


@pytest.mark.parametrize('over,neto,ddv', [
    (dict(cena=D('0.5'), enota='kos', popust=D(0), stopnja_ddv=D('0.01'), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1), D('0.50'), D('0.01')),
    (dict(cena=D('10.005'), enota='kos', popust=D(0), stopnja_ddv=D(0), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1), D('10.01'), D(0)),
    (dict(cena=D(0), enota='kos', popust=D(0), urna_postavka=D(25), stevilo_ur=D(8), stevilo_delavcev=2), D('400.00'), D('88.00')),
    (dict(cena=D(0), enota='kos', popust=D(0), stopnja_ddv=D(0), urna_postavka=D('33.33'), stevilo_ur=D('1.5'), stevilo_delavcev=3), D('149.99'), D(0)),
    (dict(cena=D(7), enota='kos', kolicina=D(3), popust=D('0.5'), stopnja_ddv=D(0), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1), D('10.50'), D(0)),
])
def test_zaokrozevanje_in_delo_samo_pavsal_m9(e, over, neto, ddv):
    it = put(e, **over)['id']; meas(e, it, kosi=D(1))
    r = row(e.db, 'postavka_projekta', it); assert (r['neto'], r['koncna_cena'] - r['neto']) == (neto, ddv)


def test_delo_se_ne_mnozi_s_kolicino_ali_izmerami(e):
    it = put(e, enota='kos', cena=D(0), kolicina=D(1), popust=D(0), stopnja_ddv=D(0))['id']
    meas(e, it, kosi=D(1)); a = row(e.db, 'postavka_projekta', it)['neto']; meas(e, it, kosi=D(9)); b = row(e.db, 'postavka_projekta', it)['neto']
    call(e.db, e.users, 'owner_a', 'shrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=it, vrsta_dela=e.va, naziv='x', opis='', enota='kos', cena=D(0), kolicina=D(50), popust=D(0), stopnja_ddv=D(0), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)
    assert a == b == row(e.db, 'postavka_projekta', it)['neto'] == D(400)


@pytest.mark.parametrize('unit,fields,value', [
    ('m', dict(kosi=D(3), dolzina=D('2.5')), D('7.5')),
    ('m2', dict(kosi=D(4), dolzina=D(3), visina=D('2.5')), D(30)),
    ('m3', dict(kosi=D(2), dolzina=D(2), visina=D(3), sirina=D('0.5')), D(6)),
    ('kos', dict(kosi=D(7)), D(7)),
    ('m2', dict(dolzina=D(5), visina=D(4)), D(20)),
])
def test_vrednost_izmere_po_enoti_s_kosi_kot_mnozitelj(e, unit, fields, value):
    it = put(e, enota=unit)['id']; r = meas(e, it, **fields)
    assert r['vrednost'] == value and r['enota'] == unit and total(e.db, it) == value


@pytest.mark.parametrize('unit,fields', [
    ('m', dict(dolzina=D(1), visina=D(1))), ('m', dict(dolzina=D(1), sirina=D(1))), ('m', dict()), ('m', dict(visina=D(1))),
    ('m2', dict(dolzina=D(1), visina=D(1), sirina=D(1))), ('m2', dict(dolzina=D(1))), ('m2', dict(visina=D(1))), ('m2', dict()),
    ('m3', dict(dolzina=D(1), visina=D(1))), ('m3', dict(dolzina=D(1), sirina=D(1))), ('m3', dict(sirina=D(1), visina=D(1))), ('m3', dict()),
    ('kos', dict(dolzina=D(1))), ('kos', dict(visina=D(1))), ('kos', dict(sirina=D(1))),
    ('m', dict(dolzina=D(0))), ('m', dict(dolzina=D(-1))), ('m2', dict(dolzina=D(1), visina=D(0))), ('m3', dict(dolzina=D(1), visina=D(1), sirina=D(-2))),
    ('kos', dict(kosi=D(0))), ('kos', dict(kosi=D(-3))), ('m', dict(dolzina=D(1), kosi=D(0))), ('m', dict(dolzina=D('NaN'))), ('kos', dict(kosi=D('NaN'))),
])
def test_polja_izmere_morajo_ustrezati_enoti_23514(e, unit, fields):
    it = put(e, enota=unit)['id']; bad_meas(e, {'23514', '22003'}, it, **fields)
    assert count(e.db, 'izmera') == 0 and total(e.db, it) == 0


def test_enota_izmere_je_enota_postavke_in_enote_ni_mogoce_menjati_z_izmerami(e):
    it = put(e, enota='m2')['id']
    reject(e.db, "insert into quoteflow.izmera(postavka_projekta_id,enota,zaporedje,kosi,dolzina) values(%s,'m',1,1,1)", (it,))
    assert count(e.db, 'izmera') == 0
    put(e, postavka=it, enota='m3'); assert row(e.db, 'postavka_projekta', it)['enota'] == 'm3'
    meas(e, it, dolzina=D(1), visina=D(1), sirina=D(1))
    bad(e.db, e.users, 'owner_a', 'QFP27', 'shrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=it, vrsta_dela=e.va, naziv='x', opis='', enota='m2', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)
    assert row(e.db, 'postavka_projekta', it)['enota'] == 'm3'
    reject(e.db, "update quoteflow.postavka_projekta set enota='m' where id=%s", (it,))
    reject(e.db, "update quoteflow.izmera set enota='m' where postavka_projekta_id=%s", (it,))
    bad(e.db, e.users, 'owner_a', {'23514', '22023'}, 'shrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=None, vrsta_dela=e.va, naziv='x', opis='', enota='cm', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)


def test_negativna_vsota_izmer_je_qfp25_ob_vstavljanju_spremembi_predznaka_in_brisanju(e):
    it = put(e, enota='kos')['id']; plus = meas(e, it, kosi=D(10))['id']
    bad_meas(e, 'QFP25', it, odstej=True, kosi=D(12)); assert (count(e.db, 'izmera'), total(e.db, it)) == (1, 10)
    minus = meas(e, it, odstej=True, kosi=D(10))['id']; assert total(e.db, it) == 0 == summed(e.db, it)
    bad_meas(e, 'QFP25', it, izmera=plus, odstej=True, kosi=D(10)); bad_meas(e, 'QFP25', it, izmera=plus, kosi=D(5))
    bad(e.db, e.users, 'owner_a', 'QFP25', 'odstrani_izmero', podjetje=e.a, projekt=e.pa, postavka=it, izmera=plus)
    assert (count(e.db, 'izmera'), total(e.db, it), row(e.db, 'izmera', plus)['kosi'], row(e.db, 'izmera', plus)['odstej']) == (2, 0, D(10), False)
    meas(e, it, kosi=D(5)); call(e.db, e.users, 'owner_a', 'odstrani_izmero', podjetje=e.a, projekt=e.pa, postavka=it, izmera=minus); assert total(e.db, it) == 15 == summed(e.db, it)
    assert total(e.db, it) == summed(e.db, it) == 15


def test_izmera_skupaj_je_vedno_polni_preracun_in_nikoli_negativna(e):
    it = put(e, enota='kos')['id']; a = meas(e, it, kosi=D(10))['id']; b = meas(e, it, odstej=True, kosi=D(3))['id']; assert total(e.db, it) == summed(e.db, it) == 7
    meas(e, it, izmera=b, odstej=True, kosi=D(7)); assert total(e.db, it) == 3 == summed(e.db, it)
    reject(e.db, 'update quoteflow.postavka_projekta set izmera_skupaj=-1 where id=%s', (it,))
    call(e.db, e.users, 'owner_a', 'odstrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=it); assert count(e.db, 'izmera') == 0


def test_brisanje_postavke_odstrani_njene_izmere(e):
    it = worked(e); other = put(e)['id']; meas(e, other, dolzina=D(1), visina=D(1))
    call(e.db, e.users, 'owner_a', 'odstrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=it)
    assert (count(e.db, 'postavka_projekta', 'id=%s', (it,)), count(e.db, 'izmera', 'postavka_projekta_id=%s', (it,)), count(e.db, 'izmera')) == (0, 0, 1)


def test_meje_postavke_in_izmere_m7(e):
    for field, value in [('cena', D('1000000.0001')), ('kolicina', D('1000000.0001')), ('popust', D(1)), ('popust', D('-0.1')), ('stopnja_ddv', D('1.01')), ('urna_postavka', D('10000.01')),
                         ('stevilo_ur', D('100000.01')), ('stevilo_delavcev', 0), ('stevilo_delavcev', 1001), ('kolicina', D(0)), ('cena', D(-1)), ('cena', D('NaN')), ('kolicina', D('NaN')), ('naziv', ' ')]:
        kw = dict(podjetje=e.a, projekt=e.pa, postavka=None, vrsta_dela=e.va, naziv='X', opis='', enota='kos', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None) | {field: value}
        bad(e.db, e.users, 'owner_a', {'22003', '23514', '22023'}, 'shrani_postavko_projekta', **kw)
    assert count(e.db, 'postavka_projekta') == 0
    it = put(e, enota='m2')['id']
    for f in (dict(dolzina=D('100000.0001'), visina=D(1)), dict(dolzina=D(1), visina=D('100000.01')), dict(dolzina=D(100000), visina=D(100000)), dict(dolzina=D(1), visina=D(1), kosi=D('1000000.01'))):
        bad_meas(e, {'22003', '23514'}, it, **f)
    assert count(e.db, 'izmera') == 0
    big = meas(e, it, dolzina=D(1000), visina=D(1000)); assert big['vrednost'] == 1000000


def test_neto_nad_milijardo_je_zavrnjen_in_stanje_ostane(e):
    it = put(e, enota='m', cena=D(1000000), kolicina=D(1000000), popust=D(0))['id']; before = row(e.db, 'postavka_projekta', it)
    bad_meas(e, {'22003', '23514'}, it, dolzina=D(100000), kosi=D(10)); assert row(e.db, 'postavka_projekta', it) == before and count(e.db, 'izmera') == 0


def test_najvec_200_postavk_na_projekt_qfp20(e):
    e.db.execute("insert into quoteflow.postavka_projekta(projekt_id,vrsta_dela_id,zaporedje,naziv,enota,cena_na_enoto,urna_postavka,stevilo_ur,stevilo_delavcev) select %s,%s,g,'P'||g,'kos',1,0,0,1 from generate_series(1,200) g", (e.pa, e.va))
    bad(e.db, e.users, 'owner_a', 'QFP20', 'shrani_postavko_projekta', podjetje=e.a, projekt=e.pa, postavka=None, vrsta_dela=e.va, naziv='X', opis='', enota='kos', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)
    bad(e.db, e.users, 'owner_a', 'QFP20', 'dodaj_postavko_iz_cenika', podjetje=e.a, projekt=e.pa, postavka_cenika=e.ca, kolicina=D(1), popust=D(0))
    first = e.db.execute('select id from quoteflow.postavka_projekta where zaporedje=1').fetchone()['id']; assert put(e, postavka=first, enota='kos')['id'] == first


def test_najvec_100_izmer_na_postavko_qfp28(e):
    it = put(e, enota='kos')['id']
    e.db.execute("insert into quoteflow.izmera(postavka_projekta_id,enota,zaporedje,kosi) select %s,'kos',g,1 from generate_series(1,100) g", (it,))
    bad_meas(e, 'QFP28', it, kosi=D(1)); first = e.db.execute('select id from quoteflow.izmera where zaporedje=1').fetchone()['id']
    assert meas(e, it, izmera=first, kosi=D(2))['kosi'] == 2


def test_najvec_500_vrst_dela_na_podjetje_in_50_materialov_na_vrsto(e):
    e.db.execute("insert into quoteflow.vrsta_dela(podjetje_id,naziv,urna_postavka,stevilo_ur,stevilo_delavcev) select %s,'V'||g,0,0,1 from generate_series(1,499) g", (e.a,))
    bad(e.db, e.users, 'owner_a', 'QFP31', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(naziv='Preveč')))
    assert call(e.db, e.users, 'owner_b', 'shrani_vrsto_dela', podjetje=e.b, **(VRSTA | dict(naziv='Drugo podjetje')))['id']
    assert call(e.db, e.users, 'owner_a', 'shrani_vrsto_dela', podjetje=e.a, **(VRSTA | dict(vrsta=e.va, naziv='Urejena')))['id'] == e.va
    kind = e.db.execute('select vrsta_materiala_id as k from quoteflow.material where id=%s', (e.ma,)).fetchone()['k']
    e.db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) select %s,'S'||g,'M'||g,'kg',1 from generate_series(1,49) g", (kind,))
    e.db.execute('insert into quoteflow.material_vrste_dela(vrsta_dela_id,material_id,kolicina_na_enoto) select %s,m.id,1 from quoteflow.material m where m.vrsta_materiala_id=%s and m.id<>%s', (e.va, kind, e.ma))
    assert count(e.db, 'material_vrste_dela', 'vrsta_dela_id=%s', (e.va,)) == 50
    extra = e.db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'X','X','kg',1) returning id", (kind,)).fetchone()['id']
    bad(e.db, e.users, 'owner_a', 'QFP32', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=extra, kolicina=D(1))
    assert call(e.db, e.users, 'owner_a', 'shrani_material_vrste', podjetje=e.a, vrsta=e.va, material=e.ma, kolicina=D(3))['kolicina_na_enoto'] == 3


@pytest.mark.parametrize('faza', ['termin', 'izvedba', 'obracun', 'zakljucen'])
def test_urejanje_postavk_je_samo_v_fazah_pregled_ogled_ponudba_qfp07(e, faza):
    it = worked(e); i = e.db.execute('select id from quoteflow.izmera limit 1').fetchone()['id']
    for ph in ('ogled', 'ponudba'): quiet(e.db, 'projekt', 'update quoteflow.projekt set faza=%s where id=%s', (ph, e.pa)); assert put(e, postavka=it, naziv='ok')['naziv'] == 'ok'
    quiet(e.db, 'projekt', "update quoteflow.projekt set faza=%s, zakljuceno_ob=case when %s='zakljucen' then now() end where id=%s", (faza, faza, e.pa))
    before = (row(e.db, 'postavka_projekta', it), count(e.db, 'izmera'))
    for name, kw in [('shrani_postavko_projekta', dict(podjetje=e.a, projekt=e.pa, postavka=it, vrsta_dela=e.va, naziv='x', opis='', enota='m2', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None)),
                     ('dodaj_postavko_iz_cenika', dict(podjetje=e.a, projekt=e.pa, postavka_cenika=e.ca, kolicina=D(1), popust=D(0))), ('odstrani_postavko_projekta', dict(podjetje=e.a, projekt=e.pa, postavka=it)),
                     ('shrani_izmero', dict(podjetje=e.a, projekt=e.pa, postavka=it, izmera=None, odstej=False, kosi=D(1), dolzina=D(1), visina=D(1), sirina=None)),
                     ('odstrani_izmero', dict(podjetje=e.a, projekt=e.pa, postavka=it, izmera=i))]:
        bad(e.db, e.users, 'owner_a', 'QFP07', name, **kw)
    assert (row(e.db, 'postavka_projekta', it), count(e.db, 'izmera')) == before


# --- M1: povezave med podjetji
@pytest.fixture
def w(e):
    it = worked(e); ib = put(e, who='owner_b', podjetje=e.b, projekt=e.pb, vrsta_dela=e.vb)['id']
    e.it, e.ib = it, ib; e.ib_izm = meas(e, ib, who='owner_b', podjetje=e.b, projekt=e.pb, dolzina=D(1), visina=D(1))['id']
    e.pa2 = project(e.db, e.users, e.a); e.it2 = put(e, projekt=e.pa2)['id']; e.it_izm = e.db.execute('select id from quoteflow.izmera where postavka_projekta_id=%s limit 1', (it,)).fetchone()['id']
    return e


def base(w, name):
    return dict(
        shrani_postavko_projekta=dict(podjetje=w.a, projekt=w.pa, postavka=None, vrsta_dela=w.va, naziv='X', opis='', enota='m2', cena=D(1), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None),
        dodaj_postavko_iz_cenika=dict(podjetje=w.a, projekt=w.pa, postavka_cenika=w.ca, kolicina=D(1), popust=D(0)),
        odstrani_postavko_projekta=dict(podjetje=w.a, projekt=w.pa, postavka=w.it),
        shrani_izmero=dict(podjetje=w.a, projekt=w.pa, postavka=w.it, izmera=None, odstej=False, kosi=D(1), dolzina=D(1), visina=D(1), sirina=None),
        odstrani_izmero=dict(podjetje=w.a, projekt=w.pa, postavka=w.it, izmera=w.it_izm),
        shrani_material_vrste=dict(podjetje=w.a, vrsta=w.va, material=w.ma, kolicina=D(1)), odstrani_material_vrste=dict(podjetje=w.a, vrsta=w.va, material=w.ma),
        shrani_cenik=dict(podjetje=w.a, target=None, ime='X', opis_v='', vrsta_dela_v=w.va, enota_v='m', cena=D(1), ddv=D('0.22'), aktivna_v=True),
        shrani_vrsto_dela=dict(podjetje=w.a, **VRSTA))[name]


CROSS = [('shrani_postavko_projekta', 'vrsta_dela', 'vb'), ('shrani_postavko_projekta', 'projekt', 'pb'), ('shrani_postavko_projekta', 'postavka', 'ib'), ('shrani_postavko_projekta', 'postavka', 'it2'),
         ('dodaj_postavko_iz_cenika', 'postavka_cenika', 'cb'), ('dodaj_postavko_iz_cenika', 'projekt', 'pb'), ('odstrani_postavko_projekta', 'postavka', 'ib'), ('odstrani_postavko_projekta', 'postavka', 'it2'), ('odstrani_postavko_projekta', 'projekt', 'pb'),
         ('shrani_izmero', 'postavka', 'ib'), ('shrani_izmero', 'postavka', 'it2'), ('shrani_izmero', 'izmera', 'ib_izm'), ('shrani_izmero', 'projekt', 'pb'),
         ('odstrani_izmero', 'izmera', 'ib_izm'), ('odstrani_izmero', 'postavka', 'ib'), ('odstrani_izmero', 'postavka', 'it2'),
         ('shrani_material_vrste', 'material', 'mb'), ('shrani_material_vrste', 'vrsta', 'vb'), ('odstrani_material_vrste', 'vrsta', 'vb'), ('odstrani_material_vrste', 'material', 'mb'),
         ('shrani_cenik', 'vrsta_dela_v', 'vb'), ('shrani_cenik', 'target', 'cb'), ('shrani_vrsto_dela', 'vrsta', 'vb')]


@pytest.mark.parametrize('name,arg,foreign', CROSS)
def test_tuj_zapis_je_enak_nakljucnemu_id_p0002_m1(w, name, arg, foreign):
    snap = (count(w.db, 'postavka_projekta'), count(w.db, 'izmera'), count(w.db, 'material_vrste_dela'), count(w.db, 'postavka_cenika'), count(w.db, 'vrsta_dela'))
    a = bad(w.db, w.users, 'owner_a', 'P0002', name, **(base(w, name) | {arg: getattr(w, foreign)}))
    b = bad(w.db, w.users, 'owner_a', 'P0002', name, **(base(w, name) | {arg: uuid4()}))
    assert a.diag.message_primary == b.diag.message_primary
    assert snap == (count(w.db, 'postavka_projekta'), count(w.db, 'izmera'), count(w.db, 'material_vrste_dela'), count(w.db, 'postavka_cenika'), count(w.db, 'vrsta_dela'))


@pytest.mark.parametrize('name', ['shrani_postavko_projekta', 'dodaj_postavko_iz_cenika', 'odstrani_postavko_projekta', 'shrani_izmero', 'odstrani_izmero', 'shrani_material_vrste', 'odstrani_material_vrste', 'shrani_cenik', 'shrani_vrsto_dela'])
def test_tuje_podjetje_in_napacne_vloge_so_42501(w, name):
    for who in ('owner_b', 'worker', 'customer', 'outsider', 'admin'): bad(w.db, w.users, who, '42501', name, **base(w, name))
    w.db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (w.users['worker'][0], w.a))
    w.db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='mojster'", (w.users['worker'][0],))
    bad(w.db, w.users, 'worker', '42501', name, **base(w, name))


def test_neposredne_povezave_med_podjetji_so_23514(w):
    d = w.db
    reject(d, "insert into quoteflow.postavka_projekta(projekt_id,vrsta_dela_id,zaporedje,naziv,enota,cena_na_enoto,urna_postavka,stevilo_ur,stevilo_delavcev) values(%s,%s,50,'X','kos',1,0,0,1)", (w.pa, w.vb))
    reject(d, 'update quoteflow.postavka_projekta set vrsta_dela_id=%s where id=%s', (w.vb, w.it))
    reject(d, 'insert into quoteflow.material_vrste_dela values(%s,%s,1)', (w.va, w.mb)); reject(d, 'insert into quoteflow.material_vrste_dela values(%s,%s,1)', (w.vb, w.ma))
    reject(d, 'update quoteflow.postavka_cenika set vrsta_dela_id=%s where id=%s', (w.vb, w.ca))
    reject(d, "insert into quoteflow.postavka_cenika(podjetje_id,naziv,vrsta_dela_id,enota,cena_na_enoto) values(%s,'X',%s,'m',1)", (w.a, w.vb))
    reject(d, 'update quoteflow.postavka_projekta set postavka_cenika_id=%s where id=%s', (w.cb, w.it))
    reject(d, 'update quoteflow.material_vrste_dela set material_id=%s where vrsta_dela_id=%s', (w.mb, w.va))


def test_premik_zapisov_med_podjetji_in_projekti_je_zavrnjen(w):
    d = w.db
    reject(d, 'update quoteflow.vrsta_dela set podjetje_id=%s where id=%s', (w.b, w.va))
    reject(d, 'update quoteflow.postavka_projekta set projekt_id=%s where id=%s', (w.pb, w.it)); reject(d, 'update quoteflow.postavka_projekta set projekt_id=%s where id=%s', (w.pa2, w.it))
    reject(d, 'update quoteflow.izmera set postavka_projekta_id=%s where id=%s', (w.ib, w.it_izm)); reject(d, 'update quoteflow.izmera set postavka_projekta_id=%s where id=%s', (w.it2, w.it_izm))
    reject(d, 'update quoteflow.material_vrste_dela set vrsta_dela_id=%s where vrsta_dela_id=%s', (w.vb, w.va))


# --- ponudba: osnutek je glava, pošiljanje posname (M4, M6, QFP13, QFP26)
def test_osnutek_nima_postavk_in_poslji_brez_postavk_je_qfp13(w):
    q = draft(w); assert not lines(w.db, q)
    clear(w)
    bad(w.db, w.users, 'owner_a', 'QFP13', 'poslji_ponudbo', podjetje=w.a, projekt=w.pa, ponudba=q); assert w.db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'osnutek'


def test_poslji_postavko_brez_pozitivnih_izmer_je_qfp26_in_nic_se_ne_posname(w):
    q = draft(w); empty = put(w)['id']
    bad(w.db, w.users, 'owner_a', 'QFP26', 'poslji_ponudbo', podjetje=w.a, projekt=w.pa, ponudba=q)
    assert (w.db.execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'], len(frozen(w.db, q)[0]), count(w.db, 'izmera_ponudbe')) == ('osnutek', 0, 0)
    call(w.db, w.users, 'owner_a', 'odstrani_postavko_projekta', podjetje=w.a, projekt=w.pa, postavka=empty)
    assert send(w, q)['stanje'] == 'poslana'


def test_poslji_posname_postavke_izmere_materiale_in_delo_z_natancnimi_vsotami(w):
    q = draft(w); r = send(w, q); assert r['stanje'] == 'poslana'
    (l,), izm, mats, delo = frozen(w.db, q)
    assert (l['zaporedje'], l['naziv'], l['opis'], l['vrsta_dela'], l['enota'], l['cena_na_enoto'], l['kolicina'], l['popust'], l['stopnja_ddv'], l['izmera_skupaj'], l['neto'], l['koncna_cena']) == \
        (1, 'Polaganje', 'Keramika', 'Polaganje ploščic', 'm2', D(10), D(1), D('0.1'), D('0.22'), D(20), D('540.00'), D('658.80'))
    assert [(i['zaporedje'], i['enota'], i['odstej'], i['kosi'], i['dolzina'], i['visina'], i['sirina'], i['vrednost']) for i in izm] == \
        [(1, 'm2', False, D(1), D(5), D(4), None, D(20)), (2, 'm2', False, D(1), D(2), D(1), None, D(2)), (3, 'm2', True, D(1), D(1), D(2), None, D(2))]
    assert [(m['material_id'], m['naziv'], m['enota'], m['kolicina_na_enoto'], m['cena_na_enoto']) for m in mats] == [(w.ma, 'Lepilo', 'kg', D(5), D('0.8'))]
    assert [(d['urna_postavka'], d['stevilo_ur'], d['stevilo_delavcev'], d['cena_dela']) for d in delo] == [(D(25), D(8), 2, D(400))]
    assert w.db.execute('select faza from quoteflow.projekt where id=%s', (w.pa,)).fetchone()['faza'] == 'ponudba'
    assert w.db.execute("select count(*) as n from quoteflow_private.dogodek_dokumenta where ponudba_id=%s and dejanje='poslana'", (q,)).fetchone()['n'] == 1


def test_vsota_dokumenta_je_vsota_zaokrozenih_vrstic(w):
    clear(w)
    for _ in range(2):
        it = put(w, enota='kos', cena=D('0.005'), popust=D(0), stopnja_ddv=D(0), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1)['id']; meas(w, it, kosi=D(1))
    q = draft(w); send(w, q); assert [l['neto'] for l in lines(w.db, q)] == [D('0.01'), D('0.01')]
    assert w.db.execute('select sum(neto) as n, sum(koncna_cena) as k from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone() == {'n': D('0.02'), 'k': D('0.02')}


def test_po_posiljanju_spremembe_virov_ne_spremenijo_posnetka_m4(w):
    q = draft(w); send(w, q); before = frozen(w.db, q); assert before[0] and before[1] and before[2] and before[3]
    put(w, postavka=w.it, cena=D(99)); meas(w, w.it, dolzina=D(9), visina=D(9)); call(w.db, w.users, 'owner_a', 'odstrani_izmero', podjetje=w.a, projekt=w.pa, postavka=w.it, izmera=w.it_izm)
    call(w.db, w.users, 'owner_a', 'shrani_vrsto_dela', podjetje=w.a, **(VRSTA | dict(vrsta=w.va, naziv='Nova', urna_postavka=D(1000), stevilo_ur=D(1), stevilo_delavcev=1)))
    call(w.db, w.users, 'owner_a', 'shrani_material_vrste', podjetje=w.a, vrsta=w.va, material=w.ma, kolicina=D(77))
    w.db.execute("update quoteflow.material set cena_na_enoto=500, naziv='Drugo' where id=%s", (w.ma,))
    call(w.db, w.users, 'owner_a', 'shrani_cenik', podjetje=w.a, target=w.ca, ime='Drugo', opis_v='', vrsta_dela_v=w.va, enota_v='m', cena=D(1), ddv=D(0), aktivna_v=False)
    call(w.db, w.users, 'owner_a', 'odstrani_material_vrste', podjetje=w.a, vrsta=w.va, material=w.ma)
    call(w.db, w.users, 'owner_a', 'shrani_vrsto_dela', podjetje=w.a, **(VRSTA | dict(vrsta=w.va, aktivna=False)))
    call(w.db, w.users, 'owner_a', 'odstrani_postavko_projekta', podjetje=w.a, projekt=w.pa, postavka=w.it)
    assert frozen(w.db, q) == before and before[0][0]['koncna_cena'] == D('658.80')


def test_posnetek_je_nespremenljiv_tudi_neposredno_55000(w):
    q = draft(w); send(w, q); (l,), _, _, _ = frozen(w.db, q)
    plain = w.db.execute("select is_generated='NEVER' as p from information_schema.columns where table_schema='quoteflow' and table_name='izmera_ponudbe' and column_name='vrednost'").fetchone()['p']
    extra = (',vrednost', ',1') if plain else ('', '')
    for sql, args in [('update quoteflow.postavka_ponudbe set neto=1 where id=%s', (l['id'],)), ('update quoteflow.postavka_ponudbe set izmera_skupaj=1 where id=%s', (l['id'],)), ('update quoteflow.postavka_ponudbe set koncna_cena=1 where id=%s', (l['id'],)),
                      ('delete from quoteflow.postavka_ponudbe where id=%s', (l['id'],)),
                      ('update quoteflow.izmera_ponudbe set kosi=9 where postavka_ponudbe_id=%s', (l['id'],)), ('delete from quoteflow.izmera_ponudbe where postavka_ponudbe_id=%s', (l['id'],)),
                      (f"insert into quoteflow.izmera_ponudbe(postavka_ponudbe_id,zaporedje,enota,kosi,dolzina,visina{extra[0]}) values(%s,9,'m2',1,1,1{extra[1]})", (l['id'],)),
                      ('update quoteflow.delo_ponudbe set urna_postavka=0 where postavka_ponudbe_id=%s', (l['id'],)), ('delete from quoteflow.delo_ponudbe where postavka_ponudbe_id=%s', (l['id'],)),
                      ('update quoteflow.material_ponudbe set cena_na_enoto=0 where postavka_ponudbe_id=%s', (l['id'],))]:
        fails(w.db, sql, args, '55000')


def test_nova_razlicica_posname_trenutne_postavke_in_ne_prejsnje_razlicice(w):
    q1 = draft(w); send(w, q1); v1 = frozen(w.db, q1)
    call(w.db, w.users, 'customer', 'odgovori_ponudbo', projekt=w.pa, ponudba=q1, sprejmi=False)
    put(w, postavka=w.it, cena=D(20)); q2 = draft(w); assert not lines(w.db, q2) and w.db.execute('select razlicica from quoteflow.ponudba where id=%s', (q2,)).fetchone()['razlicica'] == 2
    send(w, q2); (l2,), izm2, _, delo2 = frozen(w.db, q2)
    assert (l2['neto'], l2['koncna_cena'], l2['cena_na_enoto'], len(izm2), delo2[0]['cena_dela']) == (D('720.00'), D('878.40'), D(20), 3, D(400)) and frozen(w.db, q1) == v1


def test_sprejem_ustvari_racun_urejanje_je_qfp07_in_vsote_ostanejo(w):
    q = draft(w); send(w, q); call(w.db, w.users, 'customer', 'odgovori_ponudbo', projekt=w.pa, ponudba=q, sprejmi=True)
    assert count(w.db, 'racun', 'ponudba_id=%s', (q,)) == 1 and w.db.execute('select faza from quoteflow.projekt where id=%s', (w.pa,)).fetchone()['faza'] == 'termin'
    for name in ('shrani_postavko_projekta', 'odstrani_postavko_projekta', 'shrani_izmero', 'dodaj_postavko_iz_cenika'): bad(w.db, w.users, 'owner_a', 'QFP07', name, **base(w, name))
    call(w.db, w.users, 'owner_a', 'shrani_vrsto_dela', podjetje=w.a, **(VRSTA | dict(vrsta=w.va, urna_postavka=D(1)))); w.db.execute('update quoteflow.material set cena_na_enoto=99 where id=%s', (w.ma,))
    assert w.db.execute('select sum(neto) as n, sum(koncna_cena) as k from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone() == {'n': D('540.00'), 'k': D('658.80')}


def test_poslji_dvakrat_je_qfp10_in_posnetek_ostane_en(w):
    q = draft(w); send(w, q); before = frozen(w.db, q)
    bad(w.db, w.users, 'owner_a', 'QFP10', 'poslji_ponudbo', podjetje=w.a, projekt=w.pa, ponudba=q); assert frozen(w.db, q) == before


# --- M14: proračun zmogljivosti pri deklariranem maksimumu (RUN_PERF_TESTS=1; počasen, privzeto preskočen)
@pytest.mark.skipif(not os.getenv('RUN_PERF_TESTS'), reason='Slow: set RUN_PERF_TESTS=1')
def test_zmogljivost_posiljanja_200_postavk_s_100_izmerami_in_branje_stranke(e):
    import time
    e.db.execute("insert into quoteflow.postavka_projekta(projekt_id,vrsta_dela_id,zaporedje,naziv,enota,cena_na_enoto,urna_postavka,stevilo_ur,stevilo_delavcev) select %s,%s,g,'P'||g,'kos',1,0,0,1 from generate_series(1,200) g", (e.pa, e.va))
    e.db.execute("insert into quoteflow.izmera(postavka_projekta_id,enota,zaporedje,kosi) select p.id,'kos',g,1 from quoteflow.postavka_projekta p, generate_series(1,100) g where p.projekt_id=%s", (e.pa,))
    quiet(e.db, 'postavka_projekta', 'update quoteflow.postavka_projekta set izmera_skupaj=100 where projekt_id=%s', (e.pa,))  # bulk insert bypasses the function that maintains the total
    assert (count(e.db, 'postavka_projekta'), count(e.db, 'izmera')) == (200, 20000)
    q = draft(e); t0 = time.monotonic(); send(e, q); e.db.execute('set constraints all immediate'); sending = time.monotonic() - t0  # deferred integrity checks run here, as at commit
    assert count(e.db, 'izmera_ponudbe') == 20000 and count(e.db, 'postavka_ponudbe', 'ponudba_id=%s', (q,)) == 200
    print(f'perf: send {sending:.2f}s'); assert sending < 30, f'poslji_ponudbo + odloženi preizkusi: {sending:.1f} s'
    e.db.execute('set constraints all deferred'); t1 = time.monotonic()
    with as_user(e.db, e.users['customer']):
        n = e.db.execute("select count(*) as n from quoteflow.izmera_ponudbe i join quoteflow.postavka_ponudbe l on l.id=i.postavka_ponudbe_id join quoteflow.ponudba p on p.id=l.ponudba_id "
                         "where p.projekt_id=%s and p.razlicica=(select max(razlicica) from quoteflow.ponudba where projekt_id=%s and stanje<>'osnutek')", (e.pa, e.pa)).fetchone()['n']
    reading = time.monotonic() - t1
    assert n == 20000 and reading < 5, f'branje stranke: {n} vrstic v {reading:.1f} s'
