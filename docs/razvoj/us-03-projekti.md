# US-03: začetek projekta (#38 baza, #39 API, #40 vmesnik)

Veljavna zgodba je US-03 v [uporabniških zgodbah](../05-uporabniske-zgodbe.md). Mojster odpre projekt za registrirano stranko, ga ureja v začetnih fazah in zahteva ogled.

## Obseg

- Mojster ustvari projekt (faza `pregled`) za stranko, ki jo izbere z natančnim e-poštnim naslovom. Seznam uporabnikov se ne izpostavlja (odločitev z uporabnikom).
- Mojster projekt ureja (naziv, opis, lokacija) v fazah `pregled` in `ogled` ter zahteva ogled (`pregled` v `ogled`).
- Stranka vidi samo svoje projekte, samo za branje, in samo naziv podjetja.

## API

Poti imajo predpono `/api`.

| Metoda in pot | Dostop | Namen | Kode |
|---|---|---|---|
| `GET /podjetja/{id}/projekti` | mojster | Projekti podjetja s podatki stranke. | 200, 403 |
| `POST /podjetja/{id}/projekti` | mojster | Nov projekt (`ustvari_projekt`); telo `e_posta_stranke`, `naziv`, `opis`, `lokacija_izvedbe`. | 201, 403, 409, 422 |
| `PUT /podjetja/{id}/projekti/{projekt_id}` | mojster | Urejanje (`uredi_projekt`). | 200, 403, 404, 409, 422 |
| `POST /podjetja/{id}/projekti/{projekt_id}/ogled` | mojster | Zahteva ogled (`zahtevaj_ogled`). | 200, 403, 404, 409 |
| `GET /projekti` | prijavljen uporabnik | Lastni projekti kot stranka z nazivom podjetja. | 200 |
| `GET /projekti/{projekt_id}` | prijavljen uporabnik | En lastni projekt. | 200, 404 |

- `409` `QFP06`: e-pošta ni aktivna registrirana stranka; sporočilo je enako za neznan in neaktiven račun (brez razkrivanja računov).
- `409` `QFP07`: dejanje v tej fazi ni dovoljeno.
- `409` `QFP08`: več kot 20 poskusov ustvarjanja projekta na podjetje v drsečni uri (»Preveč poskusov ustvarjanja projektov. Poskusite znova čez nekaj časa.«).
- `403` na `/api/projekti*` za uporabnika brez vloge `stranka` (varovalka `customer`).
- `422` tudi za znak NUL v besedilnih poljih (skupni model `Input`, ki ga uporabljajo tudi vnosi projektov). Besedilni vnosi zavrnejo krmilne in oblikovne znake Unicode razen tabulatorja, preloma vrstice in pomika na začetek vrstice (CR) (»Vrednost vsebuje nedovoljene znake.«).
- Osrednja obravnava validacijskih napak v `backend/app/errors.py` vrne `422` brez odmeva vnosa, tudi za `NaN`, `Infinity`, `1e309`, osamljene surogate in globoko gnezdenje (utrditev po penetracijskem testu).
- `404`: tuj ali neobstoječ projekt.

## Baza in varnost

Migracija `20261105140049_projekti.sql`:

- funkcije `ustvari_projekt`, `uredi_projekt`, `zahtevaj_ogled` v `quoteflow_private` (preverjanje mojstra, zaklepanje vrstic, vrstni red zaklepov podjetje, vloga mojstra, vloga stranke);
- podatke stranke (`id`, `e_posta`, `ime`, `priimek`) dobi mojster samo prek funkcije `quoteflow_private.stranke_projektov(podjetje)` (`security definer`). Politika `read_stranka` in funkcija `vidi_stranko` sta odstranjeni; mojster lahko z `select` prebere samo svojo vrstico v `uporabnik`;
- omejitev poskusov: največ 20 poskusov ustvarjanja projekta na podjetje v drsečni uri (uspešni in neuspešni z neznano stranko), zapisanih v `quoteflow_private.poskus_projekta` (RLS, brez pravic aplikacijskih vlog). 21. poskus sproži `QFP08`. Pri neznani stranki funkcija vrne `id` `NULL`, API odgovori `409` s sporočilom `QFP06` in transakcije ne razveljavi, da se poskus šteje;
- funkcija `naziv_podjetja`: stranka dobi samo naziv podjetja, ne cele vrstice;
- izvajanje funkcij je dovoljeno samo vlogi `authenticated`.

Sprejeto preostalo tveganje (odločitev uporabnika, 5. 11. 2026): odobreni mojster lahko še vedno potrdi, da e-pošta pripada registrirani stranki, in vidi njeno ime. Hramba in izbris po GDPR sta v issue #104.

Kode `QFP06`–`QFP08` preslika `backend/app/errors.py` v `409`.

## Struktura backenda

Končne točke so razdeljene v `backend/app/routers/` (`identity`, `admin`, `prosnje`, `cenik`, `materiali`, `projekti`). Osrednje preslikavo kod SQLSTATE v HTTP (`CONFLICTS` `QFP01`–`QFP08`) vsebuje `backend/app/errors.py`, skupni tipi (`Input`, `Amount`, `TaxRate`) so v `backend/app/models/common.py`. Nabor poti se ni spremenil.

## Vmesnik

- **Projekti** (mojster, `features/projects/components/ProjectsWorkspace.tsx`): projekti, združeni po fazah; obrazec za nov projekt in urejanje (`ProjectForm.tsx`); gumb za zahtevo ogleda.
- **Moji projekti** (stranka, `MyProjects.tsx`): samo branje.

## Lokalni Supabase

`supabase/config.toml` za lokalni sklad izključuje studio, realtime, storage, edge_runtime in analytics; delujejo db, auth, rest, kong in inbucket.

```sh
supabase start
supabase db reset
```

## Preverjanje

```sh
cd backend && .venv/bin/python -m pytest -q
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_projekti_database.py tests/test_sestava.py -q
cd frontend && npm test && npm run build && npm run test:e2e
```

Rezultati ob zaključku US-02 in US-03: pytest z lokalnim Supabase 298 uspešnih, 3 preskočeni (brez baze 229 uspešnih); `supabase/tests/tenant_isolation.sql` uspešen; Vitest 52; build uspešen; Playwright 37 uspešnih, 1 preskočen; posnetki pregledani pri 1440 in 390 px. Varnostni pregled brez kritičnih/visokih ugotovitev, vse nižje odpravljene; penetracijski test na lokalnem okolju čist za avtorizacijo in izolacijo podjetij. Migraciji `20261105140047` in `20261105140049` sta uvedeni v Supabase 5. 11. 2026. Testi: `backend/tests/test_projekti.py`, `test_projekti_database.py`, `test_structure.py`, `frontend/src/tests/projects.test.tsx`.

## Namenoma ni vključeno

Izbira stranke s seznama, ekipe, termin, ponudbe in računi, prehodi faz nad `ogled`, brisanje projekta, obveščanje po e-pošti.
