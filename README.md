# QuoteFlow AI

Večpodjetniška spletna aplikacija za vodenje projektov, ekip, cenika, materialov, ponudb in računov. Uporabnik lahko nastopa kot stranka ter kot mojster ali delavec pri različnih podjetjih.

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

## Lokalni potek MVP

Za razvoj brez oddaljene baze uporabite lokalni Supabase (potrebna sta Supabase CLI in Docker). Ukazi iz korena repozitorija:

```sh
supabase start
supabase db reset
```

`supabase db reset` uporabi vse migracije iz `supabase/migrations/`. Nato zaženite backend in frontend (v `backend/` in `frontend/` morata biti nameščeni odvisnosti, `.venv` oziroma `npm ci`). `DATABASE_URL`, `SUPABASE_URL` in `SUPABASE_PUBLISHABLE_KEY` v `.env` usmerite na lokalni sklad (izpiše ga `supabase status`); omejeno prijavo `quoteflow_app` pripravi `scripts/configure_database.py`, prvega administratorja `scripts/bootstrap_admin.py <e-pošta>`, oba iz korena z `backend/.venv/bin/python`.

```sh
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

Vite je na http://localhost:5173 in posreduje `/api` na `127.0.0.1:8000`.

Potek skozi vmesnik (potrebujete mojstra s podjetjem z davčno številko, cenik in registrirano stranko):

1. Mojster ustvari projekt za stranko (e-pošta) in zahteva ogled.
2. Mojster v projektu pripravi vrste dela, postavke (iz cenika ali nove) z izmerami, nato ponudbo z `velja_do`, potrdi in pošlje (nastane posnetek).
3. Stranka v »Moji projekti« ponudbo sprejme (s potrditvijo); nastane osnutek računa, projekt preide v fazo termin.
4. Mojster določi termin, po koncu dela zaključi izvedbo.
5. Mojster preveri prejemnika in rok plačila ter izda račun; stranka ga vidi.
6. Mojster evidentira plačilo; projekt je zaključen.

Avtomatsko preverjanje istega poteka (API in Supabase Auth sta nadomeščena): `cd frontend && npm run test:e2e` (`e2e/acceptance.spec.ts`). Podrobnosti: [US-04–US-07](docs/razvoj/us-04-us-07-ponudbe-in-racuni.md).

## Hramba podatkov

Izdani računi in poslane ponudbe so nespremenljivi posnetki, ki se hranijo 10 let (ZDDV-1, ZGD-1; GDPR člen 17(3)(b)). Tuji ključi na uporabnika so `RESTRICT`, zato stranke z računi ni mogoče trdo izbrisati; postopek anonimizacije je odprt ([#104](https://github.com/mocaales/QuoteFlow_AI/issues/104)). Naslov prejemnika na računu je kraj izvedbe, razen če ga mojster ob izdaji spremeni.

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
- [Model v3: vrste dela, postavke projekta, izmere](docs/razvoj/model-v3-postavke-izmere.md) in [ADR-0012](docs/adr/0012-postavke-projekta-izmere-in-vrste-dela.md)
- [Administracija in US-08: delavci podjetja](docs/razvoj/admin-in-delavci-us-08.md) in [ADR-0013](docs/adr/0013-delavci-podjetja-in-skrbniski-pregled-vlog.md)
- [US-04–US-07: ponudbe, izvedba in račun (#41–#51)](docs/razvoj/us-04-us-07-ponudbe-in-racuni.md) (delovni načrt: [mvp-ponudbe-racuni-design.md](docs/razvoj/mvp-ponudbe-racuni-design.md))
- [Organizacija frontenda](docs/razvoj/frontend-arhitektura.md)
- [Zgodovina US-03–US-05: podatki ponudnika](docs/razvoj/us-03-us-05-podatki-ponudnika.md)
