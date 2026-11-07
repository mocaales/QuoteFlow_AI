"""US-08: mojster manages the delavec role in his own company. A1 enumeration, A2 field allow-list, A5 identical 404, A8 idempotence."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import session_database
from app.auth import current_user
from app.main import app
from v3_support import C, COMPANY, FAT, ME, USER, VLOGA, Fake, api, call, keys, qfp, reached, untouched

D = f'{C}/delavci'
WORKER_KEYS = {'id', 'uporabnik_id', 'e_posta', 'ime', 'priimek', 'aktivna', 'dodeljeno_ob'}
ROW = FAT | {'id': VLOGA, 'uporabnik_id': USER, 'vloga': 'delavec', 'podjetje_id': COMPANY, 'naziv': 'Podjetje', 'telefon': '1', 'maticna_stevilka': '1'}
NULL_ROW = {k: None for k in ROW}


def test_seznam_delavcev_ima_natancen_nabor_kljucev(api):
    r = api(Fake([ROW, ROW | {'aktivna': False}])).get(D)
    assert r.status_code == 200 and len(r.json()) == 2 and all(set(w) == WORKER_KEYS for w in r.json()), r.text[:300]


def test_seznam_delavcev_je_omejen_na_podjetje_in_vlogo_delavec(api):
    fake = Fake([]); api(fake).get(D)
    assert fake.calls and any(COMPANY in p for _, p in fake.calls if p) and any('delavec' in sql or 'delavec' in p for sql, p in fake.calls if sql or p)


PID = uuid4()
P = f'{D}/povabila'
INVITE_KEYS = {'id', 'e_posta', 'stanje', 'poslano_ob'}
INVITE = {'id': PID, 'e_posta': 'Delavec@Example.test', 'stanje': 'povabljen', 'poslano_ob': '2026-11-07T10:00:00+00:00', 'odloceno_ob': None}


@pytest.mark.parametrize('body', [{'e_posta': 'ana@example.test', 'vloga': 'mojster'}, {'e_posta': 'ana@example.test', 'podjetje_id': str(uuid4())}, {'e_posta': 'ana@example.test', 'uporabnik_id': str(uuid4())},
                                  {'e_posta': 'ana@example.test', 'stanje': 'sprejeto'}, {'e_posta': 'ana@example.test', 'aktivna': True}, {'uporabnik_id': str(uuid4())}, {}, {'e_posta': None}, {'e_posta': ''}, {'e_posta': '   '}, {'e_posta': 5}, {'e_posta': ['a@b.si']},
                                  {'e_posta': 'ni-e-posta'}, {'e_posta': 'a@'}, {'e_posta': '@b.si'}, {'e_posta': 'a b@c.si'}, {'e_posta': 'a@b.si\x00'}, {'e_posta': 'a@b.si\n'}, {'e_posta': 'a' * 250 + '@b.si'}])
def test_povabi_delavca_neveljavno_telo_je_422_brez_klica_baze(api, body):
    fake = Fake([INVITE]); assert untouched(call(api(fake), 'post', P, body), fake), body


def test_povabi_delavca_pokliče_funkcijo_s_podjetjem_in_prirezano_e_posto(api):
    fake = Fake([INVITE]); r = call(api(fake), 'post', P, {'e_posta': '  Delavec@Example.TEST '})
    p = fake.called('povabi_delavca'); assert r.status_code == 201 and p and p[0] == (COMPANY, 'Delavec@Example.TEST')
    assert set(r.json()) == INVITE_KEYS and r.json()['stanje'] == 'povabljen'


def test_povabi_delavca_ne_sestavlja_sql_z_nizi_in_ne_klice_stare_funkcije(api):
    fake = Fake([INVITE]); call(api(fake), 'post', P, {'e_posta': 'delavec@example.test'})
    sql = ' '.join(s for s, _ in fake.calls); assert 'delavec@example.test' not in sql and 'mojster' not in sql and not fake.called('dodaj_delavca')


def test_povabilo_odgovor_je_enak_za_vse_naslove_brez_podatkov_o_uporabniku(api):
    # known, unconfirmed, admin or unknown: the SQL function answers with the same shape; the API adds nothing and leaks no user fields
    bodies = []
    for email in ('ni@example.test', 'nepotrjen@example.test', 'admin@example.test', 'drug@example.test'):
        r = call(api(Fake([FAT | INVITE | {'e_posta': email}])), 'post', P, {'e_posta': email}); bodies.append(r)
        assert r.status_code == 201 and set(r.json()) == INVITE_KEYS, r.text
    assert {tuple(sorted(r.json())) for r in bodies} == {tuple(sorted(INVITE_KEYS))}
    assert not keys([r.json() for r in bodies]) & {'ime', 'priimek', 'uporabnik_id', 'vloga', 'aktivna', 'odloceno_ob'}


def test_ponovno_vabilo_vrne_isto_odprto_povabilo_201(api):
    for _ in range(2): r = call(api(Fake([INVITE])), 'post', P, {'e_posta': 'delavec@example.test'}); assert r.status_code == 201 and r.json()['id'] == str(PID)


def test_povabilo_brez_vrstice_je_404(api):
    assert call(api(Fake([])), 'post', P, {'e_posta': 'delavec@example.test'}).status_code == 404


@pytest.mark.parametrize('code,status', [('QFP30', 409)])
def test_povabilo_poslovna_napaka_je_409(api, code, status):
    assert call(api(Fake(error=qfp(code))), 'post', P, {'e_posta': 'delavec@example.test'}).status_code == status


def test_povabilo_neveljavna_e_posta_v_bazi_je_422(api):
    assert call(api(Fake(error=psycopg.errors.InvalidParameterValue())), 'post', P, {'e_posta': 'delavec@example.test'}).status_code == 422


def test_seznam_povabil_ima_natancen_nabor_kljucev_in_klice_funkcijo(api):
    fake = Fake([FAT | INVITE, FAT | INVITE | {'stanje': 'sprejeto'}]); r = api(fake).get(P)
    assert r.status_code == 200 and len(r.json()) == 2 and all(set(w) == INVITE_KEYS | {'odloceno_ob'} for w in r.json()), r.text[:300]
    assert fake.called('povabila_podjetja')[0][0] == COMPANY


def test_preklic_povabila_klice_funkcijo_s_podjetjem_in_povabilom(api):
    fake = Fake([INVITE | {'stanje': 'preklicano'}]); r = call(api(fake), 'post', f'{P}/{PID}/preklic')
    assert r.status_code == 200 and fake.called('preklici_povabilo')[0][:2] == (COMPANY, PID) and r.json()['stanje'] == 'preklicano'


def test_preklic_tujega_ali_neznanega_povabila_je_404_enako_za_vse(api):
    results = [call(api(Fake(error=psycopg.errors.NoDataFound())), 'post', f'{P}/{pid}/preklic') for pid in (uuid4(), uuid4(), PID)]
    assert {(r.status_code, r.text) for r in results} == {(404, '{"detail":"Zapis ni na voljo."}')}
    assert call(api(Fake([])), 'post', f'{P}/{PID}/preklic').status_code == 404


def test_preklic_id_ni_uuid_je_422(api):
    assert call(api(Fake([INVITE])), 'post', f'{P}/ni-uuid/preklic').status_code == 422


def test_stara_pot_dodaj_delavca_ne_obstaja(api):
    fake = Fake([ROW]); r = call(api(fake), 'post', D, {'e_posta': 'delavec@example.test'})
    assert r.status_code in (404, 405) and not fake.calls and not fake.called('dodaj_delavca')


# PATCH
PATCH = f'{D}/{VLOGA}'


@pytest.mark.parametrize('value', [False, True])
def test_uredi_delavca_pokliče_funkcijo_s_podjetjem_vlogo_in_stanjem(api, value):
    fake = Fake([ROW | {'aktivna': value}]); r = call(api(fake), 'patch', PATCH, {'aktivna': value})
    p = fake.called('uredi_delavca'); assert r.status_code == 200 and p and p[0][:3] == (COMPANY, VLOGA, value) and set(r.json()) == WORKER_KEYS


@pytest.mark.parametrize('body', [{}, {'aktivna': 'da'}, {'aktivna': 1}, {'aktivna': 0}, {'aktivna': None}, {'aktivna': [True]}, {'aktivna': True, 'vloga': 'mojster'}, {'aktivna': True, 'uporabnik_id': str(uuid4())},
                                  {'aktivna': True, 'podjetje_id': str(uuid4())}, {'aktivna': True, 'e_posta': 'a@b.si'}])
def test_uredi_delavca_neveljavno_telo_je_422(api, body):
    fake = Fake([ROW]); assert untouched(call(api(fake), 'patch', PATCH, body), fake)


def test_uredi_delavca_id_ni_uuid_je_422(api):
    assert call(api(Fake([ROW])), 'patch', f'{D}/ni-uuid', {'aktivna': False}).status_code == 422


def test_uredi_tuje_nakljucno_ali_mojstrovo_vlogo_je_404_enako_za_vse_a5(api):
    results = [call(api(Fake(error=psycopg.errors.NoDataFound())), 'patch', f'{D}/{vid}', {'aktivna': False}) for vid in (uuid4(), uuid4(), VLOGA)]
    assert {(r.status_code, r.text) for r in results} == {(404, '{"detail":"Zapis ni na voljo."}')}


def test_uredi_delavca_brez_vrstice_je_404_in_ne_200_null(api):
    r = call(api(Fake([])), 'patch', PATCH, {'aktivna': False}); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


def test_uredi_delavca_funkcija_brez_pravice_je_403(api):
    assert call(api(Fake(error=psycopg.errors.InsufficientPrivilege())), 'patch', PATCH, {'aktivna': False}).status_code == 403


def test_delavci_nimajo_poti_za_brisanje_in_ne_put(api):
    for m in ('delete', 'put'): assert call(api(Fake([ROW])), m, PATCH, {'aktivna': False} if m == 'put' else None).status_code in (404, 405)
    assert call(api(Fake([ROW])), 'delete', D).status_code in (404, 405)


# guards: only an active mojster of exactly this company
@pytest.mark.parametrize('method,path,body', [('get', D, None), ('post', P, {'e_posta': 'a@example.test'}), ('get', P, None), ('post', f'{P}/{PID}/preklic', None), ('patch', PATCH, {'aktivna': False})])
def test_delavec_stranka_in_odvzet_mojster_dobijo_403_brez_dostopa_do_podatkov(method, path, body):
    fake = Fake([{'allowed': False}]); app.dependency_overrides[current_user] = lambda: ME; app.dependency_overrides[session_database] = lambda: fake
    try: r = call(TestClient(app, raise_server_exceptions=False), method, path, body)
    finally: app.dependency_overrides.clear()
    assert r.status_code == 403 and len(fake.calls) == 1 and 'clan' in fake.calls[0][0] and fake.calls[0][1] == (COMPANY, 'mojster'), r.text


def test_vloga_delavec_ni_dovolj_za_upravljanje_delavcev():
    from app.access import company_member
    from fastapi.routing import APIRoute
    deps = {getattr(c, 'company_role', None) for r in app.routes if isinstance(r, APIRoute) and r.path.endswith('/delavci') for d in r.dependant.dependencies for c in [d.call]}
    assert 'mojster' in deps and 'delavec' not in deps and company_member('delavec') is not company_member('mojster')
