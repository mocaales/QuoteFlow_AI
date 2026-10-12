# QuoteFlow AI

Večpodjetniška B2B aplikacija za predmet RIRIS. Lokalna mapa: `/Users/AM/Documents/Ales.java/2026/QuoteFlow_AI`.

Repozitorij: https://github.com/mocaales/QuoteFlow_AI. `origin` je povezan. Po navodilu uporabnika ni izveden noben Git commit ali push.

## Načrtovani obseg

- **15 predvidenih funkcionalnosti F1–F15:** sedem MVP funkcionalnosti F1–F7 in osem za razvoj po MVP F8–F15.
- **5 dodatnih možnih nadgradenj F16–F20.**
- **Skupaj 20 funkcionalnosti.** Podrobnosti so v [funkcionalnostih in obsegu](docs/02-funkcionalnosti-in-obseg.md). Načrt ne pomeni, da so funkcionalnosti že izvedene.

## Trenutno stanje

Izvedeno: štirje dokumenti RIRIS, React/TypeScript demonstracijski kalkulator, FastAPI, decimalna poslovna kalkulacija, 16 preverjenih backend testov (vključno z dvema na dejanski bazi) in Docker Compose za frontend/backend. V obstoječem projektu Supabase je ustvarjenih 19 poslovnih tabel, indeksi, relacijske omejitve, RLS politike branja in zaščita nespremenljivih zapisov. Testi v bazi preverjajo dve podjetji kupcev, dva ponudnika in administratorja.

Še ni izvedeno: uporabniški vmesnik prijave in povezava s Supabase Auth, varni pisalni postopki, katalog/RFQ API, agent, poslovna validacija pri odobritvi in objavljanje ponudb. Obstoj podatkovnega modela ne pomeni dokončanega MVP. `authenticated` ima trenutno samo avtorizirano branje; pisanje ostaja zaprto.

## Supabase

Projekt: `QuoteFlow_AI`, ref `pexllfgutqiormnabzxp`, regija `eu-west-1`.

- Poslovne tabele: shema `quoteflow`.
- Interne funkcije: `quoteflow_private`.
- Identitete: Supabase Auth `auth.users`; aplikacija hrani `user_profiles`, brez gesel.
- Shemi nista dodani med izpostavljene Data API sheme.
- Migracije: `supabase/migrations/`, ena migracijska zgodovina, brez Alembic.
- Backend: omejena vloga `quoteflow_app`, LOGIN/NOINHERIT brez obida RLS. TLS in dejanska povezava sta preverjena. Preverjanje JWT sledi ob uvedbi prijave. Ne uporabljajte postgres/service_role za uporabniške zahteve.

CLI je na tem računalniku povezan s projektom. Drug računalnik potrebuje ustrezno prijavo v CLI in povezavo:

```sh
supabase link --project-ref pexllfgutqiormnabzxp
supabase migration list --linked
```

Migracije se izvajajo z `supabase db push --linked --skip-vault`; pred izvedbo preverite cilj projekta in migracije. To spreminja bazo, ne izvaja Git push. SQL testi uporabljajo transakcijo z ROLLBACK.

## Zagon z Dockerjem

Ob prvi nastavitvi kopirajte `.env.example` v `.env`. Obstoječe `.env` ne prepisujte. `SUPABASE_URL` in `SUPABASE_PROJECT_REF` sta že določena. `DATABASE_URL` je na tem računalniku nastavljen za omejeni račun `quoteflow_app` in TLS (`sslmode=require`). Prvotni skrbniški naslov je ohranjen kot `MIGRATION_DATABASE_URL`, samo za vzdrževanje. Skrivnosti so izključene iz Gita; `.env` lahko bere samo lastnik.

```sh
docker compose up --build
```

Compose poganja samo frontend/backend. Podatkovna baza je v Supabase. Frontend: http://localhost:5173, dokumentacija API: http://localhost:8000/docs. Kalkulator deluje tudi brez DATABASE_URL. `/api/health` preveri API; `/api/ready` brez povezave z bazo pravilno vrne 503.

## Razvoj brez Dockerja

Backend (Python 3.13), iz korena:

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/uvicorn app.main:app --reload
```

Backend samodejno naloži projektni `.env` neodvisno od delovne mape, brez prepisovanja že nastavljenih okolijskih spremenljivk. Frontend (Node 22 ali 24), drug terminal:

```sh
cd frontend
npm ci
npm run dev
```

Za razvoj z lokalnim Supabase lahko uporabite CLI in `supabase/config.toml`; to potrebuje Docker in je ločeno od aplikacijskega Compose. Navaden lokalni PostgreSQL brez Supabase Auth ni ustrezna zamenjava za te migracije.

## Preverjanje

```sh
cd backend
.venv/bin/python -m pytest -q
```

```sh
cd frontend
npm run build
```

Iz korena, proti povezanemu projektu:

```sh
supabase db query --linked --file supabase/tests/tenant_isolation.sql
supabase db advisors --linked --type all --level warn
```

SQL testi ne zahtevajo pgTAP in se izvajajo z `db query`, ne `supabase test db`. Testne identitete in podatki se v isti transakciji ustvarijo ter razveljavijo; ne nastanejo aktivni uporabniški računi. Testiramo dovoljen in zavrnjen dostop, prepoved pisanja ter preklic dostopa ob deaktivaciji uporabnika. Poslovni postopki za pisanje bodo potrebovali dodatne teste.

## Dokumentacija

- [Zasnova](docs/01-zasnova-resitve.md)
- [Funkcionalnosti in obseg](docs/02-funkcionalnosti-in-obseg.md)
- [Podatkovni model](docs/03-podatkovni-model.md)
- [Arhitektura](docs/04-arhitektura-in-tehnoloski-sklad.md)

`RIRIS-QuoteFlow-AI.zip` vsebuje posodobljene štiri Markdown datoteke v korenu. OPP ostaja neodvisna študija enega primera in ne določa razvoja aplikacije.

## Preverjeno 11. 10. 2026

Git je brez commitov. Obe migraciji sta zabeleženi lokalno in v Supabase. Preizkusi izolacije in podatkovnih omejitev so uspešni; 10 backend testov je uspešnih. Supabase Advisors pri stopnjah WARN/ERROR ne poroča težav. Docker Compose konfiguracija je veljavna; celoten vsebniški zagon v tej spremembi ni bil izveden. Aplikacijska DATABASE_URL še ni nastavljena.


## Preverjeno 12. 10. 2026

Aplikacijska povezava je nastavljena in preverjena z omejenim računom `quoteflow_app`. TLS je aktiven. Zdravje baze preverja dejanski dostop in zaščito sheme; prijava uporabnikov ter poslovni API še sledita. Prejšnja opomba o nenastavljenem DATABASE_URL velja za stanje pred to spremembo.

```sh
cd backend
RUN_DATABASE_TESTS=1 .venv/bin/python -m pytest -q
```

Preizkusi na pravi bazi preverijo TLS, shemo, RLS, prepoved prevzema vloge postgres in prepoved neposrednega pisanja. Ne puščajo testnih podatkov. Skripta `scripts/configure_database.py` je namenjena začetni pripravi povezave; ob že nastavljenem aplikacijskem računu zgolj preveri povezavo in ne menja gesla.
