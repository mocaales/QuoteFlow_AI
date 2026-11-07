# Administracija »Podjetja in pravice« in US-08: delavci podjetja

Zgodba [US-08](../05-uporabniske-zgodbe.md) (F8) je bila 2026-11-07 vključena v trenutni obseg. Odločitve: [ADR-0013](../adr/0013-delavci-podjetja-in-skrbniski-pregled-vlog.md). **Stanje: izvedeno; migracije uvedene v oddaljeni Supabase 2026-11-08.**

## Obseg

- **Mojster** v pogledu »Delavci« delavca **povabi** z e-poštnim naslovom, prekliče odprto povabilo ter delavca, ki je povabilo sprejel, odvzame in ponovno aktivira. Mojster ne more neposredno dodeliti vloge; dodeli lahko samo `delavec` v svojem podjetju, in to šele s sprejemom povabila. Ime in e-pošto vidi samo pri delavcih, ki so povabilo sprejeli (sprejeto preostalo tveganje, kot pri imenu stranke).
- **Povabljeni** (vsak prijavljen uporabnik s potrjeno e-pošto, ki ustreza naslovu) na strani »Pregled« vidi kartico »Povabila v podjetja« z gumboma Sprejmi in Zavrni (z potrditvijo). Po sprejemu se pravice osvežijo in podjetje se pojavi.
- **Admin** ima v »Podjetja in pravice« zavihke **Po podjetjih**, **Po uporabnikih**, **Prošnje mojstrov** (s številom čakajočih) in **Podjetja**. Iskanje in filtri (vloga, stanje; privzeto »Aktivne«) delujejo na naloženih podatkih. Vloge se odvzamejo in ponovno aktivirajo z označenim gumbom in potrditvijo.
- Vloga lastnika `mojster` se ne odvzame (`QFP33`).

### Povabila

| Stanje | Pomen |
|---|---|
| `povabljen` | Odprto; prikazano kot »Čaka«. Poteče po 14 dneh (Europe/Ljubljana). |
| `sprejeto` | Povabljeni je sprejel; ustvarjena ali ponovno aktivirana vloga `delavec` (`vloga_id`). |
| `zavrnjeno` | Povabljeni je zavrnil. |
| `preklicano` | Mojster je preklical odprto povabilo. |
| `poteklo` | Po 14 dneh brez odločitve; sprejem je zavrnjen s `QFP34`. |

- Odgovor na `POST .../delavci/povabila` je **vedno enak** (`201`, `id`, `e_posta` kot vpisana, `stanje: povabljen`, `poslano_ob`), ne glede na to, ali naslov obstaja, je nepotrjen, administratorski, neustrezen ali nov. Brez imena in `uporabnik_id`, zato obstoja računov ni mogoče ugotoviti. Neveljavna oblika naslova: `422`.
- Ponovno povabilo istega naslova (primerjava z `lower`) vrne obstoječe odprto povabilo; odprto povabilo je na (podjetje, naslov) največ eno.
- Omejitev hitrosti (`QFP30`): 20 povabil na uro na podjetje in 50 na dan na mojstra prek vseh podjetij.
- Sprejem znova preveri vse pogoje: potrjena e-pošta, aktivna vloga `stranka`, ni admin, ni stranka odprtega (nezaključenega) projekta tega podjetja (D19), podjetje je aktivno, povabilo odprto in mlajše od 14 dni. Če kateri ne velja: `QFP34` »Povabila ni mogoče sprejeti.« (`409`, splošno sporočilo). Tuj ali neznan `id`: `404`.
- Povabila se ne pošiljajo po e-pošti; vidna so samo v aplikaciji.

## API

| Metoda in pot | Dostop | Namen | Kode |
|---|---|---|---|
| `GET /podjetja/{id}/delavci` | mojster | Delavci podjetja, ki so povabilo sprejeli (`id`, `uporabnik_id`, `e_posta`, `ime`, `priimek`, `aktivna`, `dodeljeno_ob`). | 200, 403 |
| `POST /podjetja/{id}/delavci/povabila` | mojster | Telo `{e_posta}`; enak odgovor vedno. | 201, 403, 409 (`QFP30`), 422 |
| `GET /podjetja/{id}/delavci/povabila` | mojster | Odprta povabila in odločena v zadnjih 30 dneh (`id`, `e_posta`, `stanje`, `poslano_ob`, `odloceno_ob`). | 200, 403 |
| `POST /podjetja/{id}/delavci/povabila/{pid}/preklic` | mojster | Prekliče odprto povabilo. | 200, 403, 404 |
| `PATCH /podjetja/{id}/delavci/{vloga_id}` | mojster | Telo `{aktivna}`; samo vrstice `delavec` tega podjetja. | 200, 403, 404 |
| `GET /povabila` | vsak prijavljen | Lastna odprta povabila (`id`, `podjetje_id`, `podjetje_naziv`, `povabil`, `poslano_ob`). | 200 |
| `POST /povabila/{pid}/odlocitev` | povabljeni | Telo `{sprejmi: bool}`; odgovor `{id, stanje}`. | 200, 404, 409 (`QFP34`), 422 |
| `GET /admin/vloge` | admin | Vse vloge z e-pošto, imenom, podjetjem, `je_lastnik`, `dodeljeno_ob`. | 200, 403 |
| `GET /admin/uporabniki` | admin | Uporabniki s potrjenostjo e-pošte. | 200, 403 |
| `POST /admin/vloge`, `PATCH /admin/vloge/{id}` | admin | Dodelitev in odvzem vloge. | 200, 403, 404, 409, 422 |
| `POST /admin/podjetja`, `PUT /admin/podjetja/{id}` | admin | Podjetja. | 201/200, 403, 404, 409, 422 |
| `GET /admin/prosnje`, `POST /admin/prosnje/{id}/odlocitev` | admin | Prošnje mojstrov. | 200, 403, 404, 409 |

Nekdanji `POST /podjetja/{id}/delavci` (neposredno dodajanje) je odstranjen. Kode: `QFP22` skrbnik si ne more sam dodeliti vloge v podjetju; `QFP30` preveč povabil (glej zgoraj); `QFP33` lastniku ni mogoče odvzeti vloge mojster; `QFP34` povabila ni mogoče sprejeti. Kode so v `CONFLICTS` v `backend/app/errors.py`.

## Baza in varnost

Migracija `20261106210000_delavci_in_pravice.sql` (lokalna): stolpec `vloga_uporabnika.dodeljeno_ob`; zasebne tabele `quoteflow_private.dogodek_vloge` (revizija), `poskus_delavca` (omejitev hitrosti) in `povabilo_delavca` (povabila), vse s prisilnim RLS in brez pravic, izven pogodbe 22 poslovnih tabel; funkcije `povabi_delavca`, `povabila_podjetja`, `preklici_povabilo`, `moja_povabila`, `odgovori_povabilo`, `uredi_delavca`, `delavci_podjetja`, `potrjeni_uporabniki`. `dodaj_delavca` je odstranjena. Migracija doda tudi omejitvi CHECK na `postavka_cenika` (`cena_na_enoto` ≤ 1 000 000, `naziv` po obrezu 1–200 znakov; ustavi se, če obstoječe vrstice mejo kršijo).

Dodatne migracije po varnostnem pregledu (G6):

| Migracija | Vsebina |
|---|---|
| `20261107212046_aktivna_seja_uuid.sql` | `aktivna_seja()` primerja `session_id` z ključem `auth.sessions` (cast v `uuid` samo pri veljavni obliki; neveljavna zahtevka da `false`, ne napake). Podpis in pravice nespremenjeni. |
| `20261107220000_celovitost_oznaka.sql` | Oznaka opravljenega preverjanja celovitosti je v zasebni tabeli `preverjeno_podjetje` (veljavna za trenutno transakcijo), ne več v GUC, ki bi ga lahko nastavil kateri koli klicatelj. |
| `20261107221442_brisanje_racuna_dogodki.sql` | Tuji ključi uporabnika v `dogodek_vloge` in `povabilo_delavca` so `ON DELETE SET NULL`. |

- Iskanje po e-pošti ne razkrije obstoja računov: odgovor povabila je enak za vse vnose, imenika ali samodokončanja ni.
- `dodeli_vlogo` in `aktiviraj_vlogo` sta **samo za admina** (avtorizacija pred branjem vrstice); mojster uporablja povabila in `uredi_delavca`. Tudi admin pri dodelitvi in ponovni aktivaciji preveri pravilo D19 in potrjeno e-pošto ciljnega uporabnika; nihče ne dodeli podjetniške vloge aktivnemu skrbniku.
- Ponovna aktivacija zahteva aktivno vlogo `stranka` in potrjeno e-pošto. Odvzem velja pri naslednjem zahtevku.
- Revizija `dogodek_vloge`: stolpec `dejanje` (`vloga`, `povabljen`, `sprejeto`, `zavrnjeno`, `preklicano`) z `povabilo_id`; vsaka sprememba vloge in vsak korak povabila zapiše vrstico (izvajalec, tarča, podjetje, vloga, prej/zdaj, čas). Samodejna dodelitev `stranka` in lastnikova vloga `mojster` sta prav tako zapisani.
- **Brisanje računa:** uporabnika z revizijskimi vrsticami ali povabili je mogoče izbrisati; vrstice ostanejo z ničlo namesto osebe. Pravila ob vnosu (izvajalec, tarča, povabitelj) še veljajo prek sprožilcev BEFORE. Še vedno ni mogoče izbrisati stranke s projektom (ponudbe, računi) in lastnika podjetja; to in e-pošta povabljenega v `povabilo_delavca` ostajata v obsegu [#104](https://github.com/mocaales/QuoteFlow_AI/issues/104) (izbris in hramba).
- Pregled uporabnikov za admina ni stran po stran (filtriranje v odjemalcu); sprejeto, ponovni pregled z #104.

## Vmesnik

`features/workers/` (`Workers.tsx`, `api.ts`, `types.ts`): obrazec »E-pošta delavca« z gumbom »Povabi delavca« (uspeh: »Povabilo je poslano. Delavec ga mora sprejeti v svojem računu.«), razdelek »Povabila« (E-pošta, Stanje, Poslano, »Prekliči povabilo« z vrstično potrditvijo), nato delavci z iskanjem, filtrom stanja in označenimi dejanji; navigacija »Delavci« samo za mojstra. `MyInvitations.tsx`: kartica »Povabila v podjetja« na Pregledu. `features/administration/components/`: `Admin.tsx` (zavihki), `CompanyRoles.tsx`, `UserRoles.tsx`, `RoleAction.tsx`, `RoleDrawer.tsx`, `Applications.tsx`, `Companies.tsx`.

## Preverjanje

```sh
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_delavci.py tests/test_delavci_database.py tests/test_admin_vloge.py tests/test_access.py -q
cd frontend && npx vitest run src/tests/workers.test.tsx src/tests/admin-panel.test.tsx
cd frontend && npm run test:e2e
```

Zadnji polni zagon (CoS, 2026-11-07, sveže ponastavljen lokalni Supabase):

| Preverjanje | Rezultat |
|---|---|
| Backend brez baze | 1435 uspešnih, 585 preskočenih |
| Backend z lokalno bazo | 2016 uspešnih (vključno z 28 HTTP testi avtorizacije v `test_avtorizacija_v3_database.py`), 4 preskočeni (omejen test zmogljivosti, živi tok prijave, dva živa preverjanja izvajalnega okolja) |
| Test zmogljivosti (omejen) | uspešen, pošiljanje ponudbe 0,98 s |
| `supabase/tests/tenant_isolation.sql`, `brisanje_racuna.sql` | uspešna |
| Preizkus nadgradnje v1 → v2 (`v1_to_v2_upgrade`) | uspešen |
| Vitest | 227 uspešnih (20 datotek) |
| `npm run build` | uspešen |
| Playwright (1440 in 390 px) | 468 uspešnih, 2 preskočena |

Posnetke zaslona na 1440 in 390 px je pregledal CoS.

## Namenoma ni vključeno

Ekipe in dodelitev delavcev projektom (US-09, US-10), imenik uporabnikov ali samodokončanje e-pošt, pošiljanje vabil po e-pošti (vabila so samo v aplikaciji), delavec kot samostojen uporabnik poslovnih podatkov (njegov pogled še ni uveden), uvedba v oddaljeni Supabase (vse migracije US-08 so samo lokalne), izbris in hramba osebnih podatkov (#104).
