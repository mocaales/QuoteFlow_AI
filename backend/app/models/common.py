"""Shared base model and constrained decimal types."""
import re
import unicodedata
from decimal import Decimal
from typing import Annotated, ClassVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, ValidationInfo

PLAIN = re.compile(r'[0-9]+(\.[0-9]+)?')

def plain_decimal(value):
    # JSON numbers are binary floats and str(Decimal) accepts exponents, signs, spaces and non-ASCII digits: only plain ASCII strings keep precision
    if isinstance(value, Decimal): return value
    if not isinstance(value, str) or not PLAIN.fullmatch(value) or len(value) > 40: raise ValueError('Vrednost mora biti navaden decimalni niz.')
    return value

Plain = BeforeValidator(plain_decimal)
Amount = Annotated[Decimal, Plain, Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)]
TaxRate = Annotated[Decimal, Plain, Field(ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False)]
Money = Annotated[Decimal, Plain, Field(gt=0, le=1000000, max_digits=18, decimal_places=4, allow_inf_nan=False)]
Discount = Annotated[Decimal, Plain, Field(ge=0, lt=1, max_digits=7, decimal_places=6, allow_inf_nan=False)]

class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')

    blank_ok: ClassVar[frozenset[str]] = frozenset()  # free-text fields that may be empty

    @field_validator('*')
    @classmethod
    def trim(cls, value, info: ValidationInfo):
        if isinstance(value, str):
            if any((unicodedata.category(c) in ('Cc', 'Cf') and c not in '\t\n\r') for c in value):
                raise ValueError('Vrednost vsebuje nedovoljene znake.')
            value = value.strip()
            if not value and info.field_name not in cls.blank_ok:
                raise ValueError('Vrednost ne sme biti prazna.')
        return value
