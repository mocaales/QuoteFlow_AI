# Obvestila se pošiljajo po zapisu poslovnega dogodka

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** načrtovana za poznejšo funkcionalnost F10

## Kontekst in problem

Ponudnik bo obveščen o osnutku, nabavnik o odobreni ponudbi. Začasna napaka e-pošte ne sme razveljaviti odobritve ali povzročiti podvojenega pošiljanja.

## Obravnavane možnosti

- Zapis obvestila oziroma dogodka v isti transakciji, ločen pošiljatelj in idempotentna dostava.
- Neposredni klic SMTP med odobritvijo.
- Samo obvestila ob naslednji prijavi brez e-pošte.

## Izid odločitve

Izberemo **ločeno obdelavo obvestil po uspešnem poslovnem zapisu**. Odobritev se zaključi neodvisno od SMTP. Poskus dostave ima enolični ključ dogodka in prejemnika; e-pošta vsebuje povezavo do aplikacije, ne internih stroškov ali cen.

### Posledice

- **Pozitivno:** napaka dostave ne spremeni veljavnosti ponudbe; ponovni poskusi ne podvajajo sporočil.
- **Negativno:** potreben je dodatni pošiljatelj z nadzorom nedostavljenih obvestil; dostava ni trenutna.

## Preverjanje

Testi simulirajo napako SMTP, ponovljeno obdelavo istega dogodka in dostop do povezave brez ustrezne vloge.
