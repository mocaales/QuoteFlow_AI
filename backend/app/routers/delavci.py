"""US-08: a master invites workers by e-mail and manages their delavec role. An invitation never reveals whether the address belongs to a user."""
from datetime import datetime
from re import fullmatch, search
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictBool, field_validator

from app.access import company_member
from app.models.common import Input

router = APIRouter(prefix='/podjetja/{company_id}')
master = company_member('mojster')

class InviteInput(Input):
    e_posta: str = Field(min_length=3, max_length=254)

    @field_validator('e_posta', mode='before')
    @classmethod
    def no_line_breaks(cls, value):
        if isinstance(value, str) and search(r'[\t\n\r\x0b\x0c]', value): raise ValueError('E-poštni naslov ni veljaven.')
        return value

    @field_validator('e_posta')
    @classmethod
    def address(cls, value):
        if not fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', value): raise ValueError('E-poštni naslov ni veljaven.')
        return value

class WorkerUpdate(Input):
    aktivna: StrictBool

# full e-mail is deliberate (decision 16): the master must identify the worker; masters only, never customers or other workers
class WorkerRow(BaseModel):
    id: UUID
    uporabnik_id: UUID
    e_posta: str
    ime: str
    priimek: str
    aktivna: bool
    dodeljeno_ob: datetime

# the same four fields for every address: the answer never reveals whether the person exists or is eligible
class InviteRow(BaseModel):
    id: UUID
    e_posta: str
    stanje: str
    poslano_ob: datetime

class InviteListRow(InviteRow):
    odloceno_ob: datetime | None

@router.get('/delavci', response_model=list[WorkerRow])
def workers(company_id: UUID, db=Depends(master)):
    return db.execute('select id,uporabnik_id,e_posta,ime,priimek,aktivna,dodeljeno_ob from quoteflow_private.delavci_podjetja(podjetje => %s) delavec order by e_posta,id', (company_id,)).fetchall()

@router.post('/delavci/povabila', response_model=InviteRow, status_code=201)
def invite_worker(company_id: UUID, data: InviteInput, db=Depends(master)):
    row = db.execute('select id,e_posta,stanje,poslano_ob from quoteflow_private.povabi_delavca(podjetje => %s, e_posta => %s)', (company_id, data.e_posta)).fetchone()
    if not row or row.get('id') is None: raise HTTPException(404, 'Zapis ni na voljo.')
    return row

@router.get('/delavci/povabila', response_model=list[InviteListRow])
def invitations(company_id: UUID, db=Depends(master)):
    return db.execute('select id,e_posta,stanje,poslano_ob,odloceno_ob from quoteflow_private.povabila_podjetja(podjetje => %s) povabilo order by poslano_ob desc,id', (company_id,)).fetchall()

@router.post('/delavci/povabila/{povabilo_id}/preklic', response_model=InviteListRow)
def cancel_invitation(company_id: UUID, povabilo_id: UUID, db=Depends(master)):
    row = db.execute('select id,e_posta,stanje,poslano_ob,odloceno_ob from quoteflow_private.preklici_povabilo(podjetje => %s, povabilo => %s)', (company_id, povabilo_id)).fetchone()
    if not row or row.get('id') is None: raise HTTPException(404, 'Zapis ni na voljo.')
    return row

@router.patch('/delavci/{vloga_id}', response_model=WorkerRow)
def update_worker(company_id: UUID, vloga_id: UUID, data: WorkerUpdate, db=Depends(master)):
    row = db.execute('select * from quoteflow_private.uredi_delavca(podjetje => %s, vloga => %s, aktivna => %s)', (company_id, vloga_id, data.aktivna)).fetchone()
    if not row or row.get('id') is None: raise HTTPException(404, 'Zapis ni na voljo.')
    return row
