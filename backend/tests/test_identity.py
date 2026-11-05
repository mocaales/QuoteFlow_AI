"""V2 company ownership and scoped roles are validated before SQL."""
from uuid import uuid4

import pytest
from pydantic import ValidationError
from app.identity import CompanyInput, RoleInput


def test_podjetje_zahteva_lastnika_in_identifikacijske_podatke():
    owner = uuid4()
    item = CompanyInput(lastnik_id=owner, naziv='Mojster', maticna_stevilka='1234567', naslov='Naslov 1')
    assert item.lastnik_id == owner


def test_samo_naziv_ne_zadosca_za_ustvarjanje_podjetja():
    with pytest.raises(ValidationError):
        CompanyInput(naziv='Premalo podatkov')


def test_stranka_je_globalna_in_mojster_je_podjetniski():
    uid = uuid4()
    assert RoleInput(uporabnik_id=uid, podjetje_id=None, vloga='stranka').podjetje_id is None
    company = uuid4()
    assert RoleInput(uporabnik_id=uid, podjetje_id=company, vloga='mojster').podjetje_id == company


@pytest.mark.parametrize('role', ['administrator', 'nabavnik', 'ponudnik', 'admin'])
def test_api_ne_dodeljuje_starih_vlog_ali_globalnega_admina(role):
    with pytest.raises(ValidationError):
        RoleInput(uporabnik_id=uuid4(), podjetje_id=uuid4(), vloga=role)
