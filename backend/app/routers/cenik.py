"""Company service catalogue, scoped to active masters."""
import re
from uuid import UUID

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from app.access import company_member
from app.models.common import Amount, Input, TaxRate

Quantity = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4, allow_inf_nan=False)]

router = APIRouter(prefix='/podjetja/{company_id}')
master = company_member('mojster')

class CatalogInput(Input):
    naziv: str = Field(min_length=1, max_length=200)
    opis: str = Field(min_length=1, max_length=1000)
    vrsta_dela: str = Field(min_length=1, max_length=200)
    enota: str = Field(min_length=1, max_length=30)
    cena_na_enoto: Amount
    stopnja_ddv: TaxRate
    aktivna: bool = True

class CatalogRow(CatalogInput):
    id: UUID
    podjetje_id: UUID

@router.get('/cenik', response_model=list[CatalogRow])
def catalog(company_id: UUID, db=Depends(master)):
    return db.execute('''select id,podjetje_id,naziv,opis,vrsta_dela,enota,cena_na_enoto,stopnja_ddv,aktivna
        from quoteflow.postavka_cenika where podjetje_id=%s order by aktivna desc,naziv,id''', (company_id,)).fetchall()


def save(db, company_id, item_id, data):
    return db.execute('select * from quoteflow_private.shrani_cenik(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (company_id, item_id, data.naziv, data.opis, data.vrsta_dela, data.enota,
         data.cena_na_enoto, data.stopnja_ddv, data.aktivna)).fetchone()

@router.post('/cenik', status_code=201, response_model=CatalogRow)
def create_item(company_id: UUID, data: CatalogInput, db=Depends(master)):
    return save(db, company_id, None, data)

@router.put('/cenik/{item_id}', response_model=CatalogRow)
def update_item(company_id: UUID, item_id: UUID, data: CatalogInput, db=Depends(master)):
    return save(db, company_id, item_id, data)


class CompositionInput(Input):
    kolicina_na_enoto: Quantity

    @field_validator('kolicina_na_enoto', mode='before')
    @classmethod
    def plain_digits(cls, value):
        if isinstance(value, str) and not re.fullmatch(r'[0-9]{1,14}(\.[0-9]{1,4})?', value):
            raise ValueError('Količina mora biti pozitivno število z največ 4 decimalkami.')
        return value

class CompositionRow(BaseModel):
    material_id: UUID
    sifra: str
    naziv: str
    enota: str
    aktiven: bool
    kolicina_na_enoto: Decimal

@router.get('/cenik/{item_id}/sestava', response_model=list[CompositionRow])
def composition(company_id: UUID, item_id: UUID, db=Depends(master)):
    if db.execute('select 1 from quoteflow.postavka_cenika where id=%s and podjetje_id=%s', (item_id, company_id)).fetchone() is None:
        raise HTTPException(404, 'Zapis ni na voljo.')
    return db.execute('''select m.id as material_id,m.sifra,m.naziv,m.enota,m.aktiven,s.kolicina_na_enoto
        from quoteflow.sestava_cenika s join quoteflow.postavka_cenika p on p.id=s.postavka_cenika_id
        join quoteflow.material m on m.id=s.material_id where p.podjetje_id=%s and p.id=%s order by m.naziv,m.id''', (company_id, item_id)).fetchall()

@router.put('/cenik/{item_id}/sestava/{material_id}', response_model=CompositionRow)
def save_composition(company_id: UUID, item_id: UUID, material_id: UUID, data: CompositionInput, db=Depends(master)):
    return db.execute('select * from quoteflow_private.shrani_sestavo(%s,%s,%s,%s)', (company_id, item_id, material_id, data.kolicina_na_enoto)).fetchone()

@router.delete('/cenik/{item_id}/sestava/{material_id}', status_code=204)
def delete_composition(company_id: UUID, item_id: UUID, material_id: UUID, db=Depends(master)):
    db.execute('select quoteflow_private.odstrani_sestavo(%s,%s,%s)', (company_id, item_id, material_id))
    return Response(status_code=204)
