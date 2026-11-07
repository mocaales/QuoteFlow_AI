"""US-08 z vabili (G6, ugotovitev 1) + admin 'Podjetja in pravice' (ugotovitve 2, 3, 4, 11) na disposable local Supabase.
Pogodba: povabi_delavca(podjetje,e_posta) -> (id,e_posta,stanje,poslano_ob), enako za vsak naslov (22023 za neveljavno obliko, QFP30 20/uro/podjetje
in 50/dan/mojster) · povabila_podjetja(podjetje) · preklici_povabilo(podjetje,povabilo) · moja_povabila() · odgovori_povabilo(povabilo,sprejmi) -> (id,stanje),
neprimerno QFP34 · uredi_delavca / delavci_podjetja · dodeli_vlogo / aktiviraj_vlogo samo za skrbnika · quoteflow_private.povabilo_delavca,
poskus_delavca(podjetje_id,uporabnik_id,ob), dogodek_vloge(...,dejanje,povabilo_id)."""
import json
import os
from datetime import timedelta
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
KEYS = {'id', 'uporabnik_id', 'e_posta', 'ime', 'priimek', 'aktivna', 'dodeljeno_ob'}
INVITE = {'id', 'e_posta', 'stanje', 'poslano_ob'}
LISTED = INVITE | {'odloceno_ob'}
MINE = {'id', 'podjetje_id', 'podjetje_naziv', 'povabil', 'poslano_ob'}
REFUSED = {'42501', '23514', 'QFP22'}
NEW = ('povabi_delavca', 'povabila_podjetja', 'preklici_povabilo', 'moja_povabila', 'odgovori_povabilo')


def stmt(name, kw): return f"select * from {Q}{name}({','.join(f'{k} => %s' for k in kw)})", tuple(kw.values())


def fails(db, sql, args, state):
    states = {state} if isinstance(state, str) else set(state)
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): db.execute(sql, args)
    assert e.value.sqlstate in states, f'{e.value.sqlstate}: {e.value}'
    return e.value


def call(db, users, who, name, **kw):
    s, a = stmt(name, kw)
    with as_user(db, users[who]): return db.execute(s, a).fetchone()


def rows(db, users, who, name, **kw):
    s, a = stmt(name, kw)
    with as_user(db, users[who]): return db.execute(s, a).fetchall()


def bad(db, users, who, state, name, **kw):
    s, a = stmt(name, kw)
    with as_user(db, users[who]): return fails(db, s, a, state)


def mail(db, users, who): return db.execute('select e_posta from quoteflow.uporabnik where id=%s', (users[who][0],)).fetchone()['e_posta']
def invite(db, users, who, company, email): return call(db, users, who, 'povabi_delavca', podjetje=company, e_posta=email)
def answer(db, users, who, pid, yes=True): return call(db, users, who, 'odgovori_povabilo', povabilo=pid, sprejmi=yes)
def roles(db, uid, company, vloga='delavec'): return db.execute('select * from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga=%s', (uid, company, vloga)).fetchall()
def all_roles(db): return db.execute('select id,aktivna from quoteflow.vloga_uporabnika order by id').fetchall()
def attempts(db, company): return db.execute("select count(*) as n from quoteflow_private.poskus_delavca where podjetje_id=%s and ob>now()-interval '1 hour'", (company,)).fetchone()['n']
def stored(db, pid): return db.execute('select * from quoteflow_private.povabilo_delavca where id=%s', (pid,)).fetchone()
def audit(db, **w): return db.execute('select * from quoteflow_private.dogodek_vloge where ' + ' and '.join(f'{k}=%s' for k in w) + ' order by ob', tuple(w.values())).fetchall()
def member(db, users, who, company):
    with as_user(db, users[who]): return db.execute("select quoteflow_private.clan(%s,'delavec') as y", (company,)).fetchone()['y']


def make_user(db, confirmed=True, name='extra'):
    uid, sid = uuid4(), uuid4()
    db.execute("insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at) values(%s,%s,%s::jsonb,case when %s then now() end)", (uid, f'{name}-{uid}@example.test', json.dumps({'ime': 'N', 'priimek': 'P'}), confirmed))
    db.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid))
    return (uid, sid), db.execute('select e_posta from quoteflow.uporabnik where id=%s', (uid,)).fetchone()['e_posta']


def quiet(db, table, sql, args=()):
    db.execute('set constraints all immediate'); db.execute(f'alter table quoteflow.{table} disable trigger user'); db.execute(sql, args)
    db.execute(f'alter table quoteflow.{table} enable trigger user'); db.execute('set constraints all deferred')


def project(db, users, company, who='customer'):
    return db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Prenova','Opis','Maribor') returning id", (company, users[who][0])).fetchone()['id']


def close(db, p): quiet(db, 'projekt', "update quoteflow.projekt set faza='zakljucen', zakljuceno_ob=now() where id=%s", (p,))
def age(db, pid, days): db.execute('update quoteflow_private.povabilo_delavca set poslano_ob=poslano_ob-make_interval(days=>%s) where id=%s', (days, pid))
def role_id(db, uid, company, vloga): return roles(db, uid, company, vloga)[0]['id'] if company else db.execute('select id from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga=%s and podjetje_id is null', (uid, vloga)).fetchone()['id']


def company_of(db, users, who, label):
    c = db.execute("insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(%s,%s,%s,'Naslov 1','SI12345678') returning id", (users[who][0], label, uuid4().hex[:30])).fetchone()['id']
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (users[who][0], c)); return c


# --- povabi_delavca: identičen odgovor, brez vloge, brez razkrivanja uporabnika (ugotovitev 1, A1)
def test_povabi_delavca_vrne_natancne_kljuce_ne_ustvari_vloge_in_zabelezi_povabljen(db, identities):
    users, a, _, _ = identities; before = all_roles(db); r = invite(db, users, 'owner_a', a, '  ' + mail(db, users, 'outsider').upper() + ' \n')
    assert set(r) == INVITE and (r['e_posta'], r['stanje']) == (mail(db, users, 'outsider'), 'povabljen') and r['id'] and r['poslano_ob']
    assert all_roles(db) == before and not member(db, users, 'outsider', a)
    row = stored(db, r['id']); assert (row['podjetje_id'], row['povabil_id'], row['stanje'], row['odloceno_ob'], row['vloga_id']) == (a, users['owner_a'][0], 'povabljen', None, None)
    (ev,) = audit(db, povabilo_id=r['id'])
    assert (ev['dejanje'], ev['izvajalec_id'], ev['uporabnik_id'], ev['podjetje_id'], ev['vloga'], ev['aktivna_prej'], ev['aktivna_potem']) == ('povabljen', users['owner_a'][0], None, a, 'delavec', None, None)


def target(db, users, a, case):
    if case == 'obstojec': return mail(db, users, 'outsider')
    if case == 'neznan': return f'neznan-{uuid4()}@example.test'
    if case == 'nepotrjen': return make_user(db, confirmed=False)[1]
    if case == 'skrbnik': return mail(db, users, 'admin')
    if case == 'skrbnik_veliko': return mail(db, users, 'admin').upper()
    if case == 'sam': return mail(db, users, 'owner_a')
    if case == 'neaktivna_stranka':
        db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['outsider'][0],)); return mail(db, users, 'outsider')
    if case == 'stranka_odprtega_projekta': project(db, users, a); return mail(db, users, 'customer')
    raise AssertionError(case)


@pytest.mark.parametrize('case', ['obstojec', 'neznan', 'nepotrjen', 'skrbnik', 'skrbnik_veliko', 'sam', 'neaktivna_stranka', 'stranka_odprtega_projekta'])
def test_povabilo_je_enako_za_vsak_naslov_brez_spremembe_vlog(db, identities, case):
    users, a, _, _ = identities; ref = invite(db, users, 'owner_a', a, f'ref-{uuid4()}@example.test'); email = target(db, users, a, case); before = all_roles(db)
    r = invite(db, users, 'owner_a', a, email)
    assert set(r) == INVITE and r['stanje'] == ref['stanje'] == 'povabljen' and r['e_posta'] == email.strip().lower() and r['id'] != ref['id']
    assert {k: type(v) for k, v in r.items()} == {k: type(v) for k, v in ref.items()} and r['poslano_ob'] == ref['poslano_ob']
    assert all_roles(db) == before and attempts(db, a) == 2
    (ev,) = audit(db, povabilo_id=r['id']); assert ev['dejanje'] == 'povabljen' and ev['uporabnik_id'] is None


@pytest.mark.parametrize('email', ['   ', '', 'brez-afne', 'a@b', 'x' * 400 + '@example.test', 'dva@@example.test', 'pre slednji@example.test'])
def test_neveljavna_oblika_e_poste_22023(db, identities, email):
    users, a, _, _ = identities
    bad(db, users, 'owner_a', '22023', 'povabi_delavca', podjetje=a, e_posta=email)
    assert not db.execute('select 1 from quoteflow_private.povabilo_delavca where podjetje_id=%s', (a,)).fetchall()
    bad(db, users, 'owner_a', '22023', 'povabi_delavca', podjetje=a, e_posta=None)


def test_ponovno_povabilo_vrne_isto_odprto_povabilo_brez_nove_revizije(db, identities):
    users, a, b, _ = identities; email = mail(db, users, 'outsider'); first = invite(db, users, 'owner_a', a, email)
    again = invite(db, users, 'owner_a', a, ' ' + email.upper()); assert again == first and attempts(db, a) == 2
    assert db.execute("select count(*) as n from quoteflow_private.povabilo_delavca where podjetje_id=%s and stanje='povabljen'", (a,)).fetchone()['n'] == 1 and len(audit(db, podjetje_id=a, dejanje='povabljen')) == 1
    other = invite(db, users, 'owner_b', b, email); assert other['id'] != first['id']


def test_poteklo_odprto_povabilo_se_zapise_kot_poteklo_in_nastane_novo(db, identities):
    users, a, _, _ = identities; email = mail(db, users, 'outsider'); first = invite(db, users, 'owner_a', a, email); age(db, first['id'], 15)
    second = invite(db, users, 'owner_a', a, email); assert second['id'] != first['id'] and second['stanje'] == 'povabljen'
    old = stored(db, first['id']); assert old['stanje'] == 'poteklo' and old['odloceno_ob'] == db.execute('select quoteflow_private.povabilo_potece(%s) as t', (old['poslano_ob'],)).fetchone()['t']
    assert old['odloceno_ob'] - old['poslano_ob'] in (timedelta(days=14), timedelta(days=14, hours=1), timedelta(days=13, hours=23))


def test_rok_poteka_je_14_dni_po_ljubljanskem_koledarju(db):
    t = db.execute("select quoteflow_private.povabilo_potece('2026-10-20 10:00+02') as a, quoteflow_private.povabilo_potece('2026-03-20 10:00+01') as b").fetchone()
    assert t['a'] == db.execute("select '2026-11-03 10:00+01'::timestamptz as t").fetchone()['t'] and t['b'] == db.execute("select '2026-04-03 10:00+02'::timestamptz as t").fetchone()['t']


def test_omejitev_20_na_uro_na_podjetje_vkljucno_s_ponovnimi_qfp30(db, identities):
    users, a, b, _ = identities; email = mail(db, users, 'outsider')
    for i in range(18): invite(db, users, 'owner_a', a, f'neznan-{i}-{uuid4()}@example.test')
    invite(db, users, 'owner_a', a, email); invite(db, users, 'owner_a', a, email); assert attempts(db, a) == 20
    bad(db, users, 'owner_a', 'QFP30', 'povabi_delavca', podjetje=a, e_posta=email); bad(db, users, 'owner_a', 'QFP30', 'povabi_delavca', podjetje=a, e_posta=f'neznan-{uuid4()}@example.test')
    assert invite(db, users, 'owner_b', b, email)['id'] and attempts(db, b) == 1 and attempts(db, a) == 20
    db.execute("update quoteflow_private.poskus_delavca set ob=now()-interval '2 hours' where podjetje_id=%s", (a,))
    assert invite(db, users, 'owner_a', a, email)['id'] and attempts(db, a) == 1


def test_omejitev_50_na_dan_na_mojstra_cez_podjetja_qfp30(db, identities):
    users, a, b, _ = identities; extra = [company_of(db, users, 'owner_a', f'A{i}') for i in range(3)]
    for c, n in ((a, 20), (extra[0], 20), (extra[1], 10)):
        for i in range(n): invite(db, users, 'owner_a', c, f'n-{i}-{uuid4()}@example.test')
    assert db.execute('select count(*) as n from quoteflow_private.poskus_delavca where uporabnik_id=%s', (users['owner_a'][0],)).fetchone()['n'] == 50
    bad(db, users, 'owner_a', 'QFP30', 'povabi_delavca', podjetje=extra[2], e_posta=f'n-{uuid4()}@example.test'); assert attempts(db, extra[2]) == 0
    assert invite(db, users, 'owner_b', b, f'n-{uuid4()}@example.test')['id']
    db.execute("update quoteflow_private.poskus_delavca set ob=now()-interval '25 hours' where uporabnik_id=%s", (users['owner_a'][0],))
    assert invite(db, users, 'owner_a', extra[2], f'n-{uuid4()}@example.test')['id']
    assert db.execute('select count(*) as n from quoteflow_private.poskus_delavca where uporabnik_id=%s', (users['owner_a'][0],)).fetchone()['n'] == 1, 'stari poskusi se pobrišejo'


@pytest.mark.parametrize('who', ['worker', 'customer', 'outsider', 'admin', 'owner_b'])
def test_vabiti_seznam_in_preklic_samo_mojster_tega_podjetja_42501(db, identities, who):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, f'x-{uuid4()}@example.test')['id']; before = attempts(db, a)
    bad(db, users, who, '42501', 'povabi_delavca', podjetje=a, e_posta=mail(db, users, 'outsider')); bad(db, users, who, '42501', 'povabila_podjetja', podjetje=a)
    bad(db, users, who, '42501', 'preklici_povabilo', podjetje=a, povabilo=pid)
    assert attempts(db, a) == before and stored(db, pid)['stanje'] == 'povabljen' and not db.execute('select 1 from quoteflow_private.poskus_delavca where uporabnik_id=%s', (users[who][0],)).fetchall()


def test_odvzeti_mojster_ne_more_vabiti_ali_urejati_a7(db, identities):
    users, a, _, _ = identities
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster')", (users['worker'][0], a))
    pid = invite(db, users, 'worker', a, mail(db, users, 'outsider'))['id']
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='mojster'", (users['worker'][0],))
    bad(db, users, 'worker', '42501', 'povabi_delavca', podjetje=a, e_posta=mail(db, users, 'customer')); bad(db, users, 'worker', '42501', 'uredi_delavca', podjetje=a, vloga=uuid4(), aktivna=False)
    bad(db, users, 'worker', '42501', 'delavci_podjetja', podjetje=a); bad(db, users, 'worker', '42501', 'povabila_podjetja', podjetje=a); bad(db, users, 'worker', '42501', 'preklici_povabilo', podjetje=a, povabilo=pid)


# --- povabila_podjetja
def test_seznam_povabil_natancni_kljuci_samo_svoje_podjetje_poteklo_in_30_dni(db, identities):
    users, a, b, _ = identities; mk = lambda: invite(db, users, 'owner_a', a, f'p-{uuid4()}@example.test')['id']
    open_, expired, old_expired, recent, old = mk(), mk(), mk(), mk(), mk(); foreign = invite(db, users, 'owner_b', b, f'p-{uuid4()}@example.test')['id']
    age(db, expired, 15); age(db, old_expired, 50)
    db.execute("update quoteflow_private.povabilo_delavca set stanje='preklicano', odloceno_ob=now()-interval '29 days' where id=%s", (recent,))
    db.execute("update quoteflow_private.povabilo_delavca set stanje='zavrnjeno', odloceno_ob=now()-interval '31 days' where id=%s", (old,))
    got = rows(db, users, 'owner_a', 'povabila_podjetja', podjetje=a); by = {r['id']: r for r in got}
    assert all(set(r) == LISTED for r in got) and set(by) == {open_, expired, recent} and foreign not in by
    assert (by[open_]['stanje'], by[open_]['odloceno_ob']) == ('povabljen', None) and by[recent]['stanje'] == 'preklicano'
    assert by[expired]['stanje'] == 'poteklo' and by[expired]['odloceno_ob'] == db.execute('select quoteflow_private.povabilo_potece(%s) as t', (by[expired]['poslano_ob'],)).fetchone()['t']
    assert stored(db, expired)['stanje'] == 'povabljen', 'bralec ne spreminja vrstice'
    assert [r['poslano_ob'] for r in got] == sorted((r['poslano_ob'] for r in got), reverse=True)
    assert [r['id'] for r in rows(db, users, 'owner_b', 'povabila_podjetja', podjetje=b)] == [foreign]


# --- preklici_povabilo
def test_preklic_deluje_enkrat_tuje_neznano_odloceno_in_poteklo_je_p0002(db, identities):
    users, a, b, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']
    r = call(db, users, 'owner_a', 'preklici_povabilo', podjetje=a, povabilo=pid); assert set(r) == LISTED and r['id'] == pid and r['stanje'] == 'preklicano' and r['odloceno_ob']
    (ev,) = audit(db, povabilo_id=pid, dejanje='preklicano'); assert (ev['izvajalec_id'], ev['uporabnik_id'], ev['podjetje_id']) == (users['owner_a'][0], None, a)
    foreign = invite(db, users, 'owner_b', b, mail(db, users, 'outsider'))['id']; expired = invite(db, users, 'owner_a', a, f'e-{uuid4()}@example.test')['id']; age(db, expired, 15)
    ref = bad(db, users, 'owner_a', 'P0002', 'preklici_povabilo', podjetje=a, povabilo=uuid4())
    for x in (pid, foreign, expired): assert bad(db, users, 'owner_a', 'P0002', 'preklici_povabilo', podjetje=a, povabilo=x).diag.message_primary == ref.diag.message_primary
    assert stored(db, foreign)['stanje'] == 'povabljen' and stored(db, expired)['stanje'] == 'povabljen' and not member(db, users, 'outsider', a)
    assert answer(db, users, 'outsider', foreign, False)['stanje'] == 'zavrnjeno'; bad(db, users, 'owner_b', 'P0002', 'preklici_povabilo', podjetje=b, povabilo=foreign)


# --- moja_povabila
def test_moja_povabila_vidi_samo_povabljenec_s_potrjenim_naslovom(db, identities):
    users, a, b, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider').upper())['id']
    (r,) = rows(db, users, 'outsider', 'moja_povabila')
    assert set(r) == MINE and (r['id'], r['podjetje_id'], r['podjetje_naziv'], r['povabil']) == (pid, a, 'A', 'Ime Priimek') and r['poslano_ob']
    for who in ('customer', 'owner_a', 'admin', 'worker'): assert rows(db, users, who, 'moja_povabila') == [], who
    who, email = make_user(db, confirmed=False); invite(db, users, 'owner_a', a, email); users['nepotrjen'] = who
    assert rows(db, users, 'nepotrjen', 'moja_povabila') == []
    db.execute('update auth.users set email_confirmed_at=now() where id=%s', (who[0],)); assert len(rows(db, users, 'nepotrjen', 'moja_povabila')) == 1


def test_moja_povabila_skrije_neaktivno_podjetje_poteklo_in_odloceno(db, identities):
    users, a, b, _ = identities; email = mail(db, users, 'outsider')
    pa = invite(db, users, 'owner_a', a, email)['id']; pb = invite(db, users, 'owner_b', b, email)['id']
    assert {r['id'] for r in rows(db, users, 'outsider', 'moja_povabila')} == {pa, pb}
    quiet(db, 'podjetje', 'update quoteflow.podjetje set aktivno=false where id=%s', (b,)); assert [r['id'] for r in rows(db, users, 'outsider', 'moja_povabila')] == [pa]
    age(db, pa, 15); assert rows(db, users, 'outsider', 'moja_povabila') == []
    quiet(db, 'podjetje', 'update quoteflow.podjetje set aktivno=true where id=%s', (b,)); answer(db, users, 'outsider', pb, False); assert rows(db, users, 'outsider', 'moja_povabila') == []


def test_moja_povabila_in_odgovor_zahtevata_aktivno_sejo(db, identities):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']
    users['brez_seje'] = (users['outsider'][0], uuid4())
    bad(db, users, 'brez_seje', '42501', 'moja_povabila'); bad(db, users, 'brez_seje', '42501', 'odgovori_povabilo', povabilo=pid, sprejmi=True)
    assert stored(db, pid)['stanje'] == 'povabljen'


# --- odgovori_povabilo
def test_sprejem_ustvari_vlogo_delavec_in_obe_revizijski_vrstici(db, identities):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']
    r = answer(db, users, 'outsider', pid); assert set(r) == {'id', 'stanje'} and (r['id'], r['stanje']) == (pid, 'sprejeto')
    (role,) = roles(db, users['outsider'][0], a); assert role['aktivna'] and member(db, users, 'outsider', a)
    row = stored(db, pid); assert (row['stanje'], row['vloga_id']) == ('sprejeto', role['id']) and row['odloceno_ob']
    (ev,) = audit(db, uporabnik_id=users['outsider'][0], podjetje_id=a, dejanje='vloga')
    assert (ev['izvajalec_id'], ev['vloga'], ev['aktivna_prej'], ev['aktivna_potem'], ev['povabilo_id']) == (users['outsider'][0], 'delavec', None, True, None)
    (ok,) = audit(db, povabilo_id=pid, dejanje='sprejeto'); assert (ok['izvajalec_id'], ok['uporabnik_id'], ok['podjetje_id']) == (users['outsider'][0], users['outsider'][0], a)
    assert rows(db, users, 'outsider', 'moja_povabila') == []
    bad(db, users, 'outsider', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=True); bad(db, users, 'outsider', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=False)


def test_sprejem_ponovno_aktivira_obstojeco_vrstico_delavca(db, identities):
    users, a, _, role = identities; call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False)
    pid = invite(db, users, 'owner_a', a, mail(db, users, 'worker'))['id']; answer(db, users, 'worker', pid)
    (r,) = roles(db, users['worker'][0], a); assert r['id'] == role and r['aktivna'] and stored(db, pid)['vloga_id'] == role
    assert [(x['aktivna_prej'], x['aktivna_potem']) for x in audit(db, uporabnik_id=users['worker'][0], podjetje_id=a, dejanje='vloga')][-1] == (False, True)


def test_zavrnitev_ne_ustvari_vloge(db, identities):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']
    assert answer(db, users, 'outsider', pid, False) == {'id': pid, 'stanje': 'zavrnjeno'} and not roles(db, users['outsider'][0], a) and stored(db, pid)['odloceno_ob']
    (ev,) = audit(db, povabilo_id=pid, dejanje='zavrnjeno'); assert (ev['izvajalec_id'], ev['uporabnik_id']) == (users['outsider'][0], users['outsider'][0])
    bad(db, users, 'outsider', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=True); assert not roles(db, users['outsider'][0], a)


def test_tuje_ali_neznano_povabilo_je_p0002_in_null_odgovor_22004(db, identities):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']
    ref = bad(db, users, 'customer', 'P0002', 'odgovori_povabilo', povabilo=uuid4(), sprejmi=True)
    for who in ('customer', 'owner_a', 'admin'): assert bad(db, users, who, 'P0002', 'odgovori_povabilo', povabilo=pid, sprejmi=True).diag.message_primary == ref.diag.message_primary
    bad(db, users, 'outsider', '22004', 'odgovori_povabilo', povabilo=pid, sprejmi=None)
    assert stored(db, pid)['stanje'] == 'povabljen' and not roles(db, users['outsider'][0], a)


def ineligible(db, users, a, pid, case):
    """Make the invitee (outsider, or a new user for 'nepotrjen'/'skrbnik') ineligible; returns the caller."""
    uid = users['outsider'][0]
    if case == 'skrbnik': db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'admin')", (uid,))
    elif case == 'neaktivna_stranka': db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (uid,))
    elif case == 'nepotrjen': db.execute('update auth.users set email_confirmed_at=null where id=%s', (uid,))
    elif case == 'stranka_odprtega_projekta': project(db, users, a, 'outsider')
    elif case == 'poteklo': age(db, pid, 15)
    elif case == 'neaktivno_podjetje': quiet(db, 'podjetje', 'update quoteflow.podjetje set aktivno=false where id=%s', (a,))
    else: raise AssertionError(case)


@pytest.mark.parametrize('case', ['skrbnik', 'neaktivna_stranka', 'nepotrjen', 'stranka_odprtega_projekta', 'poteklo', 'neaktivno_podjetje'])
def test_neprimeren_sprejem_je_qfp34_brez_vloge(db, identities, case):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']; ineligible(db, users, a, pid, case); before = all_roles(db)
    err = bad(db, users, 'outsider', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=True); assert err.diag.message_primary == 'Povabila ni mogoče sprejeti.'
    assert all_roles(db) == before and not roles(db, users['outsider'][0], a) and stored(db, pid)['stanje'] == 'povabljen'


@pytest.mark.parametrize('case', ['nepotrjen', 'poteklo'])
def test_zavrnitev_nepotrjenega_ali_poteklega_je_qfp34(db, identities, case):
    users, a, _, _ = identities; pid = invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id']; ineligible(db, users, a, pid, case)
    bad(db, users, 'outsider', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=False); assert stored(db, pid)['stanje'] == 'povabljen'


def test_neprimeren_lahko_zavrne_in_stranka_zakljucenega_ali_tujega_projekta_lahko_sprejme(db, identities):
    users, a, b, _ = identities; email = mail(db, users, 'customer'); project(db, users, b); p = project(db, users, a)
    pid = invite(db, users, 'owner_a', a, email)['id']; bad(db, users, 'customer', 'QFP34', 'odgovori_povabilo', povabilo=pid, sprejmi=True)
    close(db, p); assert answer(db, users, 'customer', pid)['stanje'] == 'sprejeto' and member(db, users, 'customer', a)
    pid2 = invite(db, users, 'owner_b', b, mail(db, users, 'outsider'))['id']; ineligible(db, users, b, pid2, 'stranka_odprtega_projekta')
    assert answer(db, users, 'outsider', pid2, False)['stanje'] == 'zavrnjeno'


# --- uredi_delavca (A5, A7, A3, A4, A9)
def test_uredi_delavca_odvzame_dostop_takoj_in_ga_vrne(db, identities):
    users, a, _, role = identities; assert member(db, users, 'worker', a)
    off = call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False); assert off['id'] == role and off['aktivna'] is False and not member(db, users, 'worker', a)
    on = call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=True); assert on['aktivna'] is True and member(db, users, 'worker', a)
    ev = audit(db, uporabnik_id=users['worker'][0], podjetje_id=a); assert [(x['dejanje'], x['izvajalec_id'], x['vloga'], x['aktivna_prej'], x['aktivna_potem']) for x in ev] == [('vloga', users['owner_a'][0], 'delavec', True, False), ('vloga', users['owner_a'][0], 'delavec', False, True)]


def test_uredi_tuji_mojstrski_skrbniski_stranski_in_nakljucni_id_je_enak_p0002(db, identities):
    users, a, b, _ = identities
    ids = {'delavec_b': role_id(db, users['owner_a'][0], b, 'delavec'), 'mojster_a': role_id(db, users['owner_a'][0], a, 'mojster'), 'mojster_b': role_id(db, users['owner_b'][0], b, 'mojster'),
           'skrbnik': role_id(db, users['admin'][0], None, 'admin'), 'stranka': role_id(db, users['worker'][0], None, 'stranka')}
    reference = bad(db, users, 'owner_a', 'P0002', 'uredi_delavca', podjetje=a, vloga=uuid4(), aktivna=False)
    for name, rid in ids.items():
        err = bad(db, users, 'owner_a', 'P0002', 'uredi_delavca', podjetje=a, vloga=rid, aktivna=False); assert err.diag.message_primary == reference.diag.message_primary, name
        assert db.execute('select aktivna from quoteflow.vloga_uporabnika where id=%s', (rid,)).fetchone()['aktivna'] is True, name
    assert not audit(db, podjetje_id=a)


@pytest.mark.parametrize('who', ['worker', 'customer', 'outsider', 'admin', 'owner_b'])
def test_uredi_delavca_samo_mojster_tega_podjetja_42501(db, identities, who):
    users, a, _, role = identities
    bad(db, users, who, '42501', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False); assert roles(db, users['worker'][0], a)[0]['aktivna']


def test_aktivacija_uporabnika_s_skrbnisko_vlogo_je_zavrnjena_a4(db, identities):
    users, a, _, role = identities
    call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False)
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'admin')", (users['worker'][0],))
    bad(db, users, 'owner_a', '23514', 'uredi_delavca', podjetje=a, vloga=role, aktivna=True); assert roles(db, users['worker'][0], a)[0]['aktivna'] is False
    bad(db, users, 'admin', '23514', 'aktiviraj_vlogo', target=role, velja=True); assert roles(db, users['worker'][0], a)[0]['aktivna'] is False


@pytest.mark.parametrize('reason', ['stranka_izklopljena', 'e_posta_nepotrjena', 'stranka_odprtega_projekta'])
def test_delavca_ni_mogoce_ponovno_aktivirati_niti_mojster_niti_skrbnik_l1_ugotovitev_2(db, identities, reason):
    users, a, _, role = identities; uid = users['worker'][0]
    call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False)
    if reason == 'stranka_izklopljena': db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (uid,))
    elif reason == 'e_posta_nepotrjena': db.execute('update auth.users set email_confirmed_at=null where id=%s', (uid,))
    else: project(db, users, a, 'worker')
    bad(db, users, 'owner_a', '23514', 'uredi_delavca', podjetje=a, vloga=role, aktivna=True); assert roles(db, uid, a)[0]['aktivna'] is False
    bad(db, users, 'admin', '23514', 'aktiviraj_vlogo', target=role, velja=True); assert roles(db, uid, a)[0]['aktivna'] is False


# --- dodeli_vlogo / aktiviraj_vlogo: samo skrbnik (ugotovitev 3), pogoji tudi za skrbnika (ugotovitev 2)
@pytest.mark.parametrize('naloga,company', [('delavec', 'a'), ('mojster', 'a'), ('stranka', 'a'), ('admin', 'a'), ('delavec', None), ('stranka', None), ('mojster', None), ('delavec', 'b')])
def test_mojster_ne_more_klicati_dodeli_vlogo_42501(db, identities, naloga, company):
    users, a, b, _ = identities; before = all_roles(db)
    bad(db, users, 'owner_a', '42501', 'dodeli_vlogo', target=users['outsider'][0], podjetje={'a': a, 'b': b, None: None}[company], naloga=naloga)
    bad(db, users, 'owner_a', '42501', 'dodeli_vlogo', target=users['admin'][0], podjetje=a, naloga='delavec')
    assert all_roles(db) == before and [e['vloga'] for e in audit(db, izvajalec_id=users['owner_a'][0])] == ['stranka'], 'samo lastna samodejna vloga ob registraciji'


def test_mojster_ne_more_klicati_aktiviraj_vlogo_niti_za_svojega_delavca_42501_pred_branjem(db, identities):
    users, a, b, role = identities; before = all_roles(db)
    for rid in (role, role_id(db, users['owner_a'][0], a, 'mojster'), role_id(db, users['owner_b'][0], b, 'mojster'), role_id(db, users['owner_a'][0], b, 'delavec'), role_id(db, users['admin'][0], None, 'admin'), role_id(db, users['worker'][0], None, 'stranka'), uuid4()):
        for flag in (True, False, None): bad(db, users, 'owner_a', '42501', 'aktiviraj_vlogo', target=rid, velja=flag)
    for who in ('worker', 'customer', 'outsider'): bad(db, users, who, '42501', 'aktiviraj_vlogo', target=uuid4(), velja=True); bad(db, users, who, '42501', 'dodeli_vlogo', target=users[who][0], podjetje=None, naloga='stranka')
    assert all_roles(db) == before


@pytest.mark.parametrize('reason', ['stranka_odprtega_projekta', 'neaktivna_stranka', 'nepotrjen'])
@pytest.mark.parametrize('naloga', ['delavec', 'mojster'])
def test_skrbnik_ne_dodeli_ali_aktivira_vloge_v_podjetju_neprimernemu_23514(db, identities, reason, naloga):
    users, a, _, _ = identities; uid = users['outsider'][0]
    off = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga,aktivna) values(%s,%s,%s,false) returning id", (uid, a, naloga)).fetchone()['id']
    if reason == 'stranka_odprtega_projekta': project(db, users, a, 'outsider')
    elif reason == 'neaktivna_stranka': db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (uid,))
    else: db.execute('update auth.users set email_confirmed_at=null where id=%s', (uid,))
    bad(db, users, 'admin', '23514', 'dodeli_vlogo', target=uid, podjetje=a, naloga=naloga); bad(db, users, 'admin', '23514', 'aktiviraj_vlogo', target=off, velja=True)
    assert [r['aktivna'] for r in roles(db, uid, a, naloga)] == [False] and not audit(db, uporabnik_id=uid, podjetje_id=a)


def test_skrbnik_dodeli_primernemu_in_stranki_zakljucenega_projekta(db, identities):
    users, a, _, _ = identities; p = project(db, users, a)
    assert call(db, users, 'admin', 'dodeli_vlogo', target=users['outsider'][0], podjetje=a, naloga='delavec')['aktivna'] is True
    bad(db, users, 'admin', '23514', 'dodeli_vlogo', target=users['customer'][0], podjetje=a, naloga='delavec'); close(db, p)
    assert call(db, users, 'admin', 'dodeli_vlogo', target=users['customer'][0], podjetje=a, naloga='delavec')['aktivna'] is True


def test_revizijska_sled_za_skrbnisko_dodelitev_in_aktivacijo_a9(db, identities):
    users, a, _, role = identities; target = users['outsider'][0]
    granted = call(db, users, 'admin', 'dodeli_vlogo', target=target, podjetje=a, naloga='delavec')
    call(db, users, 'admin', 'aktiviraj_vlogo', target=granted['id'], velja=False); call(db, users, 'admin', 'aktiviraj_vlogo', target=granted['id'], velja=True)
    ev = audit(db, uporabnik_id=target, podjetje_id=a)
    assert [(x['dejanje'], x['izvajalec_id'], x['vloga'], x['aktivna_potem']) for x in ev] == [('vloga', users['admin'][0], 'delavec', True), ('vloga', users['admin'][0], 'delavec', False), ('vloga', users['admin'][0], 'delavec', True)]
    assert [x['aktivna_prej'] for x in ev[1:]] == [True, False] and audit(db, uporabnik_id=users['worker'][0], podjetje_id=a) == []


def test_skrbnik_ne_dodeli_ali_aktivira_vloge_v_podjetju_drugemu_skrbniku_a4(db, identities):
    users, a, _, _ = identities; other = users['outsider'][0]
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'admin')", (other,))
    for naloga in ('delavec', 'mojster'): bad(db, users, 'admin', REFUSED, 'dodeli_vlogo', target=other, podjetje=a, naloga=naloga)
    assert not roles(db, other, a) and not roles(db, other, a, 'mojster')
    rid = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga,aktivna) values(%s,%s,'delavec',false) returning id", (other, a)).fetchone()['id']
    bad(db, users, 'admin', REFUSED, 'aktiviraj_vlogo', target=rid, velja=True); assert roles(db, other, a)[0]['aktivna'] is False


# --- QFP33 (lastnik)
def owner_role_a(db, users, a): return role_id(db, users['owner_a'][0], a, 'mojster')


def test_lastniku_ni_mogoce_odvzeti_vloge_mojster_qfp33(db, identities):
    users, a, _, _ = identities; rid = owner_role_a(db, users, a)
    bad(db, users, 'admin', 'QFP33', 'aktiviraj_vlogo', target=rid, velja=False)
    assert db.execute('select aktivna from quoteflow.vloga_uporabnika where id=%s', (rid,)).fetchone()['aktivna'] is True and not audit(db, uporabnik_id=users['owner_a'][0], podjetje_id=a)


def test_qfp33_ne_velja_za_drugega_mojstra_in_aktivacija_lastnikove_vloge_je_ok(db, identities):
    users, a, _, _ = identities
    second = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a)).fetchone()['id']
    assert call(db, users, 'admin', 'aktiviraj_vlogo', target=second, velja=False)['aktivna'] is False
    assert call(db, users, 'admin', 'aktiviraj_vlogo', target=owner_role_a(db, users, a), velja=True)['aktivna'] is True


def test_lastnik_si_ne_odvzame_vloge_mojster_sam(db, identities):
    users, a, _, _ = identities; rid = owner_role_a(db, users, a)
    bad(db, users, 'owner_a', '42501', 'aktiviraj_vlogo', target=rid, velja=False); bad(db, users, 'owner_a', 'P0002', 'uredi_delavca', podjetje=a, vloga=rid, aktivna=False)
    assert db.execute('select aktivna from quoteflow.vloga_uporabnika where id=%s', (rid,)).fetchone()['aktivna'] is True


# --- delavci_podjetja (A2)
def test_seznam_delavcev_ima_natancne_kljuce_samo_delavce_tega_podjetja_tudi_odvzete(db, identities):
    users, a, b, role = identities; answer(db, users, 'outsider', invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))['id'])
    invite(db, users, 'owner_a', a, mail(db, users, 'customer'))
    call(db, users, 'owner_a', 'uredi_delavca', podjetje=a, vloga=role, aktivna=False)
    got = rows(db, users, 'owner_a', 'delavci_podjetja', podjetje=a)
    assert all(set(r) == KEYS for r in got) and {r['uporabnik_id']: r['aktivna'] for r in got} == {users['worker'][0]: False, users['outsider'][0]: True}, 'odprto povabilo ni delavec'
    assert all(r['e_posta'] and r['ime'] == 'Ime' and r['priimek'] == 'Priimek' and r['dodeljeno_ob'] for r in got)
    rows_b = rows(db, users, 'owner_b', 'delavci_podjetja', podjetje=b)
    assert [r['uporabnik_id'] for r in rows_b] == [users['owner_a'][0]] and rows_b[0]['id'] == role_id(db, users['owner_a'][0], b, 'delavec')


@pytest.mark.parametrize('who', ['worker', 'customer', 'outsider', 'admin', 'owner_b'])
def test_seznam_delavcev_samo_za_mojstra_podjetja_42501(db, identities, who):
    users, a, _, _ = identities; bad(db, users, who, '42501', 'delavci_podjetja', podjetje=a)


def test_vloga_uporabnika_ima_stolpec_dodeljeno_ob(db):
    col = db.execute("select is_nullable,column_default from information_schema.columns where table_schema='quoteflow' and table_name='vloga_uporabnika' and column_name='dodeljeno_ob'").fetchone()
    assert col and col['is_nullable'] == 'NO' and 'now()' in col['column_default']


# --- ugotovitev 4: revizija lastnikove in samodejne vloge stranka, FK za izbris (#104)
def test_ustvari_podjetje_zabelezi_lastnikovo_vlogo_mojster(db, identities):
    users, _, _, _ = identities
    c = call(db, users, 'admin', 'ustvari_podjetje', lastnik=users['outsider'][0], ime='Novo', maticna=uuid4().hex[:20], davcna='SI87654321', naslov_v='Ulica 2')
    (ev,) = audit(db, podjetje_id=c['id'])
    assert (ev['dejanje'], ev['izvajalec_id'], ev['uporabnik_id'], ev['vloga'], ev['aktivna_prej'], ev['aktivna_potem']) == ('vloga', users['admin'][0], users['outsider'][0], 'mojster', None, True)


def test_samodejna_vloga_stranka_se_zabelezi_samo_ob_dejanski_dodelitvi(db):
    (uid, _), _ = make_user(db, confirmed=True); (ev,) = audit(db, uporabnik_id=uid)
    assert (ev['dejanje'], ev['izvajalec_id'], ev['podjetje_id'], ev['vloga'], ev['aktivna_prej'], ev['aktivna_potem']) == ('vloga', uid, None, 'stranka', None, True)
    db.execute("update auth.users set raw_user_meta_data='{\"ime\":\"Drugo\"}' where id=%s", (uid,)); assert len(audit(db, uporabnik_id=uid)) == 1
    (un, _), _ = make_user(db, confirmed=False); assert audit(db, uporabnik_id=un) == []
    db.execute('update auth.users set email_confirmed_at=now() where id=%s', (un,)); (ev,) = audit(db, uporabnik_id=un); assert (ev['vloga'], ev['izvajalec_id']) == ('stranka', un)


def test_fk_dogodkov_in_povabil_na_osebo_so_on_delete_set_null(db):
    # Deleting an account keeps audit events and invitations, only the person's link is nulled.
    def fks(table, ref):
        return {r['attname']: r['confdeltype'] for r in db.execute("""select a.attname,c.confdeltype from pg_constraint c join pg_attribute a on a.attrelid=c.conrelid and a.attnum=any(c.conkey)
            where c.conrelid=%s::regclass and c.contype='f' and c.confrelid=%s::regclass""", (table, ref)).fetchall()}
    assert fks('quoteflow_private.dogodek_vloge', 'quoteflow.uporabnik') == {'izvajalec_id': 'n', 'uporabnik_id': 'n'}
    assert fks('quoteflow_private.povabilo_delavca', 'quoteflow.uporabnik') == {'povabil_id': 'n'}
    assert fks('quoteflow_private.povabilo_delavca', 'quoteflow.vloga_uporabnika') == {'vloga_id': 'n'}


# --- ugotovitev 11: meje cenika
def test_cenik_meje_cene_in_naziva(db, identities):
    users, a, _, _ = identities
    names = {r['conname'] for r in db.execute("select conname from pg_constraint where conrelid='quoteflow.postavka_cenika'::regclass")}
    assert {'postavka_cenika_cena_meja_check', 'postavka_cenika_naziv_dolzina_check'} <= names
    v = call(db, users, 'owner_a', 'shrani_vrsto_dela', podjetje=a, vrsta=None, naziv='Polaganje', opis='', urna_postavka=D(25), stevilo_ur=D(8), stevilo_delavcev=2, aktivna=True)['id']
    item = lambda ime, cena: dict(podjetje=a, target=None, ime=ime, opis_v='', vrsta_dela_v=v, enota_v='m2', cena=cena, ddv=D('0.22'), aktivna_v=True)
    assert call(db, users, 'owner_a', 'shrani_cenik', **item('x' * 200, D('1000000')))['cena_na_enoto'] == D('1000000')
    bad(db, users, 'owner_a', {'22003', '23514'}, 'shrani_cenik', **item('Ok', D('1000000.0001'))); bad(db, users, 'owner_a', {'22001', '23514'}, 'shrani_cenik', **item('x' * 201, D(1)))
    for naziv, cena in (('x' * 201, 1), ('Ok', D('1000000.0001'))):
        fails(db, "insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela_id,enota,cena_na_enoto,stopnja_ddv) values(%s,%s,'',%s,'m2',%s,0.22)", (a, naziv, v, cena), '23514')


# --- zaprte tabele in ACL funkcij
def test_zasebne_tabele_so_zaprte_za_vse_aplikacijske_vloge(db, identities):
    users, a, _, _ = identities
    for t in ('dogodek_vloge', 'poskus_delavca', 'povabilo_delavca'):
        assert db.execute("select relrowsecurity and relforcerowsecurity as ok from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow_private' and relname=%s", (t,)).fetchone()['ok'], t
        for role in ('anon', 'authenticated', 'service_role', 'quoteflow_app'):
            for p in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'): assert not db.execute('select has_table_privilege(%s,%s,%s) as y', (role, 'quoteflow_private.' + t, p)).fetchone()['y'], (t, role, p)
    invite(db, users, 'owner_a', a, mail(db, users, 'outsider'))
    with as_user(db, users['owner_a']):
        for t in ('dogodek_vloge', 'poskus_delavca', 'povabilo_delavca'): fails(db, f'select * from quoteflow_private.{t}', (), '42501')


def fn_exists(db, name): return db.execute("select count(*) as n from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='quoteflow_private' and p.proname=%s", (name,)).fetchone()['n']


def test_acl_funkcij_vabil_in_odstranjena_dodaj_delavca(db):
    assert fn_exists(db, 'dodaj_delavca') == 0 and fn_exists(db, 'zavrnjen_cilj') == 1
    sigs = {'povabi_delavca': 'uuid,text', 'povabila_podjetja': 'uuid', 'preklici_povabilo': 'uuid,uuid', 'moja_povabila': '', 'odgovori_povabilo': 'uuid,boolean'}
    for name in NEW:
        assert fn_exists(db, name) == 1, name; f = f'quoteflow_private.{name}({sigs[name]})'
        assert db.execute("select prosecdef and proconfig @> array['search_path=\"\"'] as ok from pg_proc where oid=%s::regprocedure", (f,)).fetchone()['ok'], name
        assert db.execute("select has_function_privilege('authenticated',%s,'execute') as y", (f,)).fetchone()['y'], name
        for role in ('anon', 'service_role', 'quoteflow_app'): assert not db.execute('select has_function_privilege(%s,%s,%s) as y', (role, f, 'execute')).fetchone()['y'], (name, role)
        assert not db.execute("select coalesce(bool_or(a.grantee=0),false) as y from pg_proc p, aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where p.oid=%s::regprocedure", (f,)).fetchone()['y'], (name, 'public')
    for f in ('quoteflow_private.zavrnjen_cilj(uuid,uuid)', 'quoteflow_private.povabilo_potece(timestamptz)', 'quoteflow_private.osvezi_dodelitev()',
              'quoteflow_private.zabelezi_vlogo(boolean,quoteflow.vloga_uporabnika)', 'quoteflow_private.sync_uporabnik()'):
        for role in ('anon', 'authenticated', 'service_role', 'quoteflow_app'): assert not db.execute('select has_function_privilege(%s,%s,%s) as y', (role, f, 'execute')).fetchone()['y'], (f, role)
    # Output columns: RETURNS TABLE columns, or the attributes of a composite result type (povabi_delavca, whose e_posta parameter cannot share a name).
    cols = {r['name']: r['cols'] for r in db.execute("""select p.proname as name, coalesce((select array_agg(a.n order by a.o) from unnest(p.proargnames, p.proargmodes) with ordinality a(n,m,o) where a.m='t'),
        (select array_agg(t.attname::text order by t.attnum) from pg_type y join pg_attribute t on t.attrelid=y.typrelid where y.oid=p.prorettype and t.attnum>0 and not t.attisdropped)) as cols
        from pg_proc p join pg_namespace s on s.oid=p.pronamespace where s.nspname='quoteflow_private' and p.proname = any(%s)""", (list(NEW),))}
    assert cols == {'povabi_delavca': ['id', 'e_posta', 'stanje', 'poslano_ob'], 'povabila_podjetja': ['id', 'e_posta', 'stanje', 'poslano_ob', 'odloceno_ob'],
                    'preklici_povabilo': ['id', 'e_posta', 'stanje', 'poslano_ob', 'odloceno_ob'], 'moja_povabila': ['id', 'podjetje_id', 'podjetje_naziv', 'povabil', 'poslano_ob'],
                    'odgovori_povabilo': ['id', 'stanje']}


# --- potrjeni_uporabniki (admin-only)
def test_potrjeni_uporabniki_admin_vidi_potrjenost_iz_auth_users(db, identities):
    """quoteflow_private.potrjeni_uporabniki() -> setof (id uuid, potrjen boolean); potrjen = auth.users.email_confirmed_at is not null; samo admin, sicer 42501."""
    users, _, _, _ = identities; (un, _), _ = make_user(db, confirmed=False, name='nepotrjen'); (ok, _), _ = make_user(db, confirmed=True, name='potrjen')
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga,aktivna) values(%s,'stranka',true)", (un,))  # artificial: role present, e-mail not confirmed
    got = {r['id']: r['potrjen'] for r in rows(db, users, 'admin', 'potrjeni_uporabniki')}
    assert got[un] is False and got[ok] is True and got[users['customer'][0]] is True and set(got) >= {users[k][0] for k in users}


@pytest.mark.parametrize('who', ['owner_a', 'worker', 'customer', 'outsider', 'owner_b'])
def test_potrjeni_uporabniki_ni_za_ne_administratorja_42501(db, identities, who):
    users, _, _, _ = identities; bad(db, users, who, '42501', 'potrjeni_uporabniki')
