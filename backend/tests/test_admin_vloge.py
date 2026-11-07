"""Admin 'Podjetja in pravice' rework: role rows carry the person's name and the owner flag so the UI can filter and protect the owner."""
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import session_database
from app.auth import current_user
from app.main import app
from v3_support import COMPANY, FAT, ME, USER, VLOGA, Fake, api, call, qfp

ROW = FAT | {'id': VLOGA, 'uporabnik_id': USER, 'podjetje_id': COMPANY, 'vloga': 'mojster', 'naziv': 'Gradnje d.o.o.', 'je_lastnik': True, 'podjetje_aktivno': True, 'telefon': '1', 'geslo': 'x', 'lastnik_id': USER}
BASE = {'id', 'uporabnik_id', 'podjetje_id', 'vloga', 'aktivna', 'e_posta', 'naziv'}


@pytest.fixture
def admin(api):
    from app.access import administrator
    def use(fake):
        client = api(fake); app.dependency_overrides[administrator] = lambda: fake; return client
    return use


def test_seznam_vlog_vsebuje_ime_priimek_in_oznako_lastnika(admin):
    r = admin(Fake([ROW, ROW | {'je_lastnik': False, 'vloga': 'delavec'}])).get('/api/admin/vloge')
    assert r.status_code == 200 and len(r.json()) == 2
    for row in r.json():
        assert BASE | {'ime', 'priimek', 'je_lastnik'} <= set(row), set(row)
        assert isinstance(row['je_lastnik'], bool) and row['ime'] == 'Ana' and row['priimek'] == 'Novak'
    assert [x['je_lastnik'] for x in r.json()] == [True, False]


def test_seznam_vlog_ne_pušča_internih_polj(admin):
    r = admin(Fake([ROW])).get('/api/admin/vloge'); assert r.status_code == 200
    assert not ({'telefon', 'geslo', 'lastnik_id', 'urna_postavka', 'cena_dela', 'materiali'} & set(r.json()[0]))


def test_seznam_vlog_je_za_ne_administratorja_403_tudi_z_novimi_polji():
    fake = Fake([{'allowed': False}]); app.dependency_overrides[current_user] = lambda: ME; app.dependency_overrides[session_database] = lambda: fake
    try: c = TestClient(app, raise_server_exceptions=False); r = c.get('/api/admin/vloge'); r2 = c.patch(f'/api/admin/vloge/{VLOGA}', json={'aktivna': False})
    finally: app.dependency_overrides.clear()
    assert r.status_code == 403 and r2.status_code == 403 and len(fake.calls) == 2 and not any('vloga_uporabnika' in s for s, _ in fake.calls)


def test_admin_umik_vloge_pokliče_aktiviraj_vlogo_in_vrne_vrstico(admin):
    fake = Fake([{'id': VLOGA, 'uporabnik_id': USER, 'podjetje_id': COMPANY, 'vloga': 'delavec', 'aktivna': False}]); r = admin(fake).patch(f'/api/admin/vloge/{VLOGA}', json={'aktivna': False})
    assert r.status_code == 200 and fake.called('aktiviraj_vlogo')[0] == (VLOGA, False)


@pytest.mark.parametrize('code', ['QFP22'])
def test_admin_si_ne_dodeli_vloge_v_podjetju_je_409(admin, code):
    r = admin(Fake(error=qfp(code))).post('/api/admin/vloge', json={'uporabnik_id': str(USER), 'podjetje_id': str(COMPANY), 'vloga': 'delavec'}); assert r.status_code == 409


def test_admin_umik_lastnikove_vloge_mojster_je_409_s_fiksnim_besedilom_qfp33(admin):
    r = admin(Fake(error=qfp('QFP33'))).patch(f'/api/admin/vloge/{VLOGA}', json={'aktivna': False}); assert r.status_code == 409 and r.json()['detail'] == 'Lastniku podjetja ni mogoče odvzeti vloge mojster.'


@pytest.mark.parametrize('body', [{'aktivna': 'da'}, {'aktivna': 1}, {}, {'aktivna': False, 'vloga': 'admin'}])
def test_admin_patch_vloge_strogo_telo(admin, body):
    fake = Fake([ROW]); assert admin(fake).patch(f'/api/admin/vloge/{VLOGA}', json=body).status_code == 422 and not fake.calls


def test_admin_dodelitev_mojstra_ali_delavca_brez_podjetja_je_422(admin):
    fake = Fake([ROW])
    for role in ('mojster', 'delavec'): assert admin(fake).post('/api/admin/vloge', json={'uporabnik_id': str(USER), 'vloga': role}).status_code == 422
    assert admin(fake).post('/api/admin/vloge', json={'uporabnik_id': str(USER), 'vloga': 'admin'}).status_code == 422 and not fake.wrote()


def test_seznam_uporabnikov_potrjen_pride_iz_potrjeni_uporabniki(admin):
    fake = Fake([{'id': USER, 'e_posta': 'a@b.si', 'ime': 'Ana', 'priimek': 'Novak', 'potrjen': True}]); r = admin(fake).get('/api/admin/uporabniki')
    assert r.status_code == 200 and r.json()[0]['potrjen'] is True
    sql = ' '.join(s for s, _ in fake.calls); assert 'quoteflow_private.potrjeni_uporabniki' in sql and 'vloga_uporabnika' not in sql
