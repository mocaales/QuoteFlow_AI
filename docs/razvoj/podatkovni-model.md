# Uvedba novega podatkovnega modela

**Uvedeno v Supabase 2026-11-04.** [Primarni model in diagram](../03-podatkovni-model.md) · [ADR-0010](../adr/0010-projekti-podjetja-in-vec-vlog.md).

## Baza in ohranjeni podatki

Migracija `20261103211654_v2_projects_roles_catalog.sql` je uvedla 17 tabel s prisilnim RLS. Ohranila je tri prijavne identitete Supabase Auth in obstoječo administratorsko dodelitev kot `admin`. Potrjeni računi dobijo globalno vlogo `stranka`; `mojster/delavec` veljata samo pri določenem podjetju.

Migracija `20261105114405_prosnja_varnost.sql` je bila v Supabase uvedena 5. 11. 2026. Omeji uporabnika na eno oddano prošnjo za mojstra, ob odobritvi ponovno preveri vlagatelja in matično številko ter uvede kode SQLSTATE `QFP01`–`QFP04` za pričakovane konflikte. Pred uvedbo je preverjanje pokazalo, da v bazi ni podvojenih oddanih prošenj.

Dve stari podjetji in preostali stari poslovni podatki so v omejenem arhivu `quoteflow_legacy_20261103`, stare interne funkcije v `quoteflow_private_legacy_20261103`. Aplikacijske vloge do arhiva nimajo dostopa. Nova podjetja se niso ugibala iz starih podatkov: ustvarijo se z izrecnim lastnikom in registracijskimi podatki. Pred uvedbo je nastala lokalna varnostna kopija, izključena iz Gita.

## Izvedeno in naslednji sklop

API in vmesnik uporabljata nove vloge, podjetja z lastnikom, cenik storitev, vrste materiala, materiale in zalogo po lokacijah. Poslovni zahtevki preverijo Supabase Auth, aktivno sejo, trenutno vlogo in podjetje; neposredni zapisi aplikacijske vloge v tabele niso dovoljeni.

Baza vsebuje povezave, omejitve in transakcijske postopke za prošnje mojstrov, projekte, ekipe, različice ponudb in račune. Prek API/vmesnika je uvedena le prošnja mojstra ([zapis](us-01-prosnja-mojstra.md)); preostali uporabniški postopki (projekti, ekipe, ponudbe, računi) še niso uvedeni. Samodejno pošiljanje e-pošte in AI-pomoč še nista uvedena. [Obseg](../02-funkcionalnosti-in-obseg.md), [uporabniške zgodbe](../05-uporabniske-zgodbe.md) in [wireframi](../06-wireframes.md) so usklajeni z novim načrtom: 22 predvidenih funkcionalnosti (7 MVP) in 5 možnih nadgradenj. AI F16–F20 sledi po MVP; e-pošta, priloge, opombe in del nadaljnjih funkcionalnosti potrebujejo razširitve modela oziroma shrambe.

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

Podatkovni testi zahtevajo namenski lokalni Supabase prek `TEST_DATABASE_URL`; preverjanje prijavnega toka tudi `TEST_AUTH_FLOW_URL`. Brez teh nastavitev pytest pripadajoče teste preskoči. Ne usmerjajte testov s poskusnimi zapisi v produkcijo.

Regresija nadgradnje z že napolnjeno staro shemo uporablja PostgreSQL na `127.0.0.1:54322`, ustvari začasno testno bazo in jo po preverjanju odstrani:

```sh
backend/.venv/bin/python supabase/tests/v1_to_v2_upgrade.py
```
