"""US-03 začetek projekta: functions, RLS and isolation on disposable local Supabase."""
import os
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user
from test_identity_database import api_client
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
FORM = {'naziv': 'Prenova kopalnice', 'opis': 'Menjava ploščic', 'lokacija_izvedbe': 'Maribor'}


def email(db, users, name): return db.execute('select e_posta from quoteflow.uporabnik where id=%s', (users[name][0],)).fetchone()['e_posta']


def fails(db, sql, args, state):
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): db.execute(sql, args)
    assert e.value.sqlstate == state, e.value.sqlstate


@pytest.fixture
def master(api_client, identities, db):
    client, selected = api_client; selected['name'] = 'owner_a'; users, a, b, _ = identities
    return client, selected, f'/api/podjetja/{a}', users, email(db, users, 'customer')


def test_ustvari_projekt_v_fazi_pregled_za_stranko(master):
    client, _, base, users, mail = master
    r = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': f'  {mail.upper()} '}); assert r.status_code == 201, r.text
    p = r.json()
    assert p['faza'] == 'pregled' and p['stranka_e_posta'] == mail and p['stranka_ime'] == 'Ime' and p['stranka_priimek'] == 'Priimek' and p['termin_od'] is None
    assert [x['id'] for x in client.get(base + '/projekti').json()] == [p['id']]


def test_neznana_e_posta_in_neaktivna_stranka_sta_enako_409(master, db):
    client, _, base, users, mail = master
    r = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': 'ni-take@example.test'})
    assert r.status_code == 409 and r.json()['detail'] == 'Uporabnik s tem e-poštnim naslovom ni registrirana stranka.'
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    r2 = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail})
    assert r2.status_code == 409 and r2.json() == r.json()


def test_uredi_samo_v_pregledu_ali_ogledu_ogled_samo_iz_pregleda(master, db):
    client, _, base, users, mail = master
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json(); path = f"{base}/projekti/{p['id']}"
    edit = {'naziv': 'Novo ime', 'opis': 'Nov opis', 'lokacija_izvedbe': 'Celje'}
    assert client.put(path, json=edit).json()['naziv'] == 'Novo ime'
    r = client.post(path + '/ogled'); assert r.status_code == 200 and r.json()['faza'] == 'ogled'
    assert client.put(path, json=edit | {'naziv': 'Še enkrat'}).status_code == 200
    r = client.post(path + '/ogled'); assert r.status_code == 409 and r.json()['detail'] == 'V tej fazi projekta to dejanje ni dovoljeno.'
    for phase in ('ponudba', 'termin', 'izvedba', 'obracun', 'zakljucen'):
        db.execute('set constraints all immediate'); db.execute('alter table quoteflow.projekt disable trigger user'); db.execute("update quoteflow.projekt set faza=%s, zakljuceno_ob=case when %s='zakljucen' then now() end where id=%s", (phase, phase, p['id'])); db.execute('alter table quoteflow.projekt enable trigger user')
        assert client.put(path, json=edit).status_code == 409 and client.post(path + '/ogled').status_code == 409


def test_tuj_mojster_delavec_stranka_ne_urejajo_in_ne_berejo(master, identities):
    client, selected, base, users, mail = master; _, a, b, _ = identities
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json(); path = f"{base}/projekti/{p['id']}"
    edit = {'naziv': 'X', 'opis': '', 'lokacija_izvedbe': ''}
    selected['name'] = 'owner_b'
    assert client.get(base + '/projekti').status_code == 403 and client.put(path, json=edit).status_code == 403 and client.post(path + '/ogled').status_code == 403
    foreign = f'/api/podjetja/{b}/projekti'
    assert client.get(foreign).json() == []
    assert client.put(f"{foreign}/{p['id']}", json=edit).status_code == 404 and client.post(f"{foreign}/{p['id']}/ogled").status_code == 404
    for actor in ('worker', 'customer', 'outsider', 'admin'):
        selected['name'] = actor
        assert client.get(base + '/projekti').status_code == 403 and client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).status_code == 403


def test_odvzeta_vloga_mojstra_ne_ustvarja_projektov(master, db, identities):
    client, selected, base, users, mail = master; a = identities[1]
    role = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a)).fetchone()['id']
    selected['name'] = 'outsider'
    assert client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).status_code == 201
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,))
    assert client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).status_code == 403


def test_stranka_vidi_samo_svoje_projekte(master, db, identities):
    client, selected, base, users, mail = master
    mine = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json()
    other = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': email(db, users, 'outsider')}).json()
    selected['name'] = 'customer'
    listed = client.get('/api/projekti').json()
    assert [x['id'] for x in listed] == [mine['id']] and listed[0]['podjetje_naziv'] == 'A' and 'stranka_e_posta' not in listed[0]
    assert client.get(f"/api/projekti/{mine['id']}").status_code == 200 and client.get(f"/api/projekti/{other['id']}").status_code == 404
    selected['name'] = 'outsider'; assert [x['id'] for x in client.get('/api/projekti').json()] == [other['id']]
    for who in ('owner_b', 'worker', 'admin'):
        selected['name'] = who
        assert client.get('/api/projekti').json() == [] and client.get(f"/api/projekti/{mine['id']}").status_code == 404


def test_delavec_brez_ekipe_ne_vidi_projekta_neposredno(master, db):
    client, selected, base, users, mail = master
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json()
    with as_user(db, users['worker']):
        assert db.execute('select * from quoteflow.projekt where id=%s', (p['id'],)).fetchall() == []
    with as_user(db, users['owner_b']):
        assert db.execute('select * from quoteflow.projekt where id=%s', (p['id'],)).fetchall() == []


def test_funkcije_zavrnejo_nemojstra_in_ni_nastavitve_ponudbe(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    for who in ('worker', 'customer', 'outsider', 'owner_b', 'admin'):
        with as_user(db, users[who]):
            fails(db, 'select * from quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)', (a, mail, 'N', 'O', 'L'), '42501')
    with as_user(db, users['owner_a']):
        p = db.execute('select * from quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)', (a, mail, 'N', 'O', 'L')).fetchone()
        assert p['faza'] == 'pregled'
        fails(db, "update quoteflow.projekt set faza='ponudba' where id=%s", (p['id'],), '42501')
        fails(db, 'select * from quoteflow_private.uredi_projekt(%s,%s,%s,%s,%s)', (b, p['id'], 'X', '', ''), '42501')
        fails(db, 'select * from quoteflow_private.zahtevaj_ogled(%s,%s)', (b, p['id']), '42501')
        fails(db, 'select * from quoteflow_private.zahtevaj_ogled(%s,%s)', (a, uuid4()), 'P0002')
        assert attempt(db, a, 'nihce@example.test') is None
        fails(db, 'select * from quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)', (a, mail, ' ', 'O', 'L'), '23514')
    with as_user(db, users['owner_b']):
        fails(db, 'select * from quoteflow_private.uredi_projekt(%s,%s,%s,%s,%s)', (b, p['id'], 'X', '', ''), 'P0002')
        fails(db, 'select * from quoteflow_private.zahtevaj_ogled(%s,%s)', (b, p['id']), 'P0002')


def test_stranka_ne_bere_podjetja_neposredno_naziv_samo_prek_funkcije(master, db, identities):
    client, selected, base, users, mail = master; b = identities[2]
    mine = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json()
    with as_user(db, users['customer']):
        assert db.execute('select * from quoteflow.podjetje').fetchall() == []
        assert db.execute('select * from quoteflow.podjetje where id=%s', (identities[1],)).fetchall() == []
        assert db.execute('select quoteflow_private.naziv_podjetja(%s) as n', (b,)).fetchone()['n'] is None
    selected['name'] = 'customer'
    listed = client.get('/api/projekti').json()
    assert [x['id'] for x in listed] == [mine['id']] and listed[0]['podjetje_naziv'] == 'A'


# M1a: rate limit of 20 creation attempts per company per rolling hour (ok + unknown customer), durable failures
M_PREVEC = 'Preveč poskusov ustvarjanja projektov. Poskusite znova čez nekaj časa.'
CREATE = 'select (quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)).id as id'


def attempt(db, company, mail): return db.execute(CREATE, (company, mail, 'N', 'O', 'L')).fetchone()['id']


def test_dvajset_poskusov_mesano_21_je_qfp08(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    with as_user(db, users['owner_a']):
        for i in range(20):
            got = attempt(db, a, mail if i % 2 else 'ni-take@example.test')
            assert (got is not None) == bool(i % 2)
        fails(db, CREATE, (a, mail, 'N', 'O', 'L'), 'QFP08')
        fails(db, CREATE, (a, 'ni-take@example.test', 'N', 'O', 'L'), 'QFP08')


def backdate(db, company, minutes):
    db.execute("insert into quoteflow_private.poskus_projekta(podjetje_id, ob) select %s, now() - make_interval(mins => %s) from generate_series(1,20)", (company, minutes))


def test_okno_poskusov_je_drsece_61_minut_star_poskus_ne_steje(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    backdate(db, a, 61)
    with as_user(db, users['owner_a']): assert attempt(db, a, mail) is not None


def test_okno_poskusov_je_drsece_59_minut_star_poskus_steje(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    backdate(db, a, 59)
    with as_user(db, users['owner_a']): fails(db, CREATE, (a, mail, 'N', 'O', 'L'), 'QFP08')


def test_neuspeli_iskanji_stranke_se_stejejo_in_vrnejo_null(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    with as_user(db, users['owner_a']):
        for _ in range(20): assert attempt(db, a, 'ni-take@example.test') is None
        fails(db, CREATE, (a, mail, 'N', 'O', 'L'), 'QFP08')


def test_uspesne_ustvaritve_se_stejejo(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    with as_user(db, users['owner_a']):
        for _ in range(20): assert attempt(db, a, mail) is not None
        fails(db, CREATE, (a, 'ni-take@example.test', 'N', 'O', 'L'), 'QFP08')


def test_omejitev_je_po_podjetjih(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    with as_user(db, users['owner_a']):
        for _ in range(20): attempt(db, a, 'ni-take@example.test')
    with as_user(db, users['owner_b']):
        assert attempt(db, b, mail) is not None and attempt(db, b, 'ni-take@example.test') is None


def test_neznana_in_neaktivna_stranka_vrneta_enak_null(db, identities):
    users, a, b, _ = identities; mail = email(db, users, 'customer')
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    with as_user(db, users['owner_a']):
        assert attempt(db, a, 'ni-take@example.test') is None and attempt(db, a, mail) is None


def test_api_21_poskus_je_409_s_sporocilom_o_omejitvi(master):
    client, _, base, users, mail = master
    for _ in range(20):
        r = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': 'ni-take@example.test'})
        assert r.status_code == 409 and r.json()['detail'] == 'Uporabnik s tem e-poštnim naslovom ni registrirana stranka.'
    for who in ('ni-take@example.test', mail):
        r = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': who})
        assert r.status_code == 409 and r.json()['detail'] == M_PREVEC


def test_evidenca_poskusov_je_v_quoteflow_private_in_nedostopna(db, identities):
    users, a, b, _ = identities
    tables = [r['relname'] for r in db.execute("select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow_private' and c.relkind in ('r','p')")]
    assert tables
    for t in tables:
        assert not db.execute("select has_table_privilege('authenticated',%s,'select,insert,update,delete') as p", (f'quoteflow_private.{t}',)).fetchone()['p'], t
        assert not db.execute("select has_table_privilege('anon',%s,'select,insert,update,delete') as p", (f'quoteflow_private.{t}',)).fetchone()['p'], t


# L2: own-project routes require an active customer role
def test_odvzeta_vloga_stranka_je_403_na_lastnih_projektih(master, db):
    client, selected, base, users, mail = master
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json()
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    selected['name'] = 'customer'
    assert client.get('/api/projekti').status_code == 403 and client.get(f"/api/projekti/{p['id']}").status_code == 403


# L6: master no longer reads quoteflow.uporabnik directly; customers only through stranke_projektov
def test_mojster_bere_samo_svojo_vrstico_uporabnika(master, db):
    client, _, base, users, mail = master
    client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail})
    with as_user(db, users['owner_a']):
        assert db.execute('select count(*) as n from quoteflow.uporabnik').fetchone()['n'] == 1
        assert db.execute('select count(*) as n from quoteflow.uporabnik where id=%s', (users['customer'][0],)).fetchone()['n'] == 0


def stranke(db, who, users, company):
    with as_user(db, users[who]):
        try:
            with db.transaction(): return db.execute('select * from quoteflow_private.stranke_projektov(%s)', (company,)).fetchall()
        except psycopg.Error as e:
            assert e.sqlstate == '42501', e.sqlstate
            return 'denied'


def test_stranke_projektov_vrne_stranko_lastnega_podjetja(master, db, identities):
    client, _, base, users, mail = master
    client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail})
    client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail, 'naziv': 'Drugi'})
    rows = stranke(db, 'owner_a', users, identities[1])
    assert rows != 'denied' and len(rows) == 1 and set(rows[0]) == {'id', 'e_posta', 'ime', 'priimek'}
    assert rows[0]['id'] == users['customer'][0] and rows[0]['e_posta'] == mail and rows[0]['ime'] == 'Ime' and rows[0]['priimek'] == 'Priimek'


def test_stranke_projektov_ne_vrne_nic_tujemu_delavcu_in_deaktiviranemu(master, db, identities):
    client, _, base, users, mail = master; a = identities[1]
    client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail})
    for who in ('owner_b', 'worker', 'customer', 'outsider', 'admin'): assert stranke(db, who, users, a) in ([], 'denied'), who
    assert stranke(db, 'owner_a', users, identities[2]) in ([], 'denied')
    db.execute('update quoteflow.podjetje set aktivno=false where id=%s', (a,))
    assert stranke(db, 'owner_a', users, a) in ([], 'denied')


def test_stranke_projektov_ne_vrne_strank_drugih_podjetij(master, db, identities):
    client, selected, base, users, mail = master; b = identities[2]
    selected['name'] = 'owner_b'
    client.post(f'/api/podjetja/{b}/projekti', json=FORM | {'e_posta_stranke': email(db, users, 'outsider')})
    rows = stranke(db, 'owner_a', users, identities[1])
    assert rows in ([], 'denied')
    rows_b = stranke(db, 'owner_b', users, b)
    assert [r['id'] for r in rows_b] == [users['outsider'][0]]


# Pentest pins: expected green already.
def test_tuj_mojster_ne_spremeni_faze_ne_uredi_ne_sproži_ogleda(master, db):
    client, selected, base, users, mail = master
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json(); pid = p['id']
    selected['name'] = 'owner_b'; b = client.get('/api/me').json() if False else None
    own_b = [r for r in db.execute('select podjetje_id from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga=%s and aktivna', (users['owner_b'][0], 'mojster')).fetchall()][0]['podjetje_id']
    foreign = f'/api/podjetja/{own_b}/projekti/{pid}'
    assert client.put(foreign, json={'naziv': 'Hack', 'opis': '', 'lokacija_izvedbe': ''}).status_code == 404
    assert client.post(foreign + '/ogled').status_code == 404
    assert client.put(f'{base}/projekti/{pid}', json={'naziv': 'Hack', 'opis': '', 'lokacija_izvedbe': ''}).status_code == 403
    assert client.post(f'{base}/projekti/{pid}/ogled').status_code == 403
    row = db.execute('select faza, naziv from quoteflow.projekt where id=%s', (pid,)).fetchone()
    assert row['faza'] == 'pregled' and row['naziv'] == FORM['naziv']


@pytest.mark.parametrize('extra', [{'faza': 'ogled'}, {'stranka_id': str(uuid4())}, {'podjetje_id': str(uuid4())}])
def test_dodatna_polja_pri_projektu_so_422(master, extra):
    client, _, base, users, mail = master
    assert client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail} | extra).status_code == 422
    p = client.post(base + '/projekti', json=FORM | {'e_posta_stranke': mail}).json()
    assert client.put(f"{base}/projekti/{p['id']}", json={k: v for k, v in FORM.items()} | extra).status_code == 422
