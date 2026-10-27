"""Real PostgreSQL checks; point TEST_DATABASE_URL only at a disposable local Supabase."""
import os
from contextlib import contextmanager
from uuid import uuid4
import json
import psycopg
from psycopg.rows import dict_row
import pytest

pytestmark = pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Requires disposable local Supabase')

@pytest.fixture
def db():
    url = os.environ['TEST_DATABASE_URL']
    from psycopg.conninfo import conninfo_to_dict
    assert conninfo_to_dict(url)['host'] in ('localhost', '127.0.0.1'), 'Local test database required'
    with psycopg.connect(url, row_factory=dict_row) as c:
        try:
            yield c
        finally:
            c.rollback()

@pytest.fixture
def identities(db):
    users = {}
    for name in ('admin', 'buyer', 'supplier', 'other', 'new'):
        uid, sid = uuid4(), uuid4()
        db.execute('insert into auth.users(id,email) values(%s,%s)', (uid, f'{name}-{uid}@example.test'))
        db.execute('insert into auth.sessions(id,user_id) values(%s,%s)', (sid, uid))
        users[name] = (uid, sid)
    a = db.execute("insert into quoteflow.podjetje(naziv) values('A') returning id").fetchone()['id']
    b = db.execute("insert into quoteflow.podjetje(naziv) values('B') returning id").fetchone()['id']
    for name, company, role in [('admin', None, 'administrator'), ('buyer', a, 'nabavnik'), ('supplier', b, 'ponudnik'), ('other', a, 'ponudnik')]:
        db.execute('insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,%s)', (users[name][0], company, role))
    return users, a, b

@contextmanager
def as_user(db, identity):
    uid, sid = identity
    db.execute('set local role authenticated')
    db.execute("select set_config('request.jwt.claim.sub',%s,true), set_config('request.jwt.claims',%s,true)", (str(uid), json.dumps({'sub':str(uid),'session_id':str(sid)})))
    try:
        yield db
    finally:
        if db.info.transaction_status != psycopg.pq.TransactionStatus.INERROR:
            db.execute('reset role')

def test_exact_documented_entities_and_auth_preserved(db, identities):
    actual={r['tablename'] for r in db.execute("select tablename from pg_tables where schemaname='quoteflow'")}
    assert actual=={'uporabnik','podjetje','vloga_uporabnika','pravila_ponudnika','postavka_cenika','zaloga','povprasevanje','postavka_povprasevanja','ponudba','postavka_ponudbe'}
    assert db.execute('select count(*) from auth.users').fetchone()['count']>=5
    assert all(r['relrowsecurity'] and r['relforcerowsecurity'] for r in db.execute("select relrowsecurity,relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='quoteflow' and c.relkind='r'"))

def test_role_constraints_and_no_duplicates(db, identities):
    users,a,b=identities
    for company,role,error in [(None,'nabavnik',psycopg.errors.CheckViolation),(a,'administrator',psycopg.errors.CheckViolation),(a,'nabavnik',psycopg.errors.UniqueViolation)]:
        with pytest.raises(error):
            with db.transaction():
                db.execute('insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,%s)',(users['buyer'][0],company,role))

def test_service_cannot_have_stock_and_rules_cannot_overlap(db, identities):
    _,_,b=identities
    item=db.execute("insert into quoteflow.postavka_cenika(podjetje_id,vrsta,opis,enota,cena_na_enoto,strosek_na_enoto) values(%s,'storitev','Servis','ura',100,50) returning id",(b,)).fetchone()['id']
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute('insert into quoteflow.zaloga values(%s,5,now())',(item,))
    db.execute('insert into quoteflow.pravila_ponudnika(podjetje_id,najmanjsa_marza,najvecji_popust,najdaljsi_rok_dni,velja_od) values(%s,.2,.1,7,now())',(b,))
    with pytest.raises(psycopg.errors.ExclusionViolation):
        with db.transaction():db.execute('insert into quoteflow.pravila_ponudnika(podjetje_id,najmanjsa_marza,najvecji_popust,najdaljsi_rok_dni,velja_od) values(%s,.2,.1,7,now())',(b,))

def test_rls_no_membership_and_cross_company(db, identities):
    users,a,b=identities
    with as_user(db,users['new']):assert not db.execute('select * from quoteflow.podjetje').fetchall()
    with as_user(db,users['buyer']):assert [r['id'] for r in db.execute('select * from quoteflow.podjetje')]==[a]
    with as_user(db,users['supplier']):assert [r['id'] for r in db.execute('select * from quoteflow.podjetje')]==[b]

def test_administrator_cannot_see_supplier_costs_or_gain_supplier_role(db, identities):
    users,_,b=identities
    db.execute("insert into quoteflow.postavka_cenika(podjetje_id,vrsta,opis,enota,cena_na_enoto,strosek_na_enoto) values(%s,'blago','Blago','kos',10,5)",(b,))
    with as_user(db,users['admin']):
        assert db.execute('select quoteflow_private.administrator() as yes').fetchone()['yes']
        assert not db.execute('select * from quoteflow.postavka_cenika').fetchall()
        assert not db.execute("select quoteflow_private.clan(%s,'ponudnik') as yes",(b,)).fetchone()['yes']

def test_admin_functions_and_immediate_revocation(db, identities):
    users,a,_=identities
    with as_user(db,users['admin']):
        row=db.execute("select * from quoteflow_private.dodeli_vlogo(%s,%s,'nabavnik')",(users['new'][0],a)).fetchone()
        again=db.execute("select * from quoteflow_private.dodeli_vlogo(%s,%s,'nabavnik')",(users['new'][0],a)).fetchone()
        assert row['id']==again['id']
    with as_user(db,users['new']):assert db.execute('select * from quoteflow.podjetje').fetchall()
    with as_user(db,users['admin']):db.execute('select * from quoteflow_private.aktiviraj_vlogo(%s,false)',(row['id'],))
    with as_user(db,users['new']):assert not db.execute('select * from quoteflow.podjetje').fetchall()

def test_nonadmin_cannot_mutate_and_deactivated_company_blocks_access(db, identities):
    users,a,_=identities
    with as_user(db,users['buyer']):
        for query in ["insert into quoteflow.podjetje(naziv) values('Forbidden')", "select * from quoteflow_private.ustvari_podjetje('Forbidden')"]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with db.transaction():db.execute(query)
    with as_user(db,users['admin']):db.execute("select * from quoteflow_private.uredi_podjetje(%s,'A','neaktivno')",(a,))
    with as_user(db,users['buyer']):assert not db.execute('select * from quoteflow.podjetje').fetchall()

def test_deleted_session_immediately_blocks_access(db, identities):
    users,_,_=identities
    db.execute('delete from auth.sessions where id=%s',(users['buyer'][1],))
    with as_user(db,users['buyer']):
        assert not db.execute('select quoteflow_private.aktivna_seja() as yes').fetchone()['yes']
        assert not db.execute('select * from quoteflow.podjetje').fetchall()

@pytest.fixture
def offer(db, identities):
    users,a,b=identities
    buyer_role=db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s and vloga='nabavnik'",(users['buyer'][0],)).fetchone()['id']
    supplier_role=db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s",(users['supplier'][0],)).fetchone()['id']
    rfq=db.execute('insert into quoteflow.povprasevanje(podjetje_nabavnika_id,ustvaril_vloga_id) values(%s,%s) returning id',(a,buyer_role)).fetchone()['id']
    item=db.execute("insert into quoteflow.postavka_povprasevanja(povprasevanje_id,opis,kolicina,enota) values(%s,'Servis',1,'ura') returning id",(rfq,)).fetchone()['id']
    db.execute("update quoteflow.povprasevanje set stanje='oddano',oddano_ob=now() where id=%s",(rfq,))
    rules=db.execute('insert into quoteflow.pravila_ponudnika(podjetje_id,najmanjsa_marza,najvecji_popust,najdaljsi_rok_dni,velja_od) values(%s,.2,.1,7,now()) returning id',(b,)).fetchone()['id']
    quote=db.execute("insert into quoteflow.ponudba(povprasevanje_id,podjetje_ponudnika_id,izvor_izbire) values(%s,%s,'rocna') returning id",(rfq,b)).fetchone()['id']
    line=db.execute("insert into quoteflow.postavka_ponudbe(ponudba_id,postavka_povprasevanja_id,opis,kolicina,enota,cena_na_enoto,strosek_na_enoto,dobavni_rok_dni) values(%s,%s,'Servis',1,'ura',100,50,3) returning id",(quote,item)).fetchone()['id']
    return quote,line,rules,supplier_role,rfq

def test_approval_requires_supplier_and_locks_snapshot(db,identities,offer):
    users,_,_=identities
    q,line,rules,supplier,rfq=offer
    wrong=db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s",(users['admin'][0],)).fetchone()['id']
    sql="update quoteflow.ponudba set stanje='odobrena',pravila_id=%s,odobril_vloga_id=%s,odobreno_ob=now(),znesek_skupaj=100 where id=%s"
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute(sql,(rules,wrong,q))
    db.execute(sql,(rules,supplier,q))
    for query,args in [('update quoteflow.ponudba set placilni_pogoji=%s where id=%s',('changed',q)),('update quoteflow.postavka_ponudbe set cena_na_enoto=999 where id=%s',(line,)),('delete from quoteflow.postavka_ponudbe where id=%s',(line,))]:
        with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
            with db.transaction():db.execute(query,args)
    with as_user(db,users['buyer']):assert not db.execute('select * from quoteflow.postavka_ponudbe').fetchall()

def test_wrong_rfq_and_wrong_supplier_sources_rejected(db,identities,offer):
    _,a,_=identities;q,line,_,_,_=offer
    foreign=db.execute("insert into quoteflow.postavka_cenika(podjetje_id,vrsta,opis,enota,cena_na_enoto,strosek_na_enoto) values(%s,'blago','Other','kos',1,0) returning id",(a,)).fetchone()['id']
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute('update quoteflow.postavka_ponudbe set postavka_cenika_id=%s where id=%s',(foreign,line))

def test_draft_requires_valid_buyer_and_submission_requires_items(db,identities):
    users,a,b=identities
    supplier=db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s",(users['supplier'][0],)).fetchone()['id']
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute('insert into quoteflow.povprasevanje(podjetje_nabavnika_id,ustvaril_vloga_id) values(%s,%s)',(b,supplier))
    buyer=db.execute("select id from quoteflow.vloga_uporabnika where uporabnik_id=%s",(users['buyer'][0],)).fetchone()['id']
    rfq=db.execute('insert into quoteflow.povprasevanje(podjetje_nabavnika_id,ustvaril_vloga_id) values(%s,%s) returning id',(a,buyer)).fetchone()['id']
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute("update quoteflow.povprasevanje set stanje='oddano',oddano_ob=now() where id=%s",(rfq,))

@pytest.fixture
def api_client(db, identities):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import Principal, current_user
    from app.identity import session_database
    users,_,_=identities
    selected={'name':'admin'}
    def principal():
        uid,sid=users[selected['name']]
        return Principal(uid,sid,selected['name']+'@example.test')
    def connection():
        with db.transaction():
            with as_user(db,users[selected['name']]):
                if not db.execute('select quoteflow_private.aktivna_seja() as active').fetchone()['active']:
                    from fastapi import HTTPException
                    raise HTTPException(401,'Seja ni več aktivna.')
                yield db
    app.dependency_overrides[current_user]=principal
    app.dependency_overrides[session_database]=connection
    try:
        with TestClient(app) as c:yield c,selected
    finally:
        app.dependency_overrides.clear()


def test_admin_api_end_to_end_and_role_validation(api_client,db,identities):
    c,selected=api_client;users,_,_=identities
    r=c.post('/api/admin/podjetja',json={'naziv':' Novo podjetje '});assert r.status_code==201
    company=r.json();assert company['naziv']=='Novo podjetje'
    payload={'uporabnik_id':str(users['new'][0]),'podjetje_id':company['id'],'vloga':'nabavnik'}
    r=c.post('/api/admin/vloge',json=payload);assert r.status_code==200
    role=r.json();assert c.post('/api/admin/vloge',json=payload).json()['id']==role['id']
    assert c.post('/api/admin/vloge',json=payload|{'vloga':'administrator'}).status_code==422
    assert c.post('/api/admin/podjetja',json={'naziv':' '}).status_code==422
    selected['name']='new'
    assert len(c.get('/api/me').json()['vloge'])==1
    assert c.get('/api/podjetja/'+company['id']).status_code==200
    assert c.get('/api/admin/uporabniki').status_code==403
    selected['name']='admin'
    assert c.patch('/api/admin/vloge/'+role['id'],json={'aktivna':False}).status_code==200
    selected['name']='new'
    assert c.get('/api/me').json()['vloge']==[]
    assert c.get('/api/podjetja/'+company['id']).status_code==404


def test_admin_deactivation_and_cross_company_direct_urls(api_client,identities):
    c,selected=api_client;_,a,b=identities
    selected['name']='buyer'
    assert c.get('/api/podjetja/'+str(a)).status_code==200
    assert c.get('/api/podjetja/'+str(b)).status_code==404
    assert c.post('/api/admin/podjetja',json={'naziv':'Forbidden'}).status_code==403
    selected['name']='admin'
    assert c.put('/api/admin/podjetja/'+str(a),json={'naziv':'A','stanje':'neaktivno'}).status_code==200
    assert c.put('/api/admin/podjetja/'+str(uuid4()),json={'naziv':'Missing','stanje':'aktivno'}).status_code==404
    selected['name']='buyer'
    assert c.get('/api/podjetja/'+str(a)).status_code==404


def test_revoked_session_blocks_api_with_old_token(api_client,db,identities):
    c,selected=api_client;users,_,_=identities
    assert c.get('/api/me').status_code==200
    db.execute('delete from auth.sessions where id=%s',(users['admin'][1],))
    assert c.get('/api/me').status_code==401
