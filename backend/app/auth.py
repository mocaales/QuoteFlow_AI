"""Supabase verifies tokens remotely; business roles always come from PostgreSQL."""
import base64
from dataclasses import dataclass
import json
import os
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

bearer = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Principal:
    id: UUID
    session_id: UUID
    email: str

def _payload(token: str) -> dict:
    part = token.split('.')[1]
    return json.loads(base64.urlsafe_b64decode(part + '=' * (-len(part) % 4)))

def auth_config() -> dict:
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
    public = key.startswith('sb_publishable_')
    if not public and key.count('.') == 2:
        try:
            public = _payload(key).get('role') == 'anon'
        except (ValueError, IndexError, UnicodeError):
            pass
    if not url or not public:
        raise HTTPException(503, 'Prijava ni nastavljena. Preverite konfiguracijo Supabase.')
    return {'supabase_url': url, 'supabase_publishable_key': key}

def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise HTTPException(401, 'Potrebna je prijava.', headers={'WWW-Authenticate': 'Bearer'})
    config = auth_config()
    token = credentials.credentials
    try:
        response = httpx.get(
            os.getenv('SUPABASE_INTERNAL_URL', config['supabase_url']).rstrip('/') + '/auth/v1/user',
            headers={'Authorization': f'Bearer {token}', 'apikey': config['supabase_publishable_key']},
            timeout=8,
        )
    except httpx.RequestError:
        raise HTTPException(503, 'Prijavna storitev trenutno ni dosegljiva.') from None
    if response.status_code in (401, 403):
        raise HTTPException(401, 'Seja je potekla. Prijavite se ponovno.', headers={'WWW-Authenticate': 'Bearer'})
    if response.status_code != 200:
        raise HTTPException(503, 'Preverjanje prijave trenutno ni mogoče.')
    # Claims are inspected only AFTER Auth has validated this exact token.
    try:
        user = response.json()
        claims = _payload(token)
        if claims['sub'] != user['id'] or claims['role'] != 'authenticated':
            raise ValueError()
        return Principal(UUID(user['id']), UUID(claims['session_id']), user.get('email') or '')
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
        raise HTTPException(401, 'Neveljavna prijavna seja.') from None
