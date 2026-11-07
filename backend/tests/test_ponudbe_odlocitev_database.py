"""US-05 pošiljanje in odločitev o ponudbi (model v3): poslji_ponudbo posname postavke projekta, odgovori_ponudbo, revizijska sled in API na disposable local Supabase."""
import os
from decimal import Decimal as D
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user, catalog
from test_identity_database import api_client
from v3_quotes import P, env, call, bad, fails, quiet, new_project, raw_quote, send, sent, decide, add_item, as_owner, year, LJ  # noqa: F401
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
NO_ONE = ('42501', 'P0002')


def one(db, sql, args=()): return db.execute(sql, args).fetchone()


def state(db, q): return one(db, 'select stanje from quoteflow.ponudba where id=%s', (q,))['stanje']


def phase(db, p): return one(db, 'select faza from quoteflow.projekt where id=%s', (p,))['faza']


def invoices(db, q): return one(db, 'select count(*) as n from quoteflow.racun where ponudba_id=%s', (q,))['n']


def audit(db, q): return db.execute('select * from quoteflow_private.dogodek_dokumenta where ponudba_id=%s order by ob, id', (q,)).fetchall()


def untouched(db, p, q, st='poslana', faza='ponudba'):
    assert state(db, q) == st and phase(db, p) == faza and invoices(db, q) == 0


def refuses(db, users, who, p, q, accept=True):
    with as_user(db, users[who]):
        with pytest.raises(psycopg.Error) as e:
            with db.transaction(): db.execute(f'select * from {Q}odgovori_ponudbo(%s,%s,%s)', (p, q, accept))
    assert e.value.sqlstate in NO_ONE, e.value.sqlstate


# poslji_ponudbo
@pytest.mark.parametrize('faza', ['pregled', 'ogled', 'ponudba'])
def test_poslji_nastavi_stanje_fazo_ponudba_in_revizijsko_sled(env, db, faza):
    users, a, _, p, _ = env
    if faza == 'ponudba': sent(db, users, a, p); q = raw_quote(db, p, n=2)
    else: db.execute('update quoteflow.projekt set faza=%s where id=%s', (faza, p)); q = raw_quote(db, p)
    r = send(db, users, a, q)
    assert r['id'] == q and r['stanje'] == 'poslana' and r['poslano_ob'] and r['odgovorjeno_ob'] is None and phase(db, p) == 'ponudba'
    log = audit(db, q); assert len(log) == 1
    assert (log[0]['dejanje'], log[0]['izvajalec_id'], log[0]['podjetje_id'], log[0]['projekt_id']) == ('poslana', users['owner_a'][0], a, p) and log[0]['ob']


def test_poslji_ne_osnutek_je_qfp10(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    bad(db, users, 'owner_a', 'QFP10', 'poslji_ponudbo', a, P(db, q), q)
    decide(db, users, p, q, False)
    bad(db, users, 'owner_a', 'QFP10', 'poslji_ponudbo', a, P(db, q), q)
    assert len(audit(db, q)) == 2 and one(db, 'select count(*) as n from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,))['n'] == 1


def test_poslji_brez_postavk_je_qfp13(env, db):
    users, a, _, p, _ = env; q = raw_quote(db, p, lines=0)
    bad(db, users, 'owner_a', 'QFP13', 'poslji_ponudbo', a, P(db, q), q); assert state(db, q) == 'osnutek' and not audit(db, q)


def test_poslji_potekla_veljavnost_je_qfp12_danes_je_se_dovoljeno(env, db):
    users, a, _, p, _ = env; q = raw_quote(db, p, velja=f'{LJ}-1')
    bad(db, users, 'owner_a', 'QFP12', 'poslji_ponudbo', a, P(db, q), q); assert state(db, q) == 'osnutek' and not audit(db, q) and not one(db, 'select count(*) as n from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,))['n']
    quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ} where id=%s', (q,)); assert send(db, users, a, q)['stanje'] == 'poslana'
    p2 = new_project(db, users, a); q3 = raw_quote(db, p2, velja='null')
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): send(db, users, a, q3)
    assert e.value.sqlstate == 'QFP12'


def test_poslji_ko_projekt_ze_ima_sprejeto_je_qfp07(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p); q2 = raw_quote(db, p, n=2); decide(db, users, p, q, True)
    bad(db, users, 'owner_a', 'QFP07', 'poslji_ponudbo', a, P(db, q2), q2); assert state(db, q2) == 'osnutek'


def test_nova_razlicica_ne_spremeni_stare_poslane(env, db):
    users, a, _, p, _ = env; q1 = sent(db, users, a, p); q2 = raw_quote(db, p, n=2); r = send(db, users, a, q2)
    assert r['stanje'] == 'poslana' and state(db, q1) == 'poslana' and phase(db, p) == 'ponudba' and len(audit(db, q1)) == 1 and len(audit(db, q2)) == 1


def test_poslji_tuje_podjetje_neznana_ponudba_in_napacni_akterji(env, db):
    users, a, b, p, _ = env; q = raw_quote(db, p)
    bad(db, users, 'owner_b', 'P0002', 'poslji_ponudbo', b, P(db, q), q); bad(db, users, 'owner_b', '42501', 'poslji_ponudbo', a, P(db, q), q)
    bad(db, users, 'owner_a', 'P0002', 'poslji_ponudbo', a, uuid4(), uuid4())
    pb = new_project(db, users, b); qb = raw_quote(db, pb); bad(db, users, 'owner_a', 'P0002', 'poslji_ponudbo', a, P(db, qb), qb)
    for who in ('worker', 'customer', 'outsider', 'admin'): bad(db, users, who, '42501', 'poslji_ponudbo', a, P(db, q), q)
    assert state(db, q) == 'osnutek' and state(db, qb) == 'osnutek' and not audit(db, q) and not audit(db, qb)


def test_poslji_z_odvzeto_vlogo_mojstra_ali_neaktivnim_podjetjem_ne_gre(env, db):
    users, a, _, p, _ = env; q = raw_quote(db, p)
    role = db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a)).fetchone()['id']
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,))
    bad(db, users, 'outsider', '42501', 'poslji_ponudbo', a, P(db, q), q); assert state(db, q) == 'osnutek'


# odgovori_ponudbo
def test_sprejem_je_atomaren_ena_prejemna_osnutek_racun_in_faza_termin(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    r = decide(db, users, p, q, True)
    assert r['id'] == q and r['stanje'] == 'sprejeta' and r['odgovorjeno_ob']
    db.execute('set constraints all immediate'); db.execute('set constraints all deferred')
    inv = db.execute('select * from quoteflow.racun where ponudba_id=%s', (q,)).fetchall()
    assert len(inv) == 1 and inv[0]['stanje_dokumenta'] == 'osnutek' and inv[0]['placano_ob'] is None and phase(db, p) == 'termin'
    log = audit(db, q); assert [x['dejanje'] for x in log] == ['poslana', 'sprejeta'] and log[1]['izvajalec_id'] == users['customer'][0] and log[1]['projekt_id'] == p and log[1]['podjetje_id'] == a


def test_zavrnitev_obdrzi_dokument_brez_racuna_in_faza_ostane(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    r = decide(db, users, p, q, False); assert r['stanje'] == 'zavrnjena' and r['odgovorjeno_ob']
    untouched(db, p, q, 'zavrnjena'); assert one(db, 'select count(*) as n from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,))['n'] == 1
    log = audit(db, q); assert [x['dejanje'] for x in log] == ['poslana', 'zavrnjena'] and log[1]['izvajalec_id'] == users['customer'][0]


@pytest.mark.parametrize('first,second', [(True, True), (True, False), (False, True), (False, False)])
def test_druga_odlocitev_je_qfp11(env, db, first, second):
    users, a, _, p, _ = env; q = sent(db, users, a, p); decide(db, users, p, q, first)
    n = len(audit(db, q)); inv = invoices(db, q)
    bad(db, users, 'customer', 'QFP11', 'odgovori_ponudbo', p, q, second)
    assert len(audit(db, q)) == n and invoices(db, q) == inv


def test_nadomescena_z_novejso_poslano_razlicico_je_qfp11_nova_pa_se_sprejme(env, db):
    users, a, _, p, _ = env; q1 = sent(db, users, a, p); q2 = raw_quote(db, p, n=2)
    send(db, users, a, q2)
    for accept in (True, False): bad(db, users, 'customer', 'QFP11', 'odgovori_ponudbo', p, q1, accept)
    assert state(db, q1) == 'poslana' and invoices(db, q1) == 0
    assert decide(db, users, p, q2, True)['stanje'] == 'sprejeta' and invoices(db, q2) == 1 and phase(db, p) == 'termin'


def test_osnutek_novejse_razlicice_ne_nadomesti_poslane(env, db):
    users, a, _, p, _ = env; q1 = sent(db, users, a, p); raw_quote(db, p, n=2)
    assert decide(db, users, p, q1, True)['stanje'] == 'sprejeta'


def test_odlocitev_o_osnutku_ni_mogoca(env, db):
    users, a, _, p, _ = env; q = raw_quote(db, p)
    with as_user(db, users['customer']):
        with pytest.raises(psycopg.Error) as e:
            with db.transaction(): db.execute(f'select * from {Q}odgovori_ponudbo(%s,%s,true)', (p, q))
    assert e.value.sqlstate in ('QFP11', 'P0002'); assert state(db, q) == 'osnutek' and invoices(db, q) == 0


def test_potekla_ponudba_je_qfp12_in_danes_se_velja(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ}-1 where id=%s', (q,))
    bad(db, users, 'customer', 'QFP12', 'odgovori_ponudbo', p, q, True); untouched(db, p, q)
    quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ} where id=%s', (q,))
    assert decide(db, users, p, q, True)['stanje'] == 'sprejeta'


@pytest.mark.parametrize('accept', [True, False])
def test_neaktivno_podjetje_je_qfp17(env, db, accept):
    users, a, _, p, _ = env; q = sent(db, users, a, p); db.execute('update quoteflow.podjetje set aktivno=false where id=%s', (a,))
    bad(db, users, 'customer', 'QFP17', 'odgovori_ponudbo', p, q, accept); untouched(db, p, q); assert len(audit(db, q)) == 1


@pytest.mark.parametrize('who', ['outsider', 'owner_a', 'owner_b', 'worker', 'admin'])
def test_napacen_akter_ni_stranka_projekta(env, db, who):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    for accept in (True, False): refuses(db, users, who, p, q, accept)
    untouched(db, p, q); assert len(audit(db, q)) == 1


@pytest.mark.parametrize('who', ['owner_a', 'worker'])
def test_d9_mojster_ali_delavec_podjetja_ni_svoja_stranka(env, db, who):
    users, a, _, _, _ = env
    p = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Zase','O','L') returning id", (a, users[who][0])).fetchone()['id']
    q = sent(db, users, a, p); refuses(db, users, who, p, q, True); untouched(db, p, q)


def test_ponudba_drugega_projekta_ali_nakljucni_id_je_not_found(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p); p2 = new_project(db, users, a)
    refuses(db, users, 'customer', p2, q); refuses(db, users, 'customer', p, uuid4()); refuses(db, users, 'customer', uuid4(), q); untouched(db, p, q)


def test_odvzeta_vloga_stranke_ne_more_odlocati(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p)
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    refuses(db, users, 'customer', p, q); untouched(db, p, q)


def test_prekinjena_seja_stranke_ne_more_odlocati(env, db):
    users, a, _, p, _ = env; q = sent(db, users, a, p); db.execute('delete from auth.sessions where id=%s', (users['customer'][1],))
    refuses(db, users, 'customer', p, q); untouched(db, p, q)


# ACL, revizijska tabela, RLS
def test_nove_funkcije_so_samo_za_authenticated_in_stare_podpise_ni_vec(db):
    for f in ('poslji_ponudbo(uuid,uuid,uuid)', 'odgovori_ponudbo(uuid,uuid,boolean)'):
        for role in ('anon', 'service_role', 'quoteflow_app', 'public'): assert not one(db, "select has_function_privilege(%s,%s,'execute') as p", (role, Q + f))['p'], (role, f)
        assert one(db, "select has_function_privilege('authenticated',%s,'execute') as p", (Q + f,))['p'], f
    for f in ('poslji_ponudbo(uuid,uuid)', 'odgovori_ponudbo(uuid,boolean)'): assert one(db, 'select to_regprocedure(%s) as f', (Q + f,))['f'] is None, f


def test_revizijska_tabela_je_zaprta_za_vse_razen_funkcij(env, db):
    users, a, _, p, _ = env
    t = one(db, "select relrowsecurity,relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow_private' and c.relname='dogodek_dokumenta'")
    assert t and t['relrowsecurity'] and t['relforcerowsecurity']
    for role in ('anon', 'authenticated', 'service_role', 'quoteflow_app'):
        for priv in ('SELECT', 'INSERT', 'UPDATE', 'DELETE'): assert not one(db, 'select has_table_privilege(%s,%s,%s) as p', (role, Q + 'dogodek_dokumenta', priv))['p'], (role, priv)
    q = sent(db, users, a, p)
    for who in ('owner_a', 'customer', 'admin'):
        with as_user(db, users[who]): fails(db, f'select * from {Q}dogodek_dokumenta', (), '42501')
    assert len(audit(db, q)) == 1


def test_revizijska_tabela_zahteva_veljavno_dejanje_in_izvajalca(env, db):
    users, a, _, p, _ = env
    ins = 'insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,dejanje,izvajalec_id) values(%s,%s,%s,%s)'
    fails(db, ins, (a, p, 'pobrisana', users['owner_a'][0]), '23514'); fails(db, ins, (a, p, 'poslana', None), '23502')
    for d in ('poslana', 'sprejeta', 'zavrnjena', 'termin', 'izvedba_koncana', 'izdan', 'placan'):
        with db.transaction(): db.execute(ins, (a, p, d, users['owner_a'][0]))


def test_stranka_vidi_poslano_in_sprejeto_a_ne_osnutka_racuna_in_materialov(env, db):
    users, a, _, p, cat = env; q = sent(db, users, a, p); q2 = raw_quote(db, p, n=2)
    with as_user(db, users['customer']):
        assert {r['id'] for r in db.execute('select id from quoteflow.ponudba')} == {q}
    decide(db, users, p, q, True)
    with as_user(db, users['customer']):
        assert db.execute('select stanje from quoteflow.ponudba').fetchall() == [{'stanje': 'sprejeta'}]
        assert one(db, 'select count(*) as n from quoteflow.racun')['n'] == 0 and one(db, 'select count(*) as n from quoteflow.material_ponudbe')['n'] == 0
    with as_user(db, users['outsider']): assert one(db, 'select count(*) as n from quoteflow.ponudba')['n'] == 0


# API
@pytest.fixture
def api(env, api_client):
    client, selected = api_client; users, a, b, p, cat = env; selected['name'] = 'owner_a'
    return client, selected, users, a, b, p, f'/api/podjetja/{a}/projekti/{p}'


def test_api_poslji_vrne_ponudbo_poslano_in_zapre_urejanje(api, db):
    client, _, users, a, _, p, M = api; q = raw_quote(db, p)
    r = client.post(f'{M}/ponudbe/{q}/poslji'); assert r.status_code == 200, r.text
    j = r.json(); assert j['id'] == str(q) and j['stanje'] == 'poslana' and j['poslano_ob'] and j['skupaj'] == '219.60' and len(j['postavke']) == 1 and phase(db, p) == 'ponudba'
    again = client.post(f'{M}/ponudbe/{q}/poslji'); assert again.status_code == 409 and again.json()['detail'] == 'Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.'
    assert client.put(f'{M}/ponudbe/{q}', json={'velja_do': None}).status_code == 409


def test_api_poslji_napake_so_409_s_slovenskim_sporocilom(api, db):
    client, _, users, a, _, p, M = api
    q = raw_quote(db, p, lines=0); r = client.post(f'{M}/ponudbe/{q}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'Ponudba mora imeti vsaj eno postavko.'
    add_item(db, p); quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ}-1 where id=%s', (q,))
    r = client.post(f'{M}/ponudbe/{q}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'Veljavnost ponudbe je potekla.'
    quiet(db, 'ponudba', 'update quoteflow.ponudba set velja_do=null where id=%s', (q,))
    r = client.post(f'{M}/ponudbe/{q}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'Veljavnost ponudbe je potekla.'
    assert state(db, q) == 'osnutek' and not audit(db, q)


def test_api_poslji_postavko_brez_izmer_je_409_s_fiksnim_sporocilom(api, db):
    client, _, users, a, _, p, M = api; it = add_item(db, p); q = raw_quote(db, p)
    as_owner(db, a, 'odstrani_izmero', podjetje=a, projekt=p, postavka=it, izmera=one(db, 'select id from quoteflow.izmera where postavka_projekta_id=%s', (it,))['id'])
    r = client.post(f'{M}/ponudbe/{q}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'Vsaka postavka mora imeti pozitivno količino izmer.' and 'Polaganje' not in r.json()['detail']
    assert state(db, q) == 'osnutek'


def test_api_poslji_ob_sprejeti_ponudbi_je_409_faza(api, db):
    client, _, users, a, _, p, M = api; q = sent(db, users, a, p); q2 = raw_quote(db, p, n=2); decide(db, users, p, q, True)
    r = client.post(f'{M}/ponudbe/{q2}/poslji'); assert r.status_code == 409 and r.json()['detail'] == 'V tej fazi projekta to dejanje ni dovoljeno.'


def test_api_poslji_tujec_dobi_enak_404_kot_nakljucni_id_nemojstri_403(api, db):
    client, selected, users, a, b, p, M = api; q = raw_quote(db, p)
    selected['name'] = 'owner_b'
    foreign = client.post(f'/api/podjetja/{b}/projekti/{p}/ponudbe/{q}/poslji'); rnd = client.post(f'/api/podjetja/{b}/projekti/{uuid4()}/ponudbe/{uuid4()}/poslji')
    assert foreign.status_code == 404 and (foreign.status_code, foreign.json()) == (rnd.status_code, rnd.json())
    assert client.post(f'{M}/ponudbe/{q}/poslji').status_code == 403
    for who in ('customer', 'worker', 'outsider', 'admin'):
        selected['name'] = who; assert client.post(f'{M}/ponudbe/{q}/poslji').status_code == 403, who
    assert state(db, q) == 'osnutek'


CUSTOMER_TOP = {'id', 'stevilka', 'razlicica', 'stanje', 'poslano_ob', 'odgovorjeno_ob', 'velja_do', 'nadomescena', 'neto', 'ddv', 'skupaj', 'postavke', 'ddv_po_stopnjah', 'podjetje_naziv'}
CUSTOMER_LINE = {'zaporedje', 'naziv', 'opis', 'vrsta_dela', 'enota', 'cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'neto', 'ddv', 'koncna_cena', 'izmera_skupaj', 'izmere'}
CUSTOMER_IZMERA = {'zaporedje', 'odstej', 'kosi', 'vrednost', 'enota', 'dolzina', 'visina', 'sirina'}
NEVER = ('urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'cena_dela', 'cena_materiala', 'materiali', 'kolicina_na_enoto', 'nabavna_cena', 'marza', 'postavka_projekta_id', 'vrsta_dela_id')


def test_api_stranka_vidi_samo_poslano_z_natancno_belo_listo_polj(api, db, env):
    client, selected, users, a, _, p, M = api; cat = env[4]; q = raw_quote(db, p)
    selected['name'] = 'customer'; assert client.get(f'/api/projekti/{p}/ponudbe').json() == []
    selected['name'] = 'owner_a'; assert client.post(f'{M}/ponudbe/{q}/poslji').status_code == 200
    l = one(db, 'select id from quoteflow.postavka_ponudbe where ponudba_id=%s', (q,))['id']; assert one(db, 'select count(*) as n from quoteflow.material_ponudbe where postavka_ponudbe_id=%s', (l,))['n'] == 1
    selected['name'] = 'customer'; r = client.get(f'/api/projekti/{p}/ponudbe'); assert r.status_code == 200, r.text
    got = r.json(); assert len(got) == 1; j = got[0]
    assert set(j) == CUSTOMER_TOP and j['id'] == str(q) and j['stanje'] == 'poslana' and j['nadomescena'] is False and j['podjetje_naziv'] == 'A'
    assert (j['neto'], j['ddv'], j['skupaj']) == ('180.00', '39.60', '219.60') and len(j['postavke']) == 1 and set(j['postavke'][0]) == CUSTOMER_LINE and j['postavke'][0]['koncna_cena'] == '219.60'
    assert D(j['postavke'][0]['izmera_skupaj']) == 1 and len(j['postavke'][0]['izmere']) == 1 and set(j['postavke'][0]['izmere'][0]) <= CUSTOMER_IZMERA
    assert set(j['ddv_po_stopnjah'][0]) == {'stopnja_ddv', 'osnova', 'ddv'}
    assert 'Lepilo' not in r.text and str(cat[0][1]) not in r.text and str(l) not in r.text and str(cat[0][2]) not in r.text and not any(k in r.text for k in NEVER)


def test_api_stranka_dobi_izmere_samo_za_zadnjo_poslano_razlicico_in_za_zahtevano_pri_odlocitvi(api, db):
    client, selected, users, a, _, p, M = api; q1 = sent(db, users, a, p); decide(db, users, p, q1, False)
    it = one(db, 'select id from quoteflow.postavka_projekta where projekt_id=%s', (p,))['id']
    as_owner(db, a, 'shrani_izmero', podjetje=a, projekt=p, postavka=it, izmera=None, odstej=False, kosi=D(1), dolzina=D(2), visina=D(3), sirina=None)
    q2 = sent(db, users, a, p); selected['name'] = 'customer'
    got = {x['id']: x for x in client.get(f'/api/projekti/{p}/ponudbe').json()}; assert set(got) == {str(q1), str(q2)}
    assert [len(l['izmere']) for l in got[str(q2)]['postavke']] == [2] and D(got[str(q2)]['postavke'][0]['izmera_skupaj']) == 7
    assert [l['izmere'] for l in got[str(q1)]['postavke']] == [[]] and D(got[str(q1)]['postavke'][0]['izmera_skupaj']) == 1, 'starejša različica: skupna izmera da, posamezne izmere ne'
    r = client.post(f'/api/projekti/{p}/ponudbe/{q2}/odlocitev', json={'sprejmi': True}); assert r.status_code == 200 and [len(l['izmere']) for l in r.json()['postavke']] == [2]


def test_api_stranka_vidi_nadomescenost_stare_razlicice(api, db):
    client, selected, users, a, _, p, M = api; q1 = sent(db, users, a, p); q2 = raw_quote(db, p, n=2)
    selected['name'] = 'customer'; assert [x['nadomescena'] for x in client.get(f'/api/projekti/{p}/ponudbe').json()] == [False]
    selected['name'] = 'owner_a'; assert client.post(f'{M}/ponudbe/{q2}/poslji').status_code == 200
    master = {x['id']: x['nadomescena'] for x in client.get(f'{M}/ponudbe').json()}; assert master == {str(q1): True, str(q2): False}
    selected['name'] = 'customer'; assert {x['id']: x['nadomescena'] for x in client.get(f'/api/projekti/{p}/ponudbe').json()} == {str(q1): True, str(q2): False}


@pytest.mark.parametrize('who', ['outsider', 'owner_a', 'owner_b', 'worker', 'admin'])
def test_api_tuj_seznam_ponudb_je_enak_nakljucnemu_projektu(api, db, who):
    client, selected, users, a, _, p, M = api; sent(db, users, a, p); selected['name'] = who
    f, r = client.get(f'/api/projekti/{p}/ponudbe'), client.get(f'/api/projekti/{uuid4()}/ponudbe')
    assert (f.status_code, f.json()) == (r.status_code, r.json()) and f.status_code in (200, 404) and f'P-{year(db)}' not in f.text


def test_api_stranka_sprejme_ponudbo_racun_osnutek_in_faza_termin(api, db):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = 'customer'
    r = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True}); assert r.status_code == 200, r.text
    assert r.json()['stanje'] == 'sprejeta' and set(r.json()) == CUSTOMER_TOP and invoices(db, q) == 1 and phase(db, p) == 'termin'
    again = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': False}); assert again.status_code == 409 and again.json()['detail'] == 'O tej ponudbi ni več mogoče odločati.'


def test_api_stranka_zavrne_ponudbo(api, db):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = 'customer'
    r = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': False}); assert r.status_code == 200 and r.json()['stanje'] == 'zavrnjena' and r.json()['odgovorjeno_ob']
    untouched(db, p, q, 'zavrnjena')


def test_api_odlocitev_potekla_in_neaktivno_podjetje_sta_409(api, db):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = 'customer'
    quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ}-1 where id=%s', (q,))
    r = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True}); assert r.status_code == 409 and r.json()['detail'] == 'Veljavnost ponudbe je potekla.'
    quiet(db, 'ponudba', f'update quoteflow.ponudba set velja_do={LJ}+1 where id=%s', (q,)); db.execute('update quoteflow.podjetje set aktivno=false where id=%s', (a,))
    r = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True}); assert r.status_code == 409 and r.json()['detail'] == 'Izvajalec trenutno ne posluje.'
    untouched(db, p, q)


@pytest.mark.parametrize('who', ['outsider', 'owner_a', 'owner_b', 'worker', 'admin'])
def test_api_napacen_akter_pri_odlocitvi_dobi_enak_404_kot_nakljucni_id(api, db, who):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = who
    f = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True}); r = client.post(f'/api/projekti/{uuid4()}/ponudbe/{uuid4()}/odlocitev', json={'sprejmi': True})
    assert f.status_code == 404 and (f.status_code, f.json()) == (r.status_code, r.json()); untouched(db, p, q)


def test_api_d9_mojster_kot_lastna_stranka_dobi_404(api, db):
    client, selected, users, a, _, _, M = api
    p = db.execute("insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(%s,%s,'Zase','O','L') returning id", (a, users['owner_a'][0])).fetchone()['id']
    q = sent(db, users, a, p); r = client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True})
    assert r.status_code == 404; untouched(db, p, q)


def test_api_odvzeta_vloga_stranke_je_403(api, db):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = 'customer'
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    assert client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json={'sprejmi': True}).status_code == 403
    assert client.get(f'/api/projekti/{p}/ponudbe').status_code == 403; untouched(db, p, q)


@pytest.mark.parametrize('body', [{}, {'sprejmi': None}, {'sprejmi': 'da'}, {'sprejmi': True, 'x': 1}, {'sprejmi': 2}])
def test_api_neveljavno_telo_odlocitve_je_422(api, db, body):
    client, selected, users, a, _, p, M = api; q = sent(db, users, a, p); selected['name'] = 'customer'
    assert client.post(f'/api/projekti/{p}/ponudbe/{q}/odlocitev', json=body).status_code == 422; untouched(db, p, q)
