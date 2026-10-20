# React, TypeScript in Vite za spletni vmesnik

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** delna; trenutno obstaja demonstracijski kalkulator

## Kontekst in problem

QuoteFlow potrebuje interaktivne obrazce RFQ, pregled stanj in ločene poglede nabavnika ter ponudnika. Spletni vmesnik mora jasno razlikovati osnutek od odobrene ponudbe.

## Obravnavane možnosti

- React + TypeScript + Vite.
- Strežniško izrisane predloge v FastAPI.
- Next.js s strežniškim izrisom.

## Izid odločitve

Izberemo **React + TypeScript + Vite**. React ustreza interaktivnim delovnim tokovom, TypeScript pomaga uskladiti podatke obrazcev in API-ja, Vite pa zadostuje za aplikacijo, ki ne potrebuje javnega indeksiranja strani. FastAPI ostane edini strežniški vir poslovnih pravil.

### Posledice

- **Pozitivno:** vmesnik in API imata jasno ločeni odgovornosti; razvoj obrazcev je hiter.
- **Negativno:** vzdržujemo dva gradbena postopka in moramo uskladiti tipe zahtevkov ter odgovorov.

## Preverjanje

Gradnja `npm run build` uspe; poslovnih pravic ali odločitev o objavi ponudbe ni samo v kodi vmesnika.
