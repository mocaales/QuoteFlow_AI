# Uporabniške zgodbe

Zgodbe sledijo [potrjenemu obsegu](02-funkcionalnosti-in-obseg.md): **US-01–US-22** pokrivajo 22 predvidenih funkcionalnosti, **US-23–US-27** pa pet možnih nadgradenj. **US-01–US-07 so MVP; US-08 je bila 2026-11-07 vključena v trenutni obseg.** Oznaka US-xx se v tem dokumentu preslika v Fx; označuje načrtovano vedenje, ne potrjene izvedbe.

Novi pomen oznak nadomešča stari obseg RFQ. Zgodovinski razvojni zapisi in obstoječe GitHub naloge ohranijo prvotni pomen; brez izrecne uskladitve niso dokaz izvedbe spodnjih zgodb. Dostop in izračuni upoštevajo [podatkovni model](03-podatkovni-model.md). Poznejše funkcionalnosti lahko zahtevajo njegove razširitve.

## MVP

### US-01 — Identiteta, pravice in prošnja mojstra

**Funkcionalnost:** F1 · **Vloga:** stranka ali delavec.

Kot stranka ali delavec želim uporabljati svoj račun in zaprositi za status mojstra s podatki podjetja, da lahko vodim svoje podjetje po odobritvi.

**Merila sprejema:**

1. Potrjena registracija ustvari globalno vlogo `stranka`; napačna prijava ne odpre seje, odjava pa prepreči nadaljnje poslovne zahtevke s to sejo.
2. Prošnjo je mogoče oddati s podatki podjetja iz modela; manjkajoča obvezna polja preprečijo oddajo.
3. Adminova odobritev v eni transakciji ustvari podjetje, lastništvo in aktivno dodelitev `mojster`; zavrnitev ne ustvari nobenega od teh zapisov.
4. Admin lahko upravlja dodelitve pravic; odvzem velja pri naslednjem poslovnem zahtevku. Lastniku ni mogoče odvzeti edine veljavne dodelitve mojstra njegovega podjetja.
5. Mojster podjetja A, ki je delavec podjetja B, ne more z mojstrskimi pravicami urejati B. Globalni admin brez poslovne dodelitve ne more poslati ponudbe ali odločiti namesto stranke.

### US-02 — Cenik, vrste dela in materiali

**Funkcionalnost:** F2 · **Vloga:** mojster.

Kot mojster želim urejati vrste dela, cenik ter materiale in zalogo svojega podjetja, da lahko ponovno uporabim podatke pri pripravi ponudbe.

**Merila sprejema:**

1. Vrsta dela shrani naziv, opis, urno postavko, število ur in število delavcev (1–1000); cena dela je izpeljana (`urna_postavka × stevilo_ur × stevilo_delavcev`, zaokroženo na 2 decimalki). Vrsta dela brez dela ima ceno 0 €.
2. Vrsta dela ima nič, enega ali več materialov istega podjetja s pozitivno količino na enoto dela (največ 50); neaktivnega materiala ni mogoče dodati. Vrst dela je na podjetje največ 500.
3. Postavka cenika shrani naziv, opis, obvezno vrsto dela, mersko enoto (`m`, `m2`, `m3`, `kos`), nenegativno ceno in stopnjo DDV; neveljavne vrednosti in neznana enota so zavrnjene.
4. Material ima vrsto, šifro, naziv, enoto in ceno; isti material ima lahko ločeno nenegativno količino na več lokacijah. Zaloga ni vezana na vrsto dela ali postavko.
5. Zahtevek z identifikatorjem vrste dela, cenika, materiala ali zaloge drugega podjetja ne omogoči branja ali spremembe tega zapisa.

### US-03 — Začetek projekta

**Funkcionalnost:** F3 · **Vloga:** mojster.

Kot mojster želim ustvariti projekt za stranko in opisati predvideno delo, da lahko vodim pregled zahteve in morebitni ogled.

**Merila sprejema:**

1. Projekt z nazivom, opisom in lokacijo pripada izbranemu lastnemu podjetju in obstoječemu uporabniku z aktivno vlogo `stranka`; začne v fazi `pregled`.
2. Mojster lahko uvede fazo `ogled` ali jo preskoči; brez poslane ponudbe ne more ročno nastaviti faze `ponudba`.
3. Stranka vidi samo svoje projekte; drug mojster brez dodelitve pri podjetju projekta ne more odpreti ali urejati.

### US-04 — Priprava ponudbe

**Funkcionalnost:** F4 · **Vloga:** mojster.

Kot mojster želim v projekt dodati postavke z izmerami in iz njih pripraviti ponudbo, da dobim preverljiv izračun pred pošiljanjem.

**Merila sprejema:**

1. Postavka projekta ima naziv, opis, obvezno vrsto dela, mersko enoto, ceno na enoto, pozitivno količino (privzeto 1), popust, DDV in delovne podatke (urna postavka, ure, delavci; privzeto iz vrste dela, urejeno po postavki). Mojster jo doda iz cenika ali ustvari novo in jo ureja, dokler ponudba ni poslana.
2. Izmere določajo količino: `m` dolžina, `m2` dolžina in višina, `m3` dolžina, višina in širina, `kos` samo število kosov; `kosi` množi vsako enoto. Vsaka izmera se prišteje ali odšteje; vsota ne sme biti negativna, za pošiljanje mora biti pri vsaki postavki večja od nič.
3. Izračun po formuli A: za 20 m² × 1 × 10 €, delo 25 € × 8 h × 2 delavca, popust 10 % in DDV 22 % sistem izračuna 540,00 € neto, 118,80 € DDV in 658,80 € končne cene. Material je vključen v ceno na enoto in se ne prišteje še enkrat; vsote dokumenta so vsote zaokroženih vrstic.
4. Ob pošiljanju nastane nespremenljiv posnetek postavk, izmer, materialov in dela; poznejša sprememba projekta, cenika, vrste dela ali cene materiala ga ne spremeni.
5. Osnutek ni viden stranki; stranka v poslani ponudbi ne vidi urne postavke, ur, števila delavcev ali materialov.

## Poznejši razvoj

### US-08 — Delavci podjetja

**Funkcionalnost:** F8 · **Vloga:** mojster · **Stanje:** vključeno v trenutni obseg in izvedeno (uvedeno 2026-11-08; [razvojni zapis](razvoj/admin-in-delavci-us-08.md)).

Kot mojster želim upravljati dodelitve delavcev svojega podjetja, da lahko določim sodelavce brez posega v njihove druge vloge.

**Merila sprejema:**

1. Mojster delavca povabi z e-poštnim naslovom (povabilo poteče po 14 dneh); odgovor je enak za neznan, nepotrjen, administratorski, neustrezen in nov naslov, zato obstoja računa ni mogoče ugotoviti. Vloga `delavec` nastane šele, ko povabljeni s potrjeno e-pošto povabilo sprejme v svojem računu (ali ga zavrne); mojster lahko odprto povabilo prekliče. Sprejem znova preveri pogoje; ob neizpolnjenih je odgovor splošen.
2. Enako odprto povabilo in enaka aktivna dodelitev se ne podvojita; odvzem ukine dostop delavca pri naslednjem zahtevku, ponovna dodelitev ponovno aktivira isto vrstico, zgodovina pa ostane ohranjena.
3. Dodajanje ali odvzem delavca v podjetju A ne spremeni njegovih vlog pri B in mu ne dodeli vloge mojstra; mojster dodeljuje samo `delavec` (prek povabila); neposredna dodelitev vlog je samo za admina. Ime in e-pošto delavca vidi šele po sprejemu.
4. Admin v pogledu »Podjetja in pravice« išče po podjetjih (vsi člani in vloge) in po uporabnikih (kje dela, katere vloge ima), filtrira po vlogi in stanju ter vloge odvzame ali ponovno aktivira; lastniku ni mogoče odvzeti vloge mojster.

### US-09 — Ekipe

**Funkcionalnost:** F9 · **Vloga:** mojster.

Kot mojster želim združevati delavce v ekipe, da lahko organiziram sodelavce svojega podjetja.

**Merila sprejema:**

1. Ekipa ima naziv in pripada podjetju; član je lahko samo uporabnik z aktivno dodelitvijo delavca pri tem podjetju.
2. Isti delavec je lahko v več ekipah, istega članstva pa ni mogoče podvojiti.
3. Poskus vključitve delavca drugega podjetja je zavrnjen; odstranitev iz ene ekipe ne odstrani drugih članstev.

### US-10 — Dodeljeni projekti delavca

**Funkcionalnost:** F10 · **Vloga:** delavec.

Kot delavec želim videti projekte in termine svojih ekip, da vem, kje in kdaj je predvideno moje delo.

**Merila sprejema:**

1. Mojster lahko projektu dodeli več ekip istega podjetja; ekipo drugega podjetja sistem zavrne.
2. Delavec vidi projekt in njegov termin samo ob aktivni dodelitvi delavca, članstvu v aktivni ekipi in povezavi te ekipe s projektom.
3. Odstranitev zadnje povezave do projekta ukine dostop pri naslednjem zahtevku; pogled delavca ne razkrije ponudbenih cen ali računov.

### US-11 — PDF dokumentov

**Funkcionalnost:** F11 · **Vloga:** mojster ali stranka.

Kot mojster ali stranka želim prenesti poslano ponudbo oziroma izdani račun v PDF, da lahko dokument shranim zunaj aplikacije.

**Merila sprejema:**

1. PDF ponudbe ohrani številko, različico, stranki, postavke in vsote iz izbrane poslane ponudbe; PDF računa uporabi podatke izdanega računa.
2. Stranka lahko prenese samo dokument svojega projekta; osnutki in dokumenti druge stranke ji niso dostopni.
3. PDF ne razkrije internih opomb, zalog ali materialnih kalkulacij; izvoz ne spremeni stanja dokumenta.

### US-12 — E-poštna obvestila

**Funkcionalnost:** F12 · **Vloga:** mojster ali stranka.

Kot mojster ali stranka želim prejeti e-poštno obvestilo o pomembnem poslovnem dogodku, da pravočasno opazim spremembo.

**Merila sprejema:**

1. Poslana ponudba in izdani račun sprožita obvestilo stranki, odločitev stranke mojstru, določitev ali sprememba termina pa stranki.
2. Obvestilo nastane šele po uspešno potrjenem poslovnem dogodku in vsebuje povezavo, ki še vedno zahteva prijavo ter ustrezne pravice.
3. Napaka pri dostavi ne razveljavi poslovnega dogodka; zabeleži se za ponovni poskus. Ponovna obdelava istega dogodka ne ustvari novega obvestila; ponovitve dostave uporabljajo isti identifikator, uspešno dostavljena obvestila pa se ne pošiljajo znova.

### US-13 — Primerjava različic

**Funkcionalnost:** F13 · **Vloga:** mojster.

Kot mojster želim primerjati dve različici ponudbe istega projekta, da lahko preverim, kaj se je spremenilo.

**Merila sprejema:**

1. Primerjava označi dodane in odstranjene postavke ter spremembe količin, cen, popustov, DDV in končnega zneska.
2. Primerjava uporablja shranjene podatke različic, ne trenutnega cenika, ter jasno navede obe številki različic.
3. Mojster ne more primerjati ponudb drugega podjetja; primerjava ne spremeni nobene različice.

### US-14 — Pregled poslovanja

**Funkcionalnost:** F14 · **Vloga:** mojster.

Kot mojster želim videti projekte po fazah in zneske računov, da lahko spremljam stanje svojega podjetja.

**Merila sprejema:**

1. Pregled prikaže število projektov za vsako fazo lastnega podjetja; faza brez projektov ima vrednost nič.
2. Vsote izdanih, plačanih in neplačanih računov vključijo samo izdane račune; vsota plačanih in neplačanih je enaka vsoti izdanih.
3. Osnutki in računi drugih podjetij niso vključeni; pregled ne prikazuje izmišljenega trajanja faz brez podatkov o zgodovini prehodov.

### US-15 — Potrebe po materialu

**Funkcionalnost:** F15 · **Vloga:** mojster.

Kot mojster želim primerjati materiale ponudbe z zalogo, da pred izvedbo opazim primanjkljaje.

**Merila sprejema:**

1. Pri 20 m² dela in sestavi 3 kg/m² sistem izračuna 60 kg potrebnega materiala ter sešteje potrebe istega materiala iz vseh postavk.
2. Če je na lokacijah skupaj 45 kg istega materiala, prikaže 15 kg primanjkljaja; materialov ali različnih enot ne sešteva brez določene pretvorbe.
3. Pregled uporablja materialni posnetek ponudbe in samo zalogo njenega podjetja; izračun ne rezervira ali zmanjša zaloge.

### US-16 — AI analiza zahteve

**Funkcionalnost:** F16 · **Vloga:** mojster.

Kot mojster želim dobiti strukturiran predlog iz prostega opisa projekta, da hitreje prepoznam zahtevana dela in odprta vprašanja.

**Merila sprejema:**

1. Predlog loči prepoznana dela, izrecno navedene količine in manjkajoče podatke; pri opisu »rušenje estriha 40 m²« ohrani 40 m².
2. Če opis ne vsebuje količine ali enote, jo označi kot manjkajočo in je ne zapiše kot potrjeno vrednost.
3. Analiza uporablja samo dovoljeni projekt; brez potrditve mojstra ne spremeni ponudbe, cen ali faz projekta.

### US-17 — AI predlog ponudbe

**Funkcionalnost:** F17 · **Vloga:** mojster.

Kot mojster želim dobiti predlagane postavke iz svojega cenika, da lahko hitreje pripravim osnutek ponudbe.

**Merila sprejema:**

1. Vsaka predlagana povezava na cenik ali material pripada podjetju projekta; neznano delo je označeno za ročno dopolnitev.
2. Cene in materialna sestava izhajajo iz dovoljenih shranjenih podatkov, izračune pa izvede deterministična koda; AI si ne ustvari cene ali zaloge.
3. Predlog ostane ločen od poslane vsebine; mojster izrecno izbere in potrdi postavke za osnutek ter ponudbo pošlje po običajnem postopku.

### US-18 — AI pregled obsega

**Funkcionalnost:** F18 · **Vloga:** mojster.

Kot mojster želim dobiti opozorila o obsegu ponudbe, da lahko pred pošiljanjem preverim neskladja.

**Merila sprejema:**

1. Pregled primerja opis projekta z osnutkom ter posebej označi morebitna manjkajoča, podvojena ali neskladna dela.
2. Vsako opozorilo navede povezano postavko oziroma del opisa in razlog; negotov sklep je označen kot predlog za pregled.
3. Opozorilo samo ne doda, odstrani ali podraži postavke in ne omogoči dostopa do podatkov drugega podjetja.

### US-19 — AI pomoč pri opisu

**Funkcionalnost:** F19 · **Vloga:** mojster.

Kot mojster želim izboljšati besedilo dela ali pojasnila stranki, da je vsebina razumljivejša.

**Merila sprejema:**

1. Pred uporabo sta vidna izvirnik in predlog besedila; mojster lahko predlog zavrne ali izrecno uporabi.
2. Uporaba predloga ne spremeni količine, merske enote, cene, popusta, DDV ali končnega zneska.
3. Poslane ponudbe ni mogoče prepisati s predlogom; sprememba njenega besedila zahteva novo različico.

### US-20 — AI povzetek projekta

**Funkcionalnost:** F20 · **Vloga:** mojster.

Kot mojster želim prejeti povzetek projekta in predlagane naslednje korake, da lažje nadaljujem delo.

**Merila sprejema:**

1. Povzetek navede trenutno fazo, stanje ponudbe oziroma računa in dovoljene dogovore iz izbranega projekta.
2. Predlagani naslednji koraki so ločeni od ugotovljenih dejstev; manjkajoči dogovor ali termin ni predstavljen kot potrjen.
3. Povzetek ne vključuje drugih podjetij ali nedostopnih opomb ter ne spreminja terminov, dokumentov ali stanja projekta.

### US-21 — Projektne priponke

**Funkcionalnost:** F21 · **Vloga:** mojster.

Kot mojster želim dodati fotografije in dokumente projektu, da imam meritve in dokumentacijo ogleda pri istem delu.

**Merila sprejema:**

1. Priponka je vezana na konkreten projekt in ima ime, vrsto datoteke ter podatek, ali je dovoljena stranki; nedovoljena vrsta ali presežena objavljena omejitev velikosti prepreči nalaganje.
2. Stranka lahko prenese samo njej vidne priponke lastnega projekta; neposredna povezava ne obide preverjanja pravic.
3. Datoteka drugega projekta oziroma podjetja ne postane dostopna s spremembo identifikatorja; neuspešno nalaganje ne ustvari veljavne priponke.

### US-22 — Projektne opombe in pojasnila

**Funkcionalnost:** F22 · **Vloga:** mojster ali stranka.

Kot mojster ali stranka želim izmenjati pojasnila na projektu, da so dogovori povezani s pravim delom.

**Merila sprejema:**

1. Stranka lahko objavi pojasnilo samo pri svojem projektu; mojster odgovori v okviru podjetja projekta.
2. Mojster lahko označi opombo kot interno; stranka je ne prejme prek prikaza, API ali izvoza.
3. Vsaka opomba prikaže avtorja in čas; uporabnik brez pravice do projekta je ne more dodati ali prebrati.

## Možne nadgradnje

Te zgodbe so pogojni nadaljnji obseg; niso del MVP ali obveza prvega razvojnega načrta.

### US-23 — Ure in napredek dela

**Funkcionalnost:** F23 · **Vloga:** delavec.

Kot delavec želim zapisovati ure in napredek dodeljenega dela, da lahko poročam o izvedbi.

**Merila sprejema:**

1. Vnos vsebuje datum, pozitivno trajanje in opis pri projektu, do katerega ima delavec veljaven dostop prek ekipe.
2. Delavec ne more pisati ur v imenu drugega uporabnika ali na nedodeljen projekt; mojster vidi vnose lastnega podjetja.
3. Poročilo delavca samo ne izda računa ali zaključi projekta; poslovni zaključek ostane ločeno dejanje mojstra.

### US-24 — Premiki, rezervacije in poraba

**Funkcionalnost:** F24 · **Vloga:** mojster.

Kot mojster želim evidentirati premike in projektno porabo materiala, da lahko sledim dejanskemu stanju zaloge.

**Merila sprejema:**

1. Premik med lokacijama istega podjetja v eni transakciji zmanjša izvor in poveča cilj za enako pozitivno količino.
2. Rezervacija je vezana na projekt in ne preseže razpoložljive količine po odštetih aktivnih rezervacijah.
3. Dejanska poraba je vezana na projekt in ustrezno zmanjša zalogo ter rezervacijo; neveljavna količina ne povzroči delne spremembe.

### US-25 — Razpoložljivost ekip

**Funkcionalnost:** F25 · **Vloga:** mojster.

Kot mojster želim usklajevati termine z razpoložljivostjo ekip, da preprečim dvojne dodelitve.

**Merila sprejema:**

1. Koledar pokaže termine dodeljenih projektov in vnesene odsotnosti za lastno podjetje.
2. Pred potrditvijo termina zazna prekrivanje iste ekipe ali delavca, tudi če je ta član več ekip.
3. Konflikt navede prekrivajoči se interval; koledar ne razkrije projektov podjetja, pri katerem uporabnik nima ustrezne pravice.

### US-26 — Računovodska in bančna povezava

**Funkcionalnost:** F26 · **Vloga:** mojster.

Kot mojster želim povezati dokumente in bančne evidence z zunanjim sistemom, da zmanjšam podvajanje podatkov.

**Merila sprejema:**

1. Izvoz izdanega računa ohrani številko in znesek; ponovitev istega izvoza ne ustvari drugega računa v zunanji evidenci.
2. Uvožena bančna evidenca predlaga povezavo z računom istega podjetja; dvoumno ali delno plačilo ne označi računa kot plačanega.
3. Potrditev usklajenega celotnega plačila uporabi veljaven poslovni postopek zaključka; povezava ne izvaja denarnih nakazil.

### US-27 — AI analiza fotografij in dokumentov

**Funkcionalnost:** F27 · **Vloga:** mojster.

Kot mojster želim dobiti predlog obsega del iz projektnih priponk, da lažje pripravim začetno oceno.

**Merila sprejema:**

1. AI prejme samo dovoljene priponke konkretnega projekta; ugotovitev navede izvorno fotografijo ali dokument.
2. Nezanesljive mere, količine in poškodbe označi kot negotove; iz fotografije ne zapiše ocene kot potrjene meritve.
3. Mojster mora predlog izrecno pregledati pred uporabo; analiza sama ne ustvari poslane ponudbe, cene ali poslovne odločitve.
