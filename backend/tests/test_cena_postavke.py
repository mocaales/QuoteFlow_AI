"""Model v3 formula A as an executable oracle (app.pricing): neto = round((izmera_skupaj*kolicina*cena_na_enoto + urna*ure*delavci)*(1-popust), 2).

The DB computes the same numbers; these helpers are the reference the DB tests compare with. Python never writes totals.
"""
from decimal import Decimal as D

import pytest
from app import pricing

CASE = dict(izmera_skupaj=D('20'), kolicina=D('1'), cena_na_enoto=D('10'), urna_postavka=D('25'), stevilo_ur=D('8'), stevilo_delavcev=2, popust=D('0.1'), stopnja_ddv=D('0.22'))
LINE = lambda **c: pricing.cena_postavke(**(CASE | c))
IZ = lambda **c: {'odstej': False, 'kosi': D(1), 'dolzina': None, 'visina': None, 'sirina': None} | c


def test_delovni_primer_540_118_80_658_80():
    r = LINE()
    assert (r['neto'], r['ddv'], r['koncna_cena']) == (D('540.00'), D('118.80'), D('658.80')) and r['cena_dela'] == D('400.00')


def test_izmere_primera_5x4_plus_2x1_minus_1x2_dajo_20_m2():
    assert pricing.izmera_skupaj('m2', [IZ(dolzina=D(5), visina=D(4), kosi=D(1)), IZ(dolzina=D(2), visina=D(1)), IZ(dolzina=D(1), visina=D(2), odstej=True)]) == D('20')


@pytest.mark.parametrize('enota,fields,expected', [('m', dict(dolzina=D('3'), kosi=D('4')), D('12')), ('m2', dict(dolzina=D('3'), visina=D('2.5'), kosi=D('4')), D('30')),
                                                    ('m3', dict(dolzina=D('2'), visina=D('3'), sirina=D('4'), kosi=D('2')), D('48')), ('kos', dict(kosi=D('7')), D('7')),
                                                    ('m2', dict(dolzina=D('3'), visina=D('2.5')), D('7.5')), ('kos', {}, D('1'))])
def test_kosi_mnozi_vsako_enoto_in_je_privzeto_1(enota, fields, expected):
    assert pricing.vrednost_izmere(enota, **fields) == expected


def test_m2_ne_uporablja_sirine_in_m_ne_visine():
    with pytest.raises(ValueError): pricing.vrednost_izmere('m2', dolzina=D(3), visina=D(2), sirina=D(9))
    with pytest.raises(ValueError): pricing.vrednost_izmere('m', dolzina=D(3), visina=D(2))
    with pytest.raises(ValueError): pricing.vrednost_izmere('kos', kosi=D(3), dolzina=D(2))
    with pytest.raises(ValueError): pricing.vrednost_izmere('m3', dolzina=D(3), visina=D(2))
    with pytest.raises(ValueError): pricing.vrednost_izmere('m2', dolzina=D(3))


def test_odstevanje_ne_sme_dati_negativne_vsote_qfp25():
    with pytest.raises(ValueError): pricing.izmera_skupaj('m', [IZ(dolzina=D(2)), IZ(dolzina=D(3), odstej=True)])
    assert pricing.izmera_skupaj('m', [IZ(dolzina=D(3)), IZ(dolzina=D(3), odstej=True)]) == D('0')


def test_popust_velja_tudi_za_delo_in_ddv_je_ena_stopnja():
    r = LINE(izmera_skupaj=D('0'))
    assert (r['neto'], r['ddv'], r['koncna_cena']) == (D('360.00'), D('79.20'), D('439.20'))


def test_delo_je_pavsal_in_ne_raste_s_kolicino_izmer():
    assert LINE(izmera_skupaj=D('1'), cena_na_enoto=D('0'), popust=D('0'))['neto'] == D('400.00')
    assert LINE(izmera_skupaj=D('1000'), cena_na_enoto=D('0'), popust=D('0'))['neto'] == D('400.00')


def test_kolicina_je_mnozitelj_izmer():
    assert LINE(kolicina=D('3'), urna_postavka=D(0), popust=D(0))['neto'] == D('600.00')


def test_zaokrozevanje_pol_navzgor_samo_na_koncu():
    z = dict(izmera_skupaj=D('1'), kolicina=D('1'), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1, popust=D(0), stopnja_ddv=D(0))
    assert pricing.cena_postavke(**z | dict(cena_na_enoto=D('0.005')))['neto'] == D('0.01')
    assert pricing.cena_postavke(**z | dict(cena_na_enoto=D('0.0049')))['neto'] == D('0.00')
    r = pricing.cena_postavke(**z | dict(cena_na_enoto=D('0.50'), stopnja_ddv=D('0.01')))
    assert (r['neto'], r['ddv'], r['koncna_cena']) == (D('0.50'), D('0.01'), D('0.51'))
    assert pricing.cena_postavke(**z | dict(cena_na_enoto=D('10.05'), popust=D('0.5')))['neto'] == D('5.03')


def test_rezultat_je_decimal_z_dvema_decimalkama_brez_float():
    for k, v in LINE().items(): assert isinstance(v, D) and v == v.quantize(D('.01')) and v.as_tuple().exponent == -2, k


def test_vsote_dokumenta_so_vsote_zaokrozenih_vrstic():
    z = dict(izmera_skupaj=D('1'), kolicina=D('1'), cena_na_enoto=D('0.005'), urna_postavka=D(0), stevilo_ur=D(0), stevilo_delavcev=1, popust=D(0), stopnja_ddv=D(0))
    lines = [pricing.cena_postavke(**z) for _ in range(3)]
    t = pricing.vsote_dokumenta(lines)
    assert t['neto'] == D('0.03') and t['skupaj'] == D('0.03') and t['ddv'] == D('0.00')
    t = pricing.vsote_dokumenta([LINE(), LINE()]); assert (t['neto'], t['ddv'], t['skupaj']) == (D('1080.00'), D('237.60'), D('1317.60'))
