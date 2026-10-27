# US-01–US-02: identiteta in pravice

Registracija, prijava in odjava uporabljajo Supabase Auth. Frontend hrani sejo v `sessionStorage`, API pa pri vsakem poslovnem zahtevku preveri žeton pri Auth ter aktivnost pripadajoče seje v bazi. Po odjavi stari žeton ne omogoča poslovnega dostopa. Vloge iz uporabniških metapodatkov se ne upoštevajo.

Poslovne vloge so v `quoteflow.vloga_uporabnika`. Nabavnik in ponudnik potrebujeta podjetje; administrator je globalen. Odvzem vloge ali deaktivacija podjetja učinkuje na naslednji zahtevek. Administratorska vloga sama ne omogoča vpogleda v interne kalkulacije ali odobritve ponudb.

| API | Dostop |
|---|---|
| `GET /api/config` | Samo javni URL in javni prijavni ključ. |
| `GET /api/me` | Prijavljen uporabnik in njegove trenutne aktivne vloge. |
| `GET /api/podjetja`, `GET /api/podjetja/{id}` | Lastna aktivna podjetja; administrator vidi vsa. |
| `GET /api/admin/uporabniki`, `GET /api/admin/vloge` | Administrator. |
| `POST /api/admin/podjetja`, `PUT /api/admin/podjetja/{id}` | Administrator; ustvarjanje, urejanje in deaktivacija. |
| `POST /api/admin/vloge`, `PATCH /api/admin/vloge/{id}` | Administrator; poslovne vloge in aktivnost dodelitev. |

Registracija ne dodeli poslovnih vlog. Globalnega administratorja je mogoče določiti samo z ločenim skrbniškim postopkom za že registriran račun s potrjeno e-pošto.

## Migracije

Edini vir sprememb sheme je `supabase/migrations/`. Model iz [dokumenta 03](../03-podatkovni-model.md) je uveden z migracijo `20261027161706_identity_and_permissions.sql`. Ta izrecno izbriše staro poslovno shemo, ohrani `auth.users` in zgradi deset dokumentiranih tabel. Pred uvedbo na drugem projektu najprej varnostno kopirajte staro poslovno shemo.

Prejšnje migracije ostajajo kot zgodovina; končno stanje po vseh migracijah ne vsebuje starega poslovnega modela. Že uvedenih migracij ne spreminjajte. Nova opravila dodajajte z `supabase migration new <ime>`. Običajni Dockerjev zagon migracij ne izvaja in ne prejme skrbniške povezave.

## Testi

Naslednje ukaze izvedite v mapi `backend/` z nameščenimi razvojnimi odvisnostmi. Običajni testi API-ja in poslovne logike:

```sh
.venv/bin/python -m pytest -q
```

Preverjanje obstoječe oddaljene aplikacijske povezave brez trajnih zapisov:

```sh
RUN_DATABASE_TESTS=1 .venv/bin/python -m pytest -q
```

Testi sheme, RLS in administratorskega API-ja uporabljajo samo ločen lokalni Supabase. Testni podatki se razveljavijo v transakciji:

```sh
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  .venv/bin/python -m pytest tests/test_identity_database.py -q
```

Za HTTP-preizkus dejanske registracije, prijave, odjave in administratorskega toka uporabite lokalni Supabase in aplikacijo, povezano nanj:

```sh
TEST_AUTH_FLOW_URL=http://127.0.0.1:8001 \
  .venv/bin/python -m pytest tests/test_auth_flow.py -q
```

Ta test preveri lokalni izvor, prebere podatke iz `supabase status`, ustvari samo lokalne testne račune in jih po preizkusu odstrani. Ne uporablja oddaljenega projekta. Pri Dockerjevem testnem backendu lahko `SUPABASE_INTERNAL_URL` nastavi notranji naslov istega Auth strežnika; javni `SUPABASE_URL` mora ostati dosegljiv brskalniku.

Gradnja in testi v mapi `frontend/`:

```sh
npm ci
npm test
npm run build
```
