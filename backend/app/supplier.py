"""US-03–US-05: supplier-owned catalog, optional stock, versioned sales rules."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from .access import company_member

router = APIRouter(prefix='/podjetja/{company_id}')
Amount = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Ratio = Annotated[Decimal, Field(ge=0, lt=1, max_digits=8, decimal_places=6, allow_inf_nan=False)]

class CatalogInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vrsta: Literal['blago', 'storitev']
    opis: str = Field(min_length=1, max_length=1000)
    enota: str = Field(min_length=1, max_length=30)
    cena_na_enoto: Amount
    strosek_na_enoto: Amount
    dobavni_rok_dni: int | None = Field(default=None, ge=0, le=3650, strict=True)
    aktivna: bool = True

    @field_validator('opis', 'enota')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Vrednost ne sme biti prazna.')
        return value.strip()

class StockInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    razpolozljiva_kolicina: Amount

class RulesInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    najmanjsa_marza: Ratio
    najvecji_popust: Ratio
    najdaljsi_rok_dni: int = Field(ge=0, le=3650, strict=True)
    velja_od: AwareDatetime | None = None
    velja_do: AwareDatetime | None = None

    @model_validator(mode='after')
    def valid_interval(self):
        if self.velja_od and self.velja_do and self.velja_do <= self.velja_od:
            raise ValueError('Konec veljavnosti mora biti po začetku.')
        return self

class CatalogRow(CatalogInput):
    id: UUID
    podjetje_id: UUID
    potrjeno_ob: datetime | None
    razpolozljiva_kolicina: Decimal | None = None
    zaloga_potrjeno_ob: datetime | None = None

class RulesRow(RulesInput):
    id: UUID
    podjetje_id: UUID
    velja_od: AwareDatetime


supplier = company_member('ponudnik')

@router.get('/cenik', response_model=list[CatalogRow])
def catalog(company_id: UUID, db=Depends(supplier)):
    return db.execute('''select c.*,z.razpolozljiva_kolicina,z.potrjeno_ob as zaloga_potrjeno_ob
        from quoteflow.postavka_cenika c left join quoteflow.zaloga z on z.postavka_cenika_id=c.id
        where c.podjetje_id=%s order by c.aktivna desc,c.opis,c.id''', (company_id,)).fetchall()


def save(db, company_id, item_id, data):
    return db.execute('select * from quoteflow_private.shrani_cenik(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (company_id, item_id, data.vrsta, data.opis, data.enota, data.cena_na_enoto,
         data.strosek_na_enoto, data.dobavni_rok_dni, data.aktivna)).fetchone()

@router.post('/cenik', status_code=201, response_model=CatalogRow)
def create_item(company_id: UUID, data: CatalogInput, db=Depends(supplier)):
    return save(db, company_id, None, data)

@router.put('/cenik/{item_id}', response_model=CatalogRow)
def update_item(company_id: UUID, item_id: UUID, data: CatalogInput, db=Depends(supplier)):
    return save(db, company_id, item_id, data)

@router.post('/cenik/{item_id}/potrditev', response_model=CatalogRow)
def confirm_item(company_id: UUID, item_id: UUID, db=Depends(supplier)):
    return db.execute('select * from quoteflow_private.potrdi_cenik(%s,%s)', (company_id, item_id)).fetchone()

@router.put('/cenik/{item_id}/zaloga')
def save_stock(company_id: UUID, item_id: UUID, data: StockInput, db=Depends(supplier)):
    db.execute('select quoteflow_private.shrani_zalogo(%s,%s,%s)', (company_id, item_id, data.razpolozljiva_kolicina))
    return {'status': 'ok'}

@router.delete('/cenik/{item_id}/zaloga')
def remove_stock(company_id: UUID, item_id: UUID, db=Depends(supplier)):
    db.execute('select quoteflow_private.shrani_zalogo(%s,%s,null)', (company_id, item_id))
    return {'status': 'ok'}

@router.get('/pravila', response_model=list[RulesRow])
def rules(company_id: UUID, db=Depends(supplier)):
    return db.execute('select * from quoteflow.pravila_ponudnika where podjetje_id=%s order by velja_od desc,id', (company_id,)).fetchall()

@router.post('/pravila', status_code=201, response_model=RulesRow)
def create_rules(company_id: UUID, data: RulesInput, db=Depends(supplier)):
    return db.execute('select * from quoteflow_private.nova_pravila(%s,%s,%s,%s,%s,%s)',
        (company_id, data.najmanjsa_marza, data.najvecji_popust, data.najdaljsi_rok_dni, data.velja_od, data.velja_do)).fetchone()
