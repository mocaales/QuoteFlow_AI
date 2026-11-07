"""Approved V2 contract. Database cases use a disposable LOCAL Supabase only."""
import json
import os
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
import pytest

ROOT = Path(__file__).resolve().parents[2]
V2_TABLES = {
    'uporabnik', 'vloga_uporabnika', 'podjetje', 'prosnja_mojstra',
    'projekt', 'ekipa', 'clan_ekipe', 'projekt_ekipa', 'postavka_cenika',
    'vrsta_materiala', 'material', 'zaloga', 'sestava_cenika', 'ponudba',
    'postavka_ponudbe', 'material_ponudbe', 'racun',
}
# Model v3 (G1 2026-11-07): sestava_cenika is replaced by vrsta_dela + material_vrste_dela; plus postavka_projekta, izmera, izmera_ponudbe, delo_ponudbe (mojster-only labour snapshot).
TABLES = (V2_TABLES - {'sestava_cenika'}) | {'vrsta_dela', 'material_vrste_dela', 'postavka_projekta', 'izmera', 'izmera_ponudbe', 'delo_ponudbe'}
LOCAL = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'


def test_migracija_obstaja_in_uvaja_novi_model():
    files = sorted((ROOT / 'supabase/migrations').glob('*v2*.sql'))
    assert files, 'Approved V2 requires a versioned SQL migration'
    sql = files[-1].read_text().lower()
    for table in V2_TABLES:
        assert f'quoteflow.{table}' in sql, table
    assert 'quoteflow_legacy_' in sql, 'Existing business data must be preserved in an inaccessible archive'


@pytest.fixture
def db():
    url = os.environ['TEST_DATABASE_URL']
    assert conninfo_to_dict(url)['host'] in ('localhost', '127.0.0.1'), 'Never test a remote database'
    with psycopg.connect(url, row_factory=dict_row) as connection:
        try:
            yield connection
        finally:
            connection.rollback()


@contextmanager
def as_user(db, identity):
    uid, sid = identity
    db.execute('set local role authenticated')
    db.execute("select set_config('request.jwt.claim.sub',%s,true), set_config('request.jwt.claims',%s,true)",
               (str(uid), json.dumps({'sub': str(uid), 'session_id': str(sid)})))
    try:
        yield db
    finally:
        if db.info.transaction_status != psycopg.pq.TransactionStatus.INERROR:
            db.execute('reset role')


@pytest.fixture
def identities(db):
    users = {}
    for name in ('admin', 'owner_a', 'owner_b', 'worker', 'customer', 'outsider'):
        uid, sid = uuid4(), uuid4()
        db.execute('insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at) values(%s,%s,%s::jsonb,now())',
                   (uid, f'{name}-{uid}@example.test', json.dumps({'ime': 'Ime', 'priimek': 'Priimek', 'vloga': 'admin'})))
        db.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid))
        users[name] = (uid, sid)
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'admin')", (users['admin'][0],))
    companies = []
    for name, label in [('owner_a', 'A'), ('owner_b', 'B')]:
        company = db.execute("insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(%s,%s,%s,%s,'SI12345678') returning id",
                             (users[name][0], label, uuid4().hex[:30], 'Naslov 1')).fetchone()['id']
        db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (users[name][0], company))
        companies.append(company)
    a, b = companies
    role = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'delavec') returning id", (users['worker'][0], a)).fetchone()['id']
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'delavec')", (users['owner_a'][0], b))
    db.execute('set constraints all immediate')
    db.execute('set constraints all deferred')
    return users, a, b, role


def reject(db, sql, args=()):
    with pytest.raises(psycopg.Error):
        with db.transaction():
            db.execute(sql, args)
            db.execute('set constraints all immediate')


def test_pogodba_pripravljenosti_pricakuje_22_tabel_modela_v3():
    from app.database import EXPECTED_TABLES
    assert len(TABLES) == 22 and EXPECTED_TABLES == TABLES


@LOCAL
def test_natancno_22_tabel_in_zasciten_arhiv(db):
    actual = {r['tablename'] for r in db.execute("select tablename from pg_tables where schemaname='quoteflow'")}
    assert actual == TABLES
    assert all(r['relrowsecurity'] and r['relforcerowsecurity'] for r in db.execute("select relrowsecurity,relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow' and c.relkind='r'"))
    archived = db.execute("select nspname from pg_namespace where nspname like 'quoteflow_legacy_%'").fetchall()
    assert archived
    for row in archived:
        assert not db.execute("select has_schema_privilege('authenticated',%s,'USAGE') as allowed", (row['nspname'],)).fetchone()['allowed']
        assert not db.execute("select has_schema_privilege('anon',%s,'USAGE') as allowed", (row['nspname'],)).fetchone()['allowed']


@LOCAL
def test_nov_racun_dobi_stranko_in_ne_pravic_iz_metapodatkov(db, identities):
    users, _, _, _ = identities
    uid = users['outsider'][0]
    person = db.execute('select * from quoteflow.uporabnik where id=%s', (uid,)).fetchone()
    assert person['ime'] == 'Ime' and person['priimek'] == 'Priimek'
    roles = db.execute('select vloga,podjetje_id from quoteflow.vloga_uporabnika where uporabnik_id=%s', (uid,)).fetchall()
    assert roles == [{'vloga': 'stranka', 'podjetje_id': None}]


@LOCAL
def test_obseg_vlog_podvojitve_in_lastnik_mora_ostati_mojster(db, identities):
    users, a, _, _ = identities
    for role, company in [('admin', a), ('stranka', a), ('mojster', None), ('delavec', None), ('stranka', None)]:
        reject(db, 'insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,%s)', (users['customer'][0], company, role))
    reject(db, "update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='mojster'", (users['owner_a'][0],))
    reject(db, 'update quoteflow.podjetje set lastnik_id=%s where id=%s', (users['customer'][0], a))


@LOCAL
def test_ekipe_in_projekti_ne_mesajo_podjetij(db, identities):
    users, a, b, worker = identities
    team_a = db.execute("insert into quoteflow.ekipa(podjetje_id,naziv) values(%s,'A') returning id", (a,)).fetchone()['id']
    team_b = db.execute("insert into quoteflow.ekipa(podjetje_id,naziv) values(%s,'B') returning id", (b,)).fetchone()['id']
    db.execute('insert into quoteflow.clan_ekipe values(%s,%s)', (team_a, worker))
    reject(db, 'insert into quoteflow.clan_ekipe values(%s,%s)', (team_b, worker))
    master_role = db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='mojster'", (users['owner_a'][0],)).fetchone()['id']
    reject(db, 'insert into quoteflow.clan_ekipe values(%s,%s)', (team_a, master_role))
    project = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Projekt','Opis','Maribor') returning id", (a, users['customer'][0])).fetchone()['id']
    db.execute('insert into quoteflow.projekt_ekipa values(%s,%s)', (project, team_a))
    reject(db, 'insert into quoteflow.projekt_ekipa values(%s,%s)', (project, team_b))
    with as_user(db, users['worker']):
        assert [r['id'] for r in db.execute('select id from quoteflow.projekt')] == [project]
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (worker,))
    with as_user(db, users['worker']):
        assert not db.execute('select id from quoteflow.projekt').fetchall()


@pytest.fixture
def catalog(db, identities):
    """Per company (vrsta_materiala, material, postavka_cenika); the item points at a vrsta dela without labour that uses the material (2 kg per unit)."""
    users, a, b, _ = identities
    data = []
    for company in (a, b):
        kind = db.execute("insert into quoteflow.vrsta_materiala(podjetje_id,naziv) values(%s,'Lepilo') returning id", (company,)).fetchone()['id']
        material = db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'M1','Lepilo','kg',2) returning id", (kind,)).fetchone()['id']
        vrsta = db.execute("insert into quoteflow.vrsta_dela(podjetje_id,naziv,opis,urna_postavka,stevilo_ur,stevilo_delavcev) values(%s,'Gradnja','Splošna gradnja',0,0,1) returning id", (company,)).fetchone()['id']
        db.execute('insert into quoteflow.material_vrste_dela(vrsta_dela_id,material_id,kolicina_na_enoto) values(%s,%s,2)', (vrsta, material))
        item = db.execute("insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela_id,enota,cena_na_enoto,stopnja_ddv) values(%s,'Polaganje','Opis',%s,'m2',25,.22) returning id", (company, vrsta)).fetchone()['id']
        data.append((kind, material, item))
    return data


def vrsta_of(db, item): return db.execute('select vrsta_dela_id as v from quoteflow.postavka_cenika where id=%s', (item,)).fetchone()['v']


@LOCAL
def test_materiali_vrsta_dela_zaloga_in_zasebnost(db, identities, catalog):
    users, a, b, _ = identities
    ka, ma, ca = catalog[0]
    _, mb, cb = catalog[1]
    db.execute("insert into quoteflow.zaloga values(%s,'Skladisce',10)", (ma,))
    reject(db, 'insert into quoteflow.material_vrste_dela(vrsta_dela_id,material_id,kolicina_na_enoto) values(%s,%s,2)', (vrsta_of(db, ca), mb))
    reject(db, "insert into quoteflow.zaloga values(%s,'Drugje',-1)", (ma,))
    reject(db, "insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'M1','Duplikat','kg',2)", (ka,))
    reject(db, "update quoteflow.material set enota='m' where id=%s", (ma,))
    with as_user(db, users['customer']):
        assert not db.execute('select * from quoteflow.material').fetchall()
        assert not db.execute('select * from quoteflow.zaloga').fetchall()
    with as_user(db, users['owner_a']):
        assert [r['id'] for r in db.execute('select id from quoteflow.postavka_cenika')] == [ca]
    with as_user(db, users['admin']):
        assert not db.execute('select * from quoteflow.postavka_cenika').fetchall()


@LOCAL
def test_brez_seje_ni_branja_in_ni_neposrednega_pisanja(db, identities):
    users, _, _, _ = identities
    db.execute('delete from auth.sessions where id=%s', (users['admin'][1],))
    with as_user(db, users['admin']):
        assert not db.execute('select * from quoteflow.uporabnik').fetchall()
        assert not db.execute('select * from quoteflow.podjetje').fetchall()
    with as_user(db, users['customer']):
        reject(db, "insert into quoteflow.ekipa(podjetje_id,naziv) values(%s,'Vdor')", (uuid4(),))


@pytest.fixture
def offer(db, identities, catalog):
    """v3: postavka projekta iz cenika (4 x 25 EUR, popust 10 %, izmera 1) + osnutek ponudbe (samo glava). Vrne (projekt, ponudba, postavka_projekta)."""
    users, a, _, _ = identities
    _, material, item = catalog[0]
    project = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (a, users['customer'][0])).fetchone()['id']
    with as_user(db, users['owner_a']):
        it = db.execute(f'select * from {Q}dodaj_postavko_iz_cenika(podjetje => %s, projekt => %s, postavka_cenika => %s, kolicina => 4, popust => 0.1)', (a, project, item)).fetchone()['id']
        db.execute(f'select * from {Q}shrani_izmero(podjetje => %s, projekt => %s, postavka => %s, izmera => null, odstej => false, kosi => 1, dolzina => 1, visina => 1, sirina => null)', (a, project, it))
        quote = db.execute(f'select * from {Q}ustvari_ponudbo(podjetje => %s, projekt => %s, velja_do => current_date+10)', (a, project)).fetchone()['id']
    return project, quote, it


def lines_of(db, quote): return db.execute('select * from quoteflow.postavka_ponudbe where ponudba_id=%s order by zaporedje', (quote,)).fetchall()


@LOCAL
def test_ponudba_cena_izolacija_in_nespremenljiv_posnetek(db, identities, catalog, offer):
    users, a, _, _ = identities
    project, quote, _ = offer
    assert not lines_of(db, quote), 'osnutek je samo glava'
    with as_user(db, users['customer']):
        assert not db.execute('select * from quoteflow.ponudba').fetchall()
        reject(db, 'select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (a, project, quote))
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (a, project, quote))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'ponudba'
    (line,) = lines_of(db, quote)
    assert str(line['koncna_cena']) == '109.80' and str(line['neto']) == '90.00'
    reject(db, 'update quoteflow.postavka_ponudbe set postavka_cenika_id=%s where id=%s', (catalog[1][2], line['id']))
    reject(db, "insert into quoteflow.material_ponudbe values(%s,%s,'Tuji','kg',1,1)", (line['id'], catalog[1][1]))
    with as_user(db, users['customer']):
        assert [r['id'] for r in db.execute('select id from quoteflow.ponudba')] == [quote]
    with as_user(db, users['outsider']):
        assert not db.execute('select id from quoteflow.ponudba').fetchall()
        reject(db, 'select quoteflow_private.odgovori_ponudbo(%s,%s,true)', (project, quote))
    for sql, args in [
        ('update quoteflow.postavka_ponudbe set cena_na_enoto=999 where id=%s', (line['id'],)),
        ('delete from quoteflow.material_ponudbe where postavka_ponudbe_id=%s', (line['id'],)),
        ('delete from quoteflow.izmera_ponudbe where postavka_ponudbe_id=%s', (line['id'],)),
        ('delete from quoteflow.ponudba where id=%s', (quote,)),
    ]:
        reject(db, sql, args)
    # Updating the reusable source must not rewrite a sent document.
    db.execute('update quoteflow.postavka_cenika set cena_na_enoto=999 where id=%s', (catalog[0][2],))
    assert str(db.execute('select cena_na_enoto from quoteflow.postavka_ponudbe where id=%s', (line['id'],)).fetchone()['cena_na_enoto']) == '25.0000'


@LOCAL
def test_sprejem_racun_termin_izvedba_in_placilo_so_povezani(db, identities, catalog, offer):
    users, a, _, _ = identities
    project, quote, _ = offer
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (a, project, quote))
    with as_user(db, users['customer']):
        db.execute('select quoteflow_private.odgovori_ponudbo(%s,%s,true)', (project, quote))
    invoice = db.execute('select * from quoteflow.racun where ponudba_id=%s', (quote,)).fetchone()
    assert invoice['stanje_dokumenta'] == 'osnutek' and invoice['placano_ob'] is None
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'termin'
    reject(db, 'update quoteflow.racun set placano_ob=now() where id=%s', (invoice['id'],))
    start = "date_trunc('day',now())"
    with as_user(db, users['owner_b']):
        reject(db, f"select quoteflow_private.doloci_termin(%s,%s,{start},{start}+interval '2 days')", (a, project))
    with as_user(db, users['owner_a']):
        db.execute(f"select quoteflow_private.doloci_termin(%s,%s,{start},{start}+interval '2 days')", (a, project))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'izvedba'
    # Only the company master finishes the work; invoicing then needs the finished work, tax number and location.
    with as_user(db, users['owner_a']):
        reject(db, 'select quoteflow_private.izdaj_racun(%s,%s,%s,%s,current_date+14)', (a, project, 'Ime Priimek', 'Maribor'))
        db.execute('select quoteflow_private.zakljuci_izvedbo(%s,%s)', (a, project))
    with as_user(db, users['customer']):
        reject(db, 'select quoteflow_private.izdaj_racun(%s,%s,%s,%s,current_date+14)', (a, project, 'Ime Priimek', 'Maribor'))
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.izdaj_racun(%s,%s,%s,%s,current_date+14)', (a, project, 'Ime Priimek', 'Maribor'))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'obracun'
    reject(db, "update quoteflow.racun set prejemnik_naziv='Spremenjeno' where id=%s", (invoice['id'],))
    with as_user(db, users['customer']):
        reject(db, 'select quoteflow_private.placaj_racun(%s,%s)', (a, project))
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.placaj_racun(%s,%s)', (a, project))
    assert db.execute('select placano_ob from quoteflow.racun where id=%s', (invoice['id'],)).fetchone()['placano_ob']
    closed = db.execute('select faza,zakljuceno_ob from quoteflow.projekt where id=%s', (project,)).fetchone()
    assert closed['faza'] == 'zakljucen' and closed['zakljuceno_ob']


@LOCAL
def test_ponudba_brez_postavk_projekta_in_poljuben_preskok_faze_nista_dovoljena(db, identities, offer):
    users, a, _, _ = identities
    project, quote, item = offer
    with as_user(db, users['owner_a']):
        db.execute(f'select * from {Q}odstrani_postavko_projekta(podjetje => %s, projekt => %s, postavka => %s)', (a, project, item))
        reject(db, 'select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (a, project, quote))
    reject(db, "update quoteflow.projekt set faza='zakljucen',zakljuceno_ob=now() where id=%s", (project,))


@LOCAL
def test_mojster_pri_a_delavec_pri_b_ne_podeduje_upravljanja_b(db, identities, catalog):
    users, a, b, _ = identities
    with as_user(db, users['owner_a']):
        assert db.execute("select quoteflow_private.clan(%s,'mojster') as yes", (a,)).fetchone()['yes']
        assert not db.execute("select quoteflow_private.clan(%s,'mojster') as yes", (b,)).fetchone()['yes']
        assert db.execute("select quoteflow_private.clan(%s,'delavec') as yes", (b,)).fetchone()['yes']
    # A direct write grant would let a forged company ID bypass the intended helpers.
    for table in TABLES:
        for privilege in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
            assert not db.execute('select has_table_privilege(%s,%s,%s) as yes', ('authenticated', 'quoteflow.' + table, privilege)).fetchone()['yes'], (table, privilege)


@LOCAL
def test_uporabljeni_starsi_se_ne_selijo_med_podjetji(db, identities, catalog, offer):
    users, a, b, _ = identities
    kind, material, item = catalog[0]
    project, _, _ = offer
    reject(db, 'update quoteflow.postavka_cenika set podjetje_id=%s where id=%s', (b, item))
    reject(db, 'update quoteflow.vrsta_materiala set podjetje_id=%s where id=%s', (b, kind))
    reject(db, 'update quoteflow.material set vrsta_materiala_id=%s where id=%s', (catalog[1][0], material))
    reject(db, 'update quoteflow.projekt set podjetje_id=%s where id=%s', (b, project))


@LOCAL
def test_odlocitev_o_ponudbi_pripada_samo_stranki(db, identities, offer):
    users, a, _, _ = identities
    project, quote, _ = offer
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (a, project, quote))
        reject(db, 'select quoteflow_private.odgovori_ponudbo(%s,%s,true)', (project, quote))
    with as_user(db, users['customer']):
        db.execute('select quoteflow_private.odgovori_ponudbo(%s,%s,false)', (project, quote))
    assert db.execute('select stanje from quoteflow.ponudba where id=%s', (quote,)).fetchone()['stanje'] == 'zavrnjena'
    assert not db.execute('select * from quoteflow.racun where ponudba_id=%s', (quote,)).fetchall()
