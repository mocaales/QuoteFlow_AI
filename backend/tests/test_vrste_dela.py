"""Model v3: vrste dela (type of work, labour defaults, materials per type) and the catalogue that now points at a vrsta dela."""
from uuid import uuid4

import psycopg
import pytest
from pydantic import ValidationError
from v3_support import *  # noqa: F401,F403
from v3_support import C, CATALOG, CENIK_FORM, COMPANY, FAT, MATERIAL, VRSTA, VRSTA_FORM, Fake, api, call, qfp, reached, untouched

VR = f'{C}/vrste-dela'
ROW = FAT | {'id': VRSTA, 'materiali': [{'material_id': MATERIAL, 'naziv': 'Lepilo', 'enota': 'kg', 'kolicina_na_enoto': '1.2500', 'cena_na_enoto': '0.8000', 'aktiven': True}]}
LIST_KEYS = {'id', 'podjetje_id', 'naziv', 'opis', 'urna_postavka', 'stevilo_ur', 'stevilo_delavcev', 'aktivna', 'cena_dela', 'materiali'}


def test_seznam_vrst_dela_ima_natancen_nabor_kljucev_in_nize(api):
    r = api(Fake([ROW])).get(VR)
    assert r.status_code == 200 and set(r.json()[0]) == LIST_KEYS, r.text[:300]
    assert all(isinstance(r.json()[0][k], str) for k in ('urna_postavka', 'stevilo_ur', 'cena_dela')) and isinstance(r.json()[0]['stevilo_delavcev'], int)


def test_seznam_vrst_dela_je_omejen_na_podjetje(api):
    fake = Fake([]); api(fake).get(VR); assert fake.calls and any(COMPANY in p for _, p in fake.calls if p)


@pytest.mark.parametrize('method,path', [('post', VR), ('put', f'{VR}/{VRSTA}')])
def test_shrani_vrsto_dela_pokliče_funkcijo_s_podjetjem(api, method, path):
    fake = Fake([ROW]); r = call(api(fake), method, path, VRSTA_FORM)
    assert reached(r, fake, 'shrani_vrsto_dela') and fake.called('shrani_vrsto_dela')[0][0] == COMPANY
    if method == 'put': assert VRSTA in fake.called('shrani_vrsto_dela')[0]


def test_ustvarjanje_vrste_dela_je_201(api):
    assert call(api(Fake([ROW])), 'post', VR, VRSTA_FORM).status_code == 201


def test_delo_brez_dela_je_veljavno_in_material_je_neobvezen(api):
    for body in (VRSTA_FORM | {'urna_postavka': '0', 'stevilo_ur': '0'}, {k: v for k, v in VRSTA_FORM.items() if k != 'aktivna'}):
        fake = Fake([ROW]); assert reached(call(api(fake), 'post', VR, body), fake, 'shrani_vrsto_dela'), body


@pytest.mark.parametrize('extra', [{'cena_dela': '1'}, {'podjetje_id': str(uuid4())}, {'id': str(uuid4())}, {'materiali': []}, {'material_id': str(uuid4())}, {'strosek_na_enoto': '8'}, {'aktivna_do': 'x'}])
@pytest.mark.parametrize('method,path', [('post', VR), ('put', f'{VR}/{VRSTA}')])
def test_vrsta_dela_dodatna_polja_so_422(api, method, path, extra):
    fake = Fake([ROW]); assert untouched(call(api(fake), method, path, VRSTA_FORM | extra), fake)


BAD = [{'naziv': ' '}, {'naziv': ''}, {'naziv': 'x' * 201}, {'opis': 'x' * 2001}, {'naziv': 'a\x00b'},
       {'urna_postavka': '-1'}, {'urna_postavka': 'NaN'}, {'urna_postavka': 'Infinity'}, {'urna_postavka': '1e2'}, {'urna_postavka': '10000.0001'}, {'urna_postavka': '1.00001'}, {'urna_postavka': 25.5}, {'urna_postavka': 25}, {'urna_postavka': '１２'},
       {'stevilo_ur': '-0.5'}, {'stevilo_ur': 'NaN'}, {'stevilo_ur': '100000.0001'}, {'stevilo_ur': '1.00001'}, {'stevilo_ur': 8}, {'stevilo_ur': ' '},
       {'stevilo_delavcev': 0}, {'stevilo_delavcev': -1}, {'stevilo_delavcev': 1001}, {'stevilo_delavcev': 2.0}, {'stevilo_delavcev': '2'}, {'stevilo_delavcev': True}, {'stevilo_delavcev': 1.5}, {'stevilo_delavcev': None},
       {'aktivna': 'da'}, {'aktivna': 1}]


@pytest.mark.parametrize('change', BAD)
@pytest.mark.parametrize('method,path', [('post', VR), ('put', f'{VR}/{VRSTA}')])
def test_neveljavna_vrsta_dela_je_422_brez_klica_baze(api, method, path, change):
    fake = Fake([ROW]); assert untouched(call(api(fake), method, path, VRSTA_FORM | change), fake)


@pytest.mark.parametrize('change', [{'urna_postavka': '10000'}, {'stevilo_ur': '100000'}, {'stevilo_delavcev': 1000}, {'stevilo_delavcev': 1}, {'urna_postavka': '0.0001'}])
def test_mejne_vrednosti_vrste_dela_so_sprejete(api, change):
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', VR, VRSTA_FORM | change), fake, 'shrani_vrsto_dela')


# materials of a vrsta dela
MAT = f'{VR}/{VRSTA}/materiali/{MATERIAL}'


def test_material_vrste_dela_pokliče_funkcijo_s_podjetjem_vrsto_in_materialom(api):
    fake = Fake([ROW]); r = call(api(fake), 'put', MAT, {'kolicina_na_enoto': '1.25'})
    assert reached(r, fake, 'shrani_material_vrste') and [str(x) for x in fake.called('shrani_material_vrste')[0][:3]] == [str(COMPANY), str(VRSTA), str(MATERIAL)]


def test_odstrani_material_vrste_je_204_brez_telesa(api):
    fake = Fake([ROW]); r = call(api(fake), 'delete', MAT)
    assert r.status_code == 204 and r.content == b'' and fake.called('odstrani_material_vrste')[0][:3] == (COMPANY, VRSTA, MATERIAL)


@pytest.mark.parametrize('value', ['0', '-1', '-0.0001', '1.23456', 'NaN', 'Infinity', '', None, 'abc', '1e2', '+1', '.5', '1_0', '１２', 1, 1.5, '1000000.0001'])
def test_kolicina_materiala_vrste_dela_neveljavna_je_422(api, value):
    fake = Fake([ROW]); assert untouched(call(api(fake), 'put', MAT, {'kolicina_na_enoto': value}), fake)


@pytest.mark.parametrize('body', [{}, {'kolicina_na_enoto': '1', 'material_id': str(uuid4())}, {'kolicina_na_enoto': '1', 'vrsta_dela_id': str(uuid4())}, {'kolicina_na_enoto': '1', 'podjetje_id': str(uuid4())}])
def test_material_vrste_dela_manjkajoca_ali_dodatna_polja_so_422(api, body):
    fake = Fake([ROW]); assert untouched(call(api(fake), 'put', MAT, body), fake)


def test_material_vrste_dela_neaktiven_material_je_409_qfp05(api):
    r = call(api(Fake(error=qfp('QFP05'))), 'put', MAT, {'kolicina_na_enoto': '1'}); assert r.status_code == 409


# foreign / random ids: identical 404 for the same company (M1)
@pytest.mark.parametrize('method,path,body', [('put', f'{VR}/{VRSTA}', VRSTA_FORM), ('put', MAT, {'kolicina_na_enoto': '1'}), ('delete', MAT, None)])
def test_tuja_vrsta_dela_ali_material_je_404(api, method, path, body):
    r = call(api(Fake(error=psycopg.errors.NoDataFound())), method, path, body); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


def test_neaktivna_vrsta_dela_pri_ceniku_je_409_qfp29(api):
    r = call(api(Fake(error=qfp('QFP29'))), 'post', f'{C}/cenik', CENIK_FORM); assert r.status_code == 409


# catalogue now references a vrsta dela and a fixed unit set
CAT = f'{C}/cenik'


def test_cenik_poklice_shrani_cenik_z_vrsto_dela_id(api):
    fake = Fake([ROW | {'id': CATALOG}]); r = call(api(fake), 'post', CAT, CENIK_FORM)
    assert reached(r, fake, 'shrani_cenik') and VRSTA in fake.called('shrani_cenik')[0]


@pytest.mark.parametrize('change', [{'vrsta_dela': 'Rušenje'}, {'vrsta_dela_id': 'ni-uuid'}, {'vrsta_dela_id': None}, {'vrsta_dela_id': ''}, {'enota': 'm²'}, {'enota': 'kg'}, {'enota': 'M2'}, {'enota': ' '}, {'enota': 'x' * 31},
                                    {'cena_na_enoto': '-1'}, {'cena_na_enoto': 'NaN'}, {'cena_na_enoto': '1.00001'}, {'stopnja_ddv': 0.22}, {'stopnja_ddv': '1.01'}, {'naziv': ' '}, {'naziv': 'a\x00b'}, {'opis': 'a\x00b'}, {'naziv': 'Ru\x07šenje'}, {'sestava': []}, {'podjetje_id': str(uuid4())}])
@pytest.mark.parametrize('method,path', [('post', CAT), ('put', f'{CAT}/{CATALOG}')])
def test_cenik_v3_neveljaven_vnos_je_422(api, method, path, change):
    ok = Fake([ROW]); assert reached(call(api(ok), method, path, CENIK_FORM), ok, 'shrani_cenik')  # the unchanged v3 form is valid, so the 422 below is caused by `change` alone
    fake = Fake([ROW]); assert untouched(call(api(fake), method, path, CENIK_FORM | change), fake)


def test_cenik_vrsta_dela_je_obvezna(api):
    ok = Fake([ROW]); assert reached(call(api(ok), 'post', CAT, CENIK_FORM), ok, 'shrani_cenik')
    fake = Fake([ROW]); assert untouched(call(api(fake), 'post', CAT, {k: v for k, v in CENIK_FORM.items() if k != 'vrsta_dela_id'}), fake)


@pytest.mark.parametrize('unit', ['m', 'm2', 'm3', 'kos'])
def test_cenik_sprejme_samo_stiri_enote(api, unit):
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', CAT, CENIK_FORM | {'enota': unit}), fake, 'shrani_cenik')


def test_cenik_input_model_vsebuje_vrsto_dela_id_in_zavrne_besedilo():
    from app.routers.cenik import CatalogInput
    assert 'vrsta_dela_id' in CatalogInput.model_fields and 'vrsta_dela' not in CatalogInput.model_fields
    CatalogInput(**CENIK_FORM)
    with pytest.raises(ValidationError): CatalogInput(**(CENIK_FORM | {'enota': 'kg'}))


def test_cenik_seznam_vrne_vrsto_dela_id_in_ne_besedila(api):
    r = api(Fake([ROW | {'id': CATALOG}])).get(CAT)
    assert r.status_code == 200 and 'vrsta_dela_id' in r.json()[0] and 'vrsta_dela' not in r.json()[0]
