"""US-01/US-02: scoped reads and narrow administrative database procedures."""
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import Principal, current_user, auth_config
from .database import connection_options, DatabaseConfigurationError

router = APIRouter()

def session_database(user: Principal = Depends(current_user)):
    try:
        options = connection_options()
    except DatabaseConfigurationError:
        raise HTTPException(503, 'Podatkovna baza ni nastavljena.') from None
    with psycopg.connect(**options, row_factory=dict_row) as connection:
        role = connection.execute('select current_user as name, rolsuper, rolbypassrls from pg_roles where rolname=current_user').fetchone()
        if role['name'] != 'quoteflow_app' or role['rolsuper'] or role['rolbypassrls']:
            raise HTTPException(503, 'Aplikacijska povezava ni pravilno nastavljena.')
        connection.execute('set local role authenticated')
        connection.execute("select set_config('request.jwt.claim.sub',%s,true), set_config('request.jwt.claims',%s,true)",
                           (str(user.id), json.dumps({'sub':str(user.id),'role':'authenticated','session_id':str(user.session_id)})))
        if not connection.execute('select quoteflow_private.aktivna_seja() as active').fetchone()['active']:
            raise HTTPException(401, 'Seja ni več aktivna. Prijavite se ponovno.')
        yield connection

def administrator(db=Depends(session_database)):
    if not db.execute('select quoteflow_private.administrator() as allowed').fetchone()['allowed']:
        raise HTTPException(403, 'Potrebna je vloga administratorja.')
    return db

class CompanyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    naziv: str = Field(min_length=1, max_length=200)
    @field_validator('naziv')
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError('Naziv ne sme biti prazen.')
        return value.strip()

class CompanyUpdate(CompanyInput):
    stanje: Literal['aktivno','neaktivno']

class RoleInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    uporabnik_id: UUID
    podjetje_id: UUID
    vloga: Literal['nabavnik','ponudnik']

class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    aktivna: bool

@router.get('/config')
def configuration():
    return auth_config()

@router.get('/me')
def me(user: Principal = Depends(current_user), db=Depends(session_database)):
    roles = db.execute('''select v.id,v.podjetje_id,v.vloga,p.naziv from quoteflow.vloga_uporabnika v
        left join quoteflow.podjetje p on p.id=v.podjetje_id
        where v.uporabnik_id=%s and v.aktivna and (v.podjetje_id is null or p.stanje='aktivno')
        order by v.vloga,p.naziv''',(user.id,)).fetchall()
    return {'id':user.id,'e_posta':user.email,'vloge':roles}

@router.get('/podjetja')
def companies(db=Depends(session_database)):
    return db.execute('select id,naziv,stanje from quoteflow.podjetje order by naziv,id').fetchall()

@router.get('/podjetja/{company_id}')
def company(company_id: UUID, db=Depends(session_database)):
    row = db.execute('select id,naziv,stanje from quoteflow.podjetje where id=%s',(company_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Podjetje ni na voljo.')
    return row

@router.get('/admin/uporabniki')
def users(db=Depends(administrator)):
    return db.execute('select id,e_posta from quoteflow.uporabnik order by e_posta,id').fetchall()

@router.get('/admin/vloge')
def roles(db=Depends(administrator)):
    return db.execute('''select v.id,v.uporabnik_id,u.e_posta,v.podjetje_id,p.naziv,v.vloga,v.aktivna
        from quoteflow.vloga_uporabnika v join quoteflow.uporabnik u on u.id=v.uporabnik_id
        left join quoteflow.podjetje p on p.id=v.podjetje_id order by u.e_posta,v.vloga,p.naziv''').fetchall()

@router.post('/admin/podjetja', status_code=201)
def create_company(data: CompanyInput, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.ustvari_podjetje(%s)',(data.naziv,)).fetchone()

@router.put('/admin/podjetja/{company_id}')
def update_company(company_id: UUID, data: CompanyUpdate, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.uredi_podjetje(%s,%s,%s)',(company_id,data.naziv,data.stanje)).fetchone()

@router.post('/admin/vloge')
def assign_role(data: RoleInput, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.dodeli_vlogo(%s,%s,%s)',(data.uporabnik_id,data.podjetje_id,data.vloga)).fetchone()

@router.patch('/admin/vloge/{role_id}')
def update_role(role_id: UUID, data: RoleUpdate, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.aktiviraj_vlogo(%s,%s)',(role_id,data.aktivna)).fetchone()
