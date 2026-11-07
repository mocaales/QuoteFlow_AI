"""Model v3: project items (postavke projekta) and their izmere. Fake connection, no database."""
from decimal import Decimal as D
from uuid import uuid4

import psycopg
import pytest
from pydantic import ValidationError
from v3_support import C, COMPANY, FAT, IZ_CENIKA_FORM, IZMERA, IZMERA_FORM, ITEM, M, POSTAVKA_FORM, PROJECT, VRSTA, Fake, api, call, make_api, qfp, reached, untouched  # noqa: F401

P = f'{M}/postavke'
I = f'{P}/{ITEM}/izmere'
ROW = FAT | {'izmere': [FAT]}


# --- create / update / delete item
@pytest.mark.parametrize('method,path', [('post', P), ('put', f'{P}/{ITEM}')])
def test_postavka_projekta_pokliče_funkcijo_s_podjetjem_in_projektom(api, method, path):
    fake = Fake([ROW]); r = call(api(fake), method, path, POSTAVKA_FORM)
    p = fake.called('shrani_postavko_projekta'); assert reached(r, fake, 'shrani_postavko_projekta') and (p[0][0], p[0][1]) == (COMPANY, PROJECT)
    assert VRSTA in p[0] and (method == 'post' or ITEM in p[0])


def test_ustvarjena_postavka_je_201(api):
    assert call(api(Fake([ROW])), 'post', P, POSTAVKA_FORM).status_code == 201


def test_podatki_dela_so_neobvezni_ker_se_kopirajo_iz_vrste_dela(api):
    body = {k: v for k, v in POSTAVKA_FORM.items() if k not in ('urna_postavka', 'stevilo_ur', 'stevilo_delavcev')}
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', P, body), fake, 'shrani_postavko_projekta')


def test_vrsta_dela_je_obvezna(api):
    fake = Fake([ROW]); assert untouched(call(api(fake), 'post', P, {k: v for k, v in POSTAVKA_FORM.items() if k != 'vrsta_dela_id'}), fake)


def test_kolicina_je_privzeto_1_ker_je_mnozitelj(api):
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', P, {k: v for k, v in POSTAVKA_FORM.items() if k != 'kolicina'}), fake, 'shrani_postavko_projekta')


MASS = ['id', 'projekt_id', 'podjetje_id', 'izmera_skupaj', 'cena_dela', 'neto', 'ddv', 'koncna_cena', 'skupaj', 'zaporedje', 'postavka_cenika_id', 'izmere', 'materiali', 'faza', 'strosek_na_enoto', 'marza']


@pytest.mark.parametrize('field', MASS)
@pytest.mark.parametrize('method,path', [('post', P), ('put', f'{P}/{ITEM}')])
def test_postavka_mass_assignment_je_422(api, method, path, field):
    fake = Fake([ROW]); assert untouched(call(api(fake), method, path, POSTAVKA_FORM | {field: '1'}), fake)


BAD = [{'naziv': ' '}, {'naziv': ''}, {'naziv': 'x' * 201}, {'opis': 'x' * 2001}, {'naziv': 'a\x00b'}, {'vrsta_dela_id': 'ni-uuid'}, {'vrsta_dela_id': None},
       {'enota': 'm²'}, {'enota': 'kg'}, {'enota': ''}, {'enota': 'M2'}, {'enota': 'm4'},
       {'cena_na_enoto': '-1'}, {'cena_na_enoto': 'NaN'}, {'cena_na_enoto': 'Infinity'}, {'cena_na_enoto': '1e2'}, {'cena_na_enoto': '1000000.0001'}, {'cena_na_enoto': '1.00001'}, {'cena_na_enoto': 10}, {'cena_na_enoto': 10.5}, {'cena_na_enoto': '１２'}, {'cena_na_enoto': ' '},
       {'kolicina': '0'}, {'kolicina': '-1'}, {'kolicina': 'NaN'}, {'kolicina': '1000000.0001'}, {'kolicina': '1.00001'}, {'kolicina': 2}, {'kolicina': 1.5}, {'kolicina': 'Infinity'},
       {'popust': '1'}, {'popust': '-0.01'}, {'popust': '1.5'}, {'popust': 'NaN'}, {'popust': 0.1}, {'popust': '0.1234567'},
       {'stopnja_ddv': '1.01'}, {'stopnja_ddv': '-0.1'}, {'stopnja_ddv': 0.22}, {'stopnja_ddv': 'NaN'}, {'stopnja_ddv': '0.1234567'},
       {'urna_postavka': '-1'}, {'urna_postavka': '10000.0001'}, {'urna_postavka': 'NaN'}, {'urna_postavka': 25}, {'urna_postavka': '1.00001'},
       {'stevilo_ur': '-1'}, {'stevilo_ur': '100000.0001'}, {'stevilo_ur': 'Infinity'}, {'stevilo_ur': 8},
       {'stevilo_delavcev': 0}, {'stevilo_delavcev': 1001}, {'stevilo_delavcev': 2.0}, {'stevilo_delavcev': '2'}, {'stevilo_delavcev': True}, {'stevilo_delavcev': -1}]


@pytest.mark.parametrize('change', BAD)
@pytest.mark.parametrize('method,path', [('post', P), ('put', f'{P}/{ITEM}')])
def test_neveljavna_postavka_je_422_brez_klica_baze(api, method, path, change):
    fake = Fake([ROW]); assert untouched(call(api(fake), method, path, POSTAVKA_FORM | change), fake)


@pytest.mark.parametrize('change', [{'cena_na_enoto': '1000000'}, {'cena_na_enoto': '0'}, {'kolicina': '1000000'}, {'kolicina': '0.0001'}, {'popust': '0'}, {'popust': '0.999999'}, {'stopnja_ddv': '0'}, {'stopnja_ddv': '1'},
                                    {'urna_postavka': '10000'}, {'stevilo_ur': '100000'}, {'stevilo_delavcev': 1000}, {'stevilo_delavcev': 1}, {'enota': 'm'}, {'enota': 'm3'}, {'enota': 'kos'}])
def test_mejne_vrednosti_postavke_so_sprejete(api, change):
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', P, POSTAVKA_FORM | change), fake, 'shrani_postavko_projekta')


def test_delete_postavke_je_204_in_pokliče_funkcijo(api):
    fake = Fake([ROW]); r = call(api(fake), 'delete', f'{P}/{ITEM}')
    assert r.status_code == 204 and r.content == b'' and fake.called('odstrani_postavko_projekta')[0][:3] == (COMPANY, PROJECT, ITEM)


# --- from catalogue
def test_iz_cenika_pokliče_funkcijo_s_podjetjem_in_projektom(api):
    fake = Fake([ROW]); r = call(api(fake), 'post', f'{P}/iz-cenika', IZ_CENIKA_FORM)
    p = fake.called('dodaj_postavko_iz_cenika'); assert reached(r, fake, 'dodaj_postavko_iz_cenika') and (p[0][0], p[0][1]) == (COMPANY, PROJECT) and r.status_code == 201


@pytest.mark.parametrize('body', [{'postavka_cenika_id': str(uuid4())}, {'postavka_cenika_id': str(uuid4()), 'kolicina': '2'}, {'postavka_cenika_id': str(uuid4()), 'popust': '0.1'}])
def test_iz_cenika_kolicina_in_popust_sta_neobvezna(api, body):
    fake = Fake([ROW]); assert reached(call(api(fake), 'post', f'{P}/iz-cenika', body), fake, 'dodaj_postavko_iz_cenika')


@pytest.mark.parametrize('change', [{'kolicina': '0'}, {'kolicina': '1000000.0001'}, {'kolicina': 2}, {'kolicina': 'NaN'}, {'popust': '1'}, {'popust': '-0.01'}, {'popust': 0}, {'postavka_cenika_id': 'ni-uuid'}, {'postavka_cenika_id': None},
                                    {'naziv': 'x'}, {'cena_na_enoto': '1'}, {'vrsta_dela_id': str(uuid4())}, {'enota': 'm'}, {'projekt_id': str(uuid4())}, {'neto': '1'}])
def test_iz_cenika_neveljavno_ali_dodatno_je_422(api, change):
    fake = Fake([ROW]); assert untouched(call(api(fake), 'post', f'{P}/iz-cenika', IZ_CENIKA_FORM | change), fake)


@pytest.mark.parametrize('code', ['QFP16', 'QFP29', 'QFP07', 'QFP20'])
def test_iz_cenika_poslovne_napake_so_409(api, code):
    assert call(api(Fake(error=qfp(code))), 'post', f'{P}/iz-cenika', IZ_CENIKA_FORM).status_code == 409


# --- izmere: unit specific field rules, enforced by the API (422) before any write
def row_for(unit): return [ROW | {'enota': unit}]


OK = [('m', dict(dolzina='3')), ('m', dict(dolzina='3', kosi='4')), ('m', dict(dolzina='3', odstej=True)),
      ('m2', dict(dolzina='3', visina='2.5')), ('m2', dict(dolzina='3', visina='2.5', kosi='4')),
      ('m3', dict(dolzina='3', visina='2', sirina='1.5')), ('m3', dict(dolzina='3', visina='2', sirina='1.5', kosi='2')),
      ('kos', dict(kosi='7')), ('kos', dict(kosi='1')), ('kos', dict(kosi='0.5', odstej=True))]
NOT_OK = [('m', {}), ('m', dict(dolzina='3', visina='2')), ('m', dict(dolzina='3', sirina='2')), ('m', dict(kosi='2')), ('m', dict(visina='2')),
          ('m2', dict(dolzina='3')), ('m2', dict(visina='3')), ('m2', dict(dolzina='3', visina='2', sirina='1')), ('m2', {}), ('m2', dict(kosi='2')),
          ('m3', dict(dolzina='3', visina='2')), ('m3', dict(dolzina='3', sirina='2')), ('m3', dict(visina='3', sirina='2')), ('m3', {}),
          ('kos', {}), ('kos', dict(kosi='2', dolzina='3')), ('kos', dict(kosi='2', visina='3')), ('kos', dict(kosi='2', sirina='3')), ('kos', dict(dolzina='3'))]


@pytest.mark.parametrize('unit,fields', OK)
@pytest.mark.parametrize('method,path', [('post', I), ('put', f'{I}/{IZMERA}')])
def test_izmera_z_ustreznimi_polji_za_enoto_je_sprejeta(api, method, path, unit, fields):
    fake = Fake(row_for(unit)); body = {'odstej': False} | fields; r = call(api(fake), method, path, body)
    assert reached(r, fake, 'shrani_izmero'), (unit, fields, r.status_code)
    p = fake.called('shrani_izmero')[0]; assert (p[0], p[1]) == (COMPANY, PROJECT) and ITEM in p


@pytest.mark.parametrize('unit,fields', NOT_OK)
@pytest.mark.parametrize('method,path', [('post', I), ('put', f'{I}/{IZMERA}')])
def test_izmera_z_napacnimi_polji_za_enoto_je_422_brez_pisanja(api, method, path, unit, fields):
    fake = Fake(row_for(unit)); r = call(api(fake), method, path, {'odstej': False} | fields)
    assert untouched(r, fake), (unit, fields, r.status_code)


def test_izmera_ne_sprejme_enote_iz_telesa_ker_izhaja_iz_postavke(api):
    fake = Fake(row_for('m')); assert untouched(call(api(fake), 'post', I, {'odstej': False, 'dolzina': '3', 'enota': 'm2'}), fake)


IZ_MASS = ['id', 'vrednost', 'zaporedje', 'postavka_projekta_id', 'podjetje_id', 'projekt_id', 'izmera_skupaj', 'neto', 'strosek']


@pytest.mark.parametrize('field', IZ_MASS)
def test_izmera_mass_assignment_je_422(api, field):
    fake = Fake(row_for('m2')); assert untouched(call(api(fake), 'post', I, IZMERA_FORM | {field: '1'}), fake)


NUM = ['-1', '0', '-0.0001', 'NaN', 'Infinity', '-Infinity', '1e2', '1E2', '+1', '.5', '5.', '1_0', '１２', ' ', '', '0.00001', '1.00001', '100000.0001', 'abc', '0x10', '1,5']


@pytest.mark.parametrize('bad', NUM + [5, 5.5, True])
@pytest.mark.parametrize('field', ['dolzina', 'visina', 'kosi'])
def test_izmera_polje_m2_neveljavno_je_422(api, field, bad):
    fake = Fake(row_for('m2')); assert untouched(call(api(fake), 'post', I, {'odstej': False, 'kosi': '1', 'dolzina': '5', 'visina': '4'} | {field: bad}), fake), (field, bad)


@pytest.mark.parametrize('bad', NUM + [5, 5.5])
def test_izmera_sirina_m3_neveljavna_je_422(api, bad):
    fake = Fake(row_for('m3')); assert untouched(call(api(fake), 'post', I, {'odstej': False, 'dolzina': '5', 'visina': '4', 'sirina': bad}), fake)


@pytest.mark.parametrize('bad', NUM + [5])
def test_izmera_kosi_kos_neveljavno_je_422(api, bad):
    fake = Fake(row_for('kos')); assert untouched(call(api(fake), 'post', I, {'odstej': False, 'kosi': bad}), fake)


@pytest.mark.parametrize('field,unit,extra', [('dolzina', 'm2', {'visina': '4'}), ('visina', 'm2', {'dolzina': '4'}), ('kosi', 'kos', {}), ('sirina', 'm3', {'dolzina': '1', 'visina': '1'})])
def test_izmera_zgornja_meja_100000_je_vkljucena(api, field, unit, extra):
    fake = Fake(row_for(unit)); assert reached(call(api(fake), 'post', I, {'odstej': False} | extra | {field: '100000'}), fake, 'shrani_izmero')
    fake = Fake(row_for(unit)); assert untouched(call(api(fake), 'post', I, {'odstej': False} | extra | {field: '100000.0001'}), fake)


def test_izmera_stirje_decimalke_so_dovoljene_pet_ne(api):
    fake = Fake(row_for('m')); assert reached(call(api(fake), 'post', I, {'odstej': False, 'dolzina': '1.2345'}), fake, 'shrani_izmero')
    fake = Fake(row_for('m')); assert untouched(call(api(fake), 'post', I, {'odstej': False, 'dolzina': '1.23456'}), fake)


@pytest.mark.parametrize('bad', ['true', 'da', 1, 0, None, [True], 'false'])
def test_odstej_mora_biti_strogi_bool(api, bad):
    fake = Fake(row_for('m')); assert untouched(call(api(fake), 'post', I, {'odstej': bad, 'dolzina': '3'}), fake)


def test_odstej_in_kosi_sta_neobvezna(api):
    fake = Fake(row_for('m')); assert reached(call(api(fake), 'post', I, {'dolzina': '3'}), fake, 'shrani_izmero')


def test_izmerni_model_privzeto_kosi_1_in_odstej_false():
    from app.routers.postavke import IzmeraInput
    m = IzmeraInput(dolzina='3'); assert m.kosi == D(1) and m.odstej is False and m.visina is None and m.sirina is None
    with pytest.raises(ValidationError): IzmeraInput(dolzina='3', enota='m')
    with pytest.raises(ValidationError): IzmeraInput(dolzina=3)


def test_postavka_input_model_je_strog():
    from app.models.common import Input
    from app.routers.postavke import PostavkaInput
    assert issubclass(PostavkaInput, Input) and PostavkaInput.model_config['extra'] == 'forbid'
    PostavkaInput(**POSTAVKA_FORM)
    for field in ('izmera_skupaj', 'neto', 'koncna_cena', 'cena_dela'):
        with pytest.raises(ValidationError): PostavkaInput(**(POSTAVKA_FORM | {field: '1'}))


def test_izmera_delete_je_204_in_pokliče_funkcijo(api):
    fake = Fake([ROW]); r = call(api(fake), 'delete', f'{I}/{IZMERA}')
    p = fake.called('odstrani_izmero'); assert r.status_code == 204 and r.content == b'' and (p[0][0], p[0][1]) == (COMPANY, PROJECT) and ITEM in p[0] and IZMERA in p[0]


# --- state / conflict mapping
@pytest.mark.parametrize('code,method,path,body', [(c, m, p, b) for c in ('QFP07', 'QFP27', 'QFP20') for m, p, b in [('post', P, POSTAVKA_FORM), ('put', f'{P}/{ITEM}', POSTAVKA_FORM), ('delete', f'{P}/{ITEM}', None)]]
                         + [(c, m, p, b) for c in ('QFP07', 'QFP25', 'QFP28') for m, p, b in [('post', I, IZMERA_FORM), ('put', f'{I}/{IZMERA}', IZMERA_FORM), ('delete', f'{I}/{IZMERA}', None)]])
def test_poslovni_konflikti_postavk_in_izmer_so_409(api, code, method, path, body):
    r = call(api(Fake(row_for('m2'), error=qfp(code))), method, path, body); assert r.status_code == 409 and r.json()['detail'], code


@pytest.mark.parametrize('method,path,body', [('post', P, POSTAVKA_FORM), ('put', f'{P}/{ITEM}', POSTAVKA_FORM), ('delete', f'{P}/{ITEM}', None), ('post', f'{P}/iz-cenika', IZ_CENIKA_FORM),
                                              ('post', I, IZMERA_FORM), ('put', f'{I}/{IZMERA}', IZMERA_FORM), ('delete', f'{I}/{IZMERA}', None)])
def test_tuja_ali_neobstojeca_postavka_projekt_ali_izmera_je_404(api, method, path, body):
    r = call(api(Fake(error=psycopg.errors.NoDataFound())), method, path, body); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'


def test_izmera_neobstojece_postavke_je_404_ne_422(api):
    # no row for the item: indistinguishable from a foreign item
    fake = Fake([]); r = call(api(fake), 'post', I, IZMERA_FORM); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.' and not fake.wrote()


def test_branje_postavk_je_omejeno_na_podjetje_in_projekt(api):
    fake = Fake([ROW]); r = api(fake).get(P)
    assert r.status_code == 200 and any(COMPANY in p and PROJECT in p for _, p in fake.calls if p)


def test_poslovno_sporocilo_qfp25_26_27_28_29_je_slovensko():
    from app.errors import CONFLICTS
    assert CONFLICTS['QFP25'] == 'Izmere bi dale negativno količino.' and CONFLICTS['QFP26'] == 'Vsaka postavka mora imeti pozitivno količino izmer.'
    assert CONFLICTS['QFP27'] == 'Mersko enoto lahko spremenite le, ko postavka nima izmer.' and CONFLICTS['QFP28'] == 'Postavka ima lahko največ 100 izmer.'
    assert CONFLICTS['QFP29'] == 'Neaktivne vrste dela ni mogoče uporabiti.'


def test_branje_postavk_vrne_postavke_in_zneske_kot_nize(api):
    r = api(Fake([ROW])).get(P); b = r.json()
    assert r.status_code == 200 and isinstance(b, dict) and set(b) == {'postavke', 'neto', 'ddv', 'skupaj'}
    assert len(b['postavke']) == 1 and b['postavke'][0]['id'] == str(ITEM) and (b['neto'], b['ddv'], b['skupaj']) == ('540.00', '118.80', '658.80')


def test_branje_postavk_tujega_ali_neobstojecega_projekta_je_404(api):
    r = api(Fake([])).get(P); assert r.status_code == 404 and r.json()['detail'] == 'Zapis ni na voljo.'
