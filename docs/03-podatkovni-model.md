# Podatkovni model

Primarni relacijski model ima **22 tabel** in nadomešča prejšnji model RFQ. Obsega uporabnike, podjetja, projekte z njihovimi postavkami in izmerami, ekipe, cenik, vrste dela, materiale, ponudbe in račune. Model v3 (postavke projekta, izmere, vrste dela) razširja prvotnih 17 tabel: doda 6 tabel in odstrani `sestava_cenika`; odločitve so v [ADR-0012](adr/0012-postavke-projekta-izmere-in-vrste-dela.md), uvedba v [razvojnem zapisu](razvoj/model-v3-postavke-izmere.md). Stanje uvedbe je v [razvojnih navodilih](razvoj/podatkovni-model.md).

## Poslovna logika

### Uporabniki, vloge in podjetja

Uporabnik ima lahko več vlog hkrati. `admin` in `stranka` veljata globalno, `mojster` in `delavec` pa izključno pri konkretnem podjetju. Po potrditvi registracije uporabnik samodejno dobi vlogo `stranka`. Mojster je lahko tudi delavec svojega ali drugega podjetja, vendar potrebuje ločeno dodelitev. Nobena poslovna vloga ne daje pravic pri drugem podjetju.

Podjetje ima enega lastnika. Lastnik mora imeti aktivno vlogo `mojster` prav pri tem podjetju; lastništvo je povezava na uporabnika, ne peta vloga. Stranka ali delavec lahko odda prošnjo s podatki svojega podjetja. Prošnjo odobri admin. Odobritev v eni transakciji ustvari podjetje, lastništvo in vlogo mojstra. Zavrnitev ne ustvari podjetja ali pravice. Mojster delavce v svoje podjetje povabi; vlogo `delavec` dobi uporabnik šele, ko povabilo sprejme. Povabila (`quoteflow_private.povabilo_delavca`), revizija vlog (`dogodek_vloge`) in omejitve hitrosti (`poskus_delavca`) so zasebne tabele brez aplikacijskih pravic in niso del pogodbe 22 poslovnih tabel.

### Projekti in ekipe

Projekt pripada enemu podjetju in eni stranki. Ekipa pripada enemu podjetju; uporabnik je njen član prek svoje dodelitve `delavec` pri istem podjetju. Delavec je lahko v več ekipah, ekipa na več projektih, projekt pa ima več ekip. Udeležba delavca pri projektu izhaja iz članstva in dodelitve ekipe; dodatne podvojene povezave delavec–projekt ni.

| Faza oziroma stanje projekta | Poslovni dogodek |
|---|---|
| `pregled` | Nastane projekt in pregleda se zahteva stranke. |
| `ogled` | Potreben je ogled; po potrebi se faza preskoči. |
| `ponudba` | Stranki je poslana prva ponudba. Zavrnitev omogoča novo različico. |
| `termin` | Stranka sprejme ponudbo. |
| `izvedba` | Vnesen je dogovorjeni termin izvedbe. |
| `obracun` | Izvedba je zaključena, račun izdan in poslan stranki. |
| `zakljucen` | Račun je v celoti plačan; zapiše se čas zaključka projekta. |

Projekt hrani `faza` in `zakljuceno_ob`. Njegovo splošno stanje je izpeljano: brez časa zaključka je `v_teku`, sicer `zakljucen`; podvojeni stolpec za isto informacijo ni potreben. Vnos termina označi fazo izvedbe, sam po sebi pa ne potrjuje opravljenega dela.

### Cenik, vrste dela, materiali in zaloga

**Vrsta dela** (`vrsta_dela`) pripada podjetju in hrani naziv, opis ter ceno dela: `urna_postavka`, `stevilo_ur` in `stevilo_delavcev` (število delavcev, ne oseba). Izpeljano `cena_dela = round(urna_postavka × stevilo_ur × stevilo_delavcev, 2)`. Vrsta dela ima nič, enega ali več materialov (`material_vrste_dela`, količina na enoto dela). Vrsta dela brez dela ima ceno dela 0 €. Vrsta dela je obvezna pri vsaki postavki cenika in projekta.

**Postavka cenika** je ponovno uporabna postavka z nazivom, opisom, vrsto dela (`vrsta_dela_id`), mersko enoto (`m`, `m2`, `m3`, `kos`), ceno na enoto in stopnjo DDV. Materialna sestava ni več na postavki cenika (`sestava_cenika` je odstranjena); material pripada vrsti dela.

**Materiali** so ločeni od storitev: imajo vrsto, šifro, mersko enoto in ceno. Zaloga hrani količino po lokacijah; ključ `(material_id, lokacija)` omogoča isti material na več lokacijah. Podjetje materiala izhaja iz njegove vrste. Zaloga ne pripada postavki ali vrsti dela.

### Postavke projekta in izmere

Postavke živijo na projektu (`postavka_projekta`) in jih mojster ureja, dokler ponudba ni poslana. Nastanejo iz cenika (kopija cene, enote, DDV in ure iz vrste dela, vse urejeno po postavki) ali kot nove. Postavka ima naziv, opis, vrsto dela, mersko enoto, ceno na enoto, količino (privzeto 1), popust, DDV, delovne podatke (`urna_postavka`, `stevilo_ur`, `stevilo_delavcev`) ter izpeljane vrednosti.

Količino meri **izmera** (`izmera`). Merska enota postavke določa polja:

| Enota | Polja | Vrednost izmere |
|---|---|---|
| `m` | dolžina | `dolzina × kosi` |
| `m2` | dolžina, višina | `dolzina × visina × kosi` |
| `m3` | dolžina, višina, širina | `dolzina × visina × sirina × kosi` |
| `kos` | samo `kosi` | `kosi` |

`kosi` (privzeto 1) množi vsako enoto. Neuporabljena polja so `NULL`; izmera ima enoto postavke (sestavljen tuji ključ). `odstej = true` pomeni odštevanje. `izmera_skupaj = Σ ±vrednost` je vedno ≥ 0 (nižja vsota zavrne `QFP25`), pošiljanje zahteva `izmera_skupaj > 0` pri vsaki postavki (`QFP26`). Enote postavke ni mogoče spremeniti, ko ima izmere (`QFP27`). Pravilo za m² (brez širine) je potrjeno 2026-11-07.

### Izračun postavke (formula A)

```
neto   = round((izmera_skupaj × kolicina × cena_na_enoto + urna_postavka × stevilo_ur × stevilo_delavcev) × (1 − popust), 2)
ddv    = round(neto × stopnja_ddv, 2)
koncna = neto + ddv
```

Material je vključen v `cena_na_enoto` in se ne zaračuna posebej. Delo se zaračuna enkrat na postavko (pavšal), ne na enoto; popust velja tudi za delo; ena stopnja DDV na postavko. Vsote dokumenta so vsote zaokroženih vrstic.

Primer: 20 m² × količina 1 × 10 € = 200,00 €; delo 25 €/h × 8 h × 2 delavca = 400,00 €; skupaj 600,00 €; popust 10 % → neto **540,00 €**; DDV 22 % → **118,80 €**; končna cena **658,80 €**. Izračun je v bazi (generirani stolpci); Python (`app/pricing.py`) je samo referenca za teste.

### Ponudbe in računi

Ponudba pripada projektu. Osnutek je samo glava (številka, različica, `velja_do`); njegova vsebina so žive postavke projekta. Potek je `osnutek → poslana → sprejeta/zavrnjena`; stranka projekta odloča samo o poslani ponudbi.

**Ob pošiljanju** se v eni transakciji ustvari nespremenljiv posnetek: `postavka_ponudbe` (naziv, opis, ime vrste dela, enota, cena, količina, popust, DDV, `izmera_skupaj`, `neto`, `koncna_cena` kot navadni stolpci, zapisani enkrat), `izmera_ponudbe` (kopija izmer), `material_ponudbe` (ime, enota, količina in cena materiala vrste dela ob pošiljanju) in `delo_ponudbe` (ura, ure, delavci, cena dela; samo mojster). Poznejša sprememba postavk, izmer, vrste dela, cenika ali cene materiala ne spremeni posnetka. Popravek pomeni novo različico, ki se napolni iz trenutnih postavk projekta.

Stranka vidi poslano ponudbo s postavkami, zneski in izmerami (samo zahtevane ali zadnje različice); ne vidi osnutkov, urne postavke, ur, števila delavcev in materialov. Projekt ima lahko več različic, največ eno sprejeto. Račun se sklicuje na sprejeto ponudbo; njegove zneske določa posnetek. Ob sprejemu nastane osnutek računa, račun se izda po izvedbi. Plačanost se izpelje iz `placano_ob`. Ob celotnem plačilu se projekt zaključi. Delna plačila niso vključena. Ponudba ne rezervira ali zmanjšuje zaloge; količina materiala za F15 je `kolicina_na_enoto × izmera_skupaj × kolicina`.

## Enoten relacijski ER-diagram

[Uredi celoten diagram v draw.io](diagrams/03-podatkovni-model.drawio) · [Odpri SVG v polni velikosti](diagrams/03-podatkovni-model.svg)

Diagram ima **eno stran, 22 tabel in 33 povezav**. Vsaka tabela se pojavi enkrat; stolpci so **podatkovni tip | atribut | PK/FK/UQ**. Vsaka povezava povezuje konkretno vrstico FK s konkretno vrstico referenčnega ključa in je označena z imenom FK. Krog pomeni nič, črta eno in vranja noga več. Sestavljeni tuji ključ `(postavka_projekta_id, enota)` in `(postavka_ponudbe_id, enota)` je narisan kot ena povezava; stolpec `enota` ima oznako FK. Križanje črt ni povezava: povezave obstajajo samo na označenih koncih pri tabelah.

![Enoten relacijski model uporabnikov, podjetij in projektov](diagrams/03-podatkovni-model.svg)

## Entitete in atributi

`PK` je primarni ključ, `FK` tuji ključ, `UQ` enoličnost, `?` dovoljen NULL in `IZP` izpeljana vrednost. Drugi atributi so obvezni. Samostojni ID so UUID; časovni podatki so `timestamptz`, denar in količine decimalni. `IZP` se samodejno izračuna v bazi in se ne ureja neposredno.

| Entiteta | Atributi |
|---|---|
| `uporabnik` | `id uuid PK`; `e_posta text UQ`; `ime text`; `priimek text` |
| `vloga_uporabnika` | `id uuid PK`; `uporabnik_id uuid FK`; `podjetje_id uuid? FK`; `vloga text`; `aktivna boolean`; `dodeljeno_ob timestamptz` |
| `podjetje` | `id uuid PK`; `lastnik_id uuid FK`; `naziv text`; `maticna_stevilka text UQ`; `davcna_stevilka text?`; `naslov text`; `aktivno boolean` |
| `prosnja_mojstra` | `id uuid PK`; `uporabnik_id uuid FK`; `naziv_podjetja text`; `maticna_stevilka text`; `davcna_stevilka text?`; `naslov_podjetja text`; `stanje text`; `podjetje_id uuid? FK,UQ`; `odlocil_id uuid? FK`; `oddano_ob timestamptz`; `odloceno_ob timestamptz?` |
| `projekt` | `id uuid PK`; `podjetje_id uuid FK`; `stranka_id uuid FK`; `naziv text`; `opis text`; `lokacija_izvedbe text`; `faza text`; `termin_od timestamptz?`; `termin_do timestamptz?`; `izvedba_koncana_ob timestamptz?`; `zakljuceno_ob timestamptz?` |
| `ekipa` | `id uuid PK`; `podjetje_id uuid FK`; `naziv text`; `aktivna boolean` |
| `clan_ekipe` | `ekipa_id uuid PK,FK`; `delavec_vloga_id uuid PK,FK` |
| `projekt_ekipa` | `projekt_id uuid PK,FK`; `ekipa_id uuid PK,FK` |
| `postavka_cenika` | `id uuid PK`; `podjetje_id uuid FK`; `vrsta_dela_id uuid FK`; `naziv text`; `opis text`; `enota text`; `cena_na_enoto numeric(18,4)`; `stopnja_ddv numeric(7,6)`; `aktivna boolean` |
| `vrsta_materiala` | `id uuid PK`; `podjetje_id uuid FK`; `naziv text` |
| `material` | `id uuid PK`; `vrsta_materiala_id uuid FK`; `sifra text`; `naziv text`; `enota text`; `cena_na_enoto numeric(18,4)`; `aktiven boolean` |
| `zaloga` | `material_id uuid PK,FK`; `lokacija text PK`; `kolicina numeric(18,4)` |
| `vrsta_dela` | `id uuid PK`; `podjetje_id uuid FK`; `naziv text`; `opis text`; `urna_postavka numeric(18,4)`; `stevilo_ur numeric(18,4)`; `stevilo_delavcev integer`; `aktivna boolean`; `cena_dela numeric(18,2) IZP` |
| `material_vrste_dela` | `vrsta_dela_id uuid PK,FK`; `material_id uuid PK,FK`; `kolicina_na_enoto numeric(18,4)` |
| `postavka_projekta` | `id uuid PK`; `projekt_id uuid FK`; `postavka_cenika_id uuid? FK`; `vrsta_dela_id uuid FK`; `zaporedje integer`; `naziv text`; `opis text`; `enota text`; `cena_na_enoto numeric(18,4)`; `kolicina numeric(18,4)`; `popust numeric(7,6)`; `stopnja_ddv numeric(7,6)`; `urna_postavka numeric(18,4)`; `stevilo_ur numeric(18,4)`; `stevilo_delavcev integer`; `izmera_skupaj numeric(18,4)`; `cena_dela numeric(18,2) IZP`; `neto numeric(18,2) IZP`; `koncna_cena numeric(18,2) IZP` |
| `izmera` | `id uuid PK`; `postavka_projekta_id uuid FK`; `enota text FK`; `zaporedje integer`; `odstej boolean`; `kosi numeric(18,4)`; `dolzina numeric(18,4)?`; `visina numeric(18,4)?`; `sirina numeric(18,4)?`; `vrednost numeric(18,4) IZP` |
| `ponudba` | `id uuid PK`; `projekt_id uuid FK`; `stevilka text`; `razlicica integer`; `stanje text`; `poslano_ob timestamptz?`; `odgovorjeno_ob timestamptz?`; `velja_do date?`; `valuta char(3)` |
| `postavka_ponudbe` | `id uuid PK`; `ponudba_id uuid FK`; `postavka_cenika_id uuid? FK`; `zaporedje integer`; `naziv text`; `opis text`; `vrsta_dela text`; `enota text`; `cena_na_enoto numeric(18,4)`; `kolicina numeric(18,4)`; `popust numeric(7,6)`; `stopnja_ddv numeric(7,6)`; `izmera_skupaj numeric(18,4)`; `neto numeric(18,2)`; `koncna_cena numeric(18,2)` |
| `izmera_ponudbe` | `postavka_ponudbe_id uuid PK,FK`; `zaporedje integer PK`; `enota text FK`; `odstej boolean`; `kosi numeric(18,4)`; `dolzina numeric(18,4)?`; `visina numeric(18,4)?`; `sirina numeric(18,4)?`; `vrednost numeric(18,4)` |
| `delo_ponudbe` | `postavka_ponudbe_id uuid PK,FK`; `urna_postavka numeric(18,4)`; `stevilo_ur numeric(18,4)`; `stevilo_delavcev integer`; `cena_dela numeric(18,2)` |
| `material_ponudbe` | `postavka_ponudbe_id uuid PK,FK`; `material_id uuid PK,FK`; `naziv text`; `enota text`; `kolicina_na_enoto numeric(18,4)`; `cena_na_enoto numeric(18,4)` |
| `racun` | `id uuid PK`; `ponudba_id uuid FK,UQ`; `stevilka text?`; `stanje_dokumenta text`; `izdajatelj_naziv text?`; `izdajatelj_naslov text?`; `izdajatelj_davcna text?`; `prejemnik_naziv text?`; `prejemnik_naslov text?`; `izdan_ob timestamptz?`; `poslan_ob timestamptz?`; `zapade_dne date?`; `placano_ob timestamptz?`; `stanje_placila text IZP` |

## Celovitost in dostop

- PK/FK zagotavljajo obstoj povezanih zapisov; uporabljeni zapisi se ne brišejo kaskadno. Vloge so enolične za uporabnika in obseg. Lastnik mora ohraniti aktivno vlogo mojstra v svojem podjetju.
- Sestavljeni PK preprečijo podvojena članstva, ekipe projekta, materiale vrste dela in posnetke izmer. Enolične so matična številka, različica ponudbe v projektu, zaporedje postavke projekta in ponudbe, zaporedje izmere v postavki in račun ponudbe. Šifra materiala ter številka izdanega računa sta enolični znotraj podjetja.
- Članstvo, ekipa projekta, vrsta dela, material vrste dela, postavka projekta, izmera in izvori postavk/materialov ponudbe morajo pripadati istemu podjetju. Poleg FK so potrebna preverjanja, ki preprečijo tudi naknadno premikanje povezanih zapisov med podjetji.
- Stranka vidi svoje projekte in poslane dokumente, delavec dodeljene projekte prek ekip, mojster upravlja svoje podjetje. Admin upravlja uporabnike, podjetja in prošnje. Backend in RLS preverjata sejo, aktivno vlogo ter konkretno podjetje.
- Poslane ponudbe in izdani računi so nespremenljivi. Sprejem ponudbe, nastanek osnutka računa in prehod projekta v `termin` so ena transakcija; enako velja za evidentiranje plačila in zaključek projekta.
- Količine, mere in količine materiala so pozitivne, zaloga in cene nenegativne. `0 ≤ popust < 1`, `0 ≤ stopnja_ddv ≤ 1`; delež `0.22` pomeni 22 %. Valuta je EUR. Izračun je formula A zgoraj; uporablja se decimalna aritmetika in zaokroževanje polovice navzgor.
- Zgornje meje (tabelarne omejitve CHECK in Pydantic): `kolicina`, `cena_na_enoto` ≤ 1 000 000; `urna_postavka` ≤ 10 000; `stevilo_ur` ≤ 100 000; `stevilo_delavcev` 1–1000; `dolzina`, `visina`, `sirina` in `kosi` ≤ 100 000; `vrednost` izmere ≤ 1 000 000; `izmera_skupaj` ≤ 100 000 000; `neto` ≤ 1 000 000 000. Na podjetje največ 500 vrst dela (`QFP31`), na vrsto dela 50 materialov (`QFP32`), na projekt 200 postavk (`QFP20`), na postavko 100 izmer (`QFP28`).
- `vrsta_dela`, `material_vrste_dela`, `postavka_projekta`, `izmera`, `izmera_ponudbe` in `delo_ponudbe` berejo samo mojstri podjetja (RLS); stranka vidi posnetek postavk in izmer prek ozkih poizvedb API-ja, ne teh tabel.

Model ne vključuje starega RFQ in izbire ponudnikov. [Načrtovani obseg](02-funkcionalnosti-in-obseg.md) poleg osnovnega procesa predvideva AI-pomoč F16–F20, e-pošto F12, priloge F21 in opombe F22; ti postopki še niso izvedeni in lahko zahtevajo dodatne evidence oziroma shrambo. Shema 22 tabel ne predstavlja vseh prihodnjih funkcionalnosti. Evidentiranje dejanskih delovnih ur ter rezervacije in poraba zaloge ostajajo nadgradnje F23–F24; delna plačila niso vključena.
