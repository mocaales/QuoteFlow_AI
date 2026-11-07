"""Pure deterministic demo calculation. Never approves or publishes a quote."""
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field

class CalculationInput(BaseModel):
    quantity: int = Field(gt=0, le=1000000)
    unit_cost: Decimal = Field(ge=0, le=100000000, max_digits=13, decimal_places=4)
    unit_price: Decimal = Field(gt=0, le=100000000, max_digits=13, decimal_places=4)
    discount: Decimal = Field(default=Decimal('0'), ge=0, lt=1)
    min_margin: Decimal = Field(default=Decimal('0.20'), ge=0, lt=1)
    max_discount: Decimal = Field(default=Decimal('0.10'), ge=0, lt=1)
    stock: int | None = Field(default=None, ge=0)
    lead_days: int | None = Field(default=None, ge=0, le=3650)
    requested_days: int = Field(default=7, ge=0, le=3650)

class CalculationResult(BaseModel):
    total: Decimal
    cost: Decimal
    margin: Decimal | None
    issues: list[str]
    checks_passed: bool

def calculate(data: CalculationInput) -> CalculationResult:
    total = (data.unit_price * (1-data.discount) * data.quantity).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    cost = (data.unit_cost * data.quantity).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    margin = (total-cost)/total if total > 0 else None
    issues = []
    if margin is None:
        issues.append('Zaokrožena prodajna vrednost mora biti večja od nič.')
    elif margin < data.min_margin:
        issues.append('Marža je nižja od minimalne dovoljene.')
    if data.discount > data.max_discount:
        issues.append('Popust presega dovoljeno mejo.')
    if data.stock is None:
        issues.append('Zaloga ni potrjena.')
    elif data.stock < data.quantity:
        issues.append('Zaloga ne zadošča za zahtevano količino.')
    if data.lead_days is None:
        issues.append('Dobavni rok ni potrjen.')
    elif data.lead_days > data.requested_days:
        issues.append('Dobavni rok presega zahtevani rok.')
    return CalculationResult(total=total, cost=cost, margin=margin, issues=issues, checks_passed=not issues)

# Model v3 formula A (ADR-0012): reference oracle for the SQL generated columns; never writes totals.
CENT = Decimal('.01')
POLJA_ENOTE = {'m': ('dolzina',), 'm2': ('dolzina', 'visina'), 'm3': ('dolzina', 'visina', 'sirina'), 'kos': ()}

def _cent(v: Decimal) -> Decimal: return v.quantize(CENT, rounding=ROUND_HALF_UP)

def vrednost_izmere(enota: str, *, kosi: Decimal = Decimal(1), dolzina: Decimal | None = None, visina: Decimal | None = None, sirina: Decimal | None = None) -> Decimal:
    if enota not in POLJA_ENOTE: raise ValueError('Neznana merska enota.')
    mere, potrebna = {'dolzina': dolzina, 'visina': visina, 'sirina': sirina}, POLJA_ENOTE[enota]
    if any((mere[k] is None) != (k not in potrebna) for k in mere): raise ValueError('Polja izmere ne ustrezajo merski enoti.')
    vrednost = kosi
    for v in [kosi, *(mere[k] for k in potrebna)]:
        if not isinstance(v, Decimal) or not v.is_finite() or v <= 0: raise ValueError('Mere izmere morajo biti pozitivna števila.')
    for k in potrebna: vrednost *= mere[k]
    return vrednost

def izmera_skupaj(enota: str, izmere: list[dict]) -> Decimal:
    skupaj = Decimal(0)
    for i in izmere:
        v = vrednost_izmere(enota, kosi=i.get('kosi', Decimal(1)), dolzina=i.get('dolzina'), visina=i.get('visina'), sirina=i.get('sirina'))
        skupaj += -v if i.get('odstej') else v
    if skupaj < 0: raise ValueError('Skupna izmera ne sme biti negativna.')
    return skupaj

def cena_postavke(*, izmera_skupaj: Decimal, kolicina: Decimal, cena_na_enoto: Decimal, urna_postavka: Decimal, stevilo_ur: Decimal, stevilo_delavcev: int, popust: Decimal, stopnja_ddv: Decimal) -> dict[str, Decimal]:
    delo = urna_postavka * stevilo_ur * stevilo_delavcev
    neto = _cent((izmera_skupaj * kolicina * cena_na_enoto + delo) * (1 - popust))
    ddv = _cent(neto * stopnja_ddv)
    return {'cena_dela': _cent(delo), 'neto': neto, 'ddv': ddv, 'koncna_cena': neto + ddv}

def vsote_dokumenta(postavke: list[dict]) -> dict[str, Decimal]:
    neto, ddv = sum((p['neto'] for p in postavke), Decimal('0.00')), sum((p['ddv'] for p in postavke), Decimal('0.00'))
    return {'neto': neto, 'ddv': ddv, 'skupaj': neto + ddv}
