"""Invoices: issue and payment (master), read-only issued invoice for the customer. Lines and totals come from the accepted quote."""
import re
from typing import Annotated
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BeforeValidator, BaseModel, Field, field_validator

from app.access import company_member, customer
from app.auth import Principal, current_user
from app.models.common import Input

IsoDate = Annotated[date, BeforeValidator(lambda v: date.fromisoformat(v) if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) else (_ for _ in ()).throw(ValueError('Datum mora biti v obliki LLLL-MM-DD.')))]

router = APIRouter()
master = company_member('mojster')

class IssueInput(Input):
    prejemnik_naziv: str = Field(min_length=1, max_length=200)
    prejemnik_naslov: str = Field(min_length=1, max_length=300)
    zapade_dne: IsoDate

    @field_validator('zapade_dne')
    @classmethod
    def window(cls, value):
        if value > datetime.now(ZoneInfo('Europe/Ljubljana')).date() + timedelta(days=366): raise ValueError('Rok plačila je lahko največ 366 dni v prihodnosti.')
        return value

class PaymentInput(Input):
    pass

class QuoteRef(BaseModel):
    stevilka: str
    razlicica: int

class InvoiceLine(BaseModel):
    zaporedje: int
    naziv: str
    opis: str
    vrsta_dela: str
    enota: str
    cena_na_enoto: Decimal
    kolicina: Decimal
    popust: Decimal
    stopnja_ddv: Decimal
    neto: Decimal
    ddv: Decimal
    koncna_cena: Decimal

class VatTotal(BaseModel):
    stopnja_ddv: Decimal
    osnova: Decimal
    ddv: Decimal

class CustomerInvoice(BaseModel):
    stevilka: str | None
    stanje_dokumenta: str
    stanje_placila: str
    izdajatelj_naziv: str | None
    izdajatelj_naslov: str | None
    izdajatelj_davcna: str | None
    prejemnik_naziv: str | None
    prejemnik_naslov: str | None
    izdan_ob: datetime | None
    poslan_ob: datetime | None
    zapade_dne: date | None
    placano_ob: datetime | None
    ponudba: QuoteRef
    postavke: list[InvoiceLine]
    ddv_po_stopnjah: list[VatTotal]
    neto: Decimal
    ddv: Decimal
    skupaj: Decimal

class MasterInvoice(CustomerInvoice):
    id: UUID

# Explicit column list: the buyer never gets more than the document itself
HEAD = '''select r.id,r.stevilka,r.stanje_dokumenta,r.stanje_placila,r.izdajatelj_naziv,r.izdajatelj_naslov,r.izdajatelj_davcna,
    r.prejemnik_naziv,r.prejemnik_naslov,r.izdan_ob,r.poslan_ob,r.zapade_dne,r.placano_ob,pn.id as ponudba_id,pn.stevilka as ponudba_stevilka,pn.razlicica as ponudba_razlicica
    from quoteflow.racun r join quoteflow.ponudba pn on pn.id=r.ponudba_id join quoteflow.projekt pr on pr.id=pn.projekt_id'''
LINES = '''select l.zaporedje,l.naziv,l.opis,l.vrsta_dela,l.enota,l.cena_na_enoto,l.kolicina,l.popust,l.stopnja_ddv,
    l.neto,l.koncna_cena-l.neto as ddv,l.koncna_cena
    from quoteflow.postavka_ponudbe l where l.ponudba_id=%s order by l.zaporedje'''
VAT = '''select l.stopnja_ddv,sum(l.neto) as osnova,sum(l.koncna_cena-l.neto) as ddv from quoteflow.postavka_ponudbe l
    where l.ponudba_id=%s group by l.stopnja_ddv order by l.stopnja_ddv'''

def build(db, row, with_id):
    if not row: raise HTTPException(404, 'Zapis ni na voljo.')
    quote_id = row.pop('ponudba_id')
    row['ponudba'] = {'stevilka': row.pop('ponudba_stevilka'), 'razlicica': row.pop('ponudba_razlicica')}
    if not with_id: row.pop('id')
    row['postavke'] = db.execute(LINES, (quote_id,)).fetchall()
    row['ddv_po_stopnjah'] = db.execute(VAT, (quote_id,)).fetchall()
    row['neto'] = sum((v['osnova'] for v in row['ddv_po_stopnjah']), Decimal(0))
    row['ddv'] = sum((v['ddv'] for v in row['ddv_po_stopnjah']), Decimal(0))
    row['skupaj'] = row['neto'] + row['ddv']
    return row

def read_master(db, company_id, project_id):
    return build(db, db.execute(HEAD + ' where pr.podjetje_id=%s and pr.id=%s', (company_id, project_id)).fetchone(), True)

PATH = '/podjetja/{company_id}/projekti/{projekt_id}/racun'

@router.get(PATH, response_model=MasterInvoice)
def invoice(company_id: UUID, projekt_id: UUID, db=Depends(master)):
    return read_master(db, company_id, projekt_id)

@router.post(PATH + '/izdaj', response_model=MasterInvoice)
def issue_invoice(company_id: UUID, projekt_id: UUID, data: IssueInput, db=Depends(master)):
    db.execute('select * from quoteflow_private.izdaj_racun(%s,%s,%s,%s,%s)', (company_id, projekt_id, data.prejemnik_naziv, data.prejemnik_naslov, data.zapade_dne)).fetchone()
    return read_master(db, company_id, projekt_id)

@router.post(PATH + '/placilo', response_model=MasterInvoice)
def pay_invoice(company_id: UUID, projekt_id: UUID, data: PaymentInput | None = None, db=Depends(master)):
    db.execute('select * from quoteflow_private.placaj_racun(%s,%s)', (company_id, projekt_id)).fetchone()
    return read_master(db, company_id, projekt_id)

@router.get('/projekti/{projekt_id}/racun', response_model=CustomerInvoice)
def own_invoice(projekt_id: UUID, user: Principal = Depends(current_user), db=Depends(customer)):
    return build(db, db.execute(HEAD + " where pr.stranka_id=%s and pr.id=%s and r.stanje_dokumenta='izdan'", (user.id, projekt_id)).fetchone(), False)
