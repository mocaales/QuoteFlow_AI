import base64
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
import pytest
from app import auth
from app.main import app

client=TestClient(app)

def token(**claims):
    return 'header.'+base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')+'.signature'

@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL','https://project.example')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test')


def test_missing_bearer_is_unauthorized():
    for path in ['/api/me','/api/podjetja','/api/admin/uporabniki','/api/admin/vloge']:
        r=client.get(path);assert r.status_code==401
        assert r.headers['cache-control']=='no-store'


def test_invalid_token_rejected_by_auth(monkeypatch):
    monkeypatch.setattr(auth.httpx,'get',lambda *a,**k:httpx.Response(401))
    assert client.get('/api/me',headers={'Authorization':'Bearer forged'}).status_code==401


def test_unavailable_auth_does_not_expose_secrets(monkeypatch):
    def fail(*args,**kwargs):raise httpx.ConnectError('DO-NOT-LEAK')
    monkeypatch.setattr(auth.httpx,'get',fail)
    r=client.get('/api/me',headers={'Authorization':'Bearer secret'})
    assert r.status_code==503 and 'DO-NOT-LEAK' not in r.text


def test_public_config_never_returns_privileged_key(monkeypatch):
    for key in ['sb_secret_PRIVATE',token(role='service_role'),'invalid']:
        monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY',key)
        r=client.get('/api/config');assert r.status_code==503 and key not in r.text
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','sb_publishable_test')
    assert client.get('/api/config').json()['supabase_publishable_key']=='sb_publishable_test'


def test_verified_token_still_requires_matching_identity_and_session(monkeypatch):
    uid,sid=str(uuid4()),str(uuid4())
    def verify(*args,**kwargs):
        assert kwargs['headers']['Authorization'].startswith('Bearer ')
        return httpx.Response(200,json={'id':uid,'email':'user@example.test'})
    monkeypatch.setattr(auth.httpx,'get',verify)
    for claims in [dict(sub=str(uuid4()),session_id=sid,role='authenticated'),dict(sub=uid,role='authenticated'),dict(sub=uid,session_id=sid,role='service_role')]:
        assert client.get('/api/me',headers={'Authorization':'Bearer '+token(**claims)}).status_code==401
