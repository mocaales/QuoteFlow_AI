"""Shared fake connection, route table and fixtures for the model v3 + admin/US-08 API tests (no database)."""
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, customer, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'ana@example.test')
COMPANY, PROJECT, QUOTE, VRSTA, MATERIAL, ITEM, IZMERA, CATALOG, VLOGA, USER = (uuid4() for _ in range(10))
M = f'/api/podjetja/{COMPANY}/projekti/{PROJECT}'
C = f'/api/podjetja/{COMPANY}'
NOT_FOUND = 'Zapis ni na voljo.'

VRSTA_FORM = {'naziv': 'Polaganje ploščic', 'opis': 'Keramika', 'urna_postavka': '25', 'stevilo_ur': '8', 'stevilo_delavcev': 2, 'aktivna': True}
POSTAVKA_FORM = {'naziv': 'Polaganje', 'opis': 'Keramika', 'vrsta_dela_id': str(VRSTA), 'enota': 'm2', 'cena_na_enoto': '10', 'kolicina': '1', 'popust': '0.1', 'stopnja_ddv': '0.22',
                 'urna_postavka': '25', 'stevilo_ur': '8', 'stevilo_delavcev': 2}
IZ_CENIKA_FORM = {'postavka_cenika_id': str(CATALOG), 'kolicina': '2', 'popust': '0'}
IZMERA_FORM = {'odstej': False, 'kosi': '1', 'dolzina': '5', 'visina': '4'}
CENIK_FORM = {'naziv': 'Rušenje estriha', 'opis': 'Odstranitev in odvoz', 'vrsta_dela_id': str(VRSTA), 'enota': 'm2', 'cena_na_enoto': '12.4500', 'stopnja_ddv': '0.22', 'aktivna': True}

# method, path, body, SQL function that performs the write ('' = read only)
NEW_ROUTES = [
    ('get', f'{C}/vrste-dela', None, ''), ('post', f'{C}/vrste-dela', VRSTA_FORM, 'shrani_vrsto_dela'), ('put', f'{C}/vrste-dela/{VRSTA}', VRSTA_FORM, 'shrani_vrsto_dela'),
    ('put', f'{C}/vrste-dela/{VRSTA}/materiali/{MATERIAL}', {'kolicina_na_enoto': '1.25'}, 'shrani_material_vrste'),
    ('delete', f'{C}/vrste-dela/{VRSTA}/materiali/{MATERIAL}', None, 'odstrani_material_vrste'),
    ('post', f'{C}/cenik', CENIK_FORM, 'shrani_cenik'), ('put', f'{C}/cenik/{CATALOG}', CENIK_FORM, 'shrani_cenik'),
    ('get', f'{M}/postavke', None, ''), ('post', f'{M}/postavke', POSTAVKA_FORM, 'shrani_postavko_projekta'), ('post', f'{M}/postavke/iz-cenika', IZ_CENIKA_FORM, 'dodaj_postavko_iz_cenika'),
    ('put', f'{M}/postavke/{ITEM}', POSTAVKA_FORM, 'shrani_postavko_projekta'), ('delete', f'{M}/postavke/{ITEM}', None, 'odstrani_postavko_projekta'),
    ('post', f'{M}/postavke/{ITEM}/izmere', IZMERA_FORM, 'shrani_izmero'), ('put', f'{M}/postavke/{ITEM}/izmere/{IZMERA}', IZMERA_FORM, 'shrani_izmero'),
    ('delete', f'{M}/postavke/{ITEM}/izmere/{IZMERA}', None, 'odstrani_izmero'),
    ('get', f'{C}/delavci', None, ''), ('post', f'{C}/delavci/povabila', {'e_posta': 'delavec@example.test'}, 'povabi_delavca'), ('get', f'{C}/delavci/povabila', None, ''),
    ('post', f'{C}/delavci/povabila/{VLOGA}/preklic', None, 'preklici_povabilo'), ('patch', f'{C}/delavci/{VLOGA}', {'aktivna': False}, 'uredi_delavca'),
]
WRITES = [r for r in NEW_ROUTES if r[3]]
REMOVED = [('get', f'{C}/cenik/{CATALOG}/sestava', None), ('put', f'{C}/cenik/{CATALOG}/sestava/{MATERIAL}', {'kolicina_na_enoto': '1'}), ('delete', f'{C}/cenik/{CATALOG}/sestava/{MATERIAL}', None),
           ('post', f'{M}/ponudbe/{QUOTE}/postavke', {'naziv': 'x'}), ('post', f'{M}/ponudbe/{QUOTE}/postavke/iz-cenika', IZ_CENIKA_FORM), ('put', f'{M}/ponudbe/{QUOTE}/postavke/{ITEM}', {'naziv': 'x'}),
           ('delete', f'{M}/ponudbe/{QUOTE}/postavke/{ITEM}', None)]


class Cursor:
    def __init__(self, rows): self.rows = [dict(r) if isinstance(r, dict) else r for r in rows]  # copies: routers may pop keys
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Fake:
    def __init__(self, rows=(), error=None): self.rows, self.error, self.calls = list(rows), error, []
    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))
        if self.error: raise self.error
        return Cursor(self.rows)
    def called(self, fn): return [p for sql, p in self.calls if f'quoteflow_private.{fn}(' in sql]
    def wrote(self): return [sql for sql, _ in self.calls if 'quoteflow_private.' in sql]


def qfp(code):
    class Custom(psycopg.DatabaseError): sqlstate = code
    return Custom()


def make_api(fake):
    app.dependency_overrides[current_user] = lambda: ME
    app.dependency_overrides[session_database] = lambda: fake
    app.dependency_overrides[company_member('mojster')] = lambda: fake
    app.dependency_overrides[customer] = lambda: fake
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api():
    try: yield make_api
    finally: app.dependency_overrides.clear()


def call(client, method, path, body=None): return getattr(client, method)(path, **({'json': body} if body is not None else {}))
def untouched(r, fake): return r.status_code == 422 and not fake.wrote()
def reached(r, fake, fn): return r.status_code not in (401, 403, 404, 405, 422) and bool(fake.called(fn))


def keys(value):
    """Every dict key anywhere in a JSON value."""
    if isinstance(value, dict): return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list): return {k for v in value for k in keys(v)}
    return set()


# one superset row: any column the implementation may SELECT, including ones that must never leave the server
FAT = {'id': ITEM, 'podjetje_id': COMPANY, 'projekt_id': PROJECT, 'postavka_projekta_id': ITEM, 'postavka_ponudbe_id': ITEM, 'ponudba_id': QUOTE, 'vrsta_dela_id': VRSTA, 'postavka_cenika_id': CATALOG, 'uporabnik_id': USER, 'material_id': MATERIAL,
       'zaporedje': 1, 'naziv': 'Polaganje', 'opis': '', 'vrsta_dela': 'Polaganje ploščic', 'enota': 'm2', 'cena_na_enoto': '10.0000', 'kolicina': '1.0000', 'popust': '0.100000', 'stopnja_ddv': '0.220000',
       'izmera_skupaj': '20.0000', 'neto': '540.00', 'ddv': '118.80', 'koncna_cena': '658.80', 'skupaj': '658.80', 'osnova': '540.00', 'odstej': False, 'kosi': '1.0000', 'dolzina': '5.0000',
       'visina': '4.0000', 'sirina': None, 'vrednost': '20.0000', 'aktivna': True, 'aktiven': True, 'allowed': True, 'e_posta': 'delavec@example.test', 'ime': 'Ana', 'priimek': 'Novak',
       'dodeljeno_ob': '2026-11-07T10:00:00+00:00', 'vloga': 'delavec', 'sifra': 'LEP-1', 'kolicina_na_enoto': '1.2500', 'kolicina_skupaj': '25.0000',
       # internal: a customer or worker must never see these
       'urna_postavka': '25.0000', 'stevilo_ur': '8.0000', 'stevilo_delavcev': 2, 'cena_dela': '400.00', 'cena_materiala': '80.00', 'nabavna_cena': '3.00', 'marza': '0.2', 'strosek_na_enoto': '8',
       'materiali': [], 'izmere': []}
