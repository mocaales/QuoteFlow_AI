"""US-01 prošnja mojstra on disposable local Supabase: submit, atomic approval, single decision, isolation."""
import os
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user
from test_identity_database import api_client
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')

def form(**change): return {'naziv_podjetja': 'Novi mojster', 'maticna_stevilka': uuid4().hex[:30], 'davcna_stevilka': None, 'naslov_podjetja': 'Cesta 1'} | change

def submit(client, selected, who='customer', **change):
    selected['name'] = who
    return client.post('/api/prosnje', json=form(**change))


def test_stranka_odda_prosnjo_in_jo_vidi_samo_sama(api_client, identities):
    client, selected = api_client; users, _, _, _ = identities
    r = submit(client, selected); assert r.status_code == 201, r.text
    assert r.json()['stanje'] == 'oddana' and r.json()['uporabnik_id'] == str(users['customer'][0]) and r.json()['podjetje_id'] is None
    assert [p['id'] for p in client.get('/api/prosnje').json()] == [r.json()['id']]
    selected['name'] = 'outsider'; assert client.get('/api/prosnje').json() == []
    selected['name'] = 'admin'; assert client.get('/api/prosnje').json() == []
    assert [p['id'] for p in client.get('/api/admin/prosnje').json()] == [r.json()['id']]
    assert client.get('/api/admin/prosnje').json()[0]['e_posta'].startswith('customer-')


def test_odobritev_ustvari_podjetje_lastnika_in_aktivnega_mojstra(api_client, db, identities):
    client, selected = api_client; users, _, _, _ = identities
    data = form(); pid = submit(client, selected, **data).json()['id']
    selected['name'] = 'admin'
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}); assert r.status_code == 200, r.text
    assert r.json()['stanje'] == 'odobrena' and r.json()['podjetje_id'] and r.json()['odloceno_ob']
    company = db.execute('select * from quoteflow.podjetje where id=%s', (r.json()['podjetje_id'],)).fetchone()
    assert company['lastnik_id'] == users['customer'][0] and company['maticna_stevilka'] == data['maticna_stevilka'] and company['naziv'] == 'Novi mojster'
    assert db.execute("select count(*) n from quoteflow.vloga_uporabnika where uporabnik_id=%s and podjetje_id=%s and vloga='mojster' and aktivna", (users['customer'][0], company['id'])).fetchone()['n'] == 1
    selected['name'] = 'customer'; assert client.get('/api/podjetja/' + str(company['id'])).status_code == 200


def test_zavrnitev_ne_ustvari_podjetja(api_client, db):
    client, selected = api_client
    data = form(); pid = submit(client, selected, **data).json()['id']
    selected['name'] = 'admin'
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': False}); assert r.status_code == 200, r.text
    assert r.json()['stanje'] == 'zavrnjena' and r.json()['podjetje_id'] is None
    assert db.execute('select count(*) n from quoteflow.podjetje where maticna_stevilka=%s', (data['maticna_stevilka'],)).fetchone()['n'] == 0
    assert submit(client, selected, **data).status_code == 201  # rejected request frees the maticna


def test_druga_odlocitev_je_409_in_ne_ustvari_drugega_podjetja(api_client, db):
    client, selected = api_client
    data = form(); pid = submit(client, selected, **data).json()['id']; selected['name'] = 'admin'
    assert client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}).status_code == 200
    for odobri in (True, False):
        r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': odobri}); assert r.status_code == 409 and r.json()['detail'] == 'Prošnja je že obravnavana.'
    assert db.execute('select count(*) n from quoteflow.podjetje where maticna_stevilka=%s', (data['maticna_stevilka'],)).fetchone()['n'] == 1
    assert client.post(f'/api/admin/prosnje/{uuid4()}/odlocitev', json={'odobri': True}).status_code == 404


def test_nedovoljene_odlocitve_in_oddaje(api_client, db, identities):
    client, selected = api_client; users, a, _, _ = identities
    pid = submit(client, selected).json()['id']
    for who in ('customer', 'owner_a', 'worker', 'outsider'):
        selected['name'] = who
        assert client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}).status_code == 403, who
        assert client.get('/api/admin/prosnje').status_code == 403
    assert db.execute('select stanje from quoteflow.prosnja_mojstra where id=%s', (pid,)).fetchone()['stanje'] == 'oddana'
    # every account gets stranka automatically; with it revoked, owner_b has only mojster and the request is forbidden
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['owner_b'][0],))
    selected['name'] = 'owner_b'; assert client.post('/api/prosnje', json=form()).status_code == 403
    # revoked stranka role
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    assert submit(client, selected, 'customer').status_code == 403


def test_podvojena_ali_obstojeca_maticna_je_409(api_client, identities):
    client, selected = api_client; _, a, _, _ = identities
    data = form(); assert submit(client, selected, **data).status_code == 201
    r = submit(client, selected, 'outsider', **data); assert r.status_code == 409, r.text
    assert r.json()['detail'] == 'Podjetje ali oddana prošnja s to matično številko že obstaja.'
    selected['name'] = 'admin'; existing = client.get('/api/podjetja/' + str(a)).json()['maticna_stevilka']
    assert submit(client, selected, 'customer', maticna_stevilka=existing).status_code == 409


def test_neprijavljen_ali_brez_seje_ne_odda(api_client, db, identities):
    client, selected = api_client; users, _, _, _ = identities
    db.execute('delete from auth.sessions where id=%s', (users['customer'][1],))
    assert submit(client, selected).status_code == 401


def test_druga_oddana_prosnja_istega_uporabnika_je_409_in_ostane_ena_vrstica(api_client, db, identities):
    client, selected = api_client; users, _, _, _ = identities
    assert submit(client, selected).status_code == 201
    r = submit(client, selected); assert r.status_code == 409, r.text
    assert r.json()['detail'] == 'Že imate oddano prošnjo, ki čaka na odločitev.'
    assert db.execute("select count(*) n from quoteflow.prosnja_mojstra where uporabnik_id=%s and stanje='oddana'", (users['customer'][0],)).fetchone()['n'] == 1


def test_po_zavrnitvi_je_ponovna_oddaja_dovoljena(api_client):
    client, selected = api_client
    pid = submit(client, selected).json()['id']; selected['name'] = 'admin'
    assert client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': False}).status_code == 200
    assert submit(client, selected).status_code == 201


def _brez_pogojev(db, users, nacin):
    if nacin == 'vloge': db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga in ('stranka','delavec')", (users['customer'][0],))
    else: db.execute('update auth.users set email_confirmed_at=null where id=%s', (users['customer'][0],))


@pytest.mark.parametrize('nacin', ['vloge', 'eposta'])
def test_odobritev_neupravicenega_vlagatelja_je_409_in_ne_ustvari_nicesar(api_client, db, identities, nacin):
    client, selected = api_client; users, _, _, _ = identities
    data = form(); pid = submit(client, selected, **data).json()['id']
    _brez_pogojev(db, users, nacin); selected['name'] = 'admin'
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}); assert r.status_code == 409, r.text
    assert r.json()['detail'] == 'Vlagatelj ne izpolnjuje pogojev za vlogo mojstra (potrjena e-pošta in aktivna vloga stranke ali delavca).'
    assert db.execute('select stanje, podjetje_id from quoteflow.prosnja_mojstra where id=%s', (pid,)).fetchone() == {'stanje': 'oddana', 'podjetje_id': None}
    assert db.execute('select count(*) n from quoteflow.podjetje where maticna_stevilka=%s', (data['maticna_stevilka'],)).fetchone()['n'] == 0
    assert db.execute("select count(*) n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='mojster' and aktivna", (users['customer'][0],)).fetchone()['n'] == 0


@pytest.mark.parametrize('nacin', ['vloge', 'eposta'])
def test_zavrnitev_neupravicenega_vlagatelja_se_vedno_dela(api_client, db, identities, nacin):
    client, selected = api_client; users, _, _, _ = identities
    pid = submit(client, selected).json()['id']
    _brez_pogojev(db, users, nacin); selected['name'] = 'admin'
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': False}); assert r.status_code == 200, r.text
    assert r.json()['stanje'] == 'zavrnjena'


def _sqlstate(db, sql, params):
    with pytest.raises(psycopg.Error) as e:
        with db.transaction(): db.execute(sql, params)
    return e.value.sqlstate


def test_sql_funkcije_dvigajo_namenske_sqlstate_kode(api_client, db, identities):
    client, selected = api_client; users, a, _, _ = identities
    data = form(); pid = submit(client, selected, **data).json()['id']
    existing = db.execute('select maticna_stevilka m from quoteflow.podjetje where id=%s', (a,)).fetchone()['m']
    with as_user(db, users['customer']):
        odda = 'select * from quoteflow_private.oddaj_prosnjo(%s,%s,%s,%s)'
        assert _sqlstate(db, odda, ('X', uuid4().hex[:30], None, 'Y')) == 'QFP02'
    with as_user(db, users['outsider']):
        assert _sqlstate(db, odda, ('X', data['maticna_stevilka'], None, 'Y')) == 'QFP04'
        assert _sqlstate(db, odda, ('X', existing, None, 'Y')) == 'QFP04'
    with as_user(db, users['admin']):
        assert db.execute('select * from quoteflow_private.odloci_prosnjo(%s,false)', (pid,)).fetchone()['stanje'] == 'zavrnjena'
        assert _sqlstate(db, 'select * from quoteflow_private.odloci_prosnjo(%s,true)', (pid,)) == 'QFP01'


def test_odobritev_z_maticno_podjetja_ustvarjenega_med_cakanjem_je_409_qfp04_brez_sprememb(api_client, db, identities):
    client, selected = api_client; users, _, _, _ = identities
    data = form(); pid = submit(client, selected, **data).json()['id']
    # a pending request does not block the admin's direct creation; the company then takes the maticna
    with as_user(db, users['admin']):
        db.execute('select * from quoteflow_private.ustvari_podjetje(%s,%s,%s,%s,%s)', (users['outsider'][0], 'Neposredno', data['maticna_stevilka'], None, 'Ulica 2'))
        assert _sqlstate(db, 'select * from quoteflow_private.odloci_prosnjo(%s,true)', (pid,)) == 'QFP04'
    selected['name'] = 'admin'
    r = client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': True}); assert r.status_code == 409, r.text
    assert r.json()['detail'] == 'Podjetje ali oddana prošnja s to matično številko že obstaja.'
    assert db.execute('select stanje, podjetje_id from quoteflow.prosnja_mojstra where id=%s', (pid,)).fetchone() == {'stanje': 'oddana', 'podjetje_id': None}
    assert db.execute('select count(*) n from quoteflow.podjetje where maticna_stevilka=%s', (data['maticna_stevilka'],)).fetchone()['n'] == 1
    assert db.execute("select count(*) n from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='mojster' and aktivna", (users['customer'][0],)).fetchone()['n'] == 0
    assert client.post(f'/api/admin/prosnje/{pid}/odlocitev', json={'odobri': False}).status_code == 200  # rejection still works
