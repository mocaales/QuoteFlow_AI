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
