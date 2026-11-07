"""US-08: the invited person lists and decides on invitations addressed to his confirmed e-mail; no company role is needed."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StrictBool

from app.access import session_database
from app.models.common import Input

router = APIRouter(prefix='/povabila')

class MyInvitation(BaseModel):
    id: UUID
    podjetje_id: UUID
    podjetje_naziv: str
    povabil: str
    poslano_ob: datetime

class Decision(Input):
    sprejmi: StrictBool

class DecisionResult(BaseModel):
    id: UUID
    stanje: Literal['sprejeto', 'zavrnjeno']

@router.get('', response_model=list[MyInvitation])
def my_invitations(db=Depends(session_database)):
    return db.execute('select id,podjetje_id,podjetje_naziv,povabil,poslano_ob from quoteflow_private.moja_povabila() povabilo order by poslano_ob desc,id').fetchall()

@router.post('/{povabilo_id}/odlocitev', response_model=DecisionResult)
def decide(povabilo_id: UUID, data: Decision, db=Depends(session_database)):
    row = db.execute('select id,stanje from quoteflow_private.odgovori_povabilo(povabilo => %s, sprejmi => %s)', (povabilo_id, data.sprejmi)).fetchone()
    if not row or row.get('id') is None: raise HTTPException(404, 'Zapis ni na voljo.')
    return row
