"""US-06 termin in izvedba (model v3; sprejeta ponudba nastane prek postavk projekta, pošiljanja in odločitve stranke, glej v3_quotes.accepted): doloci_termin, zakljuci_izvedbo, revizijska sled, izolacija in API na disposable local Supabase."""
import os
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user, catalog
from test_identity_database import api_client
from v3_quotes import env, call, bad, fails, quiet, new_project, accepted  # noqa: F401
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
TODAY = "(date_trunc('day', now() at time zone 'Europe/Ljubljana') at time zone 'Europe/Ljubljana')"
NO_ONE = ('42501', 'P0002')
M07 = 'V tej fazi projekta to dejanje ni dovoljeno.'


def one(db, sql, args=()): return db.execute(sql, args).fetchone()


def ts(db, expr): return one(db, f'select ({expr}) as t')['t']


def in_izvedba(db, p, od=TODAY, do=f"{TODAY}+interval '2 days'", finished=False):
    quiet(db, 'projekt', f"update quoteflow.projekt set faza='izvedba', termin_od={od}, termin_do={do}, izvedba_koncana_ob={'now()' if finished else 'null'} where id=%s", (p,))


def project(db, p): return one(db, 'select * from quoteflow.projekt where id=%s', (p,))


QUOTE_EVENTS = ('poslana', 'sprejeta', 'zavrnjena')  # written by v3_quotes.accepted(); these tests pin the later phases only
def audit(db, p): return sorted((x['dejanje'], x['izvajalec_id']) for x in db.execute('select * from quoteflow_private.dogodek_dokumenta where projekt_id=%s and dejanje<>all(%s)', (p, list(QUOTE_EVENTS))).fetchall())


def term(db, users, a, p, od=TODAY, do=f"{TODAY}+interval '2 days'", who='owner_a'): return call(db, users, who, 'doloci_termin', a, p, ts(db, od), ts(db, do))


def bad_term(db, users, state, a, p, od=TODAY, do=f"{TODAY}+interval '2 days'", who='owner_a'):
    with as_user(db, users[who]): fails(db, f'select * from {Q}doloci_termin(%s,%s,%s,%s)', (a, p, ts(db, od), ts(db, do)), state)


def bad_class(db, users, a, p, od, do):
    with as_user(db, users['owner_a']):
        with pytest.raises(psycopg.Error) as e:
            with db.transaction(): db.execute(f'select * from {Q}doloci_termin(%s,%s,({od})::timestamptz,({do})::timestamptz)', (a, p))
    assert e.value.sqlstate[:2] == '22', e.value.sqlstate


def untouched(db, p, faza='termin'):
    r = project(db, p); assert r['faza'] == faza and r['izvedba_koncana_ob'] is None and r['zakljuceno_ob'] is None; return r


# doloci_termin
def test_termin_prvic_nastavi_cas_fazo_izvedba_in_revizijsko_sled(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    r = term(db, users, a, p)
    assert r['id'] == p and r['faza'] == 'izvedba' and r['termin_od'] == ts(db, TODAY) and r['termin_do'] == ts(db, f"{TODAY}+interval '2 days'") and r['izvedba_koncana_ob'] is None
    assert audit(db, p) == [('termin', users['owner_a'][0])]
    log = one(db, "select * from quoteflow_private.dogodek_dokumenta where projekt_id=%s and dejanje='termin'", (p,)); assert log['podjetje_id'] == a and log['ob']


def test_termin_danes_ob_polnoci_je_dovoljen_vceraj_je_qfp18(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    bad_term(db, users, 'QFP18', a, p, od=f"{TODAY}-interval '1 second'", do=f"{TODAY}+interval '1 day'")
    bad_term(db, users, 'QFP18', a, p, od="now()-interval '3 days'", do="now()+interval '1 day'")
    untouched(db, p); assert not audit(db, p)
    assert term(db, users, a, p, od=TODAY, do=f"{TODAY}+interval '1 hour'")['faza'] == 'izvedba'


def test_prestavitev_termina_med_izvedbo_ohrani_fazo_in_zapise_novo_dejanje(env, db):
    users, a, _, p, _ = env; accepted(db, p); term(db, users, a, p)
    r = term(db, users, a, p, od=f"{TODAY}+interval '1 day'", do=f"{TODAY}+interval '3 days'")
    assert r['faza'] == 'izvedba' and r['termin_od'] == ts(db, f"{TODAY}+interval '1 day'") and r['izvedba_koncana_ob'] is None
    assert [d for d, _ in audit(db, p)] == ['termin', 'termin']


def test_prestavitev_v_fazi_termin_brez_prejsnjega_termina_je_dovoljena(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    quiet(db, 'projekt', "update quoteflow.projekt set termin_od=date_trunc('day',now()), termin_do=date_trunc('day',now())+interval '1 day' where id=%s", (p,))
    assert term(db, users, a, p)['faza'] == 'izvedba'


@pytest.mark.parametrize('faza', ['pregled', 'ogled', 'ponudba', 'obracun', 'zakljucen'])
def test_termin_v_neustrezni_fazi_je_qfp07(env, db, faza):
    users, a, _, p, _ = env; accepted(db, p)
    quiet(db, 'projekt', "update quoteflow.projekt set faza=%s, zakljuceno_ob=case when %s='zakljucen' then now() end where id=%s", (faza, faza, p))
    bad_term(db, users, 'QFP07', a, p); assert project(db, p)['termin_od'] is None and not audit(db, p)


def test_termin_brez_sprejema_je_qfp07(env, db):
    users, a, _, p, _ = env; bad_term(db, users, 'QFP07', a, p); assert project(db, p)['faza'] == 'pregled'


def test_termin_po_zakljuceni_izvedbi_je_qfp07(env, db):
    users, a, _, p, _ = env; accepted(db, p); in_izvedba(db, p, finished=True)
    bad_term(db, users, 'QFP07', a, p, od=f"{TODAY}+interval '1 day'", do=f"{TODAY}+interval '2 days'")
    assert project(db, p)['termin_od'] == ts(db, TODAY)


def test_termin_neskoncen_je_razred_22(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    bad_class(db, users, a, p, "'infinity'::timestamptz", "'infinity'::timestamptz"); bad_class(db, users, a, p, TODAY, "'infinity'::timestamptz")
    bad_class(db, users, a, p, "'infinity'::timestamptz", f"{TODAY}+interval '1 day'"); bad_class(db, users, a, p, "'-infinity'::timestamptz", TODAY)
    untouched(db, p); assert project(db, p)['termin_od'] is None and not audit(db, p)


@pytest.mark.parametrize('do', [TODAY, f"{TODAY}-interval '1 hour'", f"{TODAY}-interval '5 days'"])
def test_konec_ni_po_zacetku_je_razred_22(env, db, do):
    users, a, _, p, _ = env; accepted(db, p); bad_class(db, users, a, p, TODAY, do); untouched(db, p); assert not audit(db, p)


def test_termin_najvec_366_dni(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    bad_class(db, users, a, p, TODAY, f"{TODAY}+interval '367 days'"); bad_class(db, users, a, p, TODAY, f"{TODAY}+interval '366 days 1 second'"); untouched(db, p)
    assert term(db, users, a, p, do=f"{TODAY}+interval '366 days'")['faza'] == 'izvedba'


def test_termin_neznan_projekt_tuje_podjetje_in_napacni_akterji(env, db):
    users, a, b, p, _ = env; accepted(db, p)
    bad_term(db, users, 'P0002', a, uuid4()); bad_term(db, users, '42501', a, p, who='owner_b')
    pb = new_project(db, users, b); accepted(db, pb, number='P-B'); bad_term(db, users, 'P0002', a, pb); bad_term(db, users, 'P0002', b, p, who='owner_b')
    for who in ('worker', 'customer', 'outsider', 'admin'): bad_term(db, users, '42501', a, p, who=who)
    untouched(db, p); untouched(db, pb); assert not audit(db, p) and not audit(db, pb)


def test_termin_z_odvzeto_vlogo_ali_neaktivnim_podjetjem_ne_gre(env, db):
    users, a, _, p, _ = env; accepted(db, p)
    role = one(db, "insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a))['id']
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,)); bad_term(db, users, '42501', a, p, who='outsider')
    db.execute('update quoteflow.podjetje set aktivno=false where id=%s', (a,)); bad_term(db, users, '42501', a, p); untouched(db, p)


# zakljuci_izvedbo
def test_zakljuci_izvedbo_nastavi_cas_fazo_pusti_in_zapise_revizijsko_sled(env, db):
    users, a, _, p, _ = env; accepted(db, p); term(db, users, a, p)
    r = call(db, users, 'owner_a', 'zakljuci_izvedbo', a, p)
    assert r['id'] == p and r['faza'] == 'izvedba' and r['izvedba_koncana_ob'] and r['zakljuceno_ob'] is None
    assert audit(db, p) == sorted([('termin', users['owner_a'][0]), ('izvedba_koncana', users['owner_a'][0])])


def test_zakljuci_pred_zacetkom_termina_je_qfp14(env, db):
    users, a, _, p, _ = env; accepted(db, p); term(db, users, a, p, od="now()+interval '2 days'", do="now()+interval '3 days'")
    bad(db, users, 'owner_a', 'QFP14', 'zakljuci_izvedbo', a, p); assert project(db, p)['izvedba_koncana_ob'] is None and [d for d, _ in audit(db, p)] == ['termin']


@pytest.mark.parametrize('faza', ['pregled', 'ogled', 'ponudba', 'termin', 'obracun'])
def test_zakljuci_v_neustrezni_fazi_je_qfp07(env, db, faza):
    users, a, _, p, _ = env; accepted(db, p)
    quiet(db, 'projekt', "update quoteflow.projekt set faza=%s where id=%s", (faza, p))
    bad(db, users, 'owner_a', 'QFP07', 'zakljuci_izvedbo', a, p); assert not audit(db, p)


def test_zakljuci_drugic_je_qfp07(env, db):
    users, a, _, p, _ = env; accepted(db, p); term(db, users, a, p); call(db, users, 'owner_a', 'zakljuci_izvedbo', a, p)
    first = project(db, p)['izvedba_koncana_ob']
    bad(db, users, 'owner_a', 'QFP07', 'zakljuci_izvedbo', a, p); assert project(db, p)['izvedba_koncana_ob'] == first and len(audit(db, p)) == 2


def test_zakljuci_neznan_projekt_tuje_podjetje_in_napacni_akterji(env, db):
    users, a, b, p, _ = env; accepted(db, p); in_izvedba(db, p)
    bad(db, users, 'owner_a', 'P0002', 'zakljuci_izvedbo', a, uuid4()); bad(db, users, 'owner_b', '42501', 'zakljuci_izvedbo', a, p); bad(db, users, 'owner_b', 'P0002', 'zakljuci_izvedbo', b, p)
    for who in ('worker', 'customer', 'outsider', 'admin'): bad(db, users, who, '42501', 'zakljuci_izvedbo', a, p)
    assert project(db, p)['izvedba_koncana_ob'] is None and not audit(db, p)


def test_zakljucen_projekt_se_ne_da_nastaviti_mimo_placila(env, db):
    users, a, _, p, _ = env; accepted(db, p); in_izvedba(db, p, finished=True)
    for faza in ('obracun', 'zakljucen'):
        with pytest.raises(psycopg.Error):
            with db.transaction():
                db.execute("update quoteflow.projekt set faza=%s, zakljuceno_ob=case when %s='zakljucen' then now() end where id=%s", (faza, faza, p)); db.execute('set constraints all immediate')


# ACL
def test_funkcije_so_samo_za_authenticated_in_stari_podpisi_ne_obstajajo(db):
    for f in ('doloci_termin(uuid,uuid,timestamptz,timestamptz)', 'zakljuci_izvedbo(uuid,uuid)'):
        for role in ('anon', 'service_role', 'quoteflow_app', 'public'): assert not one(db, "select has_function_privilege(%s,%s,'execute') as p", (role, Q + f))['p'], (role, f)
        assert one(db, "select has_function_privilege('authenticated',%s,'execute') as p", (Q + f,))['p'], f
    assert one(db, 'select to_regprocedure(%s) as f', (Q + 'doloci_termin(uuid,timestamptz,timestamptz)',))['f'] is None


# API
@pytest.fixture
def api(env, api_client):
    client, selected = api_client; users, a, b, p, cat = env; selected['name'] = 'owner_a'
    return client, selected, users, a, b, p, f'/api/podjetja/{a}/projekti/{p}'


def iso(db, expr): return ts(db, expr).isoformat()


def body(db, od=TODAY, do=f"{TODAY}+interval '2 days'"): return {'termin_od': iso(db, od), 'termin_do': iso(db, do)}


PROJECT_KEYS = {'id', 'naziv', 'opis', 'lokacija_izvedbe', 'faza', 'stranka_ime', 'stranka_priimek', 'stranka_e_posta', 'termin_od', 'termin_do', 'izvedba_koncana_ob', 'zakljuceno_ob'}


def test_api_termin_vrne_projekt_s_fazo_izvedba_in_novimi_polji(api, db):
    client, _, users, a, _, p, M = api; accepted(db, p)
    r = client.put(f'{M}/termin', json=body(db)); assert r.status_code == 200, r.text
    j = r.json(); assert set(j) == PROJECT_KEYS and j['id'] == str(p) and j['faza'] == 'izvedba' and j['termin_od'] and j['izvedba_koncana_ob'] is None and j['zakljuceno_ob'] is None
    assert PROJECT_KEYS <= set(client.get(f'/api/podjetja/{a}/projekti').json()[0])


def test_api_izvedba_zakljuci_in_ne_dvakrat(api, db):
    client, _, users, a, _, p, M = api; accepted(db, p); client.put(f'{M}/termin', json=body(db))
    r = client.post(f'{M}/izvedba'); assert r.status_code == 200, r.text
    assert r.json()['izvedba_koncana_ob'] and r.json()['faza'] == 'izvedba' and set(r.json()) == PROJECT_KEYS
    again = client.post(f'{M}/izvedba'); assert again.status_code == 409 and again.json()['detail'] == M07
    resched = client.put(f'{M}/termin', json=body(db, od=f"{TODAY}+interval '1 day'", do=f"{TODAY}+interval '2 days'")); assert resched.status_code == 409 and resched.json()['detail'] == M07


def test_api_izvedba_pred_zacetkom_termina_je_409_s_sporocilom(api, db):
    client, _, users, a, _, p, M = api; accepted(db, p); client.put(f'{M}/termin', json=body(db, od="now()+interval '2 days'", do="now()+interval '3 days'"))
    r = client.post(f'{M}/izvedba'); assert r.status_code == 409 and r.json()['detail'] == 'Izvedbe ni mogoče zaključiti pred začetkom termina.'


def test_api_termin_v_preteklosti_je_409_brez_sprejema_409_faza(api, db):
    client, _, users, a, _, p, M = api
    r = client.put(f'{M}/termin', json=body(db)); assert r.status_code == 409 and r.json()['detail'] == M07
    accepted(db, p)
    r = client.put(f'{M}/termin', json=body(db, od="now()-interval '2 days'", do="now()+interval '1 day'")); assert r.status_code == 409 and r.json()['detail'] == 'Termin se ne sme začeti v preteklosti.'
    assert client.post(f'{M}/izvedba').status_code == 409; untouched(db, p)


def test_api_neveljaven_termin_je_422(api, db):
    client, _, users, a, _, p, M = api; accepted(db, p)
    r = client.put(f'{M}/termin', json=body(db, do=TODAY)); assert r.status_code == 422 and 'Konec termina mora biti po začetku.' in r.text
    assert client.put(f'{M}/termin', json=body(db, do=f"{TODAY}-interval '1 day'")).status_code == 422
    assert client.put(f'{M}/termin', json=body(db, do=f"{TODAY}+interval '400 days'")).status_code == 422
    good = body(db)
    for bad_body in ({}, {'termin_od': good['termin_od']}, good | {'termin_do': None}, good | {'termin_od': 'jutri'}, good | {'termin_do': 'infinity'}, good | {'termin_od': 'infinity'}, good | {'x': 1}): assert client.put(f'{M}/termin', json=bad_body).status_code == 422, bad_body
    untouched(db, p)


def test_api_tujec_dobi_enak_404_kot_nakljucni_id_in_nemojstri_403(api, db):
    client, selected, users, a, b, p, M = api; accepted(db, p); selected['name'] = 'owner_b'; good = body(db)
    for method, suffix, data in (('put', '/termin', good), ('post', '/izvedba', None)):
        f = getattr(client, method)(f'/api/podjetja/{b}/projekti/{p}{suffix}', **({'json': data} if data else {})); r = getattr(client, method)(f'/api/podjetja/{b}/projekti/{uuid4()}{suffix}', **({'json': data} if data else {}))
        assert f.status_code == 404 and (f.status_code, f.json()) == (r.status_code, r.json()), suffix
        assert getattr(client, method)(f'{M}{suffix}', **({'json': data} if data else {})).status_code == 403
        for who in ('customer', 'worker', 'outsider', 'admin'):
            selected['name'] = who; assert getattr(client, method)(f'{M}{suffix}', **({'json': data} if data else {})).status_code == 403, (who, suffix)
        selected['name'] = 'owner_b'
    untouched(db, p)


def test_api_stranka_vidi_termin_in_nova_polja_v_svojem_projektu(api, db):
    client, selected, users, a, _, p, M = api; accepted(db, p); client.put(f'{M}/termin', json=body(db)); client.post(f'{M}/izvedba')
    selected['name'] = 'customer'; j = client.get(f'/api/projekti/{p}').json()
    assert j['faza'] == 'izvedba' and j['termin_od'] and j['termin_do'] and j['izvedba_koncana_ob'] and j['zakljuceno_ob'] is None and {'izvedba_koncana_ob', 'zakljuceno_ob'} <= set(j)
    assert {'izvedba_koncana_ob', 'zakljuceno_ob'} <= set(client.get('/api/projekti').json()[0])
