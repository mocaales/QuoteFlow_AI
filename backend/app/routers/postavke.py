"""Project items (postavke projekta) and their measurements (izmere), scoped to active masters."""
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, StrictBool, StrictInt

from app.access import company_member
from app.models.common import Discount, Input, Plain, TaxRate
from app.pricing import POLJA_ENOTE

router = APIRouter(prefix='/podjetja/{company_id}/projekti/{project_id}')
master = company_member('mojster')
NOT_FOUND = 'Zapis ni na voljo.'

Price = Annotated[Decimal, Plain, Field(ge=0, le=1000000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Quantity = Annotated[Decimal, Plain, Field(gt=0, le=1000000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Rate = Annotated[Decimal, Plain, Field(ge=0, le=10000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Hours = Annotated[Decimal, Plain, Field(ge=0, le=100000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Workers = Annotated[StrictInt, Field(ge=1, le=1000)]
Measure = Annotated[Decimal, Plain, Field(gt=0, le=100000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Unit = Literal['m', 'm2', 'm3', 'kos']

class PostavkaInput(Input):
    blank_ok = frozenset({'opis'})
    naziv: str = Field(min_length=1, max_length=200)
    opis: str = Field(default='', max_length=2000)
    vrsta_dela_id: UUID
    enota: Unit
    cena_na_enoto: Price
    kolicina: Quantity = Decimal(1)
    popust: Discount = Decimal(0)
    stopnja_ddv: TaxRate
    urna_postavka: Rate | None = None
    stevilo_ur: Hours | None = None
    stevilo_delavcev: Workers | None = None

class FromCatalogInput(Input):
    postavka_cenika_id: UUID
    kolicina: Quantity = Decimal(1)
    popust: Discount = Decimal(0)

class IzmeraInput(Input):
    odstej: StrictBool = False
    kosi: Measure = Decimal(1)
    dolzina: Measure | None = None
    visina: Measure | None = None
    sirina: Measure | None = None

class IzmeraRow(BaseModel):
    id: UUID
    zaporedje: int
    odstej: bool
    kosi: Decimal
    dolzina: Decimal | None
    visina: Decimal | None
    sirina: Decimal | None
    vrednost: Decimal

class PostavkaSaved(BaseModel):
    id: UUID
    zaporedje: int
    postavka_cenika_id: UUID | None
    vrsta_dela_id: UUID
    naziv: str
    opis: str
    enota: str
    cena_na_enoto: Decimal
    kolicina: Decimal
    popust: Decimal
    stopnja_ddv: Decimal
    urna_postavka: Decimal
    stevilo_ur: Decimal
    stevilo_delavcev: int
    izmera_skupaj: Decimal
    cena_dela: Decimal
    neto: Decimal
    koncna_cena: Decimal

class PostavkaRow(PostavkaSaved):
    ddv: Decimal
    izmere: list[IzmeraRow]

class PostavkeList(BaseModel):
    postavke: list[PostavkaRow]
    neto: Decimal
    ddv: Decimal
    skupaj: Decimal

@router.get('/postavke', response_model=PostavkeList)
def items(company_id: UUID, project_id: UUID, db=Depends(master)):
    if not db.execute('select 1 from quoteflow.projekt where podjetje_id=%s and id=%s', (company_id, project_id)).fetchone(): raise HTTPException(404, NOT_FOUND)
    rows = db.execute('''select p.id,p.zaporedje,p.postavka_cenika_id,p.vrsta_dela_id,p.naziv,p.opis,p.enota,p.cena_na_enoto,p.kolicina,p.popust,p.stopnja_ddv,p.urna_postavka,p.stevilo_ur,p.stevilo_delavcev,
        p.izmera_skupaj,p.cena_dela,p.neto,p.koncna_cena-p.neto as ddv,p.koncna_cena,
        (select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'zaporedje',i.zaporedje,'odstej',i.odstej,'kosi',i.kosi::text,'dolzina',i.dolzina::text,'visina',i.visina::text,
          'sirina',i.sirina::text,'vrednost',i.vrednost::text) order by i.zaporedje),'[]'::jsonb) from quoteflow.izmera i where i.postavka_projekta_id=p.id) as izmere
        from quoteflow.postavka_projekta p join quoteflow.projekt j on j.id=p.projekt_id where j.podjetje_id=%s and p.projekt_id=%s order by p.zaporedje,p.id''', (company_id, project_id)).fetchall()
    neto = sum((Decimal(str(r.get('neto', 0))) for r in rows), Decimal(0)); skupaj = sum((Decimal(str(r.get('koncna_cena', 0))) for r in rows), Decimal(0))
    return {'postavke': rows, 'neto': neto, 'ddv': skupaj - neto, 'skupaj': skupaj}

def save(db, company_id, project_id, item_id, d):
    return db.execute('''select * from quoteflow_private.shrani_postavko_projekta(podjetje=>%s,projekt=>%s,postavka=>%s,vrsta_dela=>%s,naziv=>%s,opis=>%s,enota=>%s,cena=>%s,kolicina=>%s,
        popust=>%s,stopnja_ddv=>%s,urna_postavka=>%s,stevilo_ur=>%s,stevilo_delavcev=>%s)''',
        (company_id, project_id, item_id, d.vrsta_dela_id, d.naziv, d.opis, d.enota, d.cena_na_enoto, d.kolicina, d.popust, d.stopnja_ddv, d.urna_postavka, d.stevilo_ur, d.stevilo_delavcev)).fetchone()

@router.post('/postavke', status_code=201, response_model=PostavkaSaved)
def create_item(company_id: UUID, project_id: UUID, data: PostavkaInput, db=Depends(master)):
    return save(db, company_id, project_id, None, data)

# declared before the {item_id} routes so the literal segment wins
@router.post('/postavke/iz-cenika', status_code=201, response_model=PostavkaSaved)
def add_from_catalog(company_id: UUID, project_id: UUID, data: FromCatalogInput, db=Depends(master)):
    return db.execute('select * from quoteflow_private.dodaj_postavko_iz_cenika(podjetje=>%s,projekt=>%s,postavka_cenika=>%s,kolicina=>%s,popust=>%s)',
        (company_id, project_id, data.postavka_cenika_id, data.kolicina, data.popust)).fetchone()

@router.put('/postavke/{item_id}', response_model=PostavkaSaved)
def update_item(company_id: UUID, project_id: UUID, item_id: UUID, data: PostavkaInput, db=Depends(master)):
    return save(db, company_id, project_id, item_id, data)

@router.delete('/postavke/{item_id}', status_code=204)
def delete_item(company_id: UUID, project_id: UUID, item_id: UUID, db=Depends(master)):
    db.execute('select * from quoteflow_private.odstrani_postavko_projekta(podjetje=>%s,projekt=>%s,postavka=>%s)', (company_id, project_id, item_id))
    return Response(status_code=204)


def save_measure(db, company_id, project_id, item_id, measure_id, d):
    row = db.execute('''select p.enota from quoteflow.postavka_projekta p join quoteflow.projekt j on j.id=p.projekt_id
        where p.id=%s and p.projekt_id=%s and j.podjetje_id=%s''', (item_id, project_id, company_id)).fetchone()
    unit = (row or {}).get('enota')
    if unit not in POLJA_ENOTE: raise HTTPException(404, NOT_FOUND)
    given = {k for k in ('dolzina', 'visina', 'sirina') if getattr(d, k) is not None}
    if given != set(POLJA_ENOTE[unit]): raise HTTPException(422, 'Polja izmere ne ustrezajo merski enoti postavke.')
    if unit == 'kos' and 'kosi' not in d.model_fields_set: raise HTTPException(422, 'Število kosov mora biti podano.')
    return db.execute('select * from quoteflow_private.shrani_izmero(podjetje=>%s,projekt=>%s,postavka=>%s,izmera=>%s,odstej=>%s,kosi=>%s,dolzina=>%s,visina=>%s,sirina=>%s)',
        (company_id, project_id, item_id, measure_id, d.odstej, d.kosi, d.dolzina, d.visina, d.sirina)).fetchone()

@router.post('/postavke/{item_id}/izmere', status_code=201, response_model=IzmeraRow)
def create_measure(company_id: UUID, project_id: UUID, item_id: UUID, data: IzmeraInput, db=Depends(master)):
    return save_measure(db, company_id, project_id, item_id, None, data)

@router.put('/postavke/{item_id}/izmere/{measure_id}', response_model=IzmeraRow)
def update_measure(company_id: UUID, project_id: UUID, item_id: UUID, measure_id: UUID, data: IzmeraInput, db=Depends(master)):
    return save_measure(db, company_id, project_id, item_id, measure_id, data)

@router.delete('/postavke/{item_id}/izmere/{measure_id}', status_code=204)
def delete_measure(company_id: UUID, project_id: UUID, item_id: UUID, measure_id: UUID, db=Depends(master)):
    db.execute('select * from quoteflow_private.odstrani_izmero(podjetje=>%s,projekt=>%s,postavka=>%s,izmera=>%s)', (company_id, project_id, item_id, measure_id))
    return Response(status_code=204)
