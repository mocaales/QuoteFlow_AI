"""US-03 začetek projekta: API validation, status mapping and own-only customer filter with a fake connection."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app import access
from app.access import company_member, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'ana@example.test')
COMPANY, PROJECT = uuid4(), uuid4()
BASE = f'/api/podjetja/{COMPANY}/projekti'
FORM = {'e_posta_stranke': 'stranka@example.test', 'naziv': 'Prenova kopalnice', 'opis': 'Menjava ploščic', 'lokacija_izvedbe': 'Maribor'}
M_STRANKA, M_FAZA = 'Uporabnik s tem e-poštnim naslovom ni registrirana stranka.', 'V tej fazi projekta to dejanje ni dovoljeno.'


def row(**change):
    return {'id': PROJECT, 'naziv': 'Prenova kopalnice', 'opis': 'Menjava ploščic', 'lokacija_izvedbe': 'Maribor', 'faza': 'pregled',
            'stranka_ime': 'Ana', 'stranka_priimek': 'Novak', 'stranka_e_posta': 'stranka@example.test', 'termin_od': None, 'termin_do': None} | change


def own(**change):
    return {'id': PROJECT, 'naziv': 'Prenova kopalnice', 'opis': 'Menjava ploščic', 'lokacija_izvedbe': 'Maribor', 'faza': 'pregled',
            'podjetje_naziv': 'Mojster Novak d.o.o.', 'termin_od': None, 'termin_do': None} | change


class Cursor:
    def __init__(self, rows): self.rows = rows
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Fake:
    def __init__(self, rows=(), error=None): self.rows, self.error, self.calls = list(rows), error, []
    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))
        if self.error: raise self.error
        return Cursor(self.rows)


def qfp(code):
    class Custom(psycopg.DatabaseError): sqlstate = code
    return Custom()


@pytest.fixture
def api():
    def use(fake):
        app.dependency_overrides[current_user] = lambda: ME
        app.dependency_overrides[session_database] = lambda: fake
        app.dependency_overrides[company_member('mojster')] = lambda: fake
        if hasattr(access, 'customer'): app.dependency_overrides[access.customer] = lambda: fake  # guard added by L2
        return TestClient(app, raise_server_exceptions=False)
    try: yield use
    finally: app.dependency_overrides.clear()


def test_mojster_seznam_projektov_ima_ploska_polja_stranke(api):
    r = api(Fake([row(), row(id=uuid4(), faza='ogled')])).get(BASE)
    assert r.status_code == 200 and len(r.json()) == 2
    assert set(r.json()[0]) == {'id', 'naziv', 'opis', 'lokacija_izvedbe', 'faza', 'stranka_ime', 'stranka_priimek', 'stranka_e_posta', 'termin_od', 'termin_do', 'izvedba_koncana_ob', 'zakljuceno_ob'}


def test_ustvari_projekt_vrne_201_in_prireze_vnos(api):
    fake = Fake([row()])
    r = api(fake).post(BASE, json=FORM | {'naziv': '  Prenova kopalnice  ', 'e_posta_stranke': ' stranka@example.test '})
    assert r.status_code == 201, r.text
    assert r.json()['faza'] == 'pregled'
    assert any('quoteflow_private.ustvari_projekt' in sql and COMPANY in p for sql, p in fake.calls)
    flat = [x for _, p in fake.calls for x in p]
    assert 'Prenova kopalnice' in flat and '  Prenova kopalnice  ' not in flat and 'stranka@example.test' in flat


def test_opis_in_lokacija_sta_neobvezna_in_privzeto_prazna(api):
    r = api(Fake([row()])).post(BASE, json={'e_posta_stranke': 'stranka@example.test', 'naziv': 'Prenova'})
    assert r.status_code == 201, r.text


@pytest.mark.parametrize('change', [
    {'naziv': ' '}, {'naziv': ''}, {'naziv': None}, {'e_posta_stranke': ' '}, {'e_posta_stranke': None},
    {'faza': 'ponudba'}, {'stranka_id': str(uuid4())}, {'podjetje_id': str(uuid4())}, {'termin_od': '2026-12-01T08:00:00Z'},
])
def test_neveljaven_projekt_je_422_in_ne_doseze_baze(api, change):
    fake = Fake([row()])
    assert api(fake).post(BASE, json=FORM | change).status_code == 422 and fake.calls == []


def test_neznana_stranka_je_409_s_slovenskim_sporocilom(api):
    r = api(Fake(error=qfp('QFP06'))).post(BASE, json=FORM)
    assert r.status_code == 409 and r.json()['detail'] == M_STRANKA


def test_uredi_projekt_poklice_funkcijo(api):
    fake = Fake([row(naziv='Novo')])
    r = api(fake).put(f'{BASE}/{PROJECT}', json={'naziv': ' Novo ', 'opis': 'x', 'lokacija_izvedbe': 'Celje'})
    assert r.status_code == 200 and r.json()['naziv'] == 'Novo'
    assert any('quoteflow_private.uredi_projekt' in sql and COMPANY in p and PROJECT in p and 'Novo' in p for sql, p in fake.calls)


@pytest.mark.parametrize('body', [{'naziv': ' ', 'opis': '', 'lokacija_izvedbe': ''}, {'opis': 'x', 'lokacija_izvedbe': 'y'},
                                  {'naziv': 'N', 'opis': '', 'lokacija_izvedbe': '', 'faza': 'ponudba'}, {'naziv': 'N', 'opis': '', 'lokacija_izvedbe': '', 'e_posta_stranke': 'a@b.si'}])
def test_neveljavno_urejanje_je_422(api, body):
    fake = Fake([row()])
    assert api(fake).put(f'{BASE}/{PROJECT}', json=body).status_code == 422 and fake.calls == []


@pytest.mark.parametrize('method,path,body', [('put', f'{BASE}/{PROJECT}', {'naziv': 'N', 'opis': '', 'lokacija_izvedbe': ''}), ('post', f'{BASE}/{PROJECT}/ogled', None)])
def test_napacna_faza_je_409(api, method, path, body):
    r = getattr(api(Fake(error=qfp('QFP07'))), method)(path, **({'json': body} if body else {}))
    assert r.status_code == 409 and r.json()['detail'] == M_FAZA


@pytest.mark.parametrize('method,path,body', [('put', f'{BASE}/{PROJECT}', {'naziv': 'N', 'opis': '', 'lokacija_izvedbe': ''}), ('post', f'{BASE}/{PROJECT}/ogled', None)])
def test_tuj_projekt_je_404_in_brez_pravice_403(api, method, path, body):
    kw = {'json': body} if body else {}
    assert getattr(api(Fake(error=psycopg.errors.NoDataFound())), method)(path, **kw).status_code == 404
    assert getattr(api(Fake(error=psycopg.errors.InsufficientPrivilege())), method)(path, **kw).status_code == 403


def test_zahtevaj_ogled_vrne_vrstico_v_fazi_ogled(api):
    fake = Fake([row(faza='ogled')])
    r = api(fake).post(f'{BASE}/{PROJECT}/ogled')
    assert r.status_code == 200 and r.json()['faza'] == 'ogled'
    assert any('quoteflow_private.zahtevaj_ogled' in sql and COMPANY in p and PROJECT in p for sql, p in fake.calls)


def test_ni_poti_za_rocno_nastavitev_faze(api):
    c = api(Fake([row()]))
    assert c.put(f'{BASE}/{PROJECT}', json={'naziv': 'N', 'opis': '', 'lokacija_izvedbe': '', 'faza': 'ponudba'}).status_code == 422
    assert c.post(f'{BASE}/{PROJECT}/ponudba').status_code in (404, 405)


def test_nemojster_dobi_403_na_mojstrovih_poteh_projektov():
    fake = Fake([{'allowed': False}])
    app.dependency_overrides[current_user] = lambda: ME
    app.dependency_overrides[session_database] = lambda: fake
    try:
        c = TestClient(app, raise_server_exceptions=False)
        assert c.get(BASE).status_code == 403
        assert c.post(BASE, json=FORM).status_code == 403
        assert c.put(f'{BASE}/{PROJECT}', json={'naziv': 'N', 'opis': '', 'lokacija_izvedbe': ''}).status_code == 403
        assert c.post(f'{BASE}/{PROJECT}/ogled').status_code == 403
        assert not any('projekt' in sql for sql, _ in fake.calls)
    finally: app.dependency_overrides.clear()


def test_stranka_vidi_samo_lastne_projekte_in_polja_brez_stranke(api):
    fake = Fake([own()])
    r = api(fake).get('/api/projekti')
    assert r.status_code == 200 and set(r.json()[0]) == {'id', 'naziv', 'opis', 'lokacija_izvedbe', 'faza', 'podjetje_naziv', 'termin_od', 'termin_do', 'izvedba_koncana_ob', 'zakljuceno_ob'}
    sql, params = fake.calls[-1]
    assert 'stranka_id' in sql and (ME.id in params or str(ME.id) in map(str, params))


def test_stranka_podrobnosti_lastnega_projekta_in_404_za_tujega(api):
    fake = Fake([own()])
    r = api(fake).get(f'/api/projekti/{PROJECT}')
    assert r.status_code == 200 and r.json()['podjetje_naziv'] == 'Mojster Novak d.o.o.'
    sql, params = fake.calls[-1]
    assert 'stranka_id' in sql and PROJECT in params and (ME.id in params or str(ME.id) in map(str, params))
    assert api(Fake([])).get(f'/api/projekti/{uuid4()}').status_code == 404


M_PREVEC = 'Preveč poskusov ustvarjanja projektov. Poskusite znova čez nekaj časa.'


def test_prevec_poskusov_je_409_s_slovenskim_sporocilom(api):
    r = api(Fake(error=qfp('QFP08'))).post(BASE, json=FORM)
    assert r.status_code == 409 and r.json()['detail'] == M_PREVEC


def test_neznana_stranka_brez_izjeme_je_409_enako_kot_qfp06(api):
    fake = Fake([{'id': None}])
    r = api(fake).post(BASE, json=FORM)
    assert r.status_code == 409 and r.json()['detail'] == M_STRANKA
    assert not any('p.id=%s' in sql for sql, _ in fake.calls)


def test_stranka_brez_vloge_stranka_dobi_403_na_lastnih_projektih():
    fake = Fake([{'allowed': False}])
    app.dependency_overrides[current_user] = lambda: ME
    app.dependency_overrides[session_database] = lambda: fake
    try:
        c = TestClient(app, raise_server_exceptions=False)
        for path in ('/api/projekti', f'/api/projekti/{PROJECT}'):
            r = c.get(path); assert r.status_code == 403 and r.json()['detail'] == 'Za to dejanje nimate pravice.', path
        assert not any('quoteflow.projekt' in sql for sql, _ in fake.calls)
    finally: app.dependency_overrides.clear()


@pytest.mark.parametrize('field', ['naziv', 'opis', 'lokacija_izvedbe', 'e_posta_stranke'])
def test_nul_znak_v_projektu_je_422_in_ne_doseze_baze(api, field):
    fake = Fake([row()])
    assert api(fake).post(BASE, json=FORM | {field: 'a\x00b'}).status_code == 422 and fake.calls == []


@pytest.mark.parametrize('field', ['naziv', 'opis', 'lokacija_izvedbe'])
def test_nul_znak_pri_urejanju_projekta_je_422(api, field):
    fake = Fake([row()])
    body = {'naziv': 'N', 'opis': '', 'lokacija_izvedbe': ''} | {field: 'a\x00b'}
    assert api(fake).put(f'{BASE}/{PROJECT}', json=body).status_code == 422 and fake.calls == []


BAD = ['\x07', '\x1b', '\x85', '\x00', '‮', '​', '⁦']
ITEM = {'naziv': 'Rušenje estriha', 'opis': 'Odstranitev in odvoz', 'vrsta_dela_id': str(uuid4()), 'enota': 'm2', 'cena_na_enoto': '12.4500', 'stopnja_ddv': '0.22', 'aktivna': True}


@pytest.mark.parametrize('field', ['naziv', 'opis', 'lokacija_izvedbe'])
@pytest.mark.parametrize('bad', BAD)
def test_projekt_krmilni_in_format_znaki_so_422(api, field, bad):
    fake = Fake([row()])
    assert api(fake).post(BASE, json=FORM | {field: f'Pre{bad}nova'}).status_code == 422 and fake.calls == []
    assert api(fake).put(f'{BASE}/{PROJECT}', json={k: v for k, v in FORM.items() if k != 'e_posta_stranke'} | {field: f'Pre{bad}nova'}).status_code == 422 and fake.calls == []


@pytest.mark.parametrize('bad', BAD)
def test_cenik_naziv_krmilni_in_format_znaki_so_422(api, bad):
    fake = Fake([ITEM | {'id': uuid4(), 'podjetje_id': COMPANY}])
    assert api(fake).post(f'/api/podjetja/{COMPANY}/cenik', json=ITEM).status_code == 201  # the unchanged v3 form is valid
    fake = Fake([ITEM | {'id': uuid4(), 'podjetje_id': COMPANY}])
    assert api(fake).post(f'/api/podjetja/{COMPANY}/cenik', json=ITEM | {'naziv': f'Ru{bad}šenje'}).status_code == 422 and fake.calls == []


def test_projekt_slovensko_besedilo_tab_in_nova_vrstica_sta_sprejeta(api):
    r = api(Fake([row()])).post(BASE, json=FORM | {'naziv': 'Šđčćž ŠĐČĆŽ', 'opis': 'Vrstica 1\n\tvrstica 2 – šđčćž'})
    assert r.status_code == 201, r.text


def test_projekt_opis_s_crlf_je_sprejet_pri_ustvarjanju_in_urejanju(api):
    opis = 'vrstica 1\r\nvrstica 2'
    assert api(Fake([row()])).post(BASE, json=FORM | {'opis': opis}).status_code == 201
    r = api(Fake([row()])).put(f'{BASE}/{PROJECT}', json={'naziv': 'Novo', 'opis': opis, 'lokacija_izvedbe': 'Celje'})
    assert r.status_code == 200, r.text


def test_stranka_ne_vidi_e_poste_in_delavec_ne_doseze_mojstrovih_poti(api):
    r = api(Fake([own()])).get(f'/api/projekti/{PROJECT}')
    assert r.status_code == 200 and set(r.json()) == {'id', 'naziv', 'opis', 'lokacija_izvedbe', 'faza', 'podjetje_naziv', 'termin_od', 'termin_do', 'izvedba_koncana_ob', 'zakljuceno_ob'}
    assert not any('e_posta' in k or 'stranka' in k for k in r.json())
    from app.routers import projekti
    assert getattr(projekti.master, 'company_role') == 'mojster'  # e-mail only behind the mojster guard; delavec gets 403
