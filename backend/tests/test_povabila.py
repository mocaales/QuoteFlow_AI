"""US-08: the invited person lists and answers invitations (/api/povabila); any live session, no company role; foreign ids are 404."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import session_database
from app.auth import current_user
from app.main import app
from v3_support import COMPANY, FAT, ME, Fake, api, call, keys, qfp, untouched

PID = uuid4()
L = '/api/povabila'
D = f'{L}/{PID}/odlocitev'
MINE = {'id': PID, 'podjetje_id': COMPANY, 'podjetje_naziv': 'Podjetje', 'povabil': 'Ana Novak', 'poslano_ob': '2026-11-07T10:00:00+00:00'}


def test_moja_povabila_natancen_nabor_kljucev(api):
    fake = Fake([FAT | MINE]); r = api(fake).get(L)
    assert r.status_code == 200 and set(r.json()[0]) == set(MINE) and fake.called('moja_povabila') is not None and fake.calls, r.text[:300]
    assert not keys(r.json()) & {'e_posta', 'uporabnik_id', 'strosek_na_enoto', 'marza'}


def test_moja_povabila_brez_vrstic_je_prazen_seznam(api):
    r = api(Fake([])).get(L); assert r.status_code == 200 and r.json() == []


@pytest.mark.parametrize('value', [True, False])
def test_odlocitev_pokliče_funkcijo_s_povabilom_in_odlocitvijo(api, value):
    fake = Fake([{'id': PID, 'stanje': 'sprejeto' if value else 'zavrnjeno'}]); r = call(api(fake), 'post', D, {'sprejmi': value})
    p = fake.called('odgovori_povabilo'); assert r.status_code == 200 and p and p[0] == (PID, value) and set(r.json()) == {'id', 'stanje'}


@pytest.mark.parametrize('body', [{}, {'sprejmi': 'da'}, {'sprejmi': 1}, {'sprejmi': 0}, {'sprejmi': None}, {'sprejmi': [True]}, {'sprejmi': True, 'podjetje_id': str(uuid4())},
                                  {'sprejmi': True, 'vloga': 'mojster'}, {'sprejmi': True, 'stanje': 'sprejeto'}, {'sprejmi': True, 'uporabnik_id': str(uuid4())}])
def test_odlocitev_neveljavno_telo_je_422_brez_klica_baze(api, body):
    fake = Fake([{'id': PID, 'stanje': 'sprejeto'}]); assert untouched(call(api(fake), 'post', D, body), fake) and not fake.called('odgovori_povabilo'), body


def test_odlocitev_id_ni_uuid_je_422(api):
    assert call(api(Fake([])), 'post', f'{L}/ni-uuid/odlocitev', {'sprejmi': True}).status_code == 422


def test_odlocitev_tuje_ali_neznano_povabilo_je_404_enako_za_vse(api):
    results = [call(api(Fake(error=psycopg.errors.NoDataFound())), 'post', f'{L}/{pid}/odlocitev', {'sprejmi': True}) for pid in (uuid4(), uuid4(), PID)]
    assert {(r.status_code, r.text) for r in results} == {(404, '{"detail":"Zapis ni na voljo."}')}
    assert call(api(Fake([])), 'post', D, {'sprejmi': True}).status_code == 404


def test_odlocitev_neprimeren_prejemnik_je_409_s_splosnim_sporocilom(api):
    r = call(api(Fake(error=qfp('QFP34'))), 'post', D, {'sprejmi': True}); assert r.status_code == 409 and r.json()['detail'] == 'Povabila ni mogoče sprejeti.'


def test_odlocitev_ne_sestavlja_sql_z_nizi(api):
    fake = Fake([{'id': PID, 'stanje': 'zavrnjeno'}]); call(api(fake), 'post', D, {'sprejmi': False})
    assert str(PID) not in ' '.join(s for s, _ in fake.calls)


def test_povabila_brez_zetona_so_401():
    c = TestClient(app, raise_server_exceptions=False)
    assert c.get(L).status_code == 401 and c.post(D, json={'sprejmi': True}).status_code == 401


def test_povabila_ne_zahtevajo_vloge_podjetja_in_ne_odpirajo_lastne_povezave():
    fake = Fake([]); app.dependency_overrides[current_user] = lambda: ME; app.dependency_overrides[session_database] = lambda: fake
    try: r = TestClient(app, raise_server_exceptions=False).get(L)
    finally: app.dependency_overrides.clear()
    assert r.status_code == 200 and not any('clan' in s for s, _ in fake.calls)
