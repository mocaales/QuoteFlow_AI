"""X1: pretvorba cenika v modelu v3 na populiranem v2 (oddaljeno stanje pred v3). Vsak primer dela v lastni začasni LOKALNI bazi
(create database ... template, kot supabase/tests/v1_to_v2_upgrade.py); migracija v3 je datoteka med 20261105140049 in 20261106200016."""
import json
import os
from decimal import Decimal as D
from pathlib import Path
from uuid import uuid4
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / 'supabase/migrations'
DEPLOYED = ['20261027161706_identity_and_permissions.sql', '20261029195006_supplier_catalog_stock_rules.sql', '20261103211654_v2_projects_roles_catalog.sql',
            '20261105114405_prosnja_varnost.sql', '20261105140047_materialna_sestava.sql', '20261105140049_projekti.sql']
AUTH = """create schema extensions; create schema auth;
create table auth.users (id uuid primary key, email text, email_confirmed_at timestamptz, raw_user_meta_data jsonb not null default '{}');
create table auth.sessions (id uuid primary key, user_id uuid references auth.users(id), not_after timestamptz);
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;"""
EXPECTED_V3 = {'uporabnik', 'podjetje', 'vloga_uporabnika', 'prosnja_mojstra', 'projekt', 'ekipa', 'clan_ekipe', 'projekt_ekipa', 'postavka_cenika', 'vrsta_materiala', 'material', 'zaloga', 'ponudba', 'postavka_ponudbe',
               'material_ponudbe', 'racun', 'vrsta_dela', 'material_vrste_dela', 'postavka_projekta', 'izmera', 'izmera_ponudbe', 'delo_ponudbe'}


def v3_migrations(): return [p for p in sorted(MIGRATIONS.glob('*.sql')) if DEPLOYED[-1][:14] < p.name[:14] < '20261106200016']
def later_migrations(): return [p for p in sorted(MIGRATIONS.glob('*.sql')) if p.name[:14] > DEPLOYED[-1][:14] and p not in v3_migrations()]


@pytest.fixture(scope='module')
def template():
    url = os.environ['TEST_DATABASE_URL']; assert conninfo_to_dict(url)['host'] in ('localhost', '127.0.0.1'), 'Never test a remote database'
    name = f'quoteflow_v3_base_{uuid4().hex}'
    with psycopg.connect(url, autocommit=True) as control:
        control.execute(sql.SQL('create database {} template template0').format(sql.Identifier(name)))
        try:
            with psycopg.connect(url, dbname=name) as db:
                db.execute(AUTH)
                for migration in DEPLOYED: db.execute((MIGRATIONS / migration).read_text()); db.commit()
            yield url, name
        finally: control.execute(sql.SQL('drop database {} with (force)').format(sql.Identifier(name)))


@pytest.fixture
def upgrade(template):
    url, base = template; name = f'quoteflow_v3_run_{uuid4().hex}'
    with psycopg.connect(url, autocommit=True) as control:
        control.execute(sql.SQL('create database {} template {}').format(sql.Identifier(name), sql.Identifier(base)))
        try:
            with psycopg.connect(url, dbname=name, row_factory=dict_row) as db: yield db
        finally: control.execute(sql.SQL('drop database {} with (force)').format(sql.Identifier(name)))


def user(db, name):
    uid = uuid4(); db.execute('insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values(%s,%s,now(),%s::jsonb)', (uid, f'{name}-{uid}@example.test', json.dumps({'ime': name, 'priimek': 'X'}))); return uid


def populate(db, unit_a1='m²', quote_line=False):
    """Two companies with the same work-type text, whitespace variants, m²/m³, with and without composition, inactive rows."""
    owner_a, owner_b = user(db, 'a'), user(db, 'b'); co = {}
    for tag, owner in (('a', owner_a), ('b', owner_b)):
        co[tag] = db.execute("insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(%s,%s,%s,'Naslov 1','SI12345678') returning id", (owner, tag.upper(), uuid4().hex[:30])).fetchone()['id']
        db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (owner, co[tag]))
    mat = {}
    for tag, name, active, price in (('a', 'Lepilo', True, '0.8'), ('a', 'Fuga', False, '1.5'), ('b', 'Lepilo', True, '0.9')):
        kind = db.execute("insert into quoteflow.vrsta_materiala(podjetje_id,naziv) values(%s,%s) on conflict(podjetje_id,naziv) do update set naziv=excluded.naziv returning id", (co[tag], name + ' vrsta')).fetchone()['id']
        mat[(tag, name)] = db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto,aktiven) values(%s,%s,%s,'kg',%s,%s) returning id", (kind, name[:3].upper(), name, price, active)).fetchone()['id']
    items = {}
    for key, tag, naziv, vrsta, unit, price, active in [
            ('A1', 'a', 'Polaganje ploščic', 'Gradnja', unit_a1, '25', True), ('A2', 'a', 'Beljenje', 'Gradnja', 'm2', '8', True), ('A3', 'a', 'Beljenje stropa', '  Gradnja  ', 'm²', '9', True),
            ('A4', 'a', 'Beton', 'Gradnja', 'm³', '90', False), ('A5', 'a', 'Montaža', 'Montaža', 'kos', '40', True), ('A6', 'a', 'Razvoz', 'Prevoz', 'm', '2', True),
            ('B1', 'b', 'Beljenje', 'Gradnja', 'm2', '7', True), ('B2', 'b', 'Polaganje', 'Gradnja', 'kos', '12', True)]:
        items[key] = db.execute("insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela,enota,cena_na_enoto,stopnja_ddv,aktivna) values(%s,%s,'Opis',%s,%s,%s,0.22,%s) returning id", (co[tag], naziv, vrsta, unit, price, active)).fetchone()['id']
    comp = [('A1', ('a', 'Lepilo'), '5'), ('A1', ('a', 'Fuga'), '0.5'), ('A4', ('a', 'Lepilo'), '1'), ('B2', ('b', 'Lepilo'), '2')]
    for item, m, qty in comp: db.execute('insert into quoteflow.sestava_cenika values(%s,%s,%s)', (items[item], mat[m], qty))
    db.execute("insert into quoteflow.zaloga values(%s,'Maribor',10)", (mat[('a', 'Lepilo')],))
    if quote_line:
        customer = user(db, 'c'); p = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'P','O','M') returning id", (co['a'], customer)).fetchone()['id']
        q = db.execute("insert into quoteflow.ponudba(projekt_id,stevilka) values(%s,'P-2026-001') returning id", (p,)).fetchone()['id']
        db.execute("insert into quoteflow.postavka_ponudbe(ponudba_id,zaporedje,naziv,vrsta_dela,enota,cena_na_enoto,kolicina) values(%s,1,'X','Gradnja','m2',1,1)", (q,))
    db.commit()
    return co, mat, items, comp


def migration_sql():
    files = v3_migrations(); assert len(files) == 1, f'model v3 requires exactly one migration between 20261105140049 and 20261106200016, found {[f.name for f in files]}'
    return files[0].read_text()


def schema_state(db):
    return (db.execute("select column_name from information_schema.columns where table_schema='quoteflow' and table_name='postavka_cenika' order by 1").fetchall(),
            sorted(r['tablename'] for r in db.execute("select tablename from pg_tables where schemaname='quoteflow'")),
            db.execute('select count(*) as n from quoteflow.postavka_cenika').fetchone()['n'], db.execute('select count(*) as n from quoteflow.sestava_cenika').fetchone()['n'])


def test_migracija_v3_obstaja_med_uvedenimi_in_lokalnimi(template):
    assert len(v3_migrations()) == 1, [p.name for p in v3_migrations()]
    assert all(DEPLOYED[-1][:14] < p.name[:14] for p in v3_migrations()), 'uvedene migracije se ne urejajo'


def test_pretvorba_ohrani_vsako_postavko_in_sestavo_in_loci_podjetja(upgrade):
    db = upgrade; co, mat, items, comp = populate(db)
    before = {r['id']: r for r in db.execute('select * from quoteflow.postavka_cenika')}; stock = db.execute('select * from quoteflow.zaloga').fetchall(); materials = db.execute('select * from quoteflow.material order by id').fetchall()
    db.execute(migration_sql()); db.commit()
    after = {r['id']: r for r in db.execute('select * from quoteflow.postavka_cenika')}
    assert set(after) == set(before) == set(items.values())
    for id_, b in before.items():
        a = after[id_]; assert all(a[k] == b[k] for k in ('podjetje_id', 'naziv', 'opis', 'cena_na_enoto', 'stopnja_ddv', 'aktivna')), b['naziv']
        assert a['enota'] == {'m²': 'm2', 'm³': 'm3'}.get(b['enota'], b['enota']), b['enota']
        v = db.execute('select * from quoteflow.vrsta_dela where id=%s', (a['vrsta_dela_id'],)).fetchone()
        assert v and v['podjetje_id'] == a['podjetje_id'] and v['naziv'].strip() and v['aktivna'] is True, b['naziv']
    vd = {k: db.execute('select * from quoteflow.vrsta_dela where id=%s', (after[i]['vrsta_dela_id'],)).fetchone() for k, i in items.items()}
    assert vd['A2']['id'] == vd['A3']['id'] and vd['A2']['naziv'] == 'Gradnja', 'brez sestave: ena vrsta na (podjetje, trim(vrsta_dela))'
    assert len({vd[k]['id'] for k in ('A2', 'A5', 'A6')}) == 3 and vd['B1']['id'] != vd['A2']['id'] and vd['B1']['podjetje_id'] == co['b'], 'ključ združevanja vsebuje podjetje'
    assert len({vd[k]['id'] for k in ('A1', 'A4', 'A2')}) == 3, 'postavka s sestavo dobi lastno vrsto dela'
    for k in ('A2', 'A5', 'A6', 'B1'): assert vd[k]['urna_postavka'] * vd[k]['stevilo_ur'] == 0 and vd[k]['stevilo_delavcev'] == 1 and vd[k]['cena_dela'] == 0, k
    got = sorted((r['vrsta_dela_id'], r['material_id'], r['kolicina_na_enoto']) for r in db.execute('select * from quoteflow.material_vrste_dela'))
    want = sorted((after[items[i]]['vrsta_dela_id'], mat[m], D(q)) for i, m, q in comp)
    assert got == want and len(got) == 4, 'vsaka vrstica sestave je preslikana, tudi z neaktivnim materialom'
    assert stock == db.execute('select * from quoteflow.zaloga').fetchall() and materials == db.execute('select * from quoteflow.material order by id').fetchall()


def test_po_pretvorbi_ni_sestave_cenika_besedilne_vrste_dela_in_starih_funkcij(upgrade):
    db = upgrade; populate(db); db.execute(migration_sql()); db.commit()
    assert not db.execute("select 1 from pg_tables where schemaname='quoteflow' and tablename='sestava_cenika'").fetchall()
    cols = {r['column_name']: r for r in db.execute("select column_name,is_nullable from information_schema.columns where table_schema='quoteflow' and table_name='postavka_cenika'")}
    assert 'vrsta_dela' not in cols and cols['vrsta_dela_id']['is_nullable'] == 'NO'
    assert not {r['proname'] for r in db.execute("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private'")} & {'shrani_sestavo', 'odstrani_sestavo'}
    assert db.execute("select count(*) as n from pg_constraint where conrelid='quoteflow.postavka_cenika'::regclass and contype='c' and pg_get_constraintdef(oid) ilike '%m3%'").fetchone()['n'] >= 1, 'enota je omejena na m, m2, m3, kos'


def test_pretvorjeno_stanje_sprejme_celotno_verigo_migracij_22_tabel_s_prisiljenim_rls(upgrade):
    db = upgrade; populate(db); migration_sql()
    for path in [*v3_migrations(), *later_migrations()]: db.execute(path.read_text()); db.commit()
    tables = {r['tablename']: r for r in db.execute("select tablename,c.relrowsecurity as rls,c.relforcerowsecurity as forced from pg_tables t join pg_class c on c.relname=t.tablename join pg_namespace n on n.oid=c.relnamespace and n.nspname=t.schemaname where t.schemaname='quoteflow'")}
    assert set(tables) == EXPECTED_V3 and all(t['rls'] and t['forced'] for t in tables.values())
    assert db.execute('select count(*) as n from quoteflow.postavka_cenika').fetchone()['n'] == 8
    assert not db.execute("select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private' and has_function_privilege('anon',p.oid,'execute')").fetchall()
    for fn in ('preveri_celovitost', 'zakleni_podjetje'): assert 'sestava_cenika' not in db.execute("select pg_get_functiondef(p.oid) as d from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private' and proname=%s", (fn,)).fetchone()['d']


def test_neznana_enota_glasno_pade_in_nic_se_ne_spremeni(upgrade):
    db = upgrade; populate(db, unit_a1='ura'); before = schema_state(db)
    with pytest.raises(psycopg.Error) as err: db.execute(migration_sql())
    assert not err.value.sqlstate.startswith(('42', '0A')), f'pričakovan namenski neuspeh, ne sintaksna/nedefinirana napaka: {err.value.sqlstate} {err.value}'
    db.rollback(); assert schema_state(db) == before
    assert db.execute("select count(*) as n from quoteflow.postavka_cenika where enota='ura'").fetchone()['n'] == 1, 'neznana enota ni bila tiho pretvorjena v kos'


def test_neprazne_vrstice_ponudb_glasno_ustavijo_pretvorbo(upgrade):
    db = upgrade; populate(db, quote_line=True); before = schema_state(db)
    with pytest.raises(psycopg.Error) as err: db.execute(migration_sql())
    assert not err.value.sqlstate.startswith(('42', '0A')), f'{err.value.sqlstate} {err.value}'
    db.rollback(); assert schema_state(db) == before and db.execute('select count(*) as n from quoteflow.postavka_ponudbe').fetchone()['n'] == 1


def test_prazen_katalog_se_pretvori_brez_napake(upgrade):
    db = upgrade; db.execute(migration_sql()); db.commit()
    assert db.execute('select count(*) as n from quoteflow.vrsta_dela').fetchone()['n'] == 0
