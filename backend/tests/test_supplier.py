"""V2 boundary validation: service catalogue is separate from stocked materials."""
from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.routers.cenik import CatalogInput
from app.routers.materiali import StockInput

ITEM = {'naziv': 'Rušenje estriha', 'opis': 'Odstranitev in odvoz', 'vrsta_dela_id': str(uuid4()), 'enota': 'm2', 'cena_na_enoto': '12.4500', 'stopnja_ddv': '0.22', 'aktivna': True}


def test_veljavna_postavka_cenika_novega_modela():
    item = CatalogInput(**ITEM)
    assert item.naziv == ITEM['naziv']
    assert str(item.stopnja_ddv) == '0.22'


@pytest.mark.parametrize('change', [
    {'naziv': ' '}, {'opis': ' '}, {'vrsta_dela_id': ' '}, {'vrsta_dela': 'Rušenje'}, {'enota': ' '}, {'enota': 'm²'}, {'enota': 'kg'},
    {'cena_na_enoto': '-1'}, {'cena_na_enoto': 'NaN'}, {'cena_na_enoto': 'Infinity'},
    {'cena_na_enoto': '1.00001'}, {'stopnja_ddv': '-.01'}, {'stopnja_ddv': '1.01'},
    {'podjetje_id': str(uuid4())}, {'strosek_na_enoto': '8'}, {'vrsta': 'blago'},
])
def test_neveljavna_postavka_cenika(change):
    with pytest.raises(ValidationError):
        CatalogInput(**(ITEM | change))


def test_zaloga_hrani_lokacijo_in_kolicino_materiala():
    stock = StockInput(lokacija='Skladisce 1', kolicina='0')
    assert stock.lokacija == 'Skladisce 1' and stock.kolicina == 0


@pytest.mark.parametrize('change', [
    {'kolicina': '-1'}, {'kolicina': 'NaN'}, {'kolicina': 'Infinity'},
    {'kolicina': '1.00001'}, {'lokacija': ' '}, {'material_id': str(uuid4())},
])
def test_neveljavna_zaloga(change):
    with pytest.raises(ValidationError):
        StockInput(**({'lokacija': 'Skladisce', 'kolicina': '2.5'} | change))


@pytest.mark.parametrize('value', ['yes', 1, 0, 'true', 'false', None])
def test_aktivna_mora_biti_strogi_bool(value):
    with pytest.raises(ValidationError): CatalogInput(**(ITEM | {'aktivna': value}))
