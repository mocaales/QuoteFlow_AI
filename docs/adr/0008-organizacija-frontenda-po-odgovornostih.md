# Organizacija frontenda po odgovornostih

- **Status:** sprejeto
- **Datum:** 2026-10-27
- **Izvedba:** izvedena za trenutne funkcionalnosti

## Kontekst in problem

Prijava, delovni prostor in upravljanje seje so bili združeni v `App.tsx`; `client.ts` je združeval domenske tipe, Supabase in HTTP-klice. Nadaljnji MVP sklopi potrebujejo jasne meje.

## Obravnavane možnosti

- Vse komponente in odjemalci v korenu `src`.
- Razdelitev samo po vrstah datotek.
- Funkcionalnosti v `features`, sestava aplikacije in skupna infrastruktura ločeno.

## Izid odločitve

Izberemo **organizacijo po funkcionalnostih in odgovornostih**. `app` sestavlja aplikacijo, `pages` poglede, `features` združuje pripadajoče komponente, hooke, API-klice in tipe. `components`, `lib` in `services` vsebujejo skupno kodo. Praznih map ne ustvarjamo.

FastAPI ostane edini vir poslovnih pravil in preverjanja dostopa. Prikaz vloge v Reactu ne pomeni dovoljenja za poslovno operacijo. Odločitev dopolnjuje ADR-0001 in ne spreminja tehnološkega sklada.

### Posledice

- **Pozitivno:** povezano kodo najdemo skupaj; skupni HTTP-odjemalec in nastavitev Auth sta ločena od pogledov.
- **Negativno:** več manjših datotek in potreba po doslednem spoštovanju meja med funkcionalnostmi.

## Preverjanje

`npm test` preveri prijavo, registracijo, administracijo in življenjski cikel seje; `npm run build` preveri tipe in produkcijsko gradnjo. Pregled uvozov potrdi, da skupna infrastruktura ne uvaža funkcionalnosti ali strani.

Podrobna razporeditev: [organizacija frontenda](../razvoj/frontend-arhitektura.md).
