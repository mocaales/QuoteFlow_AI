"""Pentest F1: nenavadne JSON vsebine so 422 brez odmeva vnosa (ne 500)."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.access import company_member, session_database
from app.auth import Principal, current_user
from app.main import app

ME = Principal(uuid4(), uuid4(), 'mojster@example.test')
COMPANY, ITEM, MATERIAL = uuid4(), uuid4(), uuid4()
DEEP = '[' * 2000 + ']' * 2000
HEAD = {'Content-Type': 'application/json'}


class Cursor:
    def fetchone(self): return None
    def fetchall(self): return []


class Fake:
    def execute(self, sql, params=()): return Cursor()


@pytest.fixture
def client():
    app.dependency_overrides[current_user] = lambda: ME
    app.dependency_overrides[session_database] = lambda: Fake()
    app.dependency_overrides[company_member('mojster')] = lambda: Fake()
    try: yield TestClient(app, raise_server_exceptions=False)
    finally: app.dependency_overrides.clear()


def bodies(field):
    return [pytest.param(b, id=i) for b, i in ((f'{{"{field}":NaN}}', 'nan'), (f'{{"{field}":Infinity}}', 'inf'), (f'{{"{field}":1e309}}', '1e309'), (f'{{"{field}":"a\\ud800"}}', 'surogat'), (DEEP, 'globok'))]


def check(r):
    assert r.status_code == 422, r.text[:200]
    d = r.json()['detail']
    assert isinstance(d, list) and all(set(i) <= {'loc', 'msg', 'type'} and 'input' not in i for i in d)


@pytest.mark.parametrize('body', bodies('x'))
def test_demo_izracun_nenavaden_json_je_422_brez_inputa(client, body):
    check(client.post('/api/demo/calculate', content=body, headers=HEAD))


@pytest.mark.parametrize('body', bodies('kolicina_na_enoto'))
def test_sestava_nenavaden_json_je_422_brez_inputa(client, body):
    check(client.put(f'/api/podjetja/{COMPANY}/cenik/{ITEM}/sestava/{MATERIAL}', content=body, headers=HEAD))


@pytest.mark.parametrize('body', bodies('naziv'))
def test_projekt_nenavaden_json_je_422_brez_inputa(client, body):
    check(client.post(f'/api/podjetja/{COMPANY}/projekti', content=body, headers=HEAD))
