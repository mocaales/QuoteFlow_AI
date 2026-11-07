"""Company service catalogue, scoped to active masters."""
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StrictBool

from app.access import company_member
from app.models.common import Input, Plain, TaxRate

Price = Annotated[Decimal, Plain, Field(ge=0, le=1000000, max_digits=18, decimal_places=4, allow_inf_nan=False)]

router = APIRouter(prefix='/podjetja/{company_id}')
master = company_member('mojster')

class CatalogInput(Input):
    naziv: str = Field(min_length=1, max_length=200)
    opis: str = Field(min_length=1, max_length=1000)
    vrsta_dela_id: UUID
    enota: Literal['m', 'm2', 'm3', 'kos']
    cena_na_enoto: Price
    stopnja_ddv: TaxRate
    aktivna: StrictBool = True

class CatalogRow(BaseModel):
    id: UUID
    podjetje_id: UUID
    naziv: str
    opis: str
    vrsta_dela_id: UUID
    enota: Literal['m', 'm2', 'm3', 'kos']
    cena_na_enoto: Decimal
    stopnja_ddv: Decimal
    aktivna: bool

@router.get('/cenik', response_model=list[CatalogRow])
def catalog(company_id: UUID, db=Depends(master)):
    return db.execute('''select id,podjetje_id,naziv,opis,vrsta_dela_id,enota,cena_na_enoto,stopnja_ddv,aktivna
        from quoteflow.postavka_cenika where podjetje_id=%s order by aktivna desc,naziv,id''', (company_id,)).fetchall()


def save(db, company_id, item_id, data):
    return db.execute('select * from quoteflow_private.shrani_cenik(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (company_id, item_id, data.naziv, data.opis, data.vrsta_dela_id, data.enota,
         data.cena_na_enoto, data.stopnja_ddv, data.aktivna)).fetchone()

@router.post('/cenik', status_code=201, response_model=CatalogRow)
def create_item(company_id: UUID, data: CatalogInput, db=Depends(master)):
    return save(db, company_id, None, data)

@router.put('/cenik/{item_id}', response_model=CatalogRow)
def update_item(company_id: UUID, item_id: UUID, data: CatalogInput, db=Depends(master)):
    return save(db, company_id, item_id, data)
