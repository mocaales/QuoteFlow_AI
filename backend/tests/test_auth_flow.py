"""Opt-in HTTP test against disposable LOCAL Supabase Auth and a running API."""
import json
import os
from pathlib import Path
import secrets
import subprocess
from uuid import uuid4
from urllib.parse import urlsplit
import httpx
import psycopg
import pytest

pytestmark=pytest.mark.skipif(not os.getenv('TEST_AUTH_FLOW_URL'),reason='Requires local Auth and application')


def test_real_registration_login_admin_and_revocation():
    api=os.environ['TEST_AUTH_FLOW_URL'].rstrip('/')
    assert urlsplit(api).hostname in ('localhost','127.0.0.1')
    root=Path(__file__).resolve().parents[2]
    status=json.loads(subprocess.check_output(['supabase','status','--output','json'],cwd=root,text=True,stderr=subprocess.DEVNULL))
    auth_url=status['API_URL']+'/auth/v1'
    assert urlsplit(auth_url).hostname in ('localhost','127.0.0.1')
    secret=status.get('SECRET_KEY') or status['SERVICE_ROLE_KEY']
    public=status.get('PUBLISHABLE_KEY') or status['ANON_KEY']
    admin_headers={'apikey':secret,'Authorization':'Bearer '+secret}
    suffix=uuid4().hex;password=secrets.token_urlsafe(24)
    users=[];companies=[]
    with httpx.Client(timeout=20) as h:
        def auth(method,path,**kwargs):
            return h.request(method,auth_url+path,headers=admin_headers,**kwargs)
        try:
            for name in ('admin','member'):
                r=auth('POST','/admin/users',json={'email':f'{name}-{suffix}@example.test','password':password,'email_confirm':True})
                assert r.status_code==200,r.status_code
                users.append(r.json()['id'])
            with psycopg.connect(status['DB_URL']) as c:
                c.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'administrator')",(users[0],))
            def login(name,pw=password):
                return h.post(auth_url+'/token?grant_type=password',headers={'apikey':public},json={'email':f'{name}-{suffix}@example.test','password':pw})
            admin=login('admin');member=login('member');assert admin.status_code==member.status_code==200
            a={'Authorization':'Bearer '+admin.json()['access_token']};m={'Authorization':'Bearer '+member.json()['access_token']}
            assert h.get(api+'/api/me').status_code==401
            assert login('member','wrong-password').status_code==400
            assert h.get(api+'/api/me',headers=m).json()['vloge']==[]
            r=h.post(api+'/api/admin/podjetja',headers=a,json={'naziv':'HTTP test '+suffix});assert r.status_code==201,r.text
            company=r.json()['id'];companies.append(company)
            payload={'uporabnik_id':users[1],'podjetje_id':company,'vloga':'nabavnik'}
            r=h.post(api+'/api/admin/vloge',headers=a,json=payload);assert r.status_code==200,r.text
            role=r.json()['id']
            assert h.post(api+'/api/admin/vloge',headers=a,json=payload).json()['id']==role
            assert h.get(api+'/api/podjetja/'+company,headers=m).status_code==200
            assert h.get(api+'/api/admin/uporabniki',headers=m).status_code==403
            assert h.get(api+'/api/podjetja/'+str(uuid4()),headers=m).status_code==404
            assert h.patch(api+'/api/admin/vloge/'+role,headers=a,json={'aktivna':False}).status_code==200
            assert h.get(api+'/api/podjetja/'+company,headers=m).status_code==404
            assert h.get(api+'/api/me',headers=m).json()['vloge']==[]
            assert h.post(auth_url+'/logout',headers={'apikey':public}|m).status_code==204
            assert h.get(api+'/api/me',headers=m).status_code==401
            email=f'signup-{suffix}@example.test'
            r=h.post(auth_url+'/signup',headers={'apikey':public},json={'email':email,'password':password});assert r.status_code==200,r.status_code
            signed=r.json();uid=signed.get('user',signed).get('id')
            if uid:users.append(uid)
            h.post(auth_url+'/signup',headers={'apikey':public},json={'email':email,'password':password})
            with psycopg.connect(status['DB_URL']) as c:
                assert c.execute('select count(*) from auth.users where email=%s',(email,)).fetchone()[0]==1
                assert c.execute('select count(*) from quoteflow.vloga_uporabnika where uporabnik_id=%s',(uid,)).fetchone()[0]==0
        finally:
            if users:
                with psycopg.connect(status['DB_URL']) as c:
                    c.execute('delete from quoteflow.vloga_uporabnika where uporabnik_id=any(%s::uuid[])',(users,))
                    if companies:c.execute('delete from quoteflow.podjetje where id=any(%s::uuid[])',(companies,))
                    c.execute('delete from quoteflow.uporabnik where id=any(%s::uuid[])',(users,))
                for uid in users:auth('DELETE','/admin/users/'+uid)
