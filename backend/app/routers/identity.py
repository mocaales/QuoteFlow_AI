"""Verified identities and visible companies."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.access import session_database
from app.auth import Principal, current_user, auth_config
from app.routers.admin import CompanyRow

router = APIRouter()

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
