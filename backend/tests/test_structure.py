import importlib, inspect, pytest
from pydantic import ValidationError

def test_stari_moduli_odstranjeni():
 for name in ('app.identity', 'app.supplier'):
  with pytest.raises(ModuleNotFoundError): importlib.import_module(name)

@pytest.mark.parametrize('name', ['identity', 'admin', 'prosnje', 'cenik', 'materiali'])
def test_router_obstaja(name):
 assert hasattr(importlib.import_module(f'app.routers.{name}'), 'router')

def test_conflicts_sporocila():
 from app.errors import CONFLICTS
 assert CONFLICTS['QFP01'] == 'Prošnja je že obravnavana.'
 assert CONFLICTS['QFP02'] == 'Že imate oddano prošnjo, ki čaka na odločitev.'
 assert CONFLICTS['QFP03'] == 'Vlagatelj ne izpolnjuje pogojev za vlogo mojstra (potrjena e-pošta in aktivna vloga stranke ali delavca).'
 assert CONFLICTS['QFP04'] == 'Podjetje ali oddana prošnja s to matično številko že obstaja.'

def test_main_brez_psycopg_handlerja():
 from app import main
 src = inspect.getsource(main)
 assert 'exception_handler' not in src and 'CONFLICTS' not in src
 from app import errors
 assert 'psycopg' in inspect.getsource(errors)

def test_skupni_input():
 from app.models.common import Input, Amount, TaxRate
 class T(Input): a: str
 assert T(a=' x ').a == 'x'
 with pytest.raises(ValidationError): T(a='x', b=1)
 with pytest.raises(ValidationError): T(a='   ')

def test_conflicts_sestava_in_projekti():
 from app.errors import CONFLICTS
 assert CONFLICTS['QFP05'] == 'Neaktivnega materiala ni mogoče dodati v sestavo.'
 assert CONFLICTS['QFP06'] == 'Uporabnik s tem e-poštnim naslovom ni registrirana stranka.'
 assert CONFLICTS['QFP07'] == 'V tej fazi projekta to dejanje ni dovoljeno.'

def test_router_projekti_obstaja():
 assert hasattr(importlib.import_module('app.routers.projekti'), 'router')


def test_projekti_vnosi_podedujejo_skupni_input():
 from app.models.common import Input
 from app.routers.projekti import CreateInput, EditInput
 assert issubclass(EditInput, Input) and issubclass(CreateInput, Input)

def test_projekti_vnosi_prazen_naziv_ne_prazen_opis():
 from app.routers.projekti import CreateInput, EditInput
 for bad in ('', '   '):
  with pytest.raises(ValidationError): EditInput(naziv=bad)
  with pytest.raises(ValidationError): CreateInput(e_posta_stranke='a@b.si', naziv=bad)
 e = EditInput(naziv=' N ', opis='', lokacija_izvedbe='   ')
 assert e.naziv == 'N' and e.opis == '' and e.lokacija_izvedbe == ''
 assert EditInput(naziv='N').opis == '' and CreateInput(e_posta_stranke=' a@b.si ', naziv='N').e_posta_stranke == 'a@b.si'
 with pytest.raises(ValidationError): EditInput(naziv='N', faza='ponudba')

def test_skupni_input_zavrne_nul_znak():
 from app.models.common import Input
 class T(Input): a: str
 with pytest.raises(ValidationError): T(a='x\x00y')

def test_projekti_router_brez_sestavljanja_sql_z_nizi():
 import re
 from app.routers import projekti
 src = inspect.getsource(projekti)
 assert not re.search(r"""quoteflow_private\.['"]\s*\+""", src) and not re.search(r"""['"]\s*\+\s*call\b""", src)
 assert not re.search(r"""f['"][^'"\n]*quoteflow_private\.\{""", src)

def test_conflicts_qfp08():
 from app.errors import CONFLICTS
 assert CONFLICTS['QFP08'] == 'Preveč poskusov ustvarjanja projektov. Poskusite znova čez nekaj časa.'
