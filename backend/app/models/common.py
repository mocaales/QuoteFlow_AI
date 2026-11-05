"""Shared base model and constrained decimal types."""
import unicodedata
from decimal import Decimal
from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationInfo

Amount = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)]
TaxRate = Annotated[Decimal, Field(ge=0, le=1, max_digits=7, decimal_places=6, allow_inf_nan=False)]

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
