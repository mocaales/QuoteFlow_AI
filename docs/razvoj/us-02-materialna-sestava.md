# US-02: materialna sestava postavke cenika (#35 baza, #36 API, #37 vmesnik)

> **Zgodovinsko (2026-11-07):** model v3 je odstranil `sestava_cenika` in poti `/sestava`; materiali so zdaj na vrsti dela. Glej [model-v3-postavke-izmere.md](model-v3-postavke-izmere.md). Spodnji zapis opisuje uvedeno (5. 11. 2026) stanje.

Veljavna zgodba je US-02 v [uporabniških zgodbah](../05-uporabniske-zgodbe.md). Mojster določi, koliko katerega materiala porabi ena enota postavke cenika.

## Obseg

Sestava povezuje postavko cenika in material istega podjetja s količino na enoto. Mojster sestavo bere, dodaja ali spreminja ter odstranjuje. Zaloga ostane ločena od postavke (po materialu in lokaciji).

## API

Poti imajo predpono `/api`; vse zahtevajo aktivno sejo in vlogo `mojster` pri podjetju.

| Metoda in pot | Namen | Kode |
|---|---|---|
| `GET /podjetja/{id}/cenik/{item_id}/sestava` | Sestava postavke z materiali (šifra, naziv, enota, aktiven, količina na enoto). | 200, 403, 404 |
| `PUT /podjetja/{id}/cenik/{item_id}/sestava/{material_id}` | Doda ali spremeni količino (`shrani_sestavo`). Telo `{"kolicina_na_enoto": "2.5"}`. | 200, 403, 404, 409, 422 |
| `DELETE /podjetja/{id}/cenik/{item_id}/sestava/{material_id}` | Odstrani material iz sestave (`odstrani_sestavo`). | 204, 403, 404 |

- `409` (`QFP05`): material ni aktiven.
- `404`: postavka ali material ne pripada podjetju; `GET` vrne `404` tudi za postavko drugega podjetja.
- `422`: količina ni pozitivna ali telo ni veljavno; znak NUL v besedilnih poljih daje `422`. Količine potujejo kot nizi; `kolicina_na_enoto` sprejme le navadno decimalno število (do 14 mest in 4 decimalke). Besedilni vnosi zavrnejo krmilne in oblikovne znake Unicode razen tabulatorja, preloma vrstice in pomika na začetek vrstice (CR), validacijske napake pa se vračajo brez odmeva vnosa (`backend/app/errors.py`).
- Migracija `20261105140047` je uvedena v Supabase 5. 11. 2026.

## Baza in varnost

Migracija `20261105140047_materialna_sestava.sql` doda funkciji `quoteflow_private.shrani_sestavo` in `odstrani_sestavo` (`security definer`, `search_path=''`). Začneta s `preveri_mojstra`, zaklenita postavko (`for share`) in preverita, da material pripada istemu podjetju; aktivnost materiala je zaklenjena do konca transakcije, da ga ni mogoče deaktivirati med preverjanjem in vpisom. Izvajanje je dovoljeno samo vlogi `authenticated`. Koda `QFP05` je dodana v `backend/app/errors.py`.

## Vmesnik

V razdelku **Cenik** panel **Materialna sestava** (`features/supplier/components/CompositionPanel.tsx`). Količine so prikazane v slovenski obliki zapisa.

## Preverjanje

V mapi `backend/`:

```sh
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_sestava.py tests/test_projekti_database.py -q
```

V mapi `frontend/`:

```sh
npm test
npm run build
npm run test:e2e
```

Testi: `backend/tests/test_sestava.py`, `backend/tests/test_projekti_database.py` (zgoraj naveden zaradi skupne priprave), `frontend/src/tests/sestava.test.tsx`, `frontend/e2e/design.spec.ts`. Rezultati skupnega zagona ob zaključku sklopa (US-02 in US-03) in izid varnostnega pregleda so v [US-03](us-03-projekti.md).

## Namenoma ni vključeno

Izračun cene ali porabe iz sestave, odpis zaloge, različice sestave in sestava na ravni projekta ali ponudbe.
