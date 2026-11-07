# Model v3: vrste dela, postavke projekta in izmere

Razširitev F2 in F4 (brez nove oznake F); zgodbi [US-02 in US-04](../05-uporabniske-zgodbe.md). Odločitve: [ADR-0012](../adr/0012-postavke-projekta-izmere-in-vrste-dela.md). Model, formula in diagram: [dokument 03](../03-podatkovni-model.md). **Stanje: izvedeno in uvedeno v oddaljeni Supabase 2026-11-08.**

## Obseg

- Nova tabela `vrsta_dela` (naziv, opis, urna postavka, ure, število delavcev, izpeljana `cena_dela`) in `material_vrste_dela` (neobvezni materiali na enoto dela). `sestava_cenika` in njene poti `/sestava` so odstranjene; materialna sestava je zdaj lastnost vrste dela.
- `postavka_cenika` ima obvezno `vrsta_dela_id` in enoto `m`, `m2`, `m3` ali `kos` (stolpec `vrsta_dela` kot besedilo je odstranjen).
- Postavke so na projektu (`postavka_projekta`), ne več na ponudbi. Količino določajo izmere (`izmera`); formula A (540,00 / 118,80 / 658,80 za primer iz dokumenta 03) je v generiranih stolpcih.
- Pošiljanje ponudbe naredi posnetek: `postavka_ponudbe` (zneski kot navadni stolpci), `izmera_ponudbe`, `material_ponudbe`, `delo_ponudbe` (samo mojster). Tabel je zdaj 22 (`EXPECTED_TABLES` v `backend/app/database.py`).
- Stranka v poslani ponudbi vidi postavke, zneske in izmere (samo zahtevane ali zadnje različice); ne vidi urne postavke, ur, delavcev ali materialov.
- Vmesnik: `features/supplier` (zavihek Vrste dela z materiali, cenik z vrsto dela in enoto) ter `features/items` (zavihek Postavke projekta: seznam, obrazec, izmere, izbira iz cenika); ponudba (`features/quotes`) postavk več ne ureja, jih prikaže in pošlje.

## API

Predpona `/api`. `C` = `/podjetja/{company_id}`, `P` = `C/projekti/{project_id}`. Vse poti mojstra: `company_member('mojster')`; tuje podjetje, tuj projekt in naključni UUID dajo enak `404`. Denar in količine so nizi.

| Metoda in pot | Namen | Kode |
|---|---|---|
| `GET C/vrste-dela` | Vrste dela z materiali. | 200, 403 |
| `POST C/vrste-dela` | Nova vrsta dela. | 201, 403, 409, 422 |
| `PUT C/vrste-dela/{work_id}` | Urejanje (tudi `aktivna`). | 200, 403, 404, 422 |
| `PUT C/vrste-dela/{work_id}/materiali/{material_id}` | Material vrste dela (`kolicina_na_enoto`). | 200, 403, 404, 409, 422 |
| `DELETE C/vrste-dela/{work_id}/materiali/{material_id}` | Odstrani material. | 204, 403, 404 |
| `GET C/cenik`, `POST C/cenik`, `PUT C/cenik/{item_id}` | Cenik; telo ima `vrsta_dela_id` in `enota`. | 200/201, 403, 404, 409, 422 |
| `GET P/postavke` | Postavke z izmerami in vsotami (`neto`, `ddv`, `skupaj`). | 200, 403, 404 |
| `POST P/postavke` | Nova postavka. | 201, 403, 404, 409, 422 |
| `POST P/postavke/iz-cenika` | Postavka iz cenika (`postavka_cenika_id`, `kolicina`, `popust`); kopira ceno, DDV in delovne podatke vrste dela. | 201, 403, 404, 409, 422 |
| `PUT P/postavke/{item_id}` | Urejanje postavke. | 200, 403, 404, 409, 422 |
| `DELETE P/postavke/{item_id}` | Odstrani postavko. | 204, 403, 404, 409 |
| `POST P/postavke/{item_id}/izmere` | Nova izmera (`odstej`, `kosi`, `dolzina`, `visina`, `sirina`). | 201, 403, 404, 409, 422 |
| `PUT P/postavke/{item_id}/izmere/{measure_id}` | Urejanje izmere. | 200, 403, 404, 409, 422 |
| `DELETE P/postavke/{item_id}/izmere/{measure_id}` | Odstrani izmero. | 204, 403, 404, 409 |
| `GET/POST P/ponudbe`, `GET/PUT P/ponudbe/{id}`, `POST P/ponudbe/{id}/poslji` | Ponudba je glava; vrstice so postavke projekta (osnutek) ali posnetek (poslana). | glej [US-04–US-07](us-04-us-07-ponudbe-in-racuni.md) |
| `GET /projekti/{id}/ponudbe` | Stranka: poslane ponudbe s postavkami in izmerami. | 200, 403, 404 |

Polja izmere morajo ustrezati enoti postavke (`m` dolžina; `m2` dolžina in višina; `m3` vsa tri; `kos` samo `kosi`), sicer `422` pred klicem SQL; SQL CHECK ostane zadnja zaščita. Postavke so spremenljive v fazah `pregled`, `ogled`, `ponudba` brez sprejete ponudbe (sicer `QFP07`). Poti `/podjetja/{id}/projekti/{pid}/ponudbe/{id}/postavke…` in `/cenik/{id}/sestava` ne obstajajo več.

### Meje in kode konfliktov (409)

Meje vnosa so v [dokumentu 03](../03-podatkovni-model.md) (tabelarne omejitve in Pydantic); decimalke so ASCII nizi, največ 4 decimalke, brez NaN in eksponentov.

| Koda | Pomen |
|---|---|
| `QFP05` | Neaktivnega materiala ni mogoče dodati vrsti dela. |
| `QFP20` | Več kot 200 postavk na projekt. |
| `QFP25` | Izmere bi dale negativno količino (vstavljanje, urejanje, obrat predznaka, brisanje). |
| `QFP26` | Pošiljanje: postavka brez pozitivne količine izmer. |
| `QFP27` | Enote postavke ni mogoče spremeniti, ko ima izmere. |
| `QFP28` | Več kot 100 izmer na postavko. |
| `QFP29` | Neaktivne vrste dela ni mogoče uporabiti. |
| `QFP31` | Več kot 500 vrst dela na podjetje. |
| `QFP32` | Več kot 50 materialov na vrsto dela. |

`QFP07`, `QFP10`, `QFP12`, `QFP13`, `QFP16` ostanejo kot v [US-04–US-07](us-04-us-07-ponudbe-in-racuni.md). `QFP30` in `QFP33` pripadata [US-08](admin-in-delavci-us-08.md).

## Baza in varnost

| Migracija | Vsebina |
|---|---|
| `20261106100000_model_v3_postavke_izmere.sql` | Tabele (6 novih, `sestava_cenika` odstranjena), pretvorba cenika (X1), preverjanje celovitosti, bralna pravila, `shrani_vrsto_dela`, `shrani_material_vrste`, `odstrani_material_vrste`, `shrani_cenik`. Razvrščena za `20261105140049`, pred lokalnimi migracijami. |
| `20261106200016`, `…200018`, `…200759` | Prepisane na mestu (nikoli uvedene): `shrani_postavko_projekta`, `dodaj_postavko_iz_cenika`, `odstrani_postavko_projekta`, `shrani_izmero`, `odstrani_izmero`, `preracunaj_izmere`, `poslji_ponudbo` (posnetek). |
| `20261106220000_indeksi_v3.sql` | Indeks `vloga_uporabnik_idx` na `vloga_uporabnika(uporabnik_id)` po pregledu načrtov. |

Varnostni ukrepi (iz G1; vsi izvedeni):
- **Izolacija podjetij:** vsaka funkcija razreši ID skupaj s `podjetje_id` (in `projekt_id`) ali vrne `no_data_found`; sprožilci celovitosti in `zakleni_reference` preprečijo povezave med podjetji (vrsta dela, material vrste dela, postavka, izmera, posnetek); sestavljeni tuji ključ drži izmero v enoti postavke.
- **Tabele RLS:** vseh 22 tabel ima prisiljen RLS, `authenticated` samo `select`; nove žive tabele bere samo mojster podjetja (množice `mojstrova_podjetja`, `mojstrovi_projekti`, izračunane enkrat na stavek). `delo_ponudbe` stranka ne bere.
- **Nespremenljivost:** posnetek zaklene `zakleni_postavko` (tudi `izmera_ponudbe`, `delo_ponudbe`); zneski posnetka so navadni stolpci, zapisani enkrat ob pošiljanju. Pisanje v postavke in pošiljanje zaklene podjetje, nato projekt (preprečitev tekmovalnih stanj).
- **Meje:** CHECK in Pydantic; skupna izmera nikoli negativna, ponovni izračun po vsakem pisanju.
- **Pretvorba oddaljenega cenika (X1):** ena transakcija; ob neznani enoti ali obstoječih vrsticah ponudb se ustavi z napako (brez privzetka `kos`); preverjanje števila vrstic po preslikavi.
- **Odgovori:** fiksna besedila napak, brez odmeva vnosa.

## Preverjanje

```sh
cd backend && .venv/bin/python -m pytest -q
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build && npm run test:e2e
```

Lokalni Supabase mora biti zagnan (`supabase start`, `supabase db reset`). Testi: `backend/tests/test_vrste_dela.py`, `test_postavke*.py`, `test_cena_postavke.py`, `test_pricing.py`, `test_ponudbe_v3.py`, `test_katalog_v3_migracija_database.py`, `test_model_database.py`, `test_postavke_database.py`, `test_postavke_socasnost_database.py`; `frontend/src/tests/project-items.test.tsx`, `vrste-dela.test.tsx`, `supplier.test.tsx`, `quotes*.test.tsx`; `frontend/e2e/design.spec.ts`, `acceptance.spec.ts`. Izolacija: `supabase/tests/tenant_isolation.sql`.

Zadnji polni zagon (CoS, 2026-11-08, sveže ponastavljen lokalni Supabase): backend brez baze 1435 uspešnih/585 preskočenih; z lokalno bazo 2016 uspešnih/4 preskočeni; `tenant_isolation.sql` in `brisanje_racuna.sql` uspešna; preizkus nadgradnje v1 → v2 uspešen; Vitest 227 (20 datotek); `npm run build` uspešen; Playwright 468 uspešnih/2 preskočena; posnetke 1440 in 390 px je pregledal CoS. Podrobnosti: [admin-in-delavci-us-08.md](admin-in-delavci-us-08.md).

## Namenoma ni vključeno

- Shranjevanje postavke projekta nazaj v cenik.
- Posebej zaračunan material (material je v ceni na enoto); rezervacije in poraba zaloge (F24).
- Delo po enoti ali po posameznem delavcu (ena urna postavka, pavšal na postavko), več stopenj DDV na postavko.
- Evidenca dejanskih ur (F23), PDF in e-pošta ponudbe (F11, F12).
- Uvedba v oddaljeni Supabase: čaka na pregled, poskusni zagon in odobritev uporabnika.
