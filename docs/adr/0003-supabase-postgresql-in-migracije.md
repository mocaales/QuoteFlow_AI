# Supabase PostgreSQL in ena pot migracij

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** delna; povezava obstaja, ciljna shema iz dokumenta 03 še ni uvedena

## Kontekst in problem

Podatkovni model vsebuje povezane uporabnike, podjetja, RFQ, pravila, zaloge in ponudbe. Odobritev mora biti atomska, dostop do vrstic pa ločen po podjetju. Projekt Supabase že obstaja.

## Obravnavane možnosti

- Supabase PostgreSQL.
- Lastno gostovan PostgreSQL.
- MySQL z dostopnimi pravili v aplikaciji.

## Izid odločitve

Izberemo **Supabase PostgreSQL** zaradi relacij, transakcij, možnosti RLS in že pripravljenega projekta. MySQL bi lahko shranjeval isti model, vendar bi izolacijo vrstic v večji meri prenesel na aplikacijo; lastno gostovanje PostgreSQL bi dodalo operativno delo. Edini vir sprememb sheme je `supabase/migrations/`; vzporednega Alembica ne uvajamo.

### Posledice

- **Pozitivno:** omejitve in transakcije lahko varujejo povezave in odobritev v bazi.
- **Negativno:** odvisnost od upravljane storitve; pred prehodom s stare sheme potrebujemo migracijo in teste dostopa.

## Preverjanje

Migracija uvede ciljni model iz [dokumenta 03](../03-podatkovni-model.md); testi preverijo tuje ključe, omejitve in izolacijo podjetij pred odprtjem pisalnih postopkov.
