"""Types of work (labour defaults and materials per type), scoped to active masters."""
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, StrictBool, StrictInt

from app.access import company_member
from app.models.common import Input, Plain

router = APIRouter(prefix='/podjetja/{company_id}')
master = company_member('mojster')

Rate = Annotated[Decimal, Plain, Field(ge=0, le=10000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Hours = Annotated[Decimal, Plain, Field(ge=0, le=100000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Workers = Annotated[StrictInt, Field(ge=1, le=1000)]
Quantity = Annotated[Decimal, Plain, Field(gt=0, le=1000000, max_digits=18, decimal_places=4, allow_inf_nan=False)]

class WorkTypeInput(Input):
    blank_ok = frozenset({'opis'})
    naziv: str = Field(min_length=1, max_length=200)
    opis: str = Field(default='', max_length=2000)
    urna_postavka: Rate
    stevilo_ur: Hours
    stevilo_delavcev: Workers
    aktivna: StrictBool = True

class MaterialInput(Input):
    kolicina_na_enoto: Quantity

class MaterialRow(BaseModel):
    material_id: UUID
    naziv: str
    enota: str
    kolicina_na_enoto: Decimal
    cena_na_enoto: Decimal
    aktiven: bool

class WorkTypeSaved(BaseModel):
    id: UUID
    podjetje_id: UUID
    naziv: str
    opis: str
    urna_postavka: Decimal
    stevilo_ur: Decimal
    stevilo_delavcev: int
    aktivna: bool
    cena_dela: Decimal

class WorkTypeRow(WorkTypeSaved):
    materiali: list[MaterialRow]

@router.get('/vrste-dela', response_model=list[WorkTypeRow])
def work_types(company_id: UUID, db=Depends(master)):
    return db.execute('''select v.id,v.podjetje_id,v.naziv,v.opis,v.urna_postavka,v.stevilo_ur,v.stevilo_delavcev,v.aktivna,v.cena_dela,
        (select coalesce(jsonb_agg(jsonb_build_object('material_id',m.id,'naziv',m.naziv,'enota',m.enota,'kolicina_na_enoto',s.kolicina_na_enoto::text,
          'cena_na_enoto',m.cena_na_enoto::text,'aktiven',m.aktiven) order by m.naziv,m.id),'[]'::jsonb)
         from quoteflow.material_vrste_dela s join quoteflow.material m on m.id=s.material_id where s.vrsta_dela_id=v.id) as materiali
        from quoteflow.vrsta_dela v where v.podjetje_id=%s order by v.aktivna desc,v.naziv,v.id''', (company_id,)).fetchall()

def save(db, company_id, work_id, d):
    return db.execute('''select * from quoteflow_private.shrani_vrsto_dela(podjetje=>%s,vrsta=>%s,naziv=>%s,opis=>%s,urna_postavka=>%s,stevilo_ur=>%s,stevilo_delavcev=>%s,aktivna=>%s)''',
        (company_id, work_id, d.naziv, d.opis, d.urna_postavka, d.stevilo_ur, d.stevilo_delavcev, d.aktivna)).fetchone()

@router.post('/vrste-dela', status_code=201, response_model=WorkTypeSaved)
def create_work_type(company_id: UUID, data: WorkTypeInput, db=Depends(master)):
    return save(db, company_id, None, data)

@router.put('/vrste-dela/{work_id}', response_model=WorkTypeSaved)
def update_work_type(company_id: UUID, work_id: UUID, data: WorkTypeInput, db=Depends(master)):
    return save(db, company_id, work_id, data)

@router.put('/vrste-dela/{work_id}/materiali/{material_id}', response_model=MaterialRow)
def save_material(company_id: UUID, work_id: UUID, material_id: UUID, data: MaterialInput, db=Depends(master)):
    db.execute('select * from quoteflow_private.shrani_material_vrste(podjetje=>%s,vrsta=>%s,material=>%s,kolicina=>%s)', (company_id, work_id, material_id, data.kolicina_na_enoto)).fetchone()
    return db.execute('''select m.id as material_id,m.naziv,m.enota,s.kolicina_na_enoto,m.cena_na_enoto,m.aktiven from quoteflow.material_vrste_dela s
        join quoteflow.material m on m.id=s.material_id where s.vrsta_dela_id=%s and s.material_id=%s''', (work_id, material_id)).fetchone()

@router.delete('/vrste-dela/{work_id}/materiali/{material_id}', status_code=204)
def remove_material(company_id: UUID, work_id: UUID, material_id: UUID, db=Depends(master)):
    db.execute('select * from quoteflow_private.odstrani_material_vrste(podjetje=>%s,vrsta=>%s,material=>%s)', (company_id, work_id, material_id))
    return Response(status_code=204)
