"""Shared helpers for the quote-flow database tests (model v3). Quotes are built the v3 way: project items + izmere through the guarded functions, a header-only draft (ustvari_ponudbo) and poslji_ponudbo (snapshot).
Contract used (named arguments): shrani_postavko_projekta(podjetje,projekt,postavka,vrsta_dela,naziv,opis,enota,cena,kolicina,popust,stopnja_ddv,urna_postavka,stevilo_ur,stevilo_delavcev) ·
shrani_izmero(podjetje,projekt,postavka,izmera,odstej,kosi,dolzina,visina,sirina) · ustvari_ponudbo(podjetje,projekt,velja_do) · poslji_ponudbo(podjetje,projekt,ponudba) · odgovori_ponudbo(projekt,ponudba,sprejmi).
One default item (1 m2 x 2 x 100 EUR, popust 10 %, DDV 22 %, no labour) gives 180,00 / 39,60 / 219,60, as the old manual line did."""
from datetime import timedelta
from decimal import Decimal as D
import psycopg
import pytest
from test_model_database import db, identities, as_user, catalog, vrsta_of  # noqa: F401

Q = 'quoteflow_private.'
DEFAULT = 'current_date+10'
LJ = "(now() at time zone 'Europe/Ljubljana')::date"


def fails(db, sql, args, state):
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): db.execute(sql, args)
    assert e.value.sqlstate == state, e.value.sqlstate


def stmt(name, args, kw):
    parts = ['%s'] * len(args) + [f'{k} => %s' for k in kw]
    return f"select * from {Q}{name}({','.join(parts)})", (*args, *kw.values())


def call(db, users, who, name, *args, **kw):
    s, a = stmt(name, args, kw)
    with as_user(db, users[who]): return db.execute(s, a).fetchone()


def bad(db, users, who, state, name, *args, **kw):
    s, a = stmt(name, args, kw)
    with as_user(db, users[who]): fails(db, s, a, state)


def quiet(db, table, sql, args=()):
    db.execute('set constraints all immediate'); db.execute(f'alter table quoteflow.{table} disable trigger user'); db.execute(sql, args)
    db.execute(f'alter table quoteflow.{table} enable trigger user'); db.execute('set constraints all deferred')


def P(db, q):
    r = db.execute('select projekt_id from quoteflow.ponudba where id=%s', (q,)).fetchone(); return r['projekt_id'] if r else None


def year(db): return db.execute("select extract(year from (now() at time zone 'Europe/Ljubljana'))::int as y").fetchone()['y']


def new_project(db, users, company, customer='customer', faza='pregled'):
    return db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (company, users[customer][0])).fetchone()['id']


def company_of(db, p): return db.execute('select podjetje_id as c from quoteflow.projekt where id=%s', (p,)).fetchone()['c']


def owner_of(db, company):
    r = db.execute('select p.lastnik_id as u, (select id from auth.sessions where user_id=p.lastnik_id limit 1) as s from quoteflow.podjetje p where p.id=%s', (company,)).fetchone()
    return r['u'], r['s']


def as_owner(db, company, name, **kw):
    s, a = stmt(name, (), kw)
    with as_user(db, owner_of(db, company)): return db.execute(s, a).fetchone()


def vrsta(db, company):
    """Any vrsta dela of the company; created without labour when the company has none."""
    r = db.execute('select id from quoteflow.vrsta_dela where podjetje_id=%s order by naziv limit 1', (company,)).fetchone()
    if r: return r['id']
    return as_owner(db, company, 'shrani_vrsto_dela', podjetje=company, vrsta=None, naziv='Gradnja', opis='', urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1, aktivna=True)['id']


def add_item(db, p, price=D(100), qty=D(2), discount=D('0.1'), vat=D('0.22'), naziv='Polaganje', opis='Keramika'):
    c = company_of(db, p)
    it = as_owner(db, c, 'shrani_postavko_projekta', podjetje=c, projekt=p, postavka=None, vrsta_dela=vrsta(db, c), naziv=naziv, opis=opis, enota='m2', cena=price, kolicina=qty, popust=discount, stopnja_ddv=vat,
                  urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1)['id']
    as_owner(db, c, 'shrani_izmero', podjetje=c, projekt=p, postavka=it, izmera=None, odstej=False, kosi=D(1), dolzina=D(1), visina=D(1), sirina=None)
    return it


def raw_quote(db, p, n=1, velja=DEFAULT, lines=1, price=D(100), qty=D(2), discount=D('0.1'), vat=D('0.22')):
    """Header-only draft of the project. The project gets `lines` default items when it has none yet; `n` is informative only (the version number is assigned by ustvari_ponudbo)."""
    c = company_of(db, p)
    if lines and not db.execute('select 1 from quoteflow.postavka_projekta where projekt_id=%s', (p,)).fetchone():
        for i in range(lines): add_item(db, p, price, qty, discount, vat)
    q = as_owner(db, c, 'ustvari_ponudbo', podjetje=c, projekt=p, velja_do=db.execute('select current_date+10 as d').fetchone()['d'])['id']
    if velja != DEFAULT: quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={velja} where id=%s', (q,))
    return q


def send(db, users, a, q, who='owner_a'): return call(db, users, who, 'poslji_ponudbo', a, P(db, q), q)
def decide(db, users, p, q, accept, who='customer'): return call(db, users, who, 'odgovori_ponudbo', p, q, accept)
def sent(db, users, a, p, **kw): q = raw_quote(db, p, **kw); send(db, users, a, q); return q
def draft(db, users, a, p, who='owner_a'): return call(db, users, who, 'ustvari_ponudbo', a, p, None)['id']
def lines(db, q): return db.execute('select * from quoteflow.postavka_ponudbe where ponudba_id=%s order by zaporedje', (q,)).fetchall()


def accepted(db, p, a=None, number=None):
    """End state of US-05 reached through the real v3 functions (items, draft, poslji_ponudbo, odgovori_ponudbo): sprejeta ponudba, racun osnutek, faza termin. `number` is ignored (numbers are generated)."""
    c = company_of(db, p); q = raw_quote(db, p)
    with as_user(db, owner_of(db, c)): db.execute(f'select * from {Q}poslji_ponudbo(%s,%s,%s)', (c, p, q))
    cust = db.execute('select s.user_id as u, s.id as s from quoteflow.projekt pr join auth.sessions s on s.user_id=pr.stranka_id where pr.id=%s limit 1', (p,)).fetchone()
    with as_user(db, (cust['u'], cust['s'])): db.execute(f'select * from {Q}odgovori_ponudbo(%s,%s,true)', (p, q))
    return q, db.execute('select id from quoteflow.racun where ponudba_id=%s', (q,)).fetchone()['id']


@pytest.fixture
def env(db, identities, catalog):
    users, a, b, _ = identities
    return users, a, b, new_project(db, users, a), catalog
