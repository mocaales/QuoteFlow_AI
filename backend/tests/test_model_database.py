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
TABLES = {
    'uporabnik', 'vloga_uporabnika', 'podjetje', 'prosnja_mojstra',
    'projekt', 'ekipa', 'clan_ekipe', 'projekt_ekipa', 'postavka_cenika',
    'vrsta_materiala', 'material', 'zaloga', 'sestava_cenika', 'ponudba',
    'postavka_ponudbe', 'material_ponudbe', 'racun',
}
LOCAL = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')


def test_migracija_obstaja_in_uvaja_novi_model():
    files = sorted((ROOT / 'supabase/migrations').glob('*v2*.sql'))
    assert files, 'Approved V2 requires a versioned SQL migration'
    sql = files[-1].read_text().lower()
    for table in TABLES:
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


@LOCAL
def test_natancno_sedemnajst_tabel_in_zasciten_arhiv(db):
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
    users, a, b, _ = identities
    data = []
    for company in (a, b):
        kind = db.execute("insert into quoteflow.vrsta_materiala(podjetje_id,naziv) values(%s,'Lepilo') returning id", (company,)).fetchone()['id']
        material = db.execute("insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values(%s,'M1','Lepilo','kg',2) returning id", (kind,)).fetchone()['id']
        item = db.execute("insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela,enota,cena_na_enoto,stopnja_ddv) values(%s,'Polaganje','Opis','Gradnja','m2',25,.22) returning id", (company,)).fetchone()['id']
        data.append((kind, material, item))
    return data


@LOCAL
def test_materiali_sestava_zaloga_in_zasebnost(db, identities, catalog):
    users, a, b, _ = identities
    ka, ma, ca = catalog[0]
    _, mb, cb = catalog[1]
    db.execute("insert into quoteflow.zaloga values(%s,'Skladisce',10)", (ma,))
    db.execute('insert into quoteflow.sestava_cenika values(%s,%s,2)', (ca, ma))
    reject(db, 'insert into quoteflow.sestava_cenika values(%s,%s,2)', (ca, mb))
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
    users, a, _, _ = identities
    _, material, item = catalog[0]
    project = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (a, users['customer'][0])).fetchone()['id']
    quote = db.execute("insert into quoteflow.ponudba(projekt_id,stevilka,razlicica) values(%s,'P-1',1) returning id", (project,)).fetchone()['id']
    line = db.execute("insert into quoteflow.postavka_ponudbe(ponudba_id,postavka_cenika_id,zaporedje,naziv,opis,vrsta_dela,enota,cena_na_enoto,kolicina,popust,stopnja_ddv) values(%s,%s,1,'Polaganje','Opis','Gradnja','m2',25,4,.1,.22) returning id,koncna_cena", (quote, item)).fetchone()
    db.execute("insert into quoteflow.material_ponudbe values(%s,%s,'Lepilo','kg',2,2)", (line['id'], material))
    return project, quote, line['id']


@LOCAL
def test_ponudba_cena_izolacija_in_nespremenljiv_posnetek(db, identities, catalog, offer):
    users, _, _, _ = identities
    project, quote, line = offer
    assert str(db.execute('select koncna_cena from quoteflow.postavka_ponudbe where id=%s', (line,)).fetchone()['koncna_cena']) == '109.80'
    reject(db, 'update quoteflow.postavka_ponudbe set postavka_cenika_id=%s where id=%s', (catalog[1][2], line))
    reject(db, "insert into quoteflow.material_ponudbe values(%s,%s,'Tuji','kg',1,1)", (line, catalog[1][1]))
    with as_user(db, users['customer']):
        assert not db.execute('select * from quoteflow.ponudba').fetchall()
        reject(db, 'select quoteflow_private.poslji_ponudbo(%s)', (quote,))
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s)', (quote,))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'ponudba'
    with as_user(db, users['customer']):
        assert [r['id'] for r in db.execute('select id from quoteflow.ponudba')] == [quote]
    with as_user(db, users['outsider']):
        assert not db.execute('select id from quoteflow.ponudba').fetchall()
        reject(db, 'select quoteflow_private.odgovori_ponudbo(%s,true)', (quote,))
    for sql, args in [
        ('update quoteflow.postavka_ponudbe set cena_na_enoto=999 where id=%s', (line,)),
        ('delete from quoteflow.material_ponudbe where postavka_ponudbe_id=%s', (line,)),
        ('delete from quoteflow.ponudba where id=%s', (quote,)),
    ]:
        reject(db, sql, args)
    # Updating the reusable source must not rewrite a sent document.
    db.execute('update quoteflow.postavka_cenika set cena_na_enoto=999 where id=%s', (catalog[0][2],))
    assert str(db.execute('select cena_na_enoto from quoteflow.postavka_ponudbe where id=%s', (line,)).fetchone()['cena_na_enoto']) == '25.0000'


@LOCAL
def test_sprejem_racun_termin_izvedba_in_placilo_so_povezani(db, identities, catalog, offer):
    users, _, _, _ = identities
    project, quote, _ = offer
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s)', (quote,))
    with as_user(db, users['customer']):
        db.execute('select quoteflow_private.odgovori_ponudbo(%s,true)', (quote,))
    invoice = db.execute('select * from quoteflow.racun where ponudba_id=%s', (quote,)).fetchone()
    assert invoice['stanje_dokumenta'] == 'osnutek' and invoice['placano_ob'] is None
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'termin'
    reject(db, 'update quoteflow.racun set placano_ob=now() where id=%s', (invoice['id'],))
    with as_user(db, users['owner_b']):
        reject(db, "select quoteflow_private.doloci_termin(%s,now()+interval '1 day',now()+interval '2 days')", (project,))
    with as_user(db, users['owner_a']):
        db.execute("select quoteflow_private.doloci_termin(%s,now()+interval '1 day',now()+interval '2 days')", (project,))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'izvedba'
    # Marking completed work is company-only; invoice issue/send then permits billing.
    db.execute('update quoteflow.projekt set izvedba_koncana_ob=now() where id=%s', (project,))
    with as_user(db, users['owner_a']):
        db.execute("select quoteflow_private.izdaj_racun(%s,'R-1','Stranka','Naslov 2',current_date+14)", (invoice['id'],))
    assert db.execute('select faza from quoteflow.projekt where id=%s', (project,)).fetchone()['faza'] == 'obracun'
    reject(db, "update quoteflow.racun set prejemnik_naziv='Spremenjeno' where id=%s", (invoice['id'],))
    with as_user(db, users['customer']):
        reject(db, 'select quoteflow_private.placaj_racun(%s)', (invoice['id'],))
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.placaj_racun(%s)', (invoice['id'],))
    assert db.execute('select placano_ob from quoteflow.racun where id=%s', (invoice['id'],)).fetchone()['placano_ob']
    closed = db.execute('select faza,zakljuceno_ob from quoteflow.projekt where id=%s', (project,)).fetchone()
    assert closed['faza'] == 'zakljucen' and closed['zakljuceno_ob']


@LOCAL
def test_prazna_ponudba_in_poljuben_preskok_faze_nista_dovoljena(db, identities, offer):
    users, _, _, _ = identities
    project, quote, _ = offer
    empty = db.execute("insert into quoteflow.ponudba(projekt_id,stevilka,razlicica) values(%s,'P-1',2) returning id", (project,)).fetchone()['id']
    with as_user(db, users['owner_a']):
        reject(db, 'select quoteflow_private.poslji_ponudbo(%s)', (empty,))
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
    users, _, _, _ = identities
    _, quote, _ = offer
    with as_user(db, users['owner_a']):
        db.execute('select quoteflow_private.poslji_ponudbo(%s)', (quote,))
        reject(db, 'select quoteflow_private.odgovori_ponudbo(%s,true)', (quote,))
    with as_user(db, users['customer']):
        db.execute('select quoteflow_private.odgovori_ponudbo(%s,false)', (quote,))
    assert db.execute('select stanje from quoteflow.ponudba where id=%s', (quote,)).fetchone()['stanje'] == 'zavrnjena'
    assert not db.execute('select * from quoteflow.racun where ponudba_id=%s', (quote,)).fetchall()
