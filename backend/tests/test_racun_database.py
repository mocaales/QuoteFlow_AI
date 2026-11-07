"""US-07 račun in plačilo (model v3; sprejeta ponudba in račun osnutek nastaneta prek postavk projekta, glej v3_quotes.accepted): izdaj_racun, placaj_racun, številčenje, nespremenljivost, revizijska sled, stranka in API na disposable local Supabase."""
import os
from uuid import uuid4
import psycopg
import pytest
from test_model_database import db, identities, as_user, catalog
from test_identity_database import api_client
from v3_quotes import env, call, bad, fails, quiet, new_project, year  # noqa: F401
from test_izvedba_database import one, accepted, in_izvedba, project, audit, api
pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')
Q = 'quoteflow_private.'
M07 = 'V tej fazi projekta to dejanje ni dovoljeno.'
SOON = 'current_date+8'


def ready(db, p, number='P-2026-001', finished=True):
    q, r = accepted(db, p, number=number); in_izvedba(db, p, finished=finished); return q, r


REC = ('Ime Priimek', 'Maribor')


def rbody(db, expr=SOON, **change): return {'prejemnik_naziv': REC[0], 'prejemnik_naslov': REC[1], 'zapade_dne': day(db, expr)} | change


def issue(db, users, a, p, zapade=None, who='owner_a', rec=REC): return call(db, users, who, 'izdaj_racun', a, p, *rec, zapade or one(db, f'select {SOON} as d')['d'])


def invoice(db, r): return one(db, 'select * from quoteflow.racun where id=%s', (r,))


def untouched(db, p, r, faza='izvedba'):
    i = invoice(db, r); assert i['stanje_dokumenta'] == 'osnutek' and i['stevilka'] is None and i['placano_ob'] is None and project(db, p)['faza'] == faza


# izdaj_racun
def test_izdaj_racun_napolni_stevilko_izdajatelja_prejemnika_in_fazo_obracun(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p)
    i = issue(db, users, a, p)
    assert i['id'] == r and i['stanje_dokumenta'] == 'izdan' and i['stevilka'] == f'R-{year(db)}-001' and i['stanje_placila'] == 'neplacan' and i['placano_ob'] is None
    assert (i['izdajatelj_naziv'], i['izdajatelj_naslov'], i['izdajatelj_davcna']) == ('A', 'Naslov 1', 'SI12345678')
    assert (i['prejemnik_naziv'], i['prejemnik_naslov']) == ('Ime Priimek', 'Maribor')
    assert i['izdan_ob'] and i['izdan_ob'] == i['poslan_ob'] and i['zapade_dne'] == one(db, f'select {SOON} as d')['d']
    assert project(db, p)['faza'] == 'obracun'
    log = [x for x in db.execute("select * from quoteflow_private.dogodek_dokumenta where projekt_id=%s and dejanje='izdan'", (p,))]
    assert len(log) == 1 and (log[0]['dejanje'], log[0]['izvajalec_id'], log[0]['racun_id'], log[0]['podjetje_id']) == ('izdan', users['owner_a'][0], r, a)


def test_zapade_danes_je_dovoljeno_vceraj_je_qfp21(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p)
    bad(db, users, 'owner_a', 'QFP21', 'izdaj_racun', a, p, *REC, one(db, 'select current_date-1 as d')['d']); untouched(db, p, r); assert not audit(db, p)
    assert issue(db, users, a, p, one(db, 'select current_date as d')['d'])['stanje_dokumenta'] == 'izdan'


def test_stevilke_so_zaporedne_po_podjetju_in_neodvisne_med_podjetji(env, db):
    users, a, b, p, _ = env; ready(db, p); p2 = new_project(db, users, a); ready(db, p2, number='P-2026-002')
    assert issue(db, users, a, p)['stevilka'] == f'R-{year(db)}-001' and issue(db, users, a, p2)['stevilka'] == f'R-{year(db)}-002'
    pb = new_project(db, users, b); ready(db, pb, number='P-B'); assert call(db, users, 'owner_b', 'izdaj_racun', b, pb, *REC, one(db, f'select {SOON} as d')['d'])['stevilka'] == f'R-{year(db)}-001'


def test_prejemnik_je_natanko_vnesen_brez_nadomestila_z_e_postami(env, db):
    users, a, _, p, _ = env; ready(db, p)
    db.execute("update quoteflow.uporabnik set ime='Jože', priimek='Šuštar' where id=%s", (users['customer'][0],)); db.execute("update quoteflow.projekt set lokacija_izvedbe='' where id=%s", (p,))
    i = issue(db, users, a, p, rec=('  Jože Šuštar s.p.  ', 'Celje, Cesta 5'))
    assert (i['prejemnik_naziv'], i['prejemnik_naslov']) == ('Jože Šuštar s.p.', 'Celje, Cesta 5') and '@' not in i['prejemnik_naziv'] + i['prejemnik_naslov']
    assert i['stanje_dokumenta'] == 'izdan'


@pytest.mark.parametrize('rec', [('', 'Maribor'), ('   ', 'Maribor'), ('Ime', ''), ('Ime', '  '), (None, 'Maribor'), ('Ime', None), ('x' * 201, 'Maribor'), ('Ime', 'x' * 301)])
def test_prazen_ali_predolg_prejemnik_je_22023_in_racun_ostane_osnutek(env, db, rec):
    users, a, _, p, _ = env; q, r = ready(db, p)
    bad(db, users, 'owner_a', '22023', 'izdaj_racun', a, p, *rec, one(db, f'select {SOON} as d')['d']); untouched(db, p, r); assert not audit(db, p)


def test_e_posta_stranke_nikoli_ne_pride_v_posnetek_ce_je_mojster_ne_vnese(env, db):
    users, a, _, p, _ = env; ready(db, p); i = issue(db, users, a, p)
    assert one(db, "select (prejemnik_naziv||prejemnik_naslov) like '%%@%%' as m from quoteflow.racun where id=%s", (i['id'],))['m'] is False


def test_izdan_racun_s_praznim_prejemnikom_ali_izdajateljem_je_zavrnjen_tudi_neposredno(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p)
    for col in ('prejemnik_naziv', 'prejemnik_naslov', 'izdajatelj_naziv', 'izdajatelj_davcna'):
        with pytest.raises(psycopg.Error) as e:
            vals = {'izdajatelj_naziv': 'A', 'izdajatelj_naslov': 'N', 'izdajatelj_davcna': 'SI1', 'prejemnik_naziv': 'P', 'prejemnik_naslov': 'N', col: '  '}
            with db.transaction(): db.execute(f"update quoteflow.racun set stanje_dokumenta='izdan', stevilka='R-9999-001', {', '.join(k + '=%s' for k in vals)}, izdan_ob=now(), poslan_ob=now(), zapade_dne=current_date where id=%s", (*vals.values(), r))
        assert e.value.sqlstate in ('23514', '55000'), (col, e.value.sqlstate)
    untouched(db, p, r)


def test_neposredno_praznjenje_prejemnika_izdanega_racuna_je_23514_ali_55000(env, db):
    users, a, _, p, _ = env; ready(db, p); i = issue(db, users, a, p)
    for col in ('prejemnik_naziv', 'prejemnik_naslov', 'izdajatelj_naziv', 'izdajatelj_davcna'):
        with pytest.raises(psycopg.Error) as e:
            with db.transaction(): db.execute(f"update quoteflow.racun set {col}='' where id=%s", (i['id'],))
        assert e.value.sqlstate in ('23514', '55000'), (col, e.value.sqlstate)
    assert invoice(db, i['id'])['prejemnik_naziv'] == 'Ime Priimek'


def test_check_na_racunu_zahteva_neprazna_polja_ko_je_izdan(db):
    d = ' '.join(r['d'] for r in db.execute("select pg_get_constraintdef(c.oid) as d from pg_constraint c where c.conrelid='quoteflow.racun'::regclass and c.contype='c'").fetchall())
    for col in ('prejemnik_naziv', 'prejemnik_naslov', 'izdajatelj_naziv', 'izdajatelj_davcna'): assert f'TRIM(BOTH FROM {col})' in d, col


def test_prazna_lokacija_projekta_ne_ovira_izdaje_ker_naslov_vnese_mojster(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p); quiet(db, 'projekt', "update quoteflow.projekt set lokacija_izvedbe='' where id=%s", (p,))
    assert issue(db, users, a, p)['stanje_dokumenta'] == 'izdan'


def test_izdaja_pred_zakljuceno_izvedbo_je_qfp07(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p, finished=False)
    bad(db, users, 'owner_a', 'QFP07', 'izdaj_racun', a, p, *REC, one(db, f'select {SOON} as d')['d']); untouched(db, p, r); assert not audit(db, p)
    p2 = new_project(db, users, a); q2, r2 = accepted(db, p2, number='P-2026-002')
    bad(db, users, 'owner_a', 'QFP07', 'izdaj_racun', a, p2, *REC, one(db, f'select {SOON} as d')['d']); untouched(db, p2, r2, 'termin')


def test_druga_izdaja_je_qfp07_in_stevilka_ostane(env, db):
    users, a, _, p, _ = env; ready(db, p); first = issue(db, users, a, p)
    bad(db, users, 'owner_a', 'QFP07', 'izdaj_racun', a, p, *REC, one(db, f'select {SOON} as d')['d'])
    assert invoice(db, first['id'])['stevilka'] == first['stevilka'] and len(audit(db, p)) == 1


def test_podjetje_brez_davcne_je_qfp15(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p); db.execute('update quoteflow.podjetje set davcna_stevilka=null where id=%s', (a,))
    bad(db, users, 'owner_a', 'QFP15', 'izdaj_racun', a, p, *REC, one(db, f'select {SOON} as d')['d']); untouched(db, p, r); assert not audit(db, p)


def test_izdan_racun_je_nespremenljiv(env, db):
    users, a, _, p, _ = env; ready(db, p); i = issue(db, users, a, p)
    for col, val in (('prejemnik_naziv', 'Drug'), ('stevilka', 'R-X'), ('zapade_dne', None)):
        fails(db, f'update quoteflow.racun set {col}=%s where id=%s', (val, i['id']), '55000')
    fails(db, 'delete from quoteflow.racun where id=%s', (i['id'],), '55000')


def test_izdaja_neznan_projekt_tuje_podjetje_in_napacni_akterji(env, db):
    users, a, b, p, _ = env; q, r = ready(db, p); d = one(db, f'select {SOON} as d')['d']
    bad(db, users, 'owner_a', 'P0002', 'izdaj_racun', a, uuid4(), *REC, d); bad(db, users, 'owner_b', '42501', 'izdaj_racun', a, p, *REC, d); bad(db, users, 'owner_b', 'P0002', 'izdaj_racun', b, p, *REC, d)
    pb = new_project(db, users, b); qb, rb = ready(db, pb, number='P-B'); bad(db, users, 'owner_a', 'P0002', 'izdaj_racun', a, pb, *REC, d)
    for who in ('worker', 'customer', 'outsider', 'admin'): bad(db, users, who, '42501', 'izdaj_racun', a, p, *REC, d)
    untouched(db, p, r); untouched(db, pb, rb); assert not audit(db, p) and not audit(db, pb)


def test_izdaja_z_odvzeto_vlogo_ali_neaktivnim_podjetjem_ne_gre(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p); d = one(db, f'select {SOON} as d')['d']
    role = one(db, "insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'mojster') returning id", (users['outsider'][0], a))['id']
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where id=%s', (role,)); bad(db, users, 'outsider', '42501', 'izdaj_racun', a, p, *REC, d)
    db.execute('update quoteflow.podjetje set aktivno=false where id=%s', (a,)); bad(db, users, 'owner_a', '42501', 'izdaj_racun', a, p, *REC, d); untouched(db, p, r)


# placaj_racun
def test_placilo_zakljuci_projekt_in_zapise_revizijsko_sled(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p); issue(db, users, a, p)
    i = call(db, users, 'owner_a', 'placaj_racun', a, p)
    assert i['id'] == r and i['placano_ob'] and i['stanje_placila'] == 'placan' and i['stanje_dokumenta'] == 'izdan'
    pr = project(db, p); assert pr['faza'] == 'zakljucen' and pr['zakljuceno_ob']
    assert audit(db, p) == sorted([('izdan', users['owner_a'][0]), ('placan', users['owner_a'][0])])
    assert one(db, "select racun_id from quoteflow_private.dogodek_dokumenta where projekt_id=%s and dejanje='placan'", (p,))['racun_id'] == r


def test_placilo_osnutka_je_qfp07(env, db):
    users, a, _, p, _ = env; q, r = ready(db, p)
    bad(db, users, 'owner_a', 'QFP07', 'placaj_racun', a, p); untouched(db, p, r); assert not audit(db, p)


def test_placilo_dvakrat_je_qfp07(env, db):
    users, a, _, p, _ = env; ready(db, p); issue(db, users, a, p); first = call(db, users, 'owner_a', 'placaj_racun', a, p)
    bad(db, users, 'owner_a', 'QFP07', 'placaj_racun', a, p); assert invoice(db, first['id'])['placano_ob'] == first['placano_ob'] and len(audit(db, p)) == 2


def test_placilo_neznan_projekt_tuje_podjetje_in_napacni_akterji(env, db):
    users, a, b, p, _ = env; ready(db, p); issue(db, users, a, p)
    bad(db, users, 'owner_a', 'P0002', 'placaj_racun', a, uuid4()); bad(db, users, 'owner_b', '42501', 'placaj_racun', a, p); bad(db, users, 'owner_b', 'P0002', 'placaj_racun', b, p)
    for who in ('worker', 'customer', 'outsider', 'admin'): bad(db, users, who, '42501', 'placaj_racun', a, p)
    assert project(db, p)['faza'] == 'obracun' and invoice_paid(db, p) is None and [d for d, _ in audit(db, p)] == ['izdan']


def invoice_paid(db, p): return one(db, 'select r.placano_ob from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id where q.projekt_id=%s', (p,))['placano_ob']


def test_zakljucen_ni_dosegljiv_mimo_placila(env, db):
    users, a, _, p, _ = env; ready(db, p); issue(db, users, a, p)
    with pytest.raises(psycopg.Error):
        with db.transaction():
            db.execute("update quoteflow.projekt set faza='zakljucen', zakljuceno_ob=now() where id=%s", (p,)); db.execute('set constraints all immediate')


# ACL, RLS, sočasnost
def test_funkcije_so_samo_za_authenticated_in_stari_podpisi_ne_obstajajo(db):
    for f in ('izdaj_racun(uuid,uuid,text,text,date)', 'placaj_racun(uuid,uuid)'):
        for role in ('anon', 'service_role', 'quoteflow_app', 'public'): assert not one(db, "select has_function_privilege(%s,%s,'execute') as p", (role, Q + f))['p'], (role, f)
        assert one(db, "select has_function_privilege('authenticated',%s,'execute') as p", (Q + f,))['p'], f
    for f in ('izdaj_racun(uuid,text,text,text,date)', 'izdaj_racun(uuid,uuid,date)', 'placaj_racun(uuid)'): assert one(db, 'select to_regprocedure(%s) as f', (Q + f,))['f'] is None, f


def test_stranka_vidi_racun_sele_ko_je_izdan_tujec_nikoli(env, db):
    users, a, _, p, _ = env; ready(db, p)
    with as_user(db, users['customer']): assert one(db, 'select count(*) as n from quoteflow.racun')['n'] == 0
    issue(db, users, a, p)
    with as_user(db, users['customer']): assert one(db, 'select count(*) as n from quoteflow.racun')['n'] == 1
    for who in ('outsider', 'owner_b', 'worker'):
        with as_user(db, users[who]): assert one(db, 'select count(*) as n from quoteflow.racun')['n'] == 0, who


# API
RACUN = {'stevilka', 'stanje_dokumenta', 'stanje_placila', 'izdajatelj_naziv', 'izdajatelj_naslov', 'izdajatelj_davcna', 'prejemnik_naziv', 'prejemnik_naslov', 'izdan_ob', 'poslan_ob', 'zapade_dne', 'placano_ob', 'ponudba',
         'postavke', 'ddv_po_stopnjah', 'neto', 'ddv', 'skupaj'}
LINE = {'zaporedje', 'naziv', 'opis', 'vrsta_dela', 'enota', 'cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'neto', 'ddv', 'koncna_cena'}
MESSAGES = {'QFP15': 'Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.', 'QFP21': 'Rok plačila ne sme biti pred datumom izdaje.'}


def day(db, expr): return one(db, f'select ({expr})::text as d')['d']


def test_api_racun_pred_sprejemom_je_404(api, db):
    client, _, users, a, _, p, M = api; r = client.get(f'{M}/racun'); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


def test_api_racun_osnutek_mojstru_z_vsotami_brez_stevilke(api, db):
    client, _, users, a, _, p, M = api; ready(db, p)
    r = client.get(f'{M}/racun'); assert r.status_code == 200, r.text
    j = r.json(); assert RACUN <= set(j) and set(j) - RACUN <= {'id'} and j['stanje_dokumenta'] == 'osnutek' and j['stevilka'] is None and j['stanje_placila'] == 'neplacan' and j['izdan_ob'] is None
    assert (j['neto'], j['ddv'], j['skupaj']) == ('180.00', '39.60', '219.60') and LINE <= set(j['postavke'][0]) and j['ponudba'] == {'stevilka': f'P-{year(db)}-001', 'razlicica': 1}


def test_api_izdaj_racun_vrne_izdan_racun_in_odpre_obracun(api, db):
    client, _, users, a, _, p, M = api; ready(db, p)
    r = client.post(f'{M}/racun/izdaj', json=rbody(db)); assert r.status_code == 200, r.text
    j = r.json(); assert j['stanje_dokumenta'] == 'izdan' and j['stevilka'] == f'R-{year(db)}-001' and j['zapade_dne'] == day(db, SOON) and j['prejemnik_naziv'] == 'Ime Priimek' and j['izdajatelj_davcna'] == 'SI12345678' and j['skupaj'] == '219.60'
    assert project(db, p)['faza'] == 'obracun'
    again = client.post(f'{M}/racun/izdaj', json=rbody(db)); assert again.status_code == 409 and again.json()['detail'] == M07


def test_api_izdaja_napake_so_409_s_slovenskim_sporocilom(api, db):
    client, _, users, a, _, p, M = api; ready(db, p, finished=False)
    r = client.post(f'{M}/racun/izdaj', json=rbody(db)); assert r.status_code == 409 and r.json()['detail'] == M07
    in_izvedba(db, p, finished=True)
    r = client.post(f'{M}/racun/izdaj', json=rbody(db, 'current_date-1')); assert r.status_code == 409 and r.json()['detail'] == MESSAGES['QFP21']
    db.execute('update quoteflow.podjetje set davcna_stevilka=null where id=%s', (a,))
    r = client.post(f'{M}/racun/izdaj', json=rbody(db)); assert r.status_code == 409 and r.json()['detail'] == MESSAGES['QFP15']
    assert project(db, p)['faza'] == 'izvedba'


@pytest.mark.parametrize('extra', [{'stevilka': 'R-1'}, {'izdajatelj_naziv': 'X'}, {'izdajatelj_davcna': 'X'}, {'prejemnik_e_posta': 'a@b.si'}, {'x': 1}])
def test_api_izdaja_zavrne_dodatna_polja_422(api, db, extra):
    client, _, users, a, _, p, M = api; q, r = ready(db, p)
    assert client.post(f'{M}/racun/izdaj', json=rbody(db) | extra).status_code == 422; untouched(db, p, r)


@pytest.mark.parametrize('payload', [{'zapade_dne': None}, {'zapade_dne': 'jutri'}, {'zapade_dne': '2026-13-45'}, {'zapade_dne': 5}, {'prejemnik_naziv': ''}, {'prejemnik_naziv': '   '}, {'prejemnik_naziv': 'x' * 201},
                                     {'prejemnik_naslov': ''}, {'prejemnik_naslov': ' '}, {'prejemnik_naslov': 'x' * 301}, {'prejemnik_naziv': None}, {'prejemnik_naslov': 5}])
def test_api_izdaja_zahteva_veljaven_datum_in_prejemnika_422(api, db, payload):
    client, _, users, a, _, p, M = api; q, r = ready(db, p); assert client.post(f'{M}/racun/izdaj', json=rbody(db) | payload).status_code == 422; untouched(db, p, r)


@pytest.mark.parametrize('missing', ['prejemnik_naziv', 'prejemnik_naslov', 'zapade_dne'])
def test_api_izdaja_brez_obveznega_polja_je_422(api, db, missing):
    client, _, users, a, _, p, M = api; q, r = ready(db, p); b = rbody(db); b.pop(missing)
    assert client.post(f'{M}/racun/izdaj', json=b).status_code == 422; untouched(db, p, r)


def test_api_izdaja_shrani_vneseno_ime_in_naslov_brez_nadomestila(api, db):
    client, _, users, a, _, p, M = api; ready(db, p); quiet(db, 'projekt', "update quoteflow.projekt set lokacija_izvedbe='' where id=%s", (p,))
    r = client.post(f'{M}/racun/izdaj', json=rbody(db, prejemnik_naziv=' Gradnje d.o.o. ', prejemnik_naslov='Celje, Cesta 5')); assert r.status_code == 200, r.text
    assert (r.json()['prejemnik_naziv'], r.json()['prejemnik_naslov']) == ('Gradnje d.o.o.', 'Celje, Cesta 5')


def test_api_izdaja_zapade_cez_366_dni_je_422(api, db):
    client, _, users, a, _, p, M = api; q, r = ready(db, p)
    assert client.post(f'{M}/racun/izdaj', json=rbody(db, 'current_date+367')).status_code == 422; untouched(db, p, r)
    assert client.post(f'{M}/racun/izdaj', json=rbody(db, 'current_date+366')).status_code == 200


def test_api_placilo_zakljuci_projekt_in_zavrne_telo_z_zneskom(api, db):
    client, _, users, a, _, p, M = api; ready(db, p); client.post(f'{M}/racun/izdaj', json=rbody(db))
    for body in ({'znesek': '219.60'}, {'placano_ob': '2020-01-01T00:00:00Z'}): assert client.post(f'{M}/racun/placilo', json=body).status_code == 422, body
    assert invoice_paid(db, p) is None
    r = client.post(f'{M}/racun/placilo'); assert r.status_code == 200, r.text
    j = r.json(); assert j['placano_ob'] and j['stanje_placila'] == 'placan' and j['stevilka'] and project(db, p)['faza'] == 'zakljucen' and project(db, p)['zakljuceno_ob']
    again = client.post(f'{M}/racun/placilo'); assert again.status_code == 409 and again.json()['detail'] == M07


def test_api_placilo_osnutka_je_409(api, db):
    client, _, users, a, _, p, M = api; q, r = ready(db, p)
    x = client.post(f'{M}/racun/placilo'); assert x.status_code == 409 and x.json()['detail'] == M07; untouched(db, p, r)


def test_api_tujec_dobi_enak_404_kot_nakljucni_id_nemojstri_403(api, db):
    client, selected, users, a, b, p, M = api; ready(db, p); selected['name'] = 'owner_b'
    calls = (('get', 'racun', None), ('post', 'racun/izdaj', rbody(db)), ('post', 'racun/placilo', None))
    for method, suffix, data in calls:
        kw = {'json': data} if data else {}; selected['name'] = 'owner_b'
        f = getattr(client, method)(f'/api/podjetja/{b}/projekti/{p}/{suffix}', **kw); r = getattr(client, method)(f'/api/podjetja/{b}/projekti/{uuid4()}/{suffix}', **kw)
        assert f.status_code == 404 and (f.status_code, f.json()) == (r.status_code, r.json()), suffix
        assert getattr(client, method)(f'{M}/{suffix}', **kw).status_code == 403
        for who in ('customer', 'worker', 'outsider', 'admin'):
            selected['name'] = who; assert getattr(client, method)(f'{M}/{suffix}', **kw).status_code == 403, (who, suffix)
    assert invoice_paid(db, p) is None


# stranka
def issued(client, selected, db, p, M):
    selected['name'] = 'owner_a'; client.post(f'{M}/racun/izdaj', json=rbody(db))


def test_api_stranka_vidi_racun_sele_ko_je_izdan_z_natancno_belo_listo(api, db):
    client, selected, users, a, _, p, M = api; ready(db, p); selected['name'] = 'customer'
    r = client.get(f'/api/projekti/{p}/racun'); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
    issued(client, selected, db, p, M); selected['name'] = 'customer'
    r = client.get(f'/api/projekti/{p}/racun'); assert r.status_code == 200, r.text
    j = r.json(); assert set(j) == RACUN and set(j['ponudba']) == {'stevilka', 'razlicica'} and set(j['postavke'][0]) == LINE and set(j['ddv_po_stopnjah'][0]) == {'stopnja_ddv', 'osnova', 'ddv'}
    assert j['stevilka'] == f'R-{year(db)}-001' and j['stanje_dokumenta'] == 'izdan' and j['stanje_placila'] == 'neplacan' and j['prejemnik_naziv'] == 'Ime Priimek' and (j['neto'], j['ddv'], j['skupaj']) == ('180.00', '39.60', '219.60')
    assert str(p) not in r.text and str(users['customer'][0]) not in r.text


def test_api_stranka_vidi_placilo_ko_je_racun_placan(api, db):
    client, selected, users, a, _, p, M = api; ready(db, p); issued(client, selected, db, p, M); client.post(f'{M}/racun/placilo'); selected['name'] = 'customer'
    j = client.get(f'/api/projekti/{p}/racun').json(); assert j['stanje_placila'] == 'placan' and j['placano_ob']


@pytest.mark.parametrize('who', ['outsider', 'owner_a', 'owner_b', 'worker', 'admin'])
def test_api_tuj_racun_je_enak_nakljucnemu_projektu(api, db, who):
    client, selected, users, a, _, p, M = api; ready(db, p); issued(client, selected, db, p, M); selected['name'] = who
    f, r = client.get(f'/api/projekti/{p}/racun'), client.get(f'/api/projekti/{uuid4()}/racun')
    assert (f.status_code, f.json()) == (r.status_code, r.json()) and f.status_code in (403, 404) and f.json()['detail'] != 'Not Found' and 'R-20' not in f.text


def test_api_racun_osnutek_stranki_nikoli(api, db):
    client, selected, users, a, _, p, M = api; ready(db, p); selected['name'] = 'customer'
    r = client.get(f'/api/projekti/{p}/racun'); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.' and 'Ime' not in r.text and '219' not in r.text


def test_api_odvzeta_vloga_stranke_je_403(api, db):
    client, selected, users, a, _, p, M = api; ready(db, p); issued(client, selected, db, p, M); selected['name'] = 'customer'
    db.execute("update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s and vloga='stranka'", (users['customer'][0],))
    assert client.get(f'/api/projekti/{p}/racun').status_code == 403
