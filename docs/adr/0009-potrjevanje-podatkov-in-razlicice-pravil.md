# Potrjevanje podatkov ponudnika in različice pravil

- **Status:** nadomeščeno z [ADR-0010](0010-projekti-podjetja-in-vec-vlog.md)
- **Datum:** 2026-10-29
- **Izvedba:** izvedena za US-03–US-05

> Zgodovinska odločitev za prejšnji model. Ne opisuje trenutne sheme.

## Kontekst in problem

Agent sme pozneje uporabljati samo potrjene podatke. Popravljena cena ne sme obdržati stare potrditve, zaloga ne sme zamenjati pomena ob spremembi enote, prodajna pravila pa morajo ohraniti zgodovino in imeti nedvoumno veljavnost.

## Obravnavane možnosti

- Neposredno urejanje tabel iz brskalnika in trajna oznaka potrditve.
- Pisanje prek omejenih strežniških postopkov, ponovna potrditev in časovno omejene različice pravil.

## Izid odločitve

Izberemo **omejene postopke prek FastAPI**. Vsak popravek cenika razveljavi potrditev. Sprememba vrste ali enote odstrani neobvezno zalogo; storitev je nima. Nova različica pravil v isti transakciji zaključi predhodno, ohrani njene vrednosti in zavrne prekrivanje prihodnjih različic. Retroaktivne spremembe niso dovoljene.

Postopki preverijo aktivno sejo in poslovno vlogo ter do konca transakcije zaklenejo podjetje in dodelitev. Globalni administrator brez vloge ponudnika nima poslovnega dostopa. Zneski se v backendu obravnavajo kot `Decimal`, v PostgreSQL kot `numeric`.

### Posledice

- **Pozitivno:** popravljeni podatki ne predstavljajo tiho potrjenega vira; pravila imajo ohranjeno zgodovino in nedvoumno veljavnost.
- **Negativno:** popravek zahteva dodatno potrditev; pri spremembi enote je treba zalogo ponovno vnesti. Pisanje znotraj podjetja je serijsko.

## Preverjanje

API in podatkovni testi preverijo razveljavitev potrditve, omejitve zaloge, zaščito tujega podjetja, prekrivanje pravil in ohranitev zgodovine. Frontend testi preverijo menjavo podjetja ter neuspešne zapise brez lažnega uspeha.
