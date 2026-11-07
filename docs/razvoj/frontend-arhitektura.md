# Organizacija frontenda

Koda v `frontend/src/` je razdeljena po odgovornostih:

| Mapa | Odgovornost |
|---|---|
| `app/` | Sestava aplikacije, izbira poti in globalni slogi. |
| `pages/` | Pogleda delovnega prostora in demonstracije; povezujeta funkcionalnosti v stran. |
| `features/identity/` | Prijava, registracija, stanje seje, profil in tipi identitete, podjetij ter dodelitev pravic. |
| `features/administration/` | »Podjetja in pravice«: zavihki Po podjetjih, Po uporabnikih, Prošnje mojstrov in Podjetja; iskanje, filtri vloge in stanja, označeni gumbi Odvzemi/Ponovno aktiviraj s potrditvijo, stranski panel za dodelitev. |
| `features/calculator/` | API-klici in tipi demonstracijskega kalkulatorja. Izračun izvaja backend. |
| `features/supplier/` | Cenik, vrste dela (z materiali), materiali in zaloge: obrazci, pogledi, tipi in API-klici. |
| `features/items/` | Postavke projekta: tabela z vsotami, obrazec postavke (`ItemForm`), izbira iz cenika (`CatalogPick`), izmere glede na enoto (`MeasuresPanel`); zneske izračuna baza. |
| `features/workers/` | US-08: delavci podjetja za mojstra (dodaj po e-pošti, odvzemi, ponovno aktiviraj). |
| `features/projects/` | Projekti: pogled mojstra po fazah, obrazec, termin in izvedba (`ProjectProgress`), pogled stranke (samo branje). |
| `features/quotes/` | Ponudbe: osnutek (glava in vsote postavk projekta), pošiljanje, pogled stranke z izmerami. Postavke se urejajo v `features/items/`. |
| `features/invoices/` | Račun: osnutek, izdaja, plačilo, pogled stranke. |
| `components/` | Skupni elementi `Brand`, `Icon`, modalni stranski panel `Drawer` in `ActionAlert` (sporočilo o napaki dejanja). |
| `utils/` | Oblikovanje denarja, količin, odstotkov in časa; hooka `useDetailFocus` in `useTipEscape` za fokus in Esc v podrobnostih. |
| `lib/` | Enkratna nastavitev odjemalca Supabase Auth. |
| `services/` | Skupni HTTP-odjemalec za FastAPI: prenos žetona, JSON in obravnava napak. |
| `tests/` | Nastavitev testnega okolja in testi uporabniških tokov. |

`main.tsx` samo zažene React. `app/Router.tsx` ohranja trenutni poti `/` in `/demo`; prehodi med njima uporabljajo običajno nalaganje strani. Pogledi ponudnika (Cenik, Vrste dela, Zaloge, Materiali, Projekti, Delavci) in administracije se izbirajo znotraj delovnega prostora; postavke projekta so zavihek v pogledu projekta. Za trenutni obseg dodatna knjižnica za usmerjanje ni potrebna.

## Pravila odvisnosti

- `app` sestavlja strani in prijavni tok; strani sestavljajo funkcionalnosti.
- Koda posamezne funkcionalnosti ostane v svoji mapi: komponente, hooki, API-klici in tipi. Administracija uporablja skupne tipe identitete ter branje podjetij iz `identity`.
- `components`, `lib` in `services` ne uvažajo strani ali funkcionalnosti.
- Dodatne skupne mape se dodajo šele, ko obstaja dejanska skupna vsebina. Hook seje in domenski tipi zato ostajajo v `features/identity`.

## Meja s strežnikom

Frontend prikazuje stanje in pošilja zahteve. Vidnost administratorskih obrazcev je pomoč uporabniku, ne varnostna meja. FastAPI pri vsakem poslovnem zahtevku preveri identiteto, aktivno sejo, vlogo in podjetje; PostgreSQL dodatno uveljavlja izolacijo podatkov.

Cene, marže, zaloge, odobritve, dostop do baze in AI-orodja ostajajo na backendu. Supabase v brskalniku upravlja le prijavo z javnim ključem; poslovni podatki se pridobivajo prek FastAPI. Mapa `features` zato vsebuje logiko uporabniškega vmesnika, ne avtoritativnih poslovnih pravil.

## Preverjanje

V mapi `frontend/` izvedite `npm test`, `npm run build` in `npm run test:e2e`. Preureditev ohranja obstoječe uporabniške tokove in API-pogodbe.

`npm run test:e2e` zažene Playwright v Chromiumu pri širini 1440 in 390 px. API in Supabase Auth sta nadomeščena z vzorčnimi podatki v `e2e/fixtures.ts`, zato zagon ne potrebuje backenda ali prijavnih podatkov. Testi preverijo pravila vizualnega sistema in posnetke zaslonov shranijo v `test-results/screens/` za pregled. Ob prvem zagonu namestite brskalnik z `npx playwright install chromium`.

## Vizualni sistem

Uokvirjen list: navigacija in ozadje sta en zelenkasto siv okvir, delo poteka na belem listu z 1 px robom in brez sence. Zelena barva blagovne znamke je omejena na znak, aktivni zavihek in stanja potrditve; glavno dejanje je skoraj črno. Pisava je IBM Plex Sans (Google Fonts) z velikostmi 12, 14, 16 in 22 px.

Pravila, ki jih preverja `e2e/design.spec.ts`:

- en naslov `h1` na zaslon, velik 18–32 px;
- besedilo najmanj 12 px, brez razprtih velikih črk in s kontrastom vsaj 4,5 : 1;
- številke, zneski in datumi v tabelah desno poravnani, s tabelaričnimi števkami;
- svetla navigacija in nobenega vodoravnega drsenja strani;
- kontrole najmanj 28 px na namizju in 40 px na telefonu.

Tabele so glavni prikaz, urejanje poteka v modalnem stranskem panelu z upravljanjem fokusa. Seznami začnejo z ugotovitvijo, ki odgovori na vprašanje zaslona, na primer koliko postavk je potrjenih in na voljo za ponudbe. Stanja seznama so podčrtani zavihki s števili.

Na telefonu se navigacija zloži v meni pod gumbom »Meni«, tabele s podatki ponudnika pa postanejo dvovrstične vrstice z vsemi polji. Prehodi panela in kontrol upoštevajo `prefers-reduced-motion`.
