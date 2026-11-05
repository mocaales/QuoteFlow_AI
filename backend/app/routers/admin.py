"""Global administration: users, roles, companies and master request decisions."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StrictBool, model_validator

from app.access import administrator
from app.models.common import Input
from app.routers.prosnje import ProsnjaRow

router = APIRouter()

class CompanyDetails(Input):
    naziv: str = Field(min_length=1, max_length=200)
    maticna_stevilka: str = Field(min_length=1, max_length=30)
    davcna_stevilka: str | None = Field(default=None, min_length=1, max_length=30)
    naslov: str = Field(min_length=1, max_length=300)

class CompanyInput(CompanyDetails):
    lastnik_id: UUID

class CompanyUpdate(CompanyDetails):
    aktivno: bool

class CompanyRow(CompanyInput):
    id: UUID
    aktivno: bool

class RoleInput(Input):
    uporabnik_id: UUID
    podjetje_id: UUID | None = None
    vloga: Literal['stranka', 'mojster', 'delavec']

    @model_validator(mode='after')
    def scope(self):
        if (self.vloga == 'stranka') != (self.podjetje_id is None):
            raise ValueError('Stranka je globalna vloga, mojster in delavec pa sta vezana na podjetje.')
        return self

class RoleUpdate(Input):
    aktivna: bool

class UserRow(BaseModel):
    id: UUID
    e_posta: str
    ime: str
    priimek: str

class RoleRow(BaseModel):
    id: UUID
    uporabnik_id: UUID
    podjetje_id: UUID | None
    vloga: Literal['admin', 'mojster', 'delavec', 'stranka']
    aktivna: bool

class AdminRoleRow(RoleRow):
    e_posta: str
    naziv: str | None

class ProsnjaDecision(Input):
    odobri: StrictBool

class AdminProsnjaRow(ProsnjaRow):
    e_posta: str
    ime: str
    priimek: str

@router.get('/admin/uporabniki', response_model=list[UserRow])
def users(db=Depends(administrator)):
    return db.execute('select id,e_posta,ime,priimek from quoteflow.uporabnik order by e_posta,id').fetchall()

@router.get('/admin/vloge', response_model=list[AdminRoleRow])
def roles(db=Depends(administrator)):
    return db.execute('''select v.id,v.uporabnik_id,u.e_posta,v.podjetje_id,p.naziv,v.vloga,v.aktivna
        from quoteflow.vloga_uporabnika v join quoteflow.uporabnik u on u.id=v.uporabnik_id
        left join quoteflow.podjetje p on p.id=v.podjetje_id order by u.e_posta,v.vloga,p.naziv''').fetchall()

@router.post('/admin/podjetja', status_code=201, response_model=CompanyRow)
def create_company(data: CompanyInput, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.ustvari_podjetje(%s,%s,%s,%s,%s)',
        (data.lastnik_id, data.naziv, data.maticna_stevilka, data.davcna_stevilka, data.naslov)).fetchone()

@router.put('/admin/podjetja/{company_id}', response_model=CompanyRow)
def update_company(company_id: UUID, data: CompanyUpdate, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.uredi_podjetje(%s,%s,%s,%s,%s,%s)',
        (company_id, data.naziv, data.maticna_stevilka, data.davcna_stevilka, data.naslov, data.aktivno)).fetchone()

@router.post('/admin/vloge', response_model=RoleRow)
def assign_role(data: RoleInput, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.dodeli_vlogo(%s,%s,%s)', (data.uporabnik_id, data.podjetje_id, data.vloga)).fetchone()

@router.patch('/admin/vloge/{role_id}', response_model=RoleRow)
def update_role(role_id: UUID, data: RoleUpdate, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.aktiviraj_vlogo(%s,%s)', (role_id, data.aktivna)).fetchone()

@router.get('/admin/prosnje', response_model=list[AdminProsnjaRow])
def admin_requests(db=Depends(administrator)):
    return db.execute('''select p.id,p.uporabnik_id,p.naziv_podjetja,p.maticna_stevilka,p.davcna_stevilka,p.naslov_podjetja,p.stanje,p.podjetje_id,p.oddano_ob,p.odloceno_ob,
        u.e_posta,u.ime,u.priimek from quoteflow.prosnja_mojstra p join quoteflow.uporabnik u on u.id=p.uporabnik_id
        order by (p.stanje='oddana') desc,p.oddano_ob desc,p.id''').fetchall()

@router.post('/admin/prosnje/{prosnja_id}/odlocitev', response_model=ProsnjaRow)
def decide_request(prosnja_id: UUID, data: ProsnjaDecision, db=Depends(administrator)):
    return db.execute('select * from quoteflow_private.odloci_prosnjo(%s,%s)', (prosnja_id, data.odobri)).fetchone()
