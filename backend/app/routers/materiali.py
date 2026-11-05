"""Material kinds, materials and per-location stock, scoped to active masters."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field

from app.access import company_member
from app.models.common import Amount, Input

router = APIRouter(prefix='/podjetja/{company_id}')
master = company_member('mojster')

class MaterialKindInput(Input):
    naziv: str = Field(min_length=1, max_length=200)

class MaterialKindRow(MaterialKindInput):
    id: UUID
    podjetje_id: UUID

class MaterialInput(Input):
    vrsta_materiala_id: UUID
    sifra: str = Field(min_length=1, max_length=100)
    naziv: str = Field(min_length=1, max_length=200)
    enota: str = Field(min_length=1, max_length=30)
    cena_na_enoto: Amount
    aktiven: bool = True

class MaterialRow(MaterialInput):
    id: UUID

class StockInput(Input):
    lokacija: str = Field(min_length=1, max_length=200)
    kolicina: Amount

class StockRow(StockInput):
    material_id: UUID


@router.get('/vrste-materiala', response_model=list[MaterialKindRow])
def material_kinds(company_id: UUID, db=Depends(master)):
    return db.execute('select id,podjetje_id,naziv from quoteflow.vrsta_materiala where podjetje_id=%s order by naziv,id', (company_id,)).fetchall()

@router.post('/vrste-materiala', status_code=201, response_model=MaterialKindRow)
def create_material_kind(company_id: UUID, data: MaterialKindInput, db=Depends(master)):
    return db.execute('select * from quoteflow_private.shrani_vrsto_materiala(%s,%s,%s)', (company_id, None, data.naziv)).fetchone()

@router.put('/vrste-materiala/{kind_id}', response_model=MaterialKindRow)
def update_material_kind(company_id: UUID, kind_id: UUID, data: MaterialKindInput, db=Depends(master)):
    return db.execute('select * from quoteflow_private.shrani_vrsto_materiala(%s,%s,%s)', (company_id, kind_id, data.naziv)).fetchone()

@router.get('/materiali', response_model=list[MaterialRow])
def materials(company_id: UUID, db=Depends(master)):
    return db.execute('''select m.id,m.vrsta_materiala_id,m.sifra,m.naziv,m.enota,m.cena_na_enoto,m.aktiven
        from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id
        where v.podjetje_id=%s order by m.aktiven desc,m.naziv,m.id''', (company_id,)).fetchall()


def save_material(db, company_id, material_id, data):
    return db.execute('select * from quoteflow_private.shrani_material(%s,%s,%s,%s,%s,%s,%s,%s)',
        (company_id, material_id, data.vrsta_materiala_id, data.sifra, data.naziv, data.enota, data.cena_na_enoto, data.aktiven)).fetchone()

@router.post('/materiali', status_code=201, response_model=MaterialRow)
def create_material(company_id: UUID, data: MaterialInput, db=Depends(master)):
    return save_material(db, company_id, None, data)

@router.put('/materiali/{material_id}', response_model=MaterialRow)
def update_material(company_id: UUID, material_id: UUID, data: MaterialInput, db=Depends(master)):
    return save_material(db, company_id, material_id, data)

@router.get('/materiali/{material_id}/zaloga', response_model=list[StockRow])
def stocks(company_id: UUID, material_id: UUID, db=Depends(master)):
    material = db.execute('''select m.id from quoteflow.material m
        join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id
        where m.id=%s and v.podjetje_id=%s''', (material_id, company_id)).fetchone()
    if material is None:
        raise HTTPException(404, 'Material ni na voljo.')
    return db.execute('''select z.material_id,z.lokacija,z.kolicina from quoteflow.zaloga z
        join quoteflow.material m on m.id=z.material_id join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id
        where v.podjetje_id=%s and m.id=%s order by z.lokacija''', (company_id, material_id)).fetchall()

@router.put('/materiali/{material_id}/zaloga')
def save_stock(company_id: UUID, material_id: UUID, data: StockInput, db=Depends(master)):
    db.execute('select quoteflow_private.shrani_zalogo(%s,%s,%s,%s)', (company_id, material_id, data.lokacija, data.kolicina))
    return {'status': 'ok'}

@router.delete('/materiali/{material_id}/zaloga')
def remove_stock(company_id: UUID, material_id: UUID, lokacija: str = Query(min_length=1, max_length=200), db=Depends(master)):
    db.execute('select quoteflow_private.odstrani_zalogo(%s,%s,%s)', (company_id, material_id, lokacija))
    return {'status': 'ok'}
