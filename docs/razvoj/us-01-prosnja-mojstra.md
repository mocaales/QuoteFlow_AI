# US-01: prošnja mojstra (#33 API, #34 vmesnik)

Veljavna zgodba je US-01 v [uporabniških zgodbah](../05-uporabniske-zgodbe.md). Ta zapis pokriva merili 2 in 3 (oddaja in odločitev); merila 1, 4 in 5 so bila pokrita že prej. Wireframe: [05-racun-in-prosnja.svg](../wireframes/05-racun-in-prosnja.svg).

## Obseg

Stranka ali delavec odda prošnjo s podatki podjetja. Administrator jo odobri ali zavrne. Odobritev v isti transakciji ustvari podjetje, lastništvo in aktivno vlogo `mojster`.

## API

Poti imajo predpono `/api`. Vse zahtevajo aktivno sejo; `/admin/*` zahteva globalno vlogo `admin`.

| Metoda in pot | Dostop | Namen | Kode |
|---|---|---|---|
| `POST /prosnje` | prijavljen uporabnik | Oddaja prošnje (`quoteflow_private.oddaj_prosnjo`). | 201, 403, 409, 422 |
| `GET /prosnje` | prijavljen uporabnik | Lastne prošnje, najnovejše prve. | 200 |
| `GET /admin/prosnje` | admin | Vse prošnje z e-pošto in imenom vlagatelja; oddane najprej. | 200, 403 |
| `POST /admin/prosnje/{id}/odlocitev` | admin | Telo `{"odobri": true/false}` (`odloci_prosnjo`). | 200, 403, 404, 409, 422 |

Odločitve in napake:

- `409` pri oddaji: podjetje ali oddana prošnja z isto matično številko že obstaja (kršitev enoličnosti).
- `409` pri oddaji: uporabnik že ima oddano prošnjo (ena čakajoča prošnja na uporabnika); po odločitvi lahko odda novo.
- `409` pri odločitvi: prošnja je že obravnavana (kršitev omejitve stanja).
- `409` pri odobritvi: vlagatelj nima več potrjene e-pošte ali aktivne vloge stranke oziroma delavca; prošnja ostane oddana, nič se ne ustvari. Zavrnitev je vedno mogoča.
- `GET /prosnje` vedno filtrira po `uporabnik_id` prijavljenega, tudi za administratorja; pregled vseh je samo na `/admin/prosnje`.
- Neznana prošnja vrne `404`, neveljaven `id` ali telo `422`, brez pravice `403`.

## Baza in varnost

Funkciji `oddaj_prosnjo` in `odloci_prosnjo` sta v `20261103211654_v2_projects_roles_catalog.sql`. Varnostni pregled je našel tri manjše pomanjkljivosti, ki jih odpravi migracija `20261105114405_prosnja_varnost.sql`: največ ena oddana prošnja na uporabnika (preverjanje z zaklepom uporabnika in delni enolični indeks), ob odobritvi ponovno preverjanje potrjene e-pošte in aktivne vloge vlagatelja (SQLSTATE 55000) ter ponovno preverjanje zasedenosti matične številke tik pred odobritvijo. Pričakovani konflikti imajo lastne SQLSTATE kode (`QFP01` že obravnavana, `QFP02` že oddana prošnja, `QFP03` neustrezen vlagatelj, `QFP04` zasedena matična številka), ki jih v `409` s slovenskim sporočilom preslika osrednji obravnavalec v `backend/app/main.py`; poti napak ne lovijo same. Migracija se ustavi, če ima kateri uporabnik že več oddanih prošenj. Aplikacijska vloga še vedno nima neposrednih pisalnih pravic; napake gonilnika se ne vračajo odjemalcu.

## Vmesnik

- Delovni prostor: navigacija **Prošnja za mojstra** (`features/identity/components/MasterApplication.tsx`): lastne prošnje in obrazec; obrazec je skrit, dokler je prošnja v stanju `oddana`.
- Administracija: razdelek **Prošnje mojstrov** z gumbi Odobri in Zavrni (`features/administration/components/Admin.tsx`).

## Preverjanje

V mapi `backend/`:

```sh
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_prosnja_database.py -q
```

V mapi `frontend/`:

```sh
npm test
npm run build
npm run test:e2e
```

Rezultati ob zaključku: pytest z lokalnim Supabase 126 uspešnih, 3 preskočeni (brez baze 91 uspešnih); `supabase/tests/tenant_isolation.sql` uspešen; Vitest 38; build uspešen; Playwright 27 uspešnih, 1 preskočen; posnetki pregledani pri 1440 in 390 px. Testi: `backend/tests/test_prosnja.py`, `backend/tests/test_prosnja_database.py`, poteza v `test_access.py`, `frontend/src/tests/prosnja.test.tsx`, prošnja v `frontend/e2e/design.spec.ts`.

## Namenoma ni vključeno

Obveščanje po e-pošti, razlog zavrnitve, umik prošnje in projekti/ekipe/ponudbe/računi.
