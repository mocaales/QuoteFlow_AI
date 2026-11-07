# Življenjski cikel ponudbe in računa

- **Status:** sprejeto; delno nadomeščeno z [ADR-0012](0012-postavke-projekta-izmere-in-vrste-dela.md) (nadomeščena sta le postavke ponudbe in njihova cena; preostali življenjski cikel velja)
- **Datum:** 2026-11-06
- **Izvedba:** izvedeno; migracije uvedene v oddaljeno bazo 2026-11-08

## Kontekst in problem

MVP (F1–F7) zahteva ponudbe z različicami, sprejem ali zavrnitev stranke ter račun iz sprejete ponudbe. Zasnova [mvp-ponudbe-racuni-design.md](../razvoj/mvp-ponudbe-racuni-design.md) je bila potrjena 2026-11-06 (G1). Pravila iz AGENTS.md: cene, količine, DDV in stanja določata programska logika in omejitve baze; poslane ponudbe in izdani računi so nespremenljivi; poslovni dostop se preverja za vsako podjetje, tuji zapisi pa ne smejo razkriti obstoja. Po G1 so bile na podlagi varnostnih ugotovitev (uporabnikovo stalno pravilo: popravi vse) sprejete še spremembe: mojster ob izdaji potrdi naziv in naslov prejemnika računa (predizpolnjeno; zamenjuje samodejnega prejemnika iz D4, brez nadomestnega e-poštnega naslova zaradi minimizacije podatkov), potrditvi pri pošiljanju in izdaji, omejitve (`velja_do` obvezen ob pošiljanju in v [danes, danes+366], največ 50 različic, največ 10 prestavitev na dan), "danes" vedno po Europe/Ljubljana, blokada administratorske samododelitve vloge (QFP22) in prepoved, da je mojster svoja stranka.

## Obravnavane možnosti

- Ročno številčenje dokumentov: zavrnjeno, ker povzroča podvojene in manjkajoče številke ter tekmovanje med uporabniki.
- Novo stanje `nadomescena`: zavrnjeno, ker bi razširilo preverjena stanja in bi ga bilo treba sinhronizirati; nadomeščenost je izpeljana lastnost.
- Izračun vsot v Pythonu: zavrnjen, ker bi zapis lahko razkrojil vrednosti in zaobšel omejitve baze.
- Ohranitev starih podpisov funkcij življenjskega cikla (brez podjetja): zavrnjeno, ker tuj in neobstoječ zapis ločita po odgovoru.

## Izid odločitve

Izberemo **postopke v `quoteflow_private`, vezane na podjetje**. Vsak (podjetje, projekt, …) najprej avtorizira, nato bere, zato manjkajoči in tuji zapisi dajo enak odziv. Zaklepanje je vedno v vrstnem redu podjetje → projekt → ponudba → račun. Številke so samodejne za podjetje in leto: `P-LLLL-NNN`, `R-LLLL-NNN`. Nova različica kopira prejšnje postavke in posnetke. "Nadomeščena" je izpeljana zastavica, ne novo stanje. Končna cena postavke je generirani stolpec `koncna_cena` v SQL, vsote računa baza, Python samo serializira. Revizijska sled je `quoteflow_private.dogodek_dokumenta`, zunaj pogodbe 17 tabel; sprožilci celovitosti so omejeni na spremenjeno vrstico. Napake: `55000` → 409, `22003` → 422, `22023`/`22004` → 422, `40P01`/`40001` → 409, poleg tega kode `QFPxx` (npr. QFP22) prek `backend/app/errors.py`. Dodane so varnostne glave in CSP (`frontend/nginx.conf`). Model 17 tabel ([docs/03](../03-podatkovni-model.md)) je nespremenjen, [ADR-0010](0010-projekti-podjetja-in-vec-vlog.md) še velja; ta ADR ga dopolnjuje in nadomešča le prejšnjo zasnovo prejemnika računa (D4).

### Posledice

- **Pozitivno:** enotna avtorizacija brez razkritja obstoja; brez zastojev zaradi fiksnega vrstnega reda zaklepanja; ena resnica za vsote; sledljivost dokumentov; nespremenljivost poslanih ponudb in izdanih računov.
- **Negativno:** pisanje znotraj podjetja je serijsko; potrditveni koraki podaljšajo potek; revizijska tabela je zunaj pogodbe, zato jo je treba posebej omeniti v preverjanju pripravljenosti; pri `40P01`/`40001` mora odjemalec ponoviti zahtevek.
- **Nadaljnje delo:** uvedba migracij v oddaljeno bazo po uporabnikovem odobritvi; posodobitev `docs/razvoj/podatkovni-model.md` in README (G7).

## Preverjanje

Testi `backend/tests/test_ponudbe*.py`, `test_izvedba_*.py`, `test_racun_database.py`, `test_varnost_database.py` in `test_varnost_api.py` (lokalna baza prek `TEST_DATABASE_URL`) preverjajo avtorizacijo pred branjem, enak odziv za tuje in manjkajoče zapise, številčenje, kopiranje različic, omejitve (`velja_do`, 50 različic, 10 prestavitev), QFP22 ter nespremenljivost. `test_errors.py` preverja preslikavo SQLSTATE v HTTP. Frontend: Vitest (`quotes*`, `invoices*`, `customer-quote`) in Playwright (`acceptance`, `a11y-quotes-invoices`, `design`). `database.py` še naprej preverja natanko 17 tabel.
