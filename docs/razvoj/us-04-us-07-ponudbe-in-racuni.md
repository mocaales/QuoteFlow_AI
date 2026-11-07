# US-04–US-07: ponudbe, odločitev, izvedba in račun (#41–#51)

Veljavne zgodbe so US-04–US-07 v [uporabniških zgodbah](../05-uporabniske-zgodbe.md) (F4–F7, MVP). Delovni načrt iz G1 je v [mvp-ponudbe-racuni-design.md](mvp-ponudbe-racuni-design.md); ta zapis ga nadomešča in vključuje spremembe po G1.

> **Model v3 (2026-11-07):** postavke ponudbe so zdaj postavke projekta z izmerami; vrstice ponudbe so posnetek ob pošiljanju. Poti `…/ponudbe/{id}/postavke…`, ročno urejanje vrstic ponudbe in formula `kolicina × cena × (1 − popust)` spodaj so zastarele; veljajo [model-v3-postavke-izmere.md](model-v3-postavke-izmere.md) in [dokument 03](../03-podatkovni-model.md). Poti za izvedbo, račun in odločitev stranke ostanejo.

| Zgodba | Naloge | Vsebina |
|---|---|---|
| US-04 | #41–#43 | Osnutek ponudbe, postavke iz cenika in prosto urejanje, različice. |
| US-05 | #44–#45 | Pošiljanje ponudbe, sprejem ali zavrnitev stranke, nastanek osnutka računa. |
| US-06 | #46–#48 | Termin in zaključek izvedbe. |
| US-07 | #49–#51 | Izdaja računa, evidenca plačila, zaprtje projekta; potek MVP. |

## Obseg

- Mojster v projektu pripravi postavke z izmerami (iz cenika ali nove), ustvari osnutek ponudbe (glava), nastavi `velja_do` in ponudbo pošlje; ob pošiljanju se postavke projekta prepišejo v posnetek. Pred pošiljanjem in izdajo je potrditveni korak.
- Poslana ponudba je nespremenljiva. Popravek je nova različica (`razlicica + 1`) z isto številko ponudbe; je glava; ob pošiljanju se posnetek napolni iz trenutnih postavk projekta.
- Stranka vidi samo poslane ponudbe svojega projekta in jih sprejme ali zavrne (s potrditvijo). Sprejem v isti transakciji ustvari osnutek računa in premakne projekt v fazo `termin`.
- Mojster določi in prestavi termin, zaključi izvedbo, izda račun in evidentira plačilo; plačilo zaključi projekt.
- Številčenje po podjetju in letu: ponudba `P-2026-001`, račun `R-2026-001` (zaporedje pod ključavnico podjetja).
- Izračun je samo v SQL (formula A): `neto = round((izmera_skupaj × kolicina × cena + urna × ure × delavci) × (1 − popust), 2)`, `ddv = round(neto × stopnja_ddv, 2)`; vsote so vsote zaokroženih postavk. Primer: 20 m² × 1 × 10 €, delo 25 € × 8 h × 2, popust 10 %, DDV 22 % je 540,00 / 118,80 / 658,80.
- Račun: prejemnik (`prejemnik_naziv`, `prejemnik_naslov`) je predizpolnjen z imenom stranke in `lokacija_izvedbe`, mojster ga ob izdaji potrdi ali popravi. Nadomestne e-pošte ni; koda `QFP19` je odstranjena. Izdajatelj je posnetek podatkov podjetja.
- Rok plačila v vmesniku je privzeto danes + 8 dni.

## API

Poti imajo predpono `/api`. `M` = `/podjetja/{id}/projekti/{projekt_id}`. Mojstrske poti imajo varovalko `company_member('mojster')` in vsako poizvedbo filtrirajo po podjetju; tuje podjetje, tuj projekt in naključni UUID dajo enak `404`. Denar in količine potujejo kot nizi.

| Metoda in pot | Dostop | Namen | Kode |
|---|---|---|---|
| `GET M/ponudbe` | mojster | Različice ponudb projekta. | 200, 403, 404 |
| `POST M/ponudbe` | mojster | Nov osnutek ali nova različica (`velja_do` neobvezen). | 201, 403, 404, 409, 422 |
| `GET M/ponudbe/{id}` | mojster | Ponudba: osnutek prikaže žive postavke projekta, poslana posnetek z materiali; DDV po stopnjah. | 200, 403, 404 |
| `…/postavke`, `…/izmere` | mojster | Postavke in izmere projekta: glej [model-v3-postavke-izmere.md](model-v3-postavke-izmere.md). | |
| `PUT M/ponudbe/{id}` | mojster | Nastavi `velja_do` osnutka. | 200, 403, 404, 409, 422 |
| `POST M/ponudbe/{id}/poslji` | mojster | Pošlje ponudbo, naredi posnetek in jo zaklene (`QFP13` brez postavk, `QFP26` postavka brez izmer). | 200, 403, 404, 409, 422 |
| `PUT M/termin` | mojster | `termin_od`, `termin_do` (niz z datumom, časom in pasom). | 200, 403, 404, 409, 422 |
| `POST M/izvedba` | mojster | Zaključi izvedbo. | 200, 403, 404, 409 |
| `GET M/racun` | mojster | Račun projekta (`404` pred sprejemom ponudbe). | 200, 403, 404 |
| `POST M/racun/izdaj` | mojster | Telo `prejemnik_naziv` (1–200), `prejemnik_naslov` (1–300), `zapade_dne`. | 200, 403, 404, 409, 422 |
| `POST M/racun/placilo` | mojster | Evidenca plačila, zaprtje projekta (brez telesa). | 200, 403, 404, 409 |
| `GET /projekti/{id}/ponudbe` | stranka | Poslane ponudbe lastnega projekta (brez osnutkov, brez ID-jev postavk, urne postavke, ur, delavcev in materialov; z izmerami zahtevane ali zadnje različice in `podjetje_naziv`). | 200, 403, 404 |
| `POST /projekti/{id}/ponudbe/{pid}/odlocitev` | stranka | Telo `{sprejmi: bool}`. | 200, 403, 404, 409, 422 |
| `GET /projekti/{id}/racun` | stranka | Račun, samo če je izdan. | 200, 403, 404 |

Drugi odgovori:
- `413` `Zahtevek je prevelik.` za telo nad 256 KB (tudi pri pretočnem prenosu).
- `422` brez odmeva vnosa; seznam napak je okrnjen (lokacija, sporočilo in tip so skrajšani). Neznana polja (`extra='forbid'`), znak NUL in krmilni znaki so zavrnjeni.
- `409` `Dokument je zaklenjen in ga ni mogoče spremeniti.` (SQLSTATE `55000`) pri pisanju v poslano ponudbo ali izdan račun; `409` pri zastoju ali serializaciji; `422` `Vrednost presega dovoljeno mejo.` za razred 22003.
- `401` brez klica Supabase Auth za žeton, ki ni oblike `a.b.c` (znaki `A-Za-z0-9_-`) ali je daljši od 4096 znakov.

### Meje vnosa

Decimalke so samo navadni ASCII nizi (ne števila JSON, ne eksponenti, ne presledki).

| Polje | Meja |
|---|---|
| `cena_na_enoto`, `kolicina` | cena ≥ 0, količina > 0, največ 1 000 000, 4 decimalke (Pydantic in SQL); druge meje v [dokumentu 03](../03-podatkovni-model.md) |
| `popust` | 0 ≤ x < 1 |
| `naziv` / `opis` | 1–200 / do 2000 znakov; enota `m`, `m2`, `m3`, `kos` |
| postavk na projekt | največ 200 (`QFP20`) |
| različic ponudbe na projekt | največ 50 (`QFP23`) |
| `velja_do` | med danes in danes + 366 dni (sicer 422); za pošiljanje obvezen |
| `zapade_dne` | ne pred datumom izdaje (`QFP21`), največ danes + 366 dni (422) |
| termin | začetek ne pred danes (`QFP18`) in največ 366 dni vnaprej, `do > od`, dolžina največ 366 dni (422) |
| prestavitve termina | največ 10 na projekt na dan (`QFP24`) |

»Danes« je povsod datum v časovnem pasu Europe/Ljubljana (funkcija `quoteflow_private.danes()`; tudi leto v številki računa).

### Kode konfliktov (409, `backend/app/errors.py`)

| Koda | Pomen |
|---|---|
| `QFP07` | Dejanje v tej fazi ni dovoljeno (tudi: ponudba že sprejeta, izvedba že zaključena, račun že izdan ali plačan). |
| `QFP09` | Projekt že ima osnutek ponudbe. |
| `QFP10` | Poslana ponudba je zaklenjena; pripravite novo različico. |
| `QFP11` | O ponudbi ni več mogoče odločati (že odločeno ali nadomeščena z novejšo poslano). |
| `QFP12` | Veljavnost ponudbe je potekla (pošiljanje, sprejem; zavrnitev je dovoljena). |
| `QFP13` | Ponudba brez postavk. |
| `QFP14` | Izvedbe ni mogoče zaključiti pred začetkom termina. |
| `QFP15` | Podjetje nima davčne številke; računa ni mogoče izdati. |
| `QFP16` | Neaktivne postavke cenika ni mogoče dodati v projekt. |
| `QFP17` | Podjetje ne posluje (sprejem). |
| `QFP18` | Termin se začne v preteklosti. |
| `QFP20` | Več kot 200 postavk na projekt. |
| `QFP21` | Rok plačila pred datumom izdaje. |
| `QFP22` | Skrbnik si ne more sam dodeliti vloge v podjetju. |
| `QFP23` | Dosežena meja 50 različic. |
| `QFP24` | Termin je bil danes spremenjen prevečkrat. |

`QFP19` ni v uporabi. Kode `QFP25`–`QFP33` (model v3, delavci) so v [model-v3-postavke-izmere.md](model-v3-postavke-izmere.md) in [admin-in-delavci-us-08.md](admin-in-delavci-us-08.md). Spremembe faz: sprejem ponudbe → `termin`; zaključek izvedbe nastavi `izvedba_koncana_ob`; izdaja računa → `obracun`; plačilo → `zakljucen` (`zakljuceno_ob`).

## Baza in varnost

Migracije (uvedene v oddaljeni Supabase 2026-11-08, glej [podatkovni-model.md](podatkovni-model.md)); obstoječih ne urejamo. Tabele, RLS in pravice poslovnih tabel (zdaj 22) ureja [model v3](model-v3-postavke-izmere.md); spodnje migracije so po G1 prepisane na mestu (nikoli uvedene), razen označenega.

| Migracija | Vsebina |
|---|---|
| `20261106200016_celovitost_obseg.sql` | Preverjanje celovitosti in dokumentov omejeno na podjetje/projekt spremenjene vrstice. **M-2:** `dodeli_vlogo`, `aktiviraj_vlogo`, `ustvari_podjetje` in `odloci_prosnjo` zavrnejo skrbnika, ki bi sam sebi dodelil vlogo v podjetju (`QFP22`; zavrnitev lastne prošnje ostane dovoljena). **D9:** `ustvari_projekt` zavrne stranko, ki je klicatelj ali ima aktivno vlogo mojster/delavec pri podjetju (enak odgovor `QFP06`). |
| `20261106200018_ponudba_osnutek.sql` | `ustvari_ponudbo`, `uredi_ponudbo`, `shrani_postavko_projekta`, `dodaj_postavko_iz_cenika`, `odstrani_postavko_projekta`, `shrani_izmero`, `odstrani_izmero`, pomožni `preveri_osnutek`, `preracunaj_izmere` in `danes()`; meje `QFP09`, `QFP16`, `QFP20`, `QFP23`, `QFP25`, `QFP27`–`QFP29`, `velja_do`. |
| `20261106200759_ponudba_odlocitev.sql` | `poslji_ponudbo` (posnetek postavk, izmer, materialov in dela), `odgovori_ponudbo`; revizijska tabela `quoteflow_private.dogodek_dokumenta` (RLS vključen in prisiljen, brez pravic za vloge; vsako uspešno dejanje zapiše vrstico z `izvajalec_id`). Sprejem: sprejeta ponudba + osnutek računa + faza `termin` v eni transakciji. |
| `20261106202500_izvedba.sql` | `doloci_termin` (faza `termin`/`izvedba`, brez zaključka, meje in omejitev 10 prestavitev), `zakljuci_izvedbo`. |
| `20261106202550_racun.sql` | `izdaj_racun` (prejemnik potrjen ob izdaji, posnetek izdajatelja), `placaj_racun`; nova omejitev `racun_izdan_neprazen` (izdan račun ima neprazne podatke izdajatelja in prejemnika). |

Skupna pravila: funkcije so `security definer`, `search_path=''`, `execute` samo za `authenticated`. Vrstni red ključavnic povsod podjetje → projekt → ponudba → račun. Funkcije mojstra najprej pokličejo `preveri_mojstra(podjetje)`, tuj in neobstoječ cilj pa vrneta enak `no_data_found` (404). Stranka ne vidi osnutkov, osnutka računa ali materialnih sestav (seznam stolpcev v API-ju in RLS). Mojster ali delavec podjetja ne more biti stranka lastnega projekta (`odgovori_ponudbo` vrne `404`).

Strežniška utrditev (brez migracije):
- API vrne `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` in `Referrer-Policy: strict-origin-when-cross-origin` pri vsakem odgovoru `/api/*`, tudi pri napakah (`ApiGuard` v `backend/app/main.py`, ki šteje tudi pretočno telo).
- `frontend/nginx.conf`: `client_max_body_size 256k`, `Content-Security-Policy` (`default-src 'self'`, pisave Google, `connect-src` samo `'self'` in `https://*.supabase.co`, `frame-ancestors 'none'`), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`; `server_tokens off`.

### Zasebnost in hramba (L-9, #104)

Izdani računi in poslane ponudbe so nespremenljivi posnetki in se hranijo 10 let (ZDDV-1, ZGD-1; GDPR člen 17(3)(b)). Tuji ključi na uporabnika so `RESTRICT`/`NO ACTION`, zato stranke z računi ni mogoče trdo izbrisati. Postopek anonimizacije je odprt v #104. Naslov prejemnika na računu je kraj izvedbe, razen če ga mojster ob izdaji spremeni.

## Vmesnik

- `features/quotes/` (`api.ts`, `types.ts`, `QuoteEditor`, `CustomerQuote`): osnutek prikaže postavke projekta z vsotami, pošiljanje in sprejem/zavrnitev s potrditvijo; postavke se urejajo v `features/items/` (zavihek Postavke projekta). Wireframa 07 in 08.
- `features/projects/components/ProjectProgress.tsx`: termin in zaključek izvedbe; stranka vidi termin v `MyProjects`. Wireframe 09 (levo).
- `features/invoices/` (`InvoicePanel`, `InvoiceDocument`, `CustomerInvoice`): osnutek, izdaja, plačilo. Wireframe 09 (desno).
- Skupno: `components/ActionAlert.tsx`, `utils/useDetailFocus.ts`, `utils/useTipEscape.ts`.
- Stanja: brez osnutka; osnutek brez postavk (pošiljanje onemogočeno; vsaka postavka mora imeti izmero); osnutek z vsotami; poslana (samo branje, »pripravi novo različico«); zavrnjena/nadomeščena; pri stranki poslana s sprejemom/zavrnitvijo, sprejeta, zavrnjena, nadomeščena ali potekla; račun: osnutek (izdaja onemogočena do konca izvedbe), izdan neplačan, plačan.

## Preverjanje

```sh
cd backend && .venv/bin/python -m pytest -q
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build && npm run test:e2e
```

Lokalni Supabase mora biti zagnan (`supabase start`) z uporabljenimi migracijami (`supabase db reset`). Testi: `backend/tests/test_ponudbe.py`, `test_ponudbe_v3.py`, `test_ponudbe_database.py`, `test_ponudbe_odlocitev*.py`, `test_izvedba_*.py`, `test_racun_database.py`, `test_varnost_api.py`, `test_varnost_database.py`, `test_errors.py`; `frontend/src/tests/quotes*.test.tsx`, `project-items.test.tsx`, `customer-quote.test.tsx`, `invoices*.test.tsx`, `progress.test.tsx`; `frontend/e2e/acceptance.spec.ts`, `a11y-quotes-invoices.spec.ts`.

Števila uspešnih testov in pregledanih posnetkov za ta sklop vpiše CoS po zadnjem polnem zagonu; v tem zapisu niso izmišljena.

## Namenoma ni vključeno

Ekipe (dodelitev delavcev podjetju je zdaj v [US-08](admin-in-delavci-us-08.md)), pošiljanje e-pošte in PDF računa, delna plačila in opomini, popusti na ravni ponudbe, shranjevanje postavke projekta nazaj v cenik, brisanje ali preklic izdanega računa (dobropis), izbira stranke s seznama, anonimizacija osebnih podatkov (#104), AI-pomoč (F16–F20).
