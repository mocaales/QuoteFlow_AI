"""Model v3 quotes: the draft is only a header, sending snapshots the project items; the customer sees an exact allow-list."""
import json
from datetime import date, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from v3_support import COMPANY, FAT, ITEM, M, PROJECT, QUOTE, REMOVED, Fake, api, call, keys, qfp

SEND = f'{M}/ponudbe/{QUOTE}/poslji'
OWN = f'/api/projekti/{PROJECT}/ponudbe'
SUMMARY_KEYS = {'id', 'stevilka', 'razlicica', 'stanje', 'poslano_ob', 'odgovorjeno_ob', 'velja_do', 'nadomescena', 'neto', 'ddv', 'skupaj'}
CUSTOMER_KEYS = SUMMARY_KEYS | {'postavke', 'ddv_po_stopnjah', 'podjetje_naziv'}
CUSTOMER_LINE = {'zaporedje', 'naziv', 'opis', 'vrsta_dela', 'enota', 'cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'neto', 'ddv', 'koncna_cena', 'izmera_skupaj', 'izmere'}
CUSTOMER_IZMERA_MUST = {'zaporedje', 'odstej', 'kosi', 'vrednost'}
CUSTOMER_IZMERA_MAY = CUSTOMER_IZMERA_MUST | {'enota', 'dolzina', 'visina', 'sirina'}
NEVER = {'urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'cena_dela', 'cena_materiala', 'materiali', 'material_id', 'kolicina_na_enoto', 'kolicina_skupaj', 'vrsta_dela_id', 'postavka_cenika_id', 'nabavna_cena',
         'marza', 'strosek_na_enoto', 'podjetje_id', 'projekt_id', 'uporabnik_id', 'postavka_projekta_id', 'aktiven', 'sifra', 'allowed'}
ROW = FAT | {'stanje': 'poslana', 'stevilka': 'P-1', 'razlicica': 1, 'poslano_ob': '2026-11-07T10:00:00+00:00', 'odgovorjeno_ob': None, 'velja_do': str(date.today() + timedelta(days=5)), 'nadomescena': False,
             'podjetje_naziv': 'Gradnje d.o.o.', 'izmere': [FAT]}


@pytest.mark.parametrize('method,path,body', REMOVED)
def test_odstranjene_poti_so_404_ali_405_in_ne_zahtevajo_prijave(method, path, body):
    # a removed route never reaches the auth dependency; a live one would answer 401 without a token
    r = call(TestClient(app, raise_server_exceptions=False), method, path, body); assert r.status_code in (404, 405), (method, path, r.status_code)


@pytest.mark.parametrize('method,path,body', REMOVED)
def test_odstranjene_poti_so_404_ali_405_tudi_za_mojstra(api, method, path, body):
    fake = Fake([ROW]); r = call(api(fake), method, path, body); assert r.status_code in (404, 405) and not fake.calls, (method, path)


def test_osnutek_ponudbe_je_se_vedno_samo_glava_ustvari_in_uredi(api):
    velja = (date.today() + timedelta(days=30)).isoformat()
    fake = Fake([ROW]); assert call(api(fake), 'post', f'{M}/ponudbe', {'velja_do': velja}).status_code in (200, 201) and fake.called('ustvari_ponudbo')
    fake = Fake([ROW]); assert call(api(fake), 'put', f'{M}/ponudbe/{QUOTE}', {'velja_do': velja}).status_code == 200 and fake.called('uredi_ponudbo')


def test_osnutek_ne_sprejme_postavk_v_telesu(api):
    for method, path in (('post', f'{M}/ponudbe'), ('put', f'{M}/ponudbe/{QUOTE}')):
        fake = Fake([ROW]); r = call(api(fake), method, path, {'postavke': [{'naziv': 'x'}]}); assert r.status_code == 422 and not fake.calls


def test_poslji_pokliče_funkcijo_in_brez_telesa(api):
    fake = Fake([ROW]); r = api(fake).post(SEND); assert r.status_code == 200 and [str(x) for x in fake.called('poslji_ponudbo')[0]] == [str(COMPANY), str(PROJECT), str(QUOTE)]


@pytest.mark.parametrize('code', ['QFP13', 'QFP26', 'QFP12', 'QFP10', 'QFP07'])
def test_poslji_poslovne_napake_so_409(api, code):
    assert api(Fake(error=qfp(code))).post(SEND).status_code == 409


def test_poslji_brez_postavk_qfp26_ima_fiksno_sporocilo_brez_imena_postavke(api):
    r = api(Fake(error=qfp('QFP26'))).post(SEND); assert r.status_code == 409 and r.json()['detail'] == 'Vsaka postavka mora imeti pozitivno količino izmer.'


def test_poslji_dvakrat_je_zavrnjeno_ne_podvojeno(api):
    r = api(Fake(error=qfp('QFP10'))).post(SEND); assert r.status_code == 409 and r.json()['detail'].startswith('Poslana ponudba je zaklenjena')


def test_poslji_tuja_ponudba_je_404(api):
    assert api(Fake(error=psycopg.errors.NoDataFound())).post(SEND).status_code == 404


def test_poslji_po_sprejemu_je_409_qfp07_in_ne_spremeni_ponudbe(api):
    fake = Fake(error=qfp('QFP07')); assert api(fake).post(SEND).status_code == 409 and len(fake.called('poslji_ponudbo')) == 1


# customer view of a sent quote
def customer(api): return api(Fake([ROW])).get(OWN)


def test_stranka_vidi_natancno_dovoljene_kljuce_ponudbe_in_vrstice(api):
    r = customer(api); assert r.status_code == 200 and len(r.json()) == 1, r.text[:300]
    q = r.json()[0]; assert set(q) == CUSTOMER_KEYS, set(q) ^ CUSTOMER_KEYS
    assert q['postavke'] and all(set(l) == CUSTOMER_LINE for l in q['postavke']), {tuple(sorted(set(l) ^ CUSTOMER_LINE)) for l in q['postavke']}


def test_stranka_vidi_izmere_poslane_ponudbe_brez_notranjih_polj(api):
    q = customer(api).json()[0]
    for l in q['postavke']:
        assert isinstance(l['izmere'], list) and l['izmere'] and isinstance(l['izmera_skupaj'], str)
        for i in l['izmere']: assert CUSTOMER_IZMERA_MUST <= set(i) <= CUSTOMER_IZMERA_MAY, set(i)


def test_stranka_nikoli_ne_vidi_dela_materialov_ali_internih_id(api):
    r = customer(api); assert r.status_code == 200 and not (keys(r.json()) & NEVER), keys(r.json()) & NEVER
    assert not any(w in r.text for w in ('strosek_na_enoto', 'marza', 'urna_postavka', 'cena_dela', 'materiali', 'osnutek'))


def test_stranka_denarni_zneski_so_nizi(api):
    q = customer(api).json()[0]
    for k in ('neto', 'ddv', 'skupaj'): assert isinstance(q[k], str)
    for l in q['postavke']:
        for k in ('cena_na_enoto', 'kolicina', 'popust', 'stopnja_ddv', 'neto', 'ddv', 'koncna_cena', 'izmera_skupaj'): assert isinstance(l[k], str), k


def test_stranka_odgovor_odlocitve_ima_isti_kljuce(api):
    r = api(Fake([ROW])).post(f'{OWN}/{QUOTE}/odlocitev', json={'sprejmi': True}); assert r.status_code == 200 and set(r.json()) == CUSTOMER_KEYS
    assert all(set(l) == CUSTOMER_LINE for l in r.json()['postavke']) and not (keys(r.json()) & NEVER)


def test_stranka_ne_vidi_osnutka_ker_poizvedba_izloci_osnutke(api):
    fake = Fake([ROW]); api(fake).get(OWN); assert any("<>'osnutek'" in sql.replace(' ', '') or "'osnutek'" in sql for sql, _ in fake.calls)


def test_stranka_je_omejena_na_lastni_projekt(api):
    from v3_support import ME
    fake = Fake([ROW]); api(fake).get(OWN); assert any(ME.id in p and PROJECT in p for _, p in fake.calls if p)
