# Funkcionalnosti in obseg

Načrt obsega **22 predvidenih funkcionalnosti: 7 MVP in 15 za poznejši razvoj**, ter **5 možnih nadgradenj**. Skupaj je opisanih **27 funkcionalnosti**. MVP pomeni cilj prve celovite različice, ne oznake že dokončane implementacije. Trenutno stanje je navedeno v [razvojni dokumentaciji](razvoj/podatkovni-model.md).

Ta obseg nadomešča prejšnji proces RFQ. Oznake F in US v tem dokumentu ter [uporabniških zgodbah](05-uporabniske-zgodbe.md) veljajo za novi projektni proces; stare GitHub naloge in razvojni zapisi ohranijo prvotni pomen in se ne preslikajo samodejno.

## Uporabniške vloge

| Vloga | Pravice in omejitve |
|---|---|
| `admin` | Globalno upravlja uporabnike, vloge, podjetja in prošnje mojstrov. Administratorska vloga sama ne daje pravice nastopati kot mojster ali sprejemati ponudbe stranke. |
| `stranka` | Globalna vloga po potrjeni registraciji. Vidi svoje projekte in poslane dokumente, sprejme ali zavrne svojo ponudbo. Ne vidi internih osnutkov, zaloge ali podatkov drugih strank. |
| `mojster` | Velja pri konkretnem podjetju. Upravlja njegovo poslovanje, cenik, materiale, projekte, ponudbe in račune; pozneje tudi delavce in ekipe. Samo mojster tega podjetja je lahko njegov lastnik. |
| `delavec` | Velja pri konkretnem podjetju. Pozneje vidi projekte in termine, ki so mu dodeljeni prek ekip. Ne upravlja cenika, ponudb, računov ali poslovnih pravic. |

Uporabnik ima lahko več vlog hkrati, tudi `mojster` v enem in `delavec` v drugem podjetju. Vsako dejanje preveri konkretno podjetje in trenutno aktivno vlogo. Stranka ni vezana na podjetje. Mojster potrebuje ločeno dodelitev `delavec`, če želi nastopati tudi kot delavec.

AI-agent je **sistemski akter**, ne poslovna vloga. Njegove funkcionalnosti so načrtovane po MVP.

## Predvidene funkcionalnosti

| ID | Funkcionalnost | Obseg |
|---|---|---|
| F1 | Registracija, prijava in odjava, samodejna vloga stranke po potrditvi e-pošte ter upravljanje pravic. Stranka ali delavec odda prošnjo s podatki podjetja; adminova odobritev skupaj ustvari podjetje, lastništvo in vlogo mojstra. | **MVP** |
| F2 | Cenik del in storitev, vrste materialov, materiali in zaloga po lokacijah. Postavka cenika lahko vsebuje materialno sestavo na enoto dela. | **MVP** |
| F3 | Mojster ustvari projekt za obstoječega uporabnika z vlogo stranke, opiše zahtevo in lokacijo ter vodi začetni pregled in neobvezni ogled. | **MVP** |
| F4 | Priprava ponudbe iz cenika ali ročnih postavk s količino, enoto, ceno, popustom, DDV in determinističnim izračunom. Cene in materialna sestava se prenesejo kot posnetek. | **MVP** |
| F5 | Mojster pošlje ponudbo stranki v aplikaciji; stranka jo sprejme ali zavrne. Poslana vsebina je zaklenjena, popravek ustvari novo različico. | **MVP** |
| F6 | Po sprejemu ponudbe vnos termina in evidentiranje zaključene izvedbe. Sistem dovoljuje samo prehode faz, ki imajo izpolnjene poslovne pogoje. | **MVP** |
| F7 | Ob sprejemu ponudbe nastane osnutek računa. Po končani izvedbi ga mojster izda in pošlje v aplikaciji; ročno evidentiranje celotnega plačila zaključi projekt. | **MVP** |
| F8 | Mojster dodaja in odstranjuje dodelitve delavcev v svojem podjetju; kot delavca lahko doda tudi sebe. | Pozneje |
| F9 | Urejanje ekip in članstev; delavec je lahko v več ekipah istega podjetja. | Pozneje |
| F10 | Dodelitev ekip projektu ter pregled dodeljenih projektov in terminov za njihove delavce. | Pozneje |
| F11 | Izvoz poslane ponudbe in izdanega računa v PDF. | Pozneje |
| F12 | E-poštna obvestila ob poslani ponudbi, odločitvi stranke, določitvi ali spremembi termina in izdanem računu. | Pozneje |
| F13 | Primerjava različic ponudbe z označenimi spremembami postavk, količin in cen. | Pozneje |
| F14 | Pregled števila projektov po fazah ter zneskov izdanih, plačanih in neplačanih računov lastnega podjetja. | Pozneje |
| F15 | Izračun potreb materiala iz ponudbe, primerjava z zalogo in prikaz primanjkljajev brez rezerviranja zaloge. | Pozneje |
| F16 | AI analizira prosti opis projektne zahteve, prepozna dela, izrecno navedene količine in manjkajoče podatke. | Pozneje |
| F17 | AI predlaga osnutek ponudbe iz cenika in materialnih sestav lastnega podjetja; mojster ga pregleda in dopolni. | Pozneje |
| F18 | AI opozori na morebitna manjkajoča ali podvojena dela in neskladja med opisom projekta ter ponudbo. | Pozneje |
| F19 | AI predlaga jasnejše opise del in pojasnila za stranko brez spreminjanja finančnih vrednosti. | Pozneje |
| F20 | AI pripravi povzetek projekta, dovoljenih dogovorov in stanja ter predlaga naslednje korake. | Pozneje |
| F21 | Fotografije in dokumenti projekta, npr. stanje pred posegom, meritve in dokumentacija ogleda. | Pozneje |
| F22 | Projektne opombe in pojasnila med mojstrom ter stranko z ločitvijo internih in stranki vidnih vsebin. | Pozneje |

**MVP F1–F7 tvori tok od dostopa do plačanega projekta.** F4–F7 presegajo osnovni CRUD: vključujejo izračune, nespremenljivost dokumentov, odločitev stranke, pogojevane prehode in povezavo plačila z zaključkom projekta. Ekipe, PDF, e-pošta in AI niso pogoj za prvi MVP.

Življenjski cikel je `pregled → [ogled] → ponudba → termin → izvedba → obracun → zakljucen`. Prva poslana ponudba uvede fazo `ponudba`, sprejem fazo `termin`, vnos termina fazo `izvedba`, zaključena izvedba z izdanim računom fazo `obracun`, celotno plačilo pa zaključek. Zavrnitev dovoljuje pripravo nove različice ponudbe. Projekt ima največ eno sprejeto ponudbo in ta največ en račun; delna plačila in delni računi niso vključeni.

## Omejitve AI in podatkovnega modela

AI uporablja samo podatke, do katerih ima izvajalec pravico pri konkretnem podjetju. Ne izmišlja si cen, zaloge ali manjkajočih količin; negotovosti označi za pregled. Izračune cen, popustov, DDV in potreb materiala izvaja deterministična koda. AI ne pošilja ali sprejema ponudb, ne izdaja računov in ne spreminja faz projekta. Mojster izrecno potrdi predlagano vsebino pred običajnim postopkom pošiljanja.

[Model s 17 tabelami](03-podatkovni-model.md) je osnova projektnega procesa. Poznejša e-pošta, AI, priponke, opombe in nadgradnje lahko zahtevajo dodatne podatkovne strukture oziroma shrambo. Njihova vključitev v načrt ne pomeni, da so že uvedene v bazo ali aplikacijo.

## Pet možnih nadgradenj

| ID | Nadgradnja |
|---|---|
| F23 | Delavec zapisuje ure in poroča o napredku dela na dodeljenih projektih. |
| F24 | Evidenca premikov zaloge, rezervacij materiala in dejanske porabe po projektu. |
| F25 | Koledar razpoložljivosti ekip, odsotnosti in zaznavanje konfliktnih terminov. |
| F26 | Povezava z zunanjim računovodstvom in uvoz bančnih evidenc za usklajevanje plačil. |
| F27 | AI pomaga razbrati obseg del iz fotografij in dokumentov; ugotovitve obvezno pregleda mojster. |

## Izven obsega

- Javni trg ponudnikov, oddaja RFQ več podjetjem in samodejna izbira ponudnika.
- Celovit računovodski sistem, obračun plač in davčno potrjevanje računov.
- Samostojno sklepanje poslov, potrjevanje dokumentov ali odločanje v imenu uporabnika z AI.
- Delna plačila, avansni in delni računi ter izvajanje denarnih nakazil.
