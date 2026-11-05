"""Master requests: any verified user submits and lists their own."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.access import session_database
from app.auth import Principal, current_user
from app.models.common import Input

router = APIRouter()

class ProsnjaInput(Input):
    naziv_podjetja: str = Field(min_length=1, max_length=200)
    maticna_stevilka: str = Field(min_length=1, max_length=30)
    davcna_stevilka: str | None = Field(default=None, min_length=1, max_length=30)
    naslov_podjetja: str = Field(min_length=1, max_length=300)

class ProsnjaRow(BaseModel):
    id: UUID
    uporabnik_id: UUID
    naziv_podjetja: str
    maticna_stevilka: str
    davcna_stevilka: str | None
    naslov_podjetja: str
    stanje: Literal['oddana', 'odobrena', 'zavrnjena']
    podjetje_id: UUID | None
    oddano_ob: datetime
    odloceno_ob: datetime | None

@router.post('/prosnje', status_code=201, response_model=ProsnjaRow)
def submit_request(data: ProsnjaInput, db=Depends(session_database)):
    return db.execute('select * from quoteflow_private.oddaj_prosnjo(%s,%s,%s,%s)',
        (data.naziv_podjetja, data.maticna_stevilka, data.davcna_stevilka, data.naslov_podjetja)).fetchone()

@router.get('/prosnje', response_model=list[ProsnjaRow])
def own_requests(user: Principal = Depends(current_user), db=Depends(session_database)):
    return db.execute('''select id,uporabnik_id,naziv_podjetja,maticna_stevilka,davcna_stevilka,naslov_podjetja,stanje,podjetje_id,oddano_ob,odloceno_ob
        from quoteflow.prosnja_mojstra where uporabnik_id=%s order by oddano_ob desc,id''', (user.id,)).fetchall()
