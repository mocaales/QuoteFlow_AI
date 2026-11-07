> **Nadomeščeno.** Končni zapis je [us-04-us-07-ponudbe-in-racuni.md](us-04-us-07-ponudbe-in-racuni.md). Ta delovni načrt (G1, 2026-11-06) se ohrani kot zgodovina odločitev; po G1 so veljavne spremembe: prejemnik računa potrdi mojster ob izdaji (M-1, `QFP19` odstranjen, brez nadomestne e-pošte), potrditveni koraki, meje (`velja_do`, `zapade_dne`, termin 366 dni, 50 različic `QFP23`, 10 prestavitev `QFP24`), M-2 (`QFP22` tudi za `aktiviraj_vlogo`, `ustvari_podjetje`, `odloci_prosnjo`), utrditev API-ja in nginx ter revizijska tabela.

# Načrt US-04–US-07 (G1 potrjen 2026-11-06)

Working design for issues #41–#51, approved by the user on 2026-11-06. Binding for all teams in this run. Docs team turns it into the ADR "Življenjski cikel ponudbe in računa" and story notes at G7.

## User decisions
- D1 Numbering: per company, automatic, with year: quote `P-2026-001`, invoice `R-2026-001` (sequence per company per year, `lpad(n,3,'0')`, computed under the podjetje lock). All versions of a quote keep the quote number.
- D2 New version copies the latest version's lines and material_ponudbe snapshots.
- D3 Termin may be rescheduled while faza in (termin, izvedba) and izvedba_koncana_ob is null.
- D4 Invoice recipient: name = customer `ime||' '||priimek`; address = `projekt.lokacija_izvedbe` (empty → QFP19). Client sends only `zapade_dne`.
- D5 zakljuci_izvedbo before termin_od → QFP14.
- D6 Company without davcna_stevilka cannot issue → QFP15. No model change.
- D7 UI default zapade_dne = today + 8 days.
- D8 BLOCK admin self-assigning a company role: replaced `dodeli_vlogo` rejects target = auth.uid() for mojster/delavec (QFP22 'Skrbnik si ne more sam dodeliti vloge v podjetju.').
- D9 BLOCK mojster as own customer: replaced `ustvari_projekt` rejects a customer who is auth.uid() or holds an active mojster/delavec role at that company (uniform QFP06 response); `odgovori_ponudbo` rejects a caller with an active mojster/delavec role at the project's company (no_data_found).
- D10 Termin: start not before today (QFP18), finite, `do > od`, length ≤ 366 days (422).
- D11 Line bounds: cena_na_enoto and kolicina ≤ 1 000 000 (Pydantic and SQL), popust 0 ≤ x < 1, max 200 lines per quote (QFP20).

## Lock order and function pattern
- Order everywhere: podjetje → projekt → ponudba → racun. (`a_zakleni_podjetje` trigger locks podjetje on every write — functions must lock podjetje first.)
- Master functions `(podjetje uuid, target uuid, …)`: `preveri_mojstra(podjetje)` first, then look up target filtered by company (missing and foreign → same no_data_found), then lock.
- Customer `odgovori_ponudbo(projekt, ponudba, sprejmi)`: check stranka() + stranka_id = auth.uid() + quote belongs to project (else no_data_found), D9 check, lock podjetje (inactive → QFP17), then projekt, ponudba.
- Every function inserts one row into `quoteflow_private.dogodek_dokumenta` (audit) per action, in the same transaction.
- Every migration: header comment, `security definer set search_path=''`, revoke from public/anon/service_role/quoteflow_app, grant execute to authenticated. No table/RLS/grant change on the 17 tables.

## Migrations (new; never edit applied ones)
0. `celovitost_obseg` — create or replace `preveri_celovitost()` / `preveri_dokumente()` scoped to the changed row's company/project (same semantics, no full-table scans). Plus D8 (`dodeli_vlogo`) and D9 (`ustvari_projekt`) replacements.
1. `ponudba_osnutek` (#41): `ustvari_ponudbo(podjetje, projekt, velja_do date)` (faza pregled/ogled/ponudba else QFP07; existing sprejeta → QFP07; existing osnutek → QFP09; v1 new number, vN+1 copies number + lines + snapshots, razlicica=max+1); `uredi_ponudbo(podjetje, ponudba, velja_do)`; `dodaj_postavko_cenika(podjetje, ponudba, postavka_cenika, kolicina, popust)` (same-company active item, for share; inactive → QFP16; copies naziv/opis/vrsta_dela/enota/cena/ddv and material_ponudbe from sestava_cenika with current material naziv/enota/cena; zaporedje=max+1); `shrani_postavko(podjetje, ponudba, postavka|null, naziv, opis, vrsta_dela, enota, cena, kolicina, popust, stopnja_ddv)` (edit keeps postavka_cenika_id and snapshot); `odstrani_postavko(podjetje, ponudba, postavka)`; helper `preveri_osnutek` (not granted; not osnutek → QFP10). 201st line → QFP20; cena/kolicina > 1e6 → numeric_value_out_of_range.
2. `ponudba_odlocitev` (#44): audit table `quoteflow_private.dogodek_dokumenta(id, podjetje_id, projekt_id, ponudba_id, racun_id, dejanje check in (poslana, sprejeta, zavrnjena, termin, izvedba_koncana, izdan, placan), izvajalec_id not null, ob default now())`, RLS enabled+forced, no grants. Drop + recreate `poslji_ponudbo(podjetje, ponudba)` (not osnutek QFP10; 0 lines QFP13; velja_do < today QFP12; project has sprejeta QFP07) and `odgovori_ponudbo(projekt, ponudba, sprejmi)` (not poslana or superseded by newer sent version QFP11; expired QFP12; inactive company QFP17). Accept: sprejeta + račun osnutek + faza termin in one transaction.
3. `izvedba` (#46): drop + recreate `doloci_termin(podjetje, projekt, od, do)` (D3, D10; wrong phase QFP07); `zakljuci_izvedbo(podjetje, projekt)` (faza izvedba, not yet set else QFP07; now() < termin_od QFP14).
4. `racun` (#49): drop + recreate `izdaj_racun(podjetje, projekt, zapade date)` (faza izvedba + izvedba_koncana_ob else QFP07; QFP15; QFP19; zapade < today QFP21; number R-YYYY-NNN; issuer from podjetje; izdan_ob=poslan_ob=now(); faza obracun) and `placaj_racun(podjetje, projekt)` (izdan & unpaid else QFP07; placano_ob, faza zakljucen, zakljuceno_ob).
qa updates `backend/tests/test_model_database.py` to the new signatures.

## Errors (`backend/app/errors.py`)
- 55000 → 409 'Dokument je zaklenjen in ga ni mogoče spremeniti.'; 22003/DataError → 422 'Vrednost presega dovoljeno mejo.'; 40P01/40001 → 409 'Sočasna sprememba. Osvežite podatke in poskusite znova.'
- QFP09 'Projekt že ima osnutek ponudbe.' · QFP10 'Poslana ponudba je zaklenjena. Za popravek pripravite novo različico.' · QFP11 'O tej ponudbi ni več mogoče odločati.' · QFP12 'Veljavnost ponudbe je potekla.' · QFP13 'Ponudba mora imeti vsaj eno postavko.' · QFP14 'Izvedbe ni mogoče zaključiti pred začetkom termina.' · QFP15 'Podjetje nima davčne številke. Dopolnite podatke podjetja pred izdajo računa.' · QFP16 'Neaktivne postavke cenika ni mogoče dodati v ponudbo.' · QFP17 'Izvajalec trenutno ne posluje.' · QFP18 'Termin se ne sme začeti v preteklosti.' · QFP19 'Za izdajo računa vnesite lokacijo izvedbe projekta.' · QFP20 'Ponudba ima lahko največ 200 postavk.' · QFP21 'Rok plačila ne sme biti pred datumom izdaje.' · QFP22 'Skrbnik si ne more sam dodeliti vloge v podjetju.' · QFP07 reused for phase errors.

## API
Master, guard `company_member('mojster')`, prefix `M=/podjetja/{company_id}/projekti/{projekt_id}`, every query filtered by company_id, read back after write:
- GET `M/ponudbe` → [PonudbaPovzetek]; POST `M/ponudbe` {velja_do?} → 201 PonudbaMojster; GET/PUT `M/ponudbe/{id}` ({velja_do}); POST `M/ponudbe/{id}/postavke/iz-cenika` {postavka_cenika_id, kolicina, popust} → 201; POST `M/ponudbe/{id}/postavke` PostavkaInput → 201; PUT/DELETE `M/ponudbe/{id}/postavke/{pid}` (DELETE 204); POST `M/ponudbe/{id}/poslji`.
- PUT `M/termin` {termin_od, termin_do} → MasterProject (422 'Konec termina mora biti po začetku.'); POST `M/izvedba` → MasterProject.
- GET `M/racun` (404 before acceptance); POST `M/racun/izdaj` {zapade_dne}; POST `M/racun/placilo` (no body).
Customer, guard `customer`, filtered by stranka_id = user.id:
- GET `/projekti/{id}/ponudbe` → [PonudbaStranka] (no osnutek); POST `/projekti/{id}/ponudbe/{pid}/odlocitev` {sprejmi}; GET `/projekti/{id}/racun` (404 unless izdan).
Models: PostavkaInput (naziv 1–200, opis ≤2000, vrsta_dela 1–100, enota 1–30, cena_na_enoto/kolicina >0 ≤1e6 4dp, popust 0≤x<1, stopnja_ddv TaxRate); PonudbaPovzetek (id, stevilka, razlicica, stanje, poslano_ob, odgovorjeno_ob, velja_do, nadomescena, neto, ddv, skupaj); PonudbaMojster (+postavke[] with ids, postavka_cenika_id, money fields, materiali[] {material_id, naziv, enota, kolicina_na_enoto, cena_na_enoto, kolicina_skupaj}, ddv_po_stopnjah[]); PonudbaStranka (whitelist: no ids on lines, no postavka_cenika_id, no materiali; + podjetje_naziv); RacunMojster/RacunStranka (stevilka, stanji, izdajatelj_*, prejemnik_*, izdan_ob, poslan_ob, zapade_dne, placano_ob, ponudba {stevilka, razlicica}, lines, totals). MasterProject/OwnProject gain izvedba_koncana_ob, zakljuceno_ob. Extra fields → 422 (extra='forbid'). Money/quantities as strings.

## Calculation (docs/03)
Per line: `neto = round(kolicina × cena × (1 − popust), 2)`, `ddv = koncna_cena − neto`, `koncna_cena` generated column. Totals = sums of rounded lines. Computed in SQL only; Python serialises Decimal. 2 × 100, 10 %, 22 % → 180.00 / 39.60 / 219.60.

## Frontend
- `features/quotes/` (api.ts, types.ts, QuoteEditor, CatalogPicker, LineForm side panel, CustomerQuote) — wireframes 07, 08.
- `features/projects/components/ProjectProgress.tsx` (termin, izvedba) — wireframe 09 left; customer sees termin in MyProjects.
- `features/invoices/` (InvoicePanel, CustomerInvoice) — wireframe 09 right.
- States: no draft; draft 0 lines (send disabled); draft with totals; sent read-only + "pripravi novo različico"; rejected/superseded; customer: sent with accept/reject + confirm, accepted, rejected, superseded/expired; invoice osnutek (issue disabled until izvedba done), issued unpaid, paid/closed.

## Test invariants
1 customer never sees drafts/materials/osnutek invoice (API key-set + RLS) · 2 write to sent → 409 never 503 · 3 snapshot unchanged after cenik/material change · 4 accept → exactly 1 račun osnutek + faza termin; second/superseded/expired → QFP11/12; wrong actor → 404/403 · 5 company A in path vs B project → same 404 as random UUID; test_access covers all routes · 6 termin without acceptance QFP07; do ≤ od 422 · 7 issue before izvedba QFP07; pay osnutek/twice QFP07 · 8 R-YYYY-NNN unique, consecutive under concurrency; QFP15 · 9 no deadlock send vs accept · 10 audit row per action with izvajalec_id · 11 inactive company accept QFP17 · 12 bounds and QFP20 · 13 termin past QFP18, infinity 422, reschedule after finish QFP07 · 14 scoped triggers still reject cross-company rows · 15 D8 admin self-assign → QFP22 · 16 D9 mojster as own customer rejected.
