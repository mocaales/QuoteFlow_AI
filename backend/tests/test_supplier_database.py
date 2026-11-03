import os
from datetime import datetime,timedelta,timezone
import psycopg
import pytest
from test_identity_database import db,identities,as_user,api_client,offer
from test_supplier import ITEM

pytestmark=pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='Requires disposable local Supabase')

@pytest.fixture
def supplier_api(api_client,identities):
    c,selected=api_client;selected['name']='supplier'
    return c,selected,f'/api/podjetja/{identities[2]}'

def create(c,base,**change):
    r=c.post(base+'/cenik',json=ITEM|change);assert r.status_code==201,r.text
    return r.json()

def test_catalog_confirmation_edit_and_deactivation(supplier_api):
    c,_,base=supplier_api;item=create(c,base);path=base+'/cenik/'+item['id']
    assert item['potrjeno_ob'] is None
    assert c.post(path+'/potrditev').json()['potrjeno_ob']
    r=c.put(path,json=ITEM|{'cena_na_enoto':'13.5'})
    assert r.status_code==200 and r.json()['potrjeno_ob'] is None
    assert c.post(path+'/potrditev').status_code==200
    assert c.put(path,json=ITEM|{'aktivna':False}).json()['aktivna'] is False
    assert len(c.get(base+'/cenik').json())==1
    assert c.post(path+'/potrditev').status_code==422

def test_stock_zero_unknown_confirmation_and_unit_change(supplier_api):
    c,_,base=supplier_api;item=create(c,base);path=base+'/cenik/'+item['id']
    assert c.get(base+'/cenik').json()[0]['razpolozljiva_kolicina'] is None
    assert c.put(path+'/zaloga',json={'razpolozljiva_kolicina':'0'}).status_code==200
    row=c.get(base+'/cenik').json()[0]
    assert float(row['razpolozljiva_kolicina'])==0 and row['zaloga_potrjeno_ob']
    c.put(path,json=ITEM|{'enota':'paket'})
    assert c.get(base+'/cenik').json()[0]['razpolozljiva_kolicina'] is None
    assert c.put(path+'/zaloga',json={'razpolozljiva_kolicina':'2.5'}).status_code==200
    assert c.delete(path+'/zaloga').status_code==200
    assert c.get(base+'/cenik').json()[0]['razpolozljiva_kolicina'] is None

def test_service_and_inactive_goods_cannot_get_stock(supplier_api):
    c,_,base=supplier_api
    for change in [{'vrsta':'storitev'},{'aktivna':False}]:
        item=create(c,base,**change)
        assert c.put(base+'/cenik/'+item['id']+'/zaloga',json={'razpolozljiva_kolicina':1}).status_code==422

def test_switch_to_service_clears_stock(supplier_api):
    c,_,base=supplier_api;item=create(c,base);path=base+'/cenik/'+item['id']
    c.put(path+'/zaloga',json={'razpolozljiva_kolicina':5})
    assert c.put(path,json=ITEM|{'vrsta':'storitev'}).status_code==200
    assert c.get(base+'/cenik').json()[0]['razpolozljiva_kolicina'] is None

def test_role_required_even_for_global_admin_and_buyer(supplier_api):
    c,selected,base=supplier_api
    for name in ['admin','buyer','new','other']:
        selected['name']=name
        for suffix in ['/cenik','/pravila']:assert c.get(base+suffix).status_code==403
        assert c.post(base+'/cenik',json=ITEM).status_code==403
        assert c.post(base+'/pravila',json={'najmanjsa_marza':'.2','najvecji_popust':'.1','najdaljsi_rok_dni':7}).status_code==403

def test_foreign_item_cannot_be_targeted_under_own_company(supplier_api,db,identities):
    c,_,base=supplier_api;_,a,_=identities
    foreign=db.execute("insert into quoteflow.postavka_cenika(podjetje_id,vrsta,opis,enota,cena_na_enoto,strosek_na_enoto) values(%s,'blago','Other','kos',1,0) returning id",(a,)).fetchone()['id']
    path=base+'/cenik/'+str(foreign)
    assert c.put(path,json=ITEM).status_code==404
    assert c.post(path+'/potrditev').status_code==404
    assert c.put(path+'/zaloga',json={'razpolozljiva_kolicina':1}).status_code==404
    assert c.get(base+'/cenik').json()==[]

def test_role_revocation_and_company_deactivation(supplier_api,db,identities):
    c,_,base=supplier_api;users,_,company=identities
    db.execute('update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id=%s',(users['supplier'][0],))
    assert c.post(base+'/cenik',json=ITEM).status_code==403
    db.execute('update quoteflow.vloga_uporabnika set aktivna=true where uporabnik_id=%s',(users['supplier'][0],))
    db.execute("update quoteflow.podjetje set stanje='neaktivno' where id=%s",(company,))
    assert c.get(base+'/pravila').status_code==403

def test_new_rules_close_predecessor_preserving_values(supplier_api):
    c,_,base=supplier_api;data={'najmanjsa_marza':'.2','najvecji_popust':'.1','najdaljsi_rok_dni':7}
    r=c.post(base+'/pravila',json=data);assert r.status_code==201,r.text
    start=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    r=c.post(base+'/pravila',json=data|{'velja_od':start,'najmanjsa_marza':'.3'});assert r.status_code==201,r.text
    rows=c.get(base+'/pravila').json();assert len(rows)==2
    assert rows[1]['velja_do']==rows[0]['velja_od'] and float(rows[1]['najmanjsa_marza'])==.2

def test_rules_overlap_rolls_back_and_past_rejected(supplier_api):
    c,_,base=supplier_api;data={'najmanjsa_marza':'.2','najvecji_popust':'.1','najdaljsi_rok_dni':7}
    start=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat()
    assert c.post(base+'/pravila',json=data|{'velja_od':start}).status_code==201
    assert c.post(base+'/pravila',json=data).status_code==409
    assert len(c.get(base+'/pravila').json())==1
    past=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    assert c.post(base+'/pravila',json=data|{'velja_od':past}).status_code==422
    assert c.post(base+'/pravila',json=data|{'velja_do':past}).status_code==422

def test_direct_writes_and_internal_helper_forbidden(db,identities):
    users,_,company=identities
    with as_user(db,users['supplier']):
        for query,args in [("update quoteflow.postavka_cenika set opis='Forbidden'",()),('select quoteflow_private.preveri_ponudnika(%s)',(company,))]:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with db.transaction():db.execute(query,args)

def test_same_supplier_in_two_companies_still_gets_scoped_lists(supplier_api,db,identities):
    c,_,base=supplier_api;users,a,_=identities
    item=create(c,base)
    db.execute("insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(%s,%s,'ponudnik')",(users['supplier'][0],a))
    second='/api/podjetja/'+str(a)
    assert c.get(second+'/cenik').json()==[]
    assert c.put(second+'/cenik/'+item['id'],json=ITEM).status_code==404
    create(c,second,vrsta='storitev',opis='Servis')
    assert [row['opis'] for row in c.get(base+'/cenik').json()]==[ITEM['opis']]
    assert [row['opis'] for row in c.get(second+'/cenik').json()]==['Servis']


def test_sql_operations_recheck_supplier_role_without_api(db,identities):
    users,_,company=identities
    for name in ['admin','buyer','other']:
        with as_user(db,users[name]):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with db.transaction():
                    db.execute("select * from quoteflow_private.shrani_cenik(%s,null,'blago','Forbidden','kos',1,0,1,true)",(company,))


def test_insufficient_stock_blocks_approval_and_catalog_changes_preserve_snapshot(supplier_api,db,offer):
    c,_,base=supplier_api
    quote,line,rules,supplier_role,_=offer
    item=create(c,base)
    path=base+'/cenik/'+item['id']
    assert c.put(path+'/zaloga',json={'razpolozljiva_kolicina':'0'}).status_code==200
    db.execute('update quoteflow.postavka_ponudbe set postavka_cenika_id=%s where id=%s',(item['id'],line))
    approve="update quoteflow.ponudba set stanje='odobrena',pravila_id=%s,odobril_vloga_id=%s,odobreno_ob=now(),znesek_skupaj=100 where id=%s"
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():db.execute(approve,(rules,supplier_role,quote))
    assert db.execute('select stanje from quoteflow.ponudba where id=%s',(quote,)).fetchone()['stanje']=='povabljena'
    assert c.put(path+'/zaloga',json={'razpolozljiva_kolicina':'2'}).status_code==200
    db.execute(approve,(rules,supplier_role,quote))
    assert c.put(path,json=ITEM|{'cena_na_enoto':'999','aktivna':False}).status_code==200
    assert db.execute('select cena_na_enoto from quoteflow.postavka_ponudbe where id=%s',(line,)).fetchone()['cena_na_enoto']==100
    assert db.execute('select znesek_skupaj from quoteflow.ponudba where id=%s',(quote,)).fetchone()['znesek_skupaj']==100
