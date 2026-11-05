# QuoteFlow AI

Večpodjetniška spletna aplikacija za vodenje projektov, ekip, cenika, materialov, ponudb in računov. Uporabnik lahko nastopa kot stranka ter kot mojster ali delavec pri različnih podjetjih.

**Izvedeno:** nova relacijska shema je uvedena v Supabase. Delujejo registracija/prijava, nove vloge, administratorsko upravljanje uporabnikov in podjetij z lastnikom ter cenik storitev, materiali in zaloga po lokacijah.

**Naslednji razvoj:** uporabniški postopki za prošnje mojstrov, projekte, ekipe, ponudbe in račune. Baza že vsebuje njihove omejitve in transakcijske postopke; API in vmesnik celotnega življenjskega cikla še nista uvedena. [Stanje razvoja](docs/razvoj/podatkovni-model.md).

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

Migracije iz `supabase/migrations/` se ne izvajajo samodejno.

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
- [Organizacija frontenda](docs/razvoj/frontend-arhitektura.md)
- [Zgodovina US-03–US-05: podatki ponudnika](docs/razvoj/us-03-us-05-podatki-ponudnika.md)
