# Postavke projekta, izmere in vrste dela

- **Status:** sprejeto
- **Datum:** 2026-11-07
- **Izvedba:** izvedeno in uvedeno v oddaljeno bazo 2026-11-08 (zasnova potrjena v G1 2026-11-07)

## Kontekst in problem

Uporabnik je 2026-11-07 podal nov podatkovni opis: projekt je sestavljen iz več postavk; postavko je mogoče ponovno uporabiti ali ustvariti na novo in jo urejati. Postavka ima ime, opis, vrsto dela, mersko enoto, ceno na enoto, količino, popust, DDV in skupno ceno. Vrsta dela ima naziv, opis, ceno dela (urna postavka, število ur, delavec) in nič, enega ali več materialov iz zaloge. Merske enote so m, m², m³ in kos; izmere se seštevajo ali odštevajo in določijo količino. Uporabnikov odgovor o ceni: 20 m² × količina 1 × 10 €/enoto = 200 €, cena dela pa je urna postavka × ure × delavec. Treba je bilo določiti natančno formulo brez podvajanja cene dela.

Omejitve: AGENTS.md (cene, DDV in stanja računa programska logika in baza; poslane ponudbe nespremenljive; zaloga ločena od cenika), [ADR-0010](0010-projekti-podjetja-in-vec-vlog.md), [ADR-0011](0011-zivljenjski-cikel-ponudbe-in-racuna.md) (ponudbe z različicami, račun iz sprejete ponudbe) in varnostna ocena groženj (M2 stranka ne sme videti cene dela, M6 vsote posnetka, M7 zgornje meje, M14 omejitve števila). Migracije do `20261105140049` so v oddaljeni bazi in se ne urejajo; lokalne `20261106200016/200018/200759/202500/202550` so se smele prepisati.

## Obravnavane možnosti

- **Formula B (material in delo obračunana ločeno poleg cene na enoto):** zavrnjena, ker material in delo podvojita ceno, ki jo uporabnik že vsebuje v ceni na enoto.
- **Postavke samo znotraj osnutka ponudbe:** zavrnjeno, ker uporabnik želi postavke urejati na projektu in jih ponovno uporabiti; ponudba je nespremenljiv posnetek, ne delovni dokument.
- **Generirani stolpci za vsote posnetka:** zavrnjeno (M6), ker bi poznejša sprememba formule ali pravila zaokroževanja tiho spremenila že poslano ponudbo; posnetek je navaden stolpec, zapisan enkrat ob pošiljanju. Živa vsota na `postavka_projekta` sme ostati generirana.
- **Vhodi cene dela kot stolpci na `postavka_ponudbe`:** zavrnjeno (M2), ker stranka bere postavke ponudbe; vhodi so v ločeni tabeli samo za mojstra.
- **Samodejna pretvorba neznanih enot v kataloškem prenosu v `kos`:** zavrnjeno, ker bi tiho pokvarila cene.

## Izid odločitve

Izbrana možnost: **formula A z živimi postavkami na projektu in posnetkom ob pošiljanju**, ker uporabnikov zgled (200 €) ostane nespremenjen, cena dela se doda natanko enkrat, poslana ponudba pa ostane nespremenljiva.

- **Formula A:** `neto = round((izmera_skupaj × kolicina × cena_na_enoto + urna_postavka × stevilo_ur × stevilo_delavcev) × (1 − popust), 2)`; `ddv = round(neto × stopnja_ddv, 2)`; `koncna = neto + ddv`. Material je del `cena_na_enoto` in se ne zaračuna posebej. Delo je pavšal na postavko (enkrat), popust velja tudi za delo, ena stopnja DDV na postavko. Vsote dokumenta so vsota zaokroženih vrstic. Zgled: 20 m² × 1 × 10 € + 25 € × 8 h × 2 delavca = 200 + 400 = 600 €; popust 10 % → 540,00 €; DDV 22 % → 118,80 €; skupaj 658,80 €.
- **Izmere:** vsaka izmera ima predznak (+/−) in polja po enoti; `kosi` množi vsako enoto (privzeto 1): m = dolžina × kosi; **m² = dolžina × višina × kosi** (brez širine); m³ = dolžina × višina × širina × kosi; kos = kosi. `izmera_skupaj` = Σ ± vrednost, nikoli negativna (QFP25); pošiljanje zahteva `izmera_skupaj > 0` pri vsaki postavki (QFP26); sprememba enote postavke z izmerami je zavrnjena (QFP27).
- **Vrsta dela** je obvezna pri vsaki postavki (delo brez cene dela = vrsta dela z 0 €); ima nič ali več materialov iz zaloge (informativno, brez zaračunavanja); privzete vrednosti dela se ob izbiri skopirajo v postavko in so tam spremenljive. Shranjevanje postavke nazaj v katalog v tem koraku ni del obsega. Podobno kot prej gre za razširitev F2/F4 v MVP, brez nove F-številke.
- **Posnetek ob pošiljanju:** postavke in izmere se skopirajo v `postavka_ponudbe` in `izmera_ponudbe` z navadnimi stolpci vsot (M6); vhodi dela (urna postavka, ure, delavci, materiali) so v ločeni tabeli `delo_ponudbe`, ki jo vidi samo mojster podjetja (M2). Stranka vidi izmere poslanih različic (samo zahtevane ali zadnje) in vsote vrstic, nikoli urne postavke, ur, delavcev ali materialov.
- **Pogodba tabel:** 17 → 22 (`EXPECTED_TABLES` v `backend/app/database.py`, AGENTS.md, CLAUDE.md, `docs/03` in diagram se posodobijo). Zgornje meje po M7 (npr. količina in cena na enoto ≤ 1e6, urna postavka ≤ 1e4, delavci 1–1000, izmera_skupaj ≤ 1e8, neto ≤ 1e9) so DB CHECK in Pydantic; omejitve števila po M14: 200 postavk na projekt (QFP20), 100 izmer na postavko (QFP28), 500 vrst dela na podjetje (QFP31), 50 materialov na vrsto dela (QFP32).
- **Oddaljeni katalog:** pretvorba obstoječih postavk cenika v novo obliko ob uvedbi **glasno odpove** pri neznani enoti (brez privzetka `kos`); uvedba po pregledu in uporabnikovi odobritvi.

Odločitev velja za postavke projekta, izmere, vrste dela in posnetek ponudbe; nadomešča prejšnjo zasnovo postavk ponudbe iz [ADR-0011](0011-zivljenjski-cikel-ponudbe-in-racuna.md) (ročne postavke ponudbe in generirani `koncna_cena` na postavki ponudbe); preostali življenjski cikel ostane.

### Posledice

- **Pozitivno:** ena jasna formula brez podvajanja dela; ponovna uporaba postavk; poslana ponudba ostane nespremenjena ne glede na poznejše spremembe pravil; stranka ne vidi notranjih stroškov.
- **Negativno:** šest novih tabel (`vrsta_dela`, `material_vrste_dela`, `postavka_projekta`, `izmera`, `izmera_ponudbe`, `delo_ponudbe`) ob odstranitvi `sestava_cenika` (17 → 22) in več omejitev (QFP20, 25–28, 31, 32); preglednejši, a daljši posnetek ob pošiljanju; ni ločenega zaračunavanja materiala (mojster ga vključi v ceno na enoto); pretvorba oddaljenega kataloga lahko zahteva ročni popravek.
- **Nadaljnje delo:** prepis lokalnih migracij ter nova v3 migracija pred lokalnimi; testi in uporabniški vmesnik (`features/items/components/ProjectItems.tsx`); posodobitev `docs/02`, `docs/03`, diagrama, README in `docs/razvoj` (G7); shranjevanje postavke v katalog kot poznejši korak.

## Preverjanje

DB testi (`TEST_DATABASE_URL`): zgled 540,00 / 118,80 / 658,80, primeri pri .005, postavka le z delom, QFP20/25/26/27/28/31/32, meje M7, nespremenljivost posnetka, `delo_ponudbe` nedostopna stranki, izmere stranki samo zahtevane/zadnje različice, RLS na 22 tabelah (`supabase/tests/tenant_isolation.sql`). Backend: testi `app.pricing` in `app.routers.postavke` ter 422 pri neustreznih poljih po enoti; `database.py` preverja natanko 22 tabel. Frontend: Vitest in Playwright (1440/390) za `ProjectItems`. Test pretvorbe kataloga mora pri neznani enoti odpovedati.
