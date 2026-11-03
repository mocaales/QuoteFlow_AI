"""Boundary validation before SQL writes."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.supplier import CatalogInput, RulesInput, StockInput

ITEM={'vrsta':'blago','opis':'Ležaj 6205','enota':'kos','cena_na_enoto':'12.4500','strosek_na_enoto':'8.0000','dobavni_rok_dni':5}

@pytest.mark.parametrize('change',[{'opis':' '},{'enota':' '},{'vrsta':'izdelek'},{'cena_na_enoto':'-1'},{'cena_na_enoto':'NaN'},{'strosek_na_enoto':'Infinity'},{'cena_na_enoto':'1.00001'},{'dobavni_rok_dni':1.5},{'podjetje_id':str(uuid4())}])
def test_invalid_catalog_input(change):
    with pytest.raises(ValidationError):CatalogInput(**(ITEM|change))

@pytest.mark.parametrize('value',['-1','NaN','Infinity','1.00001'])
def test_invalid_stock(value):
    with pytest.raises(ValidationError):StockInput(razpolozljiva_kolicina=value)

@pytest.mark.parametrize('change',[{'najmanjsa_marza':'1'},{'najvecji_popust':'-0.1'},{'najdaljsi_rok_dni':-1},{'velja_od':'2026-01-01T12:00:00'}])
def test_invalid_rules(change):
    with pytest.raises(ValidationError):RulesInput(**({'najmanjsa_marza':'.2','najvecji_popust':'.1','najdaljsi_rok_dni':7}|change))
