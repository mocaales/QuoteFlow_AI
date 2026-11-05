# QuoteFlow AI

Večpodjetniška spletna aplikacija za vodenje projektov, ekip, cenika, materialov, ponudb in računov. Uporabnik lahko nastopa kot stranka ter kot mojster ali delavec pri različnih podjetjih.

**Izvedeno:** nova relacijska shema je uvedena v Supabase. Delujejo registracija/prijava, nove vloge, administratorsko upravljanje uporabnikov in podjetij z lastnikom, prošnja za mojstra z administratorsko odločitvijo (odobritev ustvari podjetje, lastništvo in vlogo mojster) cenik storitev z materialno sestavo postavk (US-02), materiali in zaloga po lokacijah ter začetek projekta: mojster odpre projekt za stranko z natančnim e-poštnim naslovom, ga ureja in zahteva ogled, stranka vidi svoje projekte (US-03).

**Naslednji razvoj:** ekipe, termin, ponudbe in računi (načrtovano). Baza že vsebuje njihove omejitve in transakcijske postopke; API in vmesnik teh postopkov še nista uvedena. Migraciji za sestavo in projekte sta uvedeni v Supabase 5. 11. 2026. [Stanje razvoja](docs/razvoj/podatkovni-model.md).

**Načrtovani obseg:** [22 funkcionalnosti, od tega 7 MVP, in 5 možnih nadgradenj](docs/02-funkcionalnosti-in-obseg.md). AI-pomoč pri analizi projekta, pripravi in pregledu osnutkov ter povzetkih je načrtovana po MVP (F16–F20) in še ni izvedena.

**Tehnologije:** React, TypeScript, Vite · Python, FastAPI · Supabase PostgreSQL in Supabase Auth.

## Zagon z Dockerjem

1. Če lokalna konfiguracija še ne obstaja, ustvarite `.env`:

   ```sh
   test -f .env || cp .env.example .env
   ```

2. V `.env` nastavite povezavo do svojega projekta Supabase. Datoteke ne dodajajte v Git.

   | Spremenljivka | Namen |
   |---|---|
   | `SUPABASE_PROJECT_REF` | Identifikator projekta Supabase. |
   | `SUPABASE_URL` | URL projekta za prijavo. |
   | `SUPABASE_PUBLISHABLE_KEY` | Javni ključ projekta za prijavo (publishable ali starejši anon). |
   | `DATABASE_URL` | PostgreSQL povezava aplikacije z omejeno vlogo `quoteflow_app` in `sslmode=require`. |
   | `DATABASE_MIGRATION_URL` | Skrbniška povezava za pripravo baze in migracije; za običajni zagon ni potrebna. |

3. Zgradite in zaženite aplikacijo:

   ```sh
   docker compose up --build -d
   ```

| Storitev | Naslov |
|---|---|
| Spletna aplikacija | http://localhost:5173 |
| Dokumentacija API | http://localhost:8000/docs |
| Delovanje API-ja | http://localhost:8000/api/health |
| Povezava in pripravljenost baze | http://localhost:8000/api/ready |

Compose zažene frontend in backend; baza ostane v Supabase.

Migracije iz `supabase/migrations/` se ne izvajajo samodejno. Lokalni Supabase za teste (`supabase start`) zažene samo db, auth, rest, kong in inbucket.

Kalkulator deluje tudi brez baze; `/api/ready` ob manjkajoči povezavi ali nepripravljeni bazi vrne HTTP 503.

Stanje in dnevniki:

```sh
docker compose ps
docker compose logs -f
```

Ustavitev:

```sh
docker compose down
```

## Dokumentacija

- [Zasnova rešitve](docs/01-zasnova-resitve.md)
- [Funkcionalnosti in obseg](docs/02-funkcionalnosti-in-obseg.md)
- [Podatkovni model](docs/03-podatkovni-model.md)
- [Arhitektura in tehnologije](docs/04-arhitektura-in-tehnoloski-sklad.md)
- [Uporabniške zgodbe](docs/05-uporabniske-zgodbe.md)
- [Wireframi](docs/06-wireframes.md)
- [Arhitekturne odločitve](docs/adr/)
- [Uvedba novega podatkovnega modela](docs/razvoj/podatkovni-model.md)
- [Zgodovina US-01–US-02: identiteta in pravice](docs/razvoj/us-01-us-02-identiteta-in-pravice.md)
- [US-01: prošnja mojstra (#33, #34)](docs/razvoj/us-01-prosnja-mojstra.md)
- [US-02: materialna sestava (#35–#37)](docs/razvoj/us-02-materialna-sestava.md)
- [US-03: začetek projekta (#38–#40)](docs/razvoj/us-03-projekti.md)
- [Organizacija frontenda](docs/razvoj/frontend-arhitektura.md)
- [Zgodovina US-03–US-05: podatki ponudnika](docs/razvoj/us-03-us-05-podatki-ponudnika.md)
