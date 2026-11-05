"""Verified identities, company ownership and narrowly scoped administration."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .access import administrator, session_database
from .auth import Principal, current_user, auth_config

router = APIRouter()

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

    @field_validator('*')
    @classmethod
    def trim(cls, value):
        if isinstance(value, str):
            if not value.strip():
                raise ValueError('Vrednost ne sme biti prazna.')
            return value.strip()
        return value

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

class ProfileRole(BaseModel):
    id: UUID
    podjetje_id: UUID | None
    vloga: Literal['admin', 'mojster', 'delavec', 'stranka']
    naziv: str | None

class Profile(BaseModel):
    id: UUID
    e_posta: str
    ime: str
    priimek: str
    vloge: list[ProfileRole]

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

@router.get('/config')
def configuration():
    return auth_config()

@router.get('/me', response_model=Profile)
def me(user: Principal = Depends(current_user), db=Depends(session_database)):
    roles = db.execute('''select v.id,v.podjetje_id,v.vloga,p.naziv from quoteflow.vloga_uporabnika v
        left join quoteflow.podjetje p on p.id=v.podjetje_id
        where v.uporabnik_id=%s and v.aktivna and (v.podjetje_id is null or p.aktivno)
        order by v.vloga,p.naziv''', (user.id,)).fetchall()
    profile = db.execute('select id,e_posta,ime,priimek from quoteflow.uporabnik where id=%s', (user.id,)).fetchone()
    if profile is None:
        raise HTTPException(404, 'Uporabniški profil ni na voljo.')
    return dict(profile) | {'vloge': roles}

@router.get('/podjetja', response_model=list[CompanyRow])
def companies(db=Depends(session_database)):
    return db.execute('select id,lastnik_id,naziv,maticna_stevilka,davcna_stevilka,naslov,aktivno from quoteflow.podjetje order by naziv,id').fetchall()

@router.get('/podjetja/{company_id}', response_model=CompanyRow)
def company(company_id: UUID, db=Depends(session_database)):
    row = db.execute('select id,lastnik_id,naziv,maticna_stevilka,davcna_stevilka,naslov,aktivno from quoteflow.podjetje where id=%s', (company_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'Podjetje ni na voljo.')
    return row

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
