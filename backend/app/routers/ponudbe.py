"""Quotes (master side): the draft is a header over the project items; sending snapshots them. Totals come from SQL columns; Python only serialises."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BeforeValidator, BaseModel, Field, StrictBool, field_validator

from app.access import company_member, customer
from app.auth import Principal, current_user
from app.models.common import Input

IsoDate = Annotated[date, BeforeValidator(lambda v: date.fromisoformat(v) if isinstance(v, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', v) else (_ for _ in ()).throw(ValueError('Datum mora biti v obliki LLLL-MM-DD.')))]

router = APIRouter()
master = company_member('mojster')

def today(): return datetime.now(ZoneInfo('Europe/Ljubljana')).date()

class QuoteInput(Input):
    velja_do: IsoDate | None = None

    @field_validator('velja_do')
    @classmethod
    def window(cls, value):
        if value is not None and not today() <= value <= today() + timedelta(days=366): raise ValueError('Veljavnost ponudbe mora biti v naslednjih 366 dneh.')
        return value

class Summary(BaseModel):
    id: UUID
    stevilka: str
    razlicica: int
    stanje: str
    poslano_ob: datetime | None
    odgovorjeno_ob: datetime | None
    velja_do: date | None
    nadomescena: bool
    neto: Decimal
    ddv: Decimal
    skupaj: Decimal

class Material(BaseModel):
    material_id: UUID
    naziv: str
    enota: str
    kolicina_na_enoto: Decimal
    cena_na_enoto: Decimal
    kolicina_skupaj: Decimal

class Line(BaseModel):
    id: UUID
    zaporedje: int
    naziv: str
    opis: str
    vrsta_dela: str
    enota: str
    cena_na_enoto: Decimal
    kolicina: Decimal
    popust: Decimal
    stopnja_ddv: Decimal
    izmera_skupaj: Decimal
    neto: Decimal
    ddv: Decimal
    koncna_cena: Decimal
    materiali: list[Material]

class VatTotal(BaseModel):
    stopnja_ddv: Decimal
    osnova: Decimal
    ddv: Decimal

class Quote(Summary):
    postavke: list[Line]
    ddv_po_stopnjah: list[VatTotal]

# Draft: live totals of the project items (mojster only, RLS); sent and later: the immutable snapshot
LIVE = 'select l.neto,l.koncna_cena from quoteflow.postavka_projekta l where l.projekt_id=pn.projekt_id and pn.stanje=\'osnutek\''
SNAP = 'select l.neto,l.koncna_cena from quoteflow.postavka_ponudbe l where l.ponudba_id=pn.id'
SUMMARY_HEAD = '''pn.id,pn.stevilka,pn.razlicica,pn.stanje,pn.poslano_ob,pn.odgovorjeno_ob,pn.velja_do,
    exists(select 1 from quoteflow.ponudba n where n.projekt_id=pn.projekt_id and n.razlicica>pn.razlicica and n.stanje<>'osnutek') as nadomescena,
    t.neto,t.skupaj-t.neto as ddv,t.skupaj
    from quoteflow.ponudba pn join quoteflow.projekt pr on pr.id=pn.projekt_id
    cross join lateral (select coalesce(sum(x.neto),0)::numeric(18,2) as neto,coalesce(sum(x.koncna_cena),0)::numeric(18,2) as skupaj from ('''
def summary(totals, scope, company=''):
    return 'select ' + company + SUMMARY_HEAD + totals + ') x) t where ' + scope
LIVE_LINES = '''select l.id,l.zaporedje,l.naziv,l.opis,v.naziv as vrsta_dela,l.enota,l.cena_na_enoto,l.kolicina,l.popust,l.stopnja_ddv,l.izmera_skupaj,
    l.neto,l.koncna_cena-l.neto as ddv,l.koncna_cena from quoteflow.postavka_projekta l join quoteflow.vrsta_dela v on v.id=l.vrsta_dela_id
    join quoteflow.projekt pr on pr.id=l.projekt_id where pr.podjetje_id=%s and pr.id=%s order by l.zaporedje'''
SNAP_LINES = '''select l.id,l.zaporedje,l.naziv,l.opis,l.vrsta_dela,l.enota,l.cena_na_enoto,l.kolicina,l.popust,l.stopnja_ddv,l.izmera_skupaj,
    l.neto,l.koncna_cena-l.neto as ddv,l.koncna_cena from quoteflow.postavka_ponudbe l join quoteflow.ponudba pn on pn.id=l.ponudba_id
    join quoteflow.projekt pr on pr.id=pn.projekt_id where pr.podjetje_id=%s and pr.id=%s and pn.id=%s order by l.zaporedje'''
MASTER_SUMMARY = summary(LIVE + ' union all ' + SNAP, 'pr.podjetje_id=%s and pr.id=%s')

def lines(db, company_id, project_id, quote):
    if quote['stanje'] == 'osnutek': return [r | {'materiali': []} for r in db.execute(LIVE_LINES, (company_id, project_id)).fetchall()]
    rows = db.execute(SNAP_LINES, (company_id, project_id, quote['id'])).fetchall()
    materials = {}
    for m in db.execute('''select m.postavka_ponudbe_id,m.material_id,m.naziv,m.enota,m.kolicina_na_enoto,m.cena_na_enoto,
        round(m.kolicina_na_enoto*l.izmera_skupaj*l.kolicina,4) as kolicina_skupaj from quoteflow.material_ponudbe m join quoteflow.postavka_ponudbe l on l.id=m.postavka_ponudbe_id
        where l.ponudba_id=%s order by m.naziv,m.material_id''', (quote['id'],)).fetchall():
        materials.setdefault(m.pop('postavka_ponudbe_id'), []).append(m)
    return [r | {'materiali': materials.get(r['id'], [])} for r in rows]

def read_quote(db, company_id, project_id, quote_id):
    row = db.execute(MASTER_SUMMARY + ' and pn.id=%s', (company_id, project_id, quote_id)).fetchone()
    if not row: raise HTTPException(404, 'Zapis ni na voljo.')
    rows = lines(db, company_id, project_id, row)
    vat = db.execute('''select stopnja_ddv,sum(neto) as osnova,sum(koncna_cena-neto) as ddv from (''' + (
        'select l.stopnja_ddv,l.neto,l.koncna_cena from quoteflow.postavka_projekta l where l.projekt_id=%s' if row['stanje'] == 'osnutek'
        else 'select l.stopnja_ddv,l.neto,l.koncna_cena from quoteflow.postavka_ponudbe l where l.ponudba_id=%s') + ') x group by stopnja_ddv order by stopnja_ddv',
        (project_id if row['stanje'] == 'osnutek' else quote_id,)).fetchall()
    return row | {'postavke': rows, 'ddv_po_stopnjah': vat}

def created_id(row):
    if not row: raise HTTPException(404, 'Zapis ni na voljo.')
    return row['id']

PATH = '/podjetja/{company_id}/projekti/{projekt_id}/ponudbe'

@router.get(PATH, response_model=list[Summary])
def quotes(company_id: UUID, projekt_id: UUID, db=Depends(master)):
    if not db.execute('select 1 from quoteflow.projekt where podjetje_id=%s and id=%s', (company_id, projekt_id)).fetchone(): raise HTTPException(404, 'Zapis ni na voljo.')
    return db.execute(MASTER_SUMMARY + ' order by pn.razlicica desc', (company_id, projekt_id)).fetchall()

@router.post(PATH, status_code=201, response_model=Quote)
def create_quote(company_id: UUID, projekt_id: UUID, data: QuoteInput, db=Depends(master)):
    quote_id = created_id(db.execute('select * from quoteflow_private.ustvari_ponudbo(%s,%s,%s)', (company_id, projekt_id, data.velja_do)).fetchone())
    return read_quote(db, company_id, projekt_id, quote_id)

@router.get(PATH + '/{ponudba_id}', response_model=Quote)
def quote(company_id: UUID, projekt_id: UUID, ponudba_id: UUID, db=Depends(master)):
    return read_quote(db, company_id, projekt_id, ponudba_id)

@router.put(PATH + '/{ponudba_id}', response_model=Quote)
def update_quote(company_id: UUID, projekt_id: UUID, ponudba_id: UUID, data: QuoteInput, db=Depends(master)):
    db.execute('select * from quoteflow_private.uredi_ponudbo(%s,%s,%s,%s)', (company_id, projekt_id, ponudba_id, data.velja_do)).fetchone()
    return read_quote(db, company_id, projekt_id, ponudba_id)

@router.post(PATH + '/{ponudba_id}/poslji', response_model=Quote)
def send_quote(company_id: UUID, projekt_id: UUID, ponudba_id: UUID, db=Depends(master)):
    db.execute('select quoteflow_private.poslji_ponudbo(%s,%s,%s)', (company_id, projekt_id, ponudba_id)).fetchone()
    return read_quote(db, company_id, projekt_id, ponudba_id)

class DecisionInput(Input):
    sprejmi: StrictBool

class CustomerMeasure(BaseModel):
    zaporedje: int
    enota: str
    odstej: bool
    kosi: Decimal
    dolzina: Decimal | None
    visina: Decimal | None
    sirina: Decimal | None
    vrednost: Decimal

class CustomerLine(BaseModel):
    zaporedje: int
    naziv: str
    opis: str
    vrsta_dela: str
    enota: str
    cena_na_enoto: Decimal
    kolicina: Decimal
    popust: Decimal
    stopnja_ddv: Decimal
    izmera_skupaj: Decimal
    neto: Decimal
    ddv: Decimal
    koncna_cena: Decimal
    izmere: list[CustomerMeasure]

class CustomerQuote(Summary):
    postavke: list[CustomerLine]
    ddv_po_stopnjah: list[VatTotal]
    podjetje_naziv: str

# Buyer side: explicit column whitelist from the snapshot only (no labour inputs, no materials), own projects (stranka_id), never drafts
CUSTOMER_SCOPE = "pr.stranka_id=%s and pr.id=%s and pn.stanje<>'osnutek'"
CUSTOMER_QUOTES = summary(SNAP, CUSTOMER_SCOPE, 'quoteflow_private.naziv_podjetja(pr.podjetje_id) as podjetje_naziv,')
CUSTOMER_QUOTE = summary(SNAP, CUSTOMER_SCOPE + ' and pn.id=%s', 'quoteflow_private.naziv_podjetja(pr.podjetje_id) as podjetje_naziv,')
CUSTOMER_LINES = '''select l.id,l.zaporedje,l.naziv,l.opis,l.vrsta_dela,l.enota,l.cena_na_enoto,l.kolicina,l.popust,l.stopnja_ddv,l.izmera_skupaj,
    l.neto,l.koncna_cena-l.neto as ddv,l.koncna_cena from quoteflow.postavka_ponudbe l where l.ponudba_id=%s order by l.zaporedje'''
CUSTOMER_MEASURES = '''select i.postavka_ponudbe_id,i.zaporedje,i.enota,i.odstej,i.kosi,i.dolzina,i.visina,i.sirina,i.vrednost
    from quoteflow.izmera_ponudbe i join quoteflow.postavka_ponudbe l on l.id=i.postavka_ponudbe_id where l.ponudba_id=%s order by i.postavka_ponudbe_id,i.zaporedje'''

def customer_quotes(db, user_id, project_id, quote_id=None):
    rows = db.execute((CUSTOMER_QUOTE if quote_id else CUSTOMER_QUOTES) + ' order by pn.razlicica desc', (user_id, project_id) + ((quote_id,) if quote_id else ())).fetchall()
    for n, r in enumerate(rows):
        r['postavke'] = db.execute(CUSTOMER_LINES, (r['id'],)).fetchall()
        # measurements only for the requested or latest version: older versions show totals alone
        measures = {}
        for m in (db.execute(CUSTOMER_MEASURES, (r['id'],)).fetchall() if n == 0 else ()): measures.setdefault(m.pop('postavka_ponudbe_id'), []).append(m)
        for l in r['postavke']: l['izmere'] = measures.get(l.pop('id'), [])
        r['ddv_po_stopnjah'] = db.execute('''select l.stopnja_ddv,sum(l.neto) as osnova,sum(l.koncna_cena-l.neto) as ddv from quoteflow.postavka_ponudbe l
            where l.ponudba_id=%s group by l.stopnja_ddv order by l.stopnja_ddv''', (r['id'],)).fetchall()
    return rows

CUSTOMER_PATH = '/projekti/{projekt_id}/ponudbe'

@router.get(CUSTOMER_PATH, response_model=list[CustomerQuote])
def own_quotes(projekt_id: UUID, user: Principal = Depends(current_user), db=Depends(customer)):
    if not db.execute('select 1 from quoteflow.projekt where stranka_id=%s and id=%s', (user.id, projekt_id)).fetchone(): raise HTTPException(404, 'Zapis ni na voljo.')
    return customer_quotes(db, user.id, projekt_id)

@router.post(CUSTOMER_PATH + '/{ponudba_id}/odlocitev', response_model=CustomerQuote)
def decide_quote(projekt_id: UUID, ponudba_id: UUID, data: DecisionInput, user: Principal = Depends(current_user), db=Depends(customer)):
    db.execute('select quoteflow_private.odgovori_ponudbo(%s,%s,%s)', (projekt_id, ponudba_id, data.sprejmi)).fetchone()
    rows = customer_quotes(db, user.id, projekt_id, ponudba_id)
    if not rows: raise HTTPException(404, 'Zapis ni na voljo.')
    return rows[0]
