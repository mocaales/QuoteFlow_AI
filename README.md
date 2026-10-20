# QuoteFlow AI

QuoteFlow AI je nastajajoča večpodjetniška B2B spletna aplikacija za obdelavo povpraševanj (RFQ) in prodajnih ponudb. Nabavnik odda povpraševanje ter ponudnike izbere sam ali izbiro prepusti sistemu. Za vsakega ponudnika nastane ločen osnutek ponudbe, ki ga mora pooblaščeni ponudnik pregledati in izrecno odobriti, preden ga lahko vidi nabavnik.

Repozitorij: [mocaales/QuoteFlow_AI](https://github.com/mocaales/QuoteFlow_AI).

## Tehnološki sklad

| Del | Tehnologija |
|---|---|
| Spletni vmesnik | React, TypeScript, Vite |
| Strežniški API | Python, FastAPI |
| Podatkovna baza | Supabase PostgreSQL |
| Identiteta | Supabase Auth (integracija v aplikacijo je načrtovana) |
| Lokalni zagon | Docker Compose ali ločen zagon obeh delov |

Poslovna shema je `quoteflow`, interne funkcije pa so v `quoteflow_private`. Migracije v `supabase/migrations/` so edini vir sprememb sheme. Aplikacijski dostop do baze uporablja omejeno vlogo; uporabniški postopki pisanja še niso odprti.

## Trenutno stanje

- **Izvedeno:** ogrodje React/FastAPI, demonstracijski kalkulator, preverjanje povezave z bazo, začetne migracije in testi izračuna ter dostopa.
- **Načrtovano:** prijava v aplikacijo, ciljni podatkovni model iz dokumenta 03, RFQ in odobritveni proces, AI-agent ter obvestila. Trenutna baza še uporablja starejšo shemo, zato dokumentacija ne pomeni, da so te funkcije že na voljo.

## Lokalni zagon

Za poln preizkus povezave z bazo potrebujete veljaven `DATABASE_URL` za projekt Supabase. Kopirajte predlogo in dopolnite lokalno datoteko `.env`; skrivnosti ne dodajajte v repozitorij.

```sh
cp -n .env.example .env
docker compose up --build
```

Vmesnik je na <http://localhost:5173>, dokumentacija API-ja pa na <http://localhost:8000/docs>. Demonstracijski kalkulator deluje tudi brez povezave z bazo. `/api/health` preverja API, `/api/ready` pa povezavo z bazo in brez nje vrne HTTP 503. Compose zažene vmesnik in API; podatkovna baza ostane v Supabase.

Za razvoj brez Dockerja zaženite dela v ločenih terminalih:

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/uvicorn app.main:app --reload
```

```sh
cd frontend
npm ci
npm run dev
```

Backend uporablja Python 3.13, frontend pa Node.js 22 ali 24. Pri ločenem razvojnem zagonu Vite posreduje zahtevke `/api` backendu na vratih 8000.

## Preverjanje

```sh
cd backend
.venv/bin/python -m pytest -q
```

```sh
cd frontend
npm run build
```

Testi proti dejanski bazi so ločeni od običajnih testov in zahtevajo nastavljen `DATABASE_URL`:

```sh
cd backend
RUN_DATABASE_TESTS=1 .venv/bin/python -m pytest -q
```

## Dokumentacija

- [Zasnova rešitve](docs/01-zasnova-resitve.md)
- [Funkcionalnosti in obseg](docs/02-funkcionalnosti-in-obseg.md)
- [Podatkovni model](docs/03-podatkovni-model.md)
- [Arhitektura in tehnološki sklad](docs/04-arhitektura-in-tehnoloski-sklad.md)
- [Uporabniške zgodbe in merila sprejema](docs/05-uporabniske-zgodbe.md)
- [Žični modeli aplikacije](docs/06-wireframes.md)
- [Arhitekturne odločitve in predloga ADR](docs/adr/README.md)

OPP uporablja ločeno študijo konkretnega poslovnega primera in ne določa obsega razvoja te aplikacije.
