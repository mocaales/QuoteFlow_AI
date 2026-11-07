"""M5: sočasnost pisanja postavk/izmer, pošiljanja in delavcev. Dve resnični povezavi s commitom na disposable LOCAL Supabase;
fixture mora na koncu pustiti 0 vrstic (truncate vseh tabel quoteflow in quoteflow_private + brisanje svojih auth zapisov)."""
import json
import os
import threading
import time
from datetime import timedelta
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from test_model_database import as_user
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
VRSTA = dict(vrsta=None, naziv='Polaganje', opis='', urna_postavka=D(25), stevilo_ur=D(8), stevilo_delavcev=2, aktivna=True)


def stmt(name, kw): return f"select * from {Q}{name}({','.join(f'{k} => %s' for k in kw)})", tuple(kw.values())


def counts(admin):
    tables = [f'{r["schemaname"]}.{r["tablename"]}' for r in admin.execute("select schemaname,tablename from pg_tables where schemaname in ('quoteflow','quoteflow_private') order by 1,2")]
    return tables, {t: admin.execute(f'select count(*) as n from {t}').fetchone()['n'] for t in tables} | {'auth.users': admin.execute('select count(*) as n from auth.users').fetchone()['n'], 'auth.sessions': admin.execute('select count(*) as n from auth.sessions').fetchone()['n']}


@pytest.fixture
def live():
    url = os.environ['TEST_DATABASE_URL']; assert conninfo_to_dict(url)['host'] in ('localhost', '127.0.0.1'), 'Never test a remote database'
    admin = psycopg.connect(url, autocommit=True, row_factory=dict_row); tables, before = counts(admin)
    if any(before.values()): admin.close(); pytest.skip('Race tests need an empty disposable database: ' + str({k: v for k, v in before.items() if v}))
    ids = []
    def person(name):
        uid, sid = uuid4(), uuid4(); ids.append(uid)
        admin.execute('insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at) values(%s,%s,%s::jsonb,now())', (uid, f'{name}-{uid}@example.test', json.dumps({'ime': 'Ime', 'priimek': name})))
        admin.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid)); return uid, sid
    try:
        owner, customer, worker = person('owner'), person('customer'), person('worker')
        with admin.transaction():
            company = admin.execute("insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(%s,'Race',%s,'Naslov 1','SI12345678') returning id", (owner[0], uuid4().hex[:30])).fetchone()['id']
            admin.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (owner[0], company))
            proj = admin.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (company, customer[0])).fetchone()['id']
        env = dict(url=url, admin=admin, owner=owner, customer=customer, worker=worker, a=company, p=proj, today=admin.execute('select quoteflow_private.danes() as d').fetchone()['d'],
                   worker_mail=admin.execute('select e_posta from quoteflow.uporabnik where id=%s', (worker[0],)).fetchone()['e_posta'])
        yield env
    finally:
        admin.execute('truncate table ' + ','.join(tables) + ' cascade')
        admin.execute('delete from auth.sessions where user_id = any(%s)', (ids,)); admin.execute('delete from auth.users where id = any(%s)', (ids,))
        _, after = counts(admin); admin.close()
        assert after == before, 'cleanup left rows: ' + str({k: v for k, v in after.items() if v})


def run(env, who, name, **kw):
    with psycopg.connect(env['url'], row_factory=dict_row) as c:
        with as_user(c, env[who]): return c.execute(*stmt(name, kw)).fetchone()


class Open:
    """A transaction that stays open (holding its locks) until commit."""
    def __init__(s, env, who):
        s.c = psycopg.connect(env['url'], row_factory=dict_row); s.cm = as_user(s.c, env[who]); s.cm.__enter__()
    def call(s, name, **kw): return s.c.execute(*stmt(name, kw)).fetchone()
    def commit(s): s.cm.__exit__(None, None, None); s.c.commit()
    def close(s): s.c.rollback(); s.c.close()


class Later(threading.Thread):
    def __init__(s, env, who, name, **kw):
        super().__init__(daemon=True); s.env, s.who, s.name_, s.kw, s.pid, s.result, s.error, s.started = env, who, name, kw, None, None, None, threading.Event()
    def run(s):
        try:
            with psycopg.connect(s.env['url'], row_factory=dict_row) as c:
                s.pid = c.info.backend_pid; c.execute("set statement_timeout='20s'"); s.started.set()
                with as_user(c, s.env[s.who]): s.result = c.execute(*stmt(s.name_, s.kw)).fetchone()
        except psycopg.Error as err: s.error = err
        finally: s.started.set()


def blocked(env, later, seconds=8.0):
    later.started.wait(5); end = time.time() + seconds
    while time.time() < end and later.is_alive():
        row = env['admin'].execute("select wait_event_type from pg_stat_activity where pid=%s", (later.pid,)).fetchone()
        if row and row['wait_event_type'] == 'Lock': return True
        time.sleep(0.05)
    return False


def race(env, first, second, then=None):
    """first holds its locks uncommitted; second must wait on them; then first commits and second finishes."""
    try:
        later = second; later.start()
        assert blocked(env, later), 'druga povezava ni počakala na zaklep prve (ni serializacije podjetje -> projekt)'
        first.commit(); later.join(25); assert not later.is_alive(), 'druga povezava se ni končala po commitu'
        return later
    finally: first.close()


def item(env, unit='kos', **o):
    kw = dict(podjetje=env['a'], projekt=env['p'], postavka=None, vrsta_dela=env['vrsta'], naziv='Postavka', opis='', enota=unit, cena=D(10), kolicina=D(1), popust=D(0), stopnja_ddv=D('0.22'), urna_postavka=None, stevilo_ur=None, stevilo_delavcev=None) | o
    return run(env, 'owner', 'shrani_postavko_projekta', **kw)['id']


def meas_kw(env, it, **o): return dict(podjetje=env['a'], projekt=env['p'], postavka=it, izmera=None, odstej=False, kosi=D(1), dolzina=None, visina=None, sirina=None) | o


@pytest.fixture
def prepared(live):
    live['vrsta'] = run(live, 'owner', 'shrani_vrsto_dela', podjetje=live['a'], **VRSTA)['id']
    live['item'] = item(live); run(live, 'owner', 'shrani_izmero', **meas_kw(live, live['item'], kosi=D(10)))
    return live


def total(env, it): return env['admin'].execute('select izmera_skupaj as s from quoteflow.postavka_projekta where id=%s', (it,)).fetchone()['s']


def new_draft(env): return run(env, 'owner', 'ustvari_ponudbo', podjetje=env['a'], projekt=env['p'], velja_do=env['today'] + timedelta(days=10))['id']


def test_pisanje_izmere_pocaka_pri_posiljanju_in_posnetek_vsebuje_commitano_izmero(prepared):
    env = prepared; q = new_draft(env); a = Open(env, 'owner'); a.call('shrani_izmero', **meas_kw(env, env['item'], kosi=D(5)))
    b = race(env, a, Later(env, 'owner', 'poslji_ponudbo', podjetje=env['a'], projekt=env['p'], ponudba=q))
    assert b.error is None and b.result['stanje'] == 'poslana', b.error
    admin = env['admin']; snap = admin.execute('select izmera_skupaj as s, neto from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone()
    parts = admin.execute('select coalesce(sum(case when odstej then -vrednost else vrednost end),0) as s from quoteflow.izmera_ponudbe where postavka_ponudbe_id in (select id from quoteflow.postavka_ponudbe where ponudba_id=%s)', (q,)).fetchone()['s']
    assert snap['s'] == parts == total(env, env['item']) == 15 and snap['neto'] == D('15') * 10 + D(400)


def test_posiljanje_pocaka_pisanje_izmere_in_posnetek_ne_vsebuje_poznejsega_pisanja(prepared):
    env = prepared; q = new_draft(env); a = Open(env, 'owner'); a.call('poslji_ponudbo', podjetje=env['a'], projekt=env['p'], ponudba=q)
    b = race(env, a, Later(env, 'owner', 'shrani_izmero', **meas_kw(env, env['item'], kosi=D(5))))
    assert b.error is None, b.error
    admin = env['admin']; snap = admin.execute('select izmera_skupaj as s from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone()['s']
    assert snap == 10 and total(env, env['item']) == 15
    assert admin.execute('select count(*) as n from quoteflow.izmera_ponudbe where postavka_ponudbe_id in (select id from quoteflow.postavka_ponudbe where ponudba_id=%s)', (q,)).fetchone()['n'] == 1


def test_dve_sociasni_odstetni_izmeri_skupaj_ne_dasta_negativne_vsote_qfp25(prepared):
    env = prepared; a = Open(env, 'owner'); a.call('shrani_izmero', **meas_kw(env, env['item'], odstej=True, kosi=D(8)))
    b = race(env, a, Later(env, 'owner', 'shrani_izmero', **meas_kw(env, env['item'], odstej=True, kosi=D(8))))
    assert b.error is not None and b.error.sqlstate == 'QFP25', b.error
    admin = env['admin']; assert total(env, env['item']) == 2 and admin.execute('select count(*) as n from quoteflow.izmera where postavka_projekta_id=%s', (env['item'],)).fetchone()['n'] == 2


def test_dvojno_posiljanje_istega_osnutka_da_en_posnetek_in_qfp10(prepared):
    env = prepared; q = new_draft(env); a = Open(env, 'owner'); a.call('poslji_ponudbo', podjetje=env['a'], projekt=env['p'], ponudba=q)
    b = race(env, a, Later(env, 'owner', 'poslji_ponudbo', podjetje=env['a'], projekt=env['p'], ponudba=q))
    assert b.error is not None and b.error.sqlstate == 'QFP10', b.error
    admin = env['admin']; assert admin.execute('select count(*) as n from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,)).fetchone()['n'] == 1
    assert admin.execute("select count(*) as n from quoteflow_private.dogodek_dokumenta where ponudba_id=%s and dejanje='poslana'", (q,)).fetchone()['n'] == 1


def test_brisanje_postavke_med_posiljanjem_se_serializira(prepared):
    env = prepared; q = new_draft(env); a = Open(env, 'owner'); a.call('odstrani_postavko_projekta', podjetje=env['a'], projekt=env['p'], postavka=env['item'])
    b = race(env, a, Later(env, 'owner', 'poslji_ponudbo', podjetje=env['a'], projekt=env['p'], ponudba=q))
    assert b.error is not None and b.error.sqlstate == 'QFP13', b.error
    assert env['admin'].execute('select stanje from quoteflow.ponudba where id=%s', (q,)).fetchone()['stanje'] == 'osnutek'


def test_sociasno_vabljenje_istega_delavca_da_eno_odprto_povabilo_in_isti_id(live):
    env = live; a = Open(env, 'owner'); first = a.call('povabi_delavca', podjetje=env['a'], e_posta=env['worker_mail'])
    b = race(env, a, Later(env, 'owner', 'povabi_delavca', podjetje=env['a'], e_posta=' ' + env['worker_mail'].upper()))
    assert b.error is None and first['id'] is not None and b.result['id'] == first['id'], b.error
    assert env['admin'].execute("select count(*) as n from quoteflow_private.povabilo_delavca where podjetje_id=%s and stanje='povabljen'", (env['a'],)).fetchone()['n'] == 1
    assert env['admin'].execute("select count(*) as n from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga='delavec'", (env['worker'][0], env['a'])).fetchone()['n'] == 0
