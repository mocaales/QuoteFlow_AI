# Uvedba novega podatkovnega modela

**Uvedeno v Supabase 2026-11-04 (17 tabel); model v3 z 22 tabelami uvedeno 2026-11-08.** [Primarni model in diagram](../03-podatkovni-model.md) · [ADR-0010](../adr/0010-projekti-podjetja-in-vec-vlog.md).

## Baza in ohranjeni podatki

Migracija `20261103211654_v2_projects_roles_catalog.sql` je uvedla prvotnih 17 tabel s prisilnim RLS. Ohranila je tri prijavne identitete Supabase Auth in obstoječo administratorsko dodelitev kot `admin`. Potrjeni računi dobijo globalno vlogo `stranka`; `mojster/delavec` veljata samo pri določenem podjetju.

Migracija `20261105114405_prosnja_varnost.sql` je bila v Supabase uvedena 5. 11. 2026. Omeji uporabnika na eno oddano prošnjo za mojstra, ob odobritvi ponovno preveri vlagatelja in matično številko ter uvede kode SQLSTATE `QFP01`–`QFP04` za pričakovane konflikte. Pred uvedbo je preverjanje pokazalo, da v bazi ni podvojenih oddanih prošenj.

Migraciji `20261105140047_materialna_sestava.sql` ([US-02](us-02-materialna-sestava.md)) in `20261105140049_projekti.sql` ([US-03](us-03-projekti.md)) sta uvedeni v Supabase 5. 11. 2026.

Po G1 (2026-11-07) so tri od njih prepisane na mestu za model v3 (nikoli niso bile uvedene). Pet migracij za ponudbe, izvedbo in račune ([US-04–US-07](us-04-us-07-ponudbe-in-racuni.md)) je **uvedenih v oddaljeni Supabase 2026-11-08** skupaj z migracijami model v3 in US-08: `20261106200016_celovitost_obseg.sql`, `20261106200018_ponudba_osnutek.sql`, `20261106200759_ponudba_odlocitev.sql`, `20261106202500_izvedba.sql`, `20261106202550_racun.sql`. Dodajo revizijsko tabelo `quoteflow_private.dogodek_dokumenta`, omejitev `racun_izdan_neprazen` in nove funkcije. Preverjanje: testi baze v `backend/tests/test_*_database.py` z `TEST_DATABASE_URL`.

### Model v3 in US-08 (uvedeno 2026-11-08)

Migracije v tej tabeli so **uporabljene samo v lokalnem Supabase, v oddaljeni projekt niso uvedene** (potrebni so pregled, poskusni zagon in odobritev uporabnika; uvedba ne sme urejati že uvedenih migracij):

| Migracija | Vsebina | Zapis |
|---|---|---|
| `20261106100000_model_v3_postavke_izmere.sql` | 17 → 22 tabel: `vrsta_dela`, `material_vrste_dela`, `postavka_projekta`, `izmera`, `izmera_ponudbe`, `delo_ponudbe`; odstranitev `sestava_cenika`; pretvorba cenika, ki se ob neznani enoti ustavi. Razvrščena za `20261105140049` in pred lokalnimi migracijami ponudb. | [model-v3-postavke-izmere.md](model-v3-postavke-izmere.md) |
| `20261106210000_delavci_in_pravice.sql` | `dodeljeno_ob`, zasebne tabele `dogodek_vloge`, `poskus_delavca` in `povabilo_delavca`, funkcije povabil (`povabi_delavca`, `povabila_podjetja`, `preklici_povabilo`, `moja_povabila`, `odgovori_povabilo`), `uredi_delavca`; `dodeli_vlogo` in `aktiviraj_vlogo` samo za admina; CHECK na `postavka_cenika` (`QFP30`, `QFP33`, `QFP34`). `dodaj_delavca` odstranjena. | [admin-in-delavci-us-08.md](admin-in-delavci-us-08.md) |
| `20261106220000_indeksi_v3.sql` | Indeks na `vloga_uporabnika(uporabnik_id)`. | isto |
| `20261107212046_aktivna_seja_uuid.sql` | `aktivna_seja()` uporablja ključ `auth.sessions` (cast v `uuid` le pri veljavni obliki). | isto |
| `20261107220000_celovitost_oznaka.sql` | Oznaka preverjene celovitosti v zasebni tabeli `preverjeno_podjetje` namesto GUC. | isto |
| `20261107221442_brisanje_racuna_dogodki.sql` | Tuji ključi uporabnika v `dogodek_vloge` in `povabilo_delavca` na `ON DELETE SET NULL`; račun je izbrisljiv, razen stranke s projekti in lastnika (#104). Test: `supabase/tests/brisanje_racuna.sql`. | isto |

Pogodba pripravljenosti (`EXPECTED_TABLES` v `backend/app/database.py`) zahteva 22 tabel; `/api/ready` na oddaljeni bazi vrne `ok`.

Uvedba 2026-11-08: 11 migracij `20261106100000_model_v3_postavke_izmere.sql` … `20261107221442_brisanje_racuna_dogodki.sql` z `supabase db push --db-url` (`DATABASE_MIGRATION_URL`) po bralnem pregledu (1 postavka cenika, enota m² → m2, brez vrstic ponudb) in poskusnem zagonu. Varnostna kopija: zasebni `.local/backups/before-v3-20261107T231854Z.dump` (gitignore). Preverjeno: zgodovina se konča pri 20261107221442; 22 tabel `quoteflow`; vsiljen RLS na vseh tabelah `quoteflow` in `quoteflow_private`; `anon` brez pravic; `authenticated` samo SELECT; nobena funkcija `quoteflow_private` ni izvedljiva za PUBLIC; cenik pretvorjen, `sestava_cenika` odstranjena; izpostavljeni sheme API samo `public` in `graphql_public`; potrditev e-pošte in »Secure email change« vključena. `/api/health`, `/api/ready` in frontend delujejo, 2 živa preverjanja (`RUN_DATABASE_TESTS`) uspešna. Migraciji ponudb (`…200016`, `…200018`, `…200759`) sta prepisani za model v3, `…202500` in `…202550` ostaneta.

Dve stari podjetji in preostali stari poslovni podatki so v omejenem arhivu `quoteflow_legacy_20261103`, stare interne funkcije v `quoteflow_private_legacy_20261103`. Aplikacijske vloge do arhiva nimajo dostopa. Nova podjetja se niso ugibala iz starih podatkov: ustvarijo se z izrecnim lastnikom in registracijskimi podatki. Pred uvedbo je nastala lokalna varnostna kopija, izključena iz Gita.

## Izvedeno in naslednji sklop

API in vmesnik uporabljata nove vloge, podjetja z lastnikom, cenik storitev, vrste materiala, materiale in zalogo po lokacijah. Poslovni zahtevki preverijo Supabase Auth, aktivno sejo, trenutno vlogo in podjetje; neposredni zapisi aplikacijske vloge v tabele niso dovoljeni.

Baza vsebuje povezave, omejitve in transakcijske postopke za prošnje mojstrov, projekte, postavke z izmerami, vrste dela, ekipe, različice ponudb in račune. Prek API/vmesnika so uvedeni prošnja mojstra ([zapis](us-01-prosnja-mojstra.md)), materialna sestava postavk ([US-02](us-02-materialna-sestava.md)) ter začetek projekta (ustvarjanje, urejanje, zahteva ogleda, pogled stranke; [US-03](us-03-projekti.md)); po US-04–US-07 so prek API/vmesnika uvedeni še ponudbe, odločitev stranke, termin, izvedba in račun (lokalno), z modelom v3 pa vrste dela, postavke projekta z izmerami ter US-08 (delavci podjetja, skrbniški pregled vlog); ekipe še niso uvedene. Samodejno pošiljanje e-pošte in AI-pomoč še nista uvedena. [Obseg](../02-funkcionalnosti-in-obseg.md), [uporabniške zgodbe](../05-uporabniske-zgodbe.md) in [wireframi](../06-wireframes.md) so usklajeni z novim načrtom: 22 predvidenih funkcionalnosti (7 MVP) in 5 možnih nadgradenj. AI F16–F20 sledi po MVP; e-pošta, priloge, opombe in del nadaljnjih funkcionalnosti potrebujejo razširitve modela oziroma shrambe.

Razvojna zapisa US-01–US-02 in US-03–US-05 opisujeta prejšnji obseg. Obstoječe GitHub naloge prav tako ohranijo prvotni pomen; s prenovo dokumentacije niso bile preštevilčene ali zaprte. Njihova uskladitev je ločen korak.

## Prvi administrator

`scripts/bootstrap_admin.py` izrecno dodeli globalno vlogo `admin` že registriranemu računu s potrjeno e-pošto. Uporablja lokalni `DATABASE_MIGRATION_URL`; ob zagonu aplikacije se ne izvaja. Navodila z ukazom so v lokalni datoteki `docs/razvoj/prvi-administrator.local.md`, ki je izključena iz Gita. Obstoječi administrator je bil ohranjen, zato ponovna dodelitev ni potrebna.

## Preverjanje

Iz korena repozitorija:

```sh
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Podatkovni testi zahtevajo namenski lokalni Supabase prek `TEST_DATABASE_URL`; preverjanje prijavnega toka tudi `TEST_AUTH_FLOW_URL`. Lokalni Supabase (`supabase start`) po `supabase/config.toml` zažene samo db, auth, rest, kong in inbucket. Brez teh nastavitev pytest pripadajoče teste preskoči. Ne usmerjajte testov s poskusnimi zapisi v produkcijo.

Regresija nadgradnje z že napolnjeno staro shemo uporablja PostgreSQL na `127.0.0.1:54322`, ustvari začasno testno bazo in jo po preverjanju odstrani:

```sh
backend/.venv/bin/python supabase/tests/v1_to_v2_upgrade.py
```
