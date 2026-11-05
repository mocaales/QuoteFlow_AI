# US-03–US-05: podatki ponudnika

> **Zgodovinski razvojni zapis:** novi primarni model in stanje uvedbe sta v [podatkovni-model.md](podatkovni-model.md). Opisi starih vlog, RFQ, cenika in pravil spodaj ne določajo nove sheme. Oznake US spodaj ohranijo stari pomen; veljavna sta novi [obseg](../02-funkcionalnosti-in-obseg.md) in [uporabniške zgodbe](../05-uporabniske-zgodbe.md).


## Obseg in uporaba

Uporabnik v glavi izbere aktivno podjetje. Ponudnik pri tem podjetju dobi poglede **Cenik**, **Zaloge** in **Prodajna pravila**. Administrator brez poslovne vloge ponudnika do internih podatkov nima dostopa.

- **US-03:** dodajanje in urejanje blaga ali storitev, izrecna potrditev ter deaktivacija. Vsako shranjevanje popravka razveljavi potrditev; postavko je treba znova pregledati. Deaktivacija ohrani zapis in povezave. Denarni vnosi podpirajo štiri decimalna mesta.
- **US-04:** vnos in potrditev nenegativne zaloge samo za aktivno blago. Količina `0` pomeni prazno zalogo, odsotnost zapisa pa pomeni, da se zaloga ne vodi. Podatek je mogoče odstraniti. Sprememba enote ali vrste cenika odstrani njegovo zalogo, ker prejšnja količina nima več istega pomena. Zaloga ni rezervacija; preverjanje zadostnosti ob pripravi ponudbe sledi v US-10.
- **US-05:** nove različice pravil z najmanjšo maržo, največjim popustom, najdaljšim rokom in obdobjem veljavnosti. Odstotki se v bazo pošljejo kot šestmestni decimalni deleži. Prazen začetek pomeni takojšnjo veljavnost. Nova različica zaključi predhodno ob svojem začetku; že načrtovane različice ni dovoljeno prekriti. Retroaktivne spremembe niso dovoljene. Pretekle vrednosti ostanejo shranjene.

Iskanje in filtri delujejo znotraj izbranega cenika. Menjava podjetja zapre predhodni pogled; njegovi podatki se ne prenesejo v novo podjetje. Časi se shranjujejo s časovnim pasom, prikazujejo pa v lokalnem času brskalnika.

## API

Vse poti imajo predpono `/api/podjetja/{company_id}` in zahtevajo aktivno sejo ter aktivno vlogo `ponudnik` pri aktivnem podjetju.

| Metoda in pot | Namen |
|---|---|
| `GET /cenik` | Cenik z neobveznim podatkom o zalogi. |
| `POST /cenik` | Nova nepotrjena postavka. |
| `PUT /cenik/{item_id}` | Popravek ali deaktivacija; razveljavi potrditev. |
| `POST /cenik/{item_id}/potrditev` | Izrecna potrditev aktivne postavke. |
| `PUT /cenik/{item_id}/zaloga` | Zapis količine in časa potrditve. |
| `DELETE /cenik/{item_id}/zaloga` | Prenehanje vodenja zaloge. |
| `GET /pravila` | Zgodovina različic pravil. |
| `POST /pravila` | Atomska uvedba nove različice. |

Tuja postavka pod dovoljenim podjetjem vrne `404`, nedovoljen dostop do podjetja `403`, neveljaven vnos `422`, prekrivanje načrtovanih pravil pa `409`.

## Baza in varnost

Migracija `20261029195006_supplier_catalog_stock_rules.sql` dodaja samo omejene pisalne funkcije v `quoteflow_private`. Ne briše podatkov, ne dodaja entitet in ne spreminja dokumentiranega modela. `authenticated` nima neposrednih pisalnih pravic na tabelah. Funkcije preverijo sejo in vlogo ter zaklenejo podjetje in dodelitev do zaključka transakcije. RLS ostane dodatna meja pri branju.

Obstoječa odobrena ponudba hrani lastne vrednosti postavk; sprememba cenika jih ne spreminja. RFQ, AI, priprava in odobritev ponudb niso del tega sklopa.

## Preverjanje

V mapi `backend/`:

```sh
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_identity_database.py tests/test_supplier_database.py -q
```

Drugi ukaz zahteva izoliran lokalni Supabase z uvedenimi migracijami. Testi uporabljajo transakcije, ki se razveljavijo; oddaljeni projekt ni cilj testnih zapisov.

V mapi `frontend/`:

```sh
npm test
npm run build
```

Testi pokrivajo potrditev in razveljavitev, decimalne vnose, storitve brez zaloge, neznano in ničelno zalogo, odvzem pravic, tuje identifikatorje, veljavnost pravil ter menjavo podjetja. Obstoječi testi ohranijo preverjanje identitete in zaklepa odobrene ponudbe.
