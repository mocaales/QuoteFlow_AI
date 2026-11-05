"""Projects: masters start and edit them per company; customers read only their own."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.access import company_member, customer
from app.auth import Principal, current_user
from app.errors import CONFLICTS
from app.models.common import Input

router = APIRouter()
master = company_member('mojster')

class EditInput(Input):
    blank_ok = frozenset({'opis', 'lokacija_izvedbe'})
    naziv: str = Field(min_length=1, max_length=200)
    opis: str = Field(default='', max_length=2000)
    lokacija_izvedbe: str = Field(default='', max_length=300)

class CreateInput(EditInput):
    e_posta_stranke: str = Field(min_length=1, max_length=320)

class MasterProject(BaseModel):
    id: UUID
    naziv: str
    opis: str
    lokacija_izvedbe: str
    faza: str
    stranka_ime: str
    stranka_priimek: str
    stranka_e_posta: str
    termin_od: datetime | None
    termin_do: datetime | None

class OwnProject(BaseModel):
    id: UUID
    naziv: str
    opis: str
    lokacija_izvedbe: str
    faza: str
    podjetje_naziv: str
    termin_od: datetime | None
    termin_do: datetime | None

# separate statement after each write: RLS helpers see the statement-start snapshot, so the row written by the function is invisible inside it
def read_back(db, company_id, project_id):
    return db.execute('''select p.id,p.naziv,p.opis,p.lokacija_izvedbe,p.faza,s.ime as stranka_ime,s.priimek as stranka_priimek,
        s.e_posta as stranka_e_posta,p.termin_od,p.termin_do from quoteflow.projekt p
        join quoteflow_private.stranke_projektov(%s) s on s.id=p.stranka_id where p.id=%s and p.podjetje_id=%s''',
        (company_id, project_id, company_id)).fetchone()

COMPANY = '/podjetja/{company_id}/projekti'

@router.get(COMPANY, response_model=list[MasterProject])
def company_projects(company_id: UUID, db=Depends(master)):
    return db.execute('''select p.id,p.naziv,p.opis,p.lokacija_izvedbe,p.faza,s.ime as stranka_ime,s.priimek as stranka_priimek,
        s.e_posta as stranka_e_posta,p.termin_od,p.termin_do from quoteflow.projekt p
        join quoteflow_private.stranke_projektov(%s) s on s.id=p.stranka_id
        where p.podjetje_id=%s order by p.id desc''', (company_id, company_id)).fetchall()

@router.post(COMPANY, status_code=201, response_model=MasterProject)
def create_project(company_id: UUID, data: CreateInput, db=Depends(master)):
    project_id = db.execute('select id from quoteflow_private.ustvari_projekt(%s,%s,%s,%s,%s)',
        (company_id, data.e_posta_stranke, data.naziv, data.opis, data.lokacija_izvedbe)).fetchone()['id']
    # the failed-lookup attempt row must persist, so the transaction must commit (raising would roll it back)
    if project_id is None: return JSONResponse(status_code=409, content={'detail': CONFLICTS['QFP06']})
    return read_back(db, company_id, project_id)

@router.put(COMPANY + '/{projekt_id}', response_model=MasterProject)
def update_project(company_id: UUID, projekt_id: UUID, data: EditInput, db=Depends(master)):
    project_id = db.execute('select id from quoteflow_private.uredi_projekt(%s,%s,%s,%s,%s)',
        (company_id, projekt_id, data.naziv, data.opis, data.lokacija_izvedbe)).fetchone()['id']
    return read_back(db, company_id, project_id)

@router.post(COMPANY + '/{projekt_id}/ogled', response_model=MasterProject)
def request_inspection(company_id: UUID, projekt_id: UUID, db=Depends(master)):
    project_id = db.execute('select id from quoteflow_private.zahtevaj_ogled(%s,%s)', (company_id, projekt_id)).fetchone()['id']
    return read_back(db, company_id, project_id)

@router.get('/projekti', response_model=list[OwnProject])
def own_projects(user: Principal = Depends(current_user), db=Depends(customer)):
    return db.execute('''select p.id,p.naziv,p.opis,p.lokacija_izvedbe,p.faza,quoteflow_private.naziv_podjetja(p.podjetje_id) as podjetje_naziv,
        p.termin_od,p.termin_do from quoteflow.projekt p where p.stranka_id=%s order by p.id desc''', (user.id,)).fetchall()

@router.get('/projekti/{projekt_id}', response_model=OwnProject)
def own_project(projekt_id: UUID, user: Principal = Depends(current_user), db=Depends(customer)):
    row = db.execute('''select p.id,p.naziv,p.opis,p.lokacija_izvedbe,p.faza,quoteflow_private.naziv_podjetja(p.podjetje_id) as podjetje_naziv,
        p.termin_od,p.termin_do from quoteflow.projekt p where p.stranka_id=%s and p.id=%s''', (user.id, projekt_id)).fetchone()
    if not row: raise HTTPException(404, 'Zapis ni na voljo.')
    return row
