# Organizacija frontenda

Koda v `frontend/src/` je razdeljena po odgovornostih:

| Mapa | Odgovornost |
|---|---|
| `app/` | Sestava aplikacije, izbira poti in globalni slogi. |
| `pages/` | Pogleda delovnega prostora in demonstracije; povezujeta funkcionalnosti v stran. |
| `features/identity/` | Prijava, registracija, stanje seje, profil in tipi identitete, podjetij ter dodelitev pravic. |
| `features/administration/` | Administratorski obrazci ter API-klici za podjetja in poslovne vloge. |
| `features/calculator/` | API-klici in tipi demonstracijskega kalkulatorja. Izračun izvaja backend. |
| `components/` | Skupni prikazni elementi, trenutno `Brand`. |
| `lib/` | Enkratna nastavitev odjemalca Supabase Auth. |
| `services/` | Skupni HTTP-odjemalec za FastAPI: prenos žetona, JSON in obravnava napak. |
| `tests/` | Nastavitev testnega okolja in testi uporabniških tokov. |

`main.tsx` samo zažene React. `app/Router.tsx` ohranja trenutni poti `/` in `/demo`; navigacija uporablja povezave z običajnim nalaganjem strani. Za trenutni obseg dodatna knjižnica za usmerjanje ni potrebna.

## Pravila odvisnosti

- `app` sestavlja strani in prijavni tok; strani sestavljajo funkcionalnosti.
- Koda posamezne funkcionalnosti ostane v svoji mapi: komponente, hooki, API-klici in tipi. Administracija uporablja skupne tipe identitete ter branje podjetij iz `identity`.
- `components`, `lib` in `services` ne uvažajo strani ali funkcionalnosti.
- Skupne mape `assets`, `hooks`, `utils` in `types` se dodajo šele, ko obstaja dejanska skupna vsebina. Hook seje in domenski tipi zato ostajajo v `features/identity`.

## Meja s strežnikom

Frontend prikazuje stanje in pošilja zahteve. Vidnost administratorskih obrazcev je pomoč uporabniku, ne varnostna meja. FastAPI pri vsakem poslovnem zahtevku preveri identiteto, aktivno sejo, vlogo in podjetje; PostgreSQL dodatno uveljavlja izolacijo podatkov.

Cene, marže, zaloge, odobritve, dostop do baze in AI-orodja ostajajo na backendu. Supabase v brskalniku upravlja le prijavo z javnim ključem; poslovni podatki se pridobivajo prek FastAPI. Mapa `features` zato vsebuje logiko uporabniškega vmesnika, ne avtoritativnih poslovnih pravil.

## Preverjanje

V mapi `frontend/` izvedite `npm test` in `npm run build`. Preureditev ohranja obstoječe uporabniške tokove in API-pogodbe.
