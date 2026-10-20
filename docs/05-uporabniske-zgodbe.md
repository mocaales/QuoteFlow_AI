# Uporabniške zgodbe

## MVP

### US-01 — Registracija in prijava

- **Funkcionalnost:** F1 · Registracija in prijava.
- **Vloga:** uporabnik.
- **Zgodba:** Kot novi uporabnik želim ustvariti račun in se prijaviti, da lahko uporabljam pravice, ki mi jih dodeli administrator.
- **Merila sprejema:**
  1. Registracija z novo e-pošto ustvari račun; z že uporabljeno e-pošto ne ustvari drugega.
  2. Pravilna prijava odpre uporabnikovo sejo; napačni prijavni podatki je ne odprejo.
  3. Registriran uporabnik brez aktivne poslovne vloge ne vidi podatkov podjetij in ne more oddati RFQ ali odobriti ponudbe.
  4. Neprijavljen uporabnik ne more dostopati do poslovnih podatkov.

### US-02 — Podjetja in dodelitev pravic

- **Funkcionalnost:** F1 · Podjetja in pravice.
- **Vloga:** administrator.
- **Zgodba:** Kot administrator želim upravljati podjetja in uporabnikom dodeliti poslovne vloge, da lahko delujejo samo za pooblaščena podjetja.
- **Merila sprejema:**
  1. Administrator lahko podjetje ustvari, popravi njegove podatke in ga deaktivira; deaktivirano podjetje ni na voljo za nove RFQ ali povabila.
  2. Obstoječemu uporabniku lahko dodeli ali odvzame vlogo nabavnika oziroma ponudnika za določeno podjetje; enake dodelitve ni mogoče podvojiti.
  3. Po odvzemu vloge uporabnik ne more več izvajati poslovnih dejanj za to podjetje, tudi če ponovno uporabi stari URL.
  4. Globalna vloga administratorja sama po sebi ne dovoljuje odobritve ponudbe.

### US-03 — Potrjen cenik

- **Funkcionalnost:** F2 · Postavke cenika.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim vnesti in potrditi postavke cenika svojega podjetja, da agent uporablja veljavne cene blaga in storitev.
- **Merila sprejema:**
  1. Ponudnik lahko vnese blago ali storitev z opisom, enoto, ceno, stroškom in morebitnim dobavnim rokom.
  2. Potrditev postavke zabeleži čas `potrjeno_ob`; neaktivne ali nepotrjene postavke agent ne uporabi.
  3. Ponudnik lahko postavko deaktivira, ne da bi izbrisal že odobrene ponudbe, ki so jo uporabile.
  4. Postavk cenika drugega podjetja ne more brati ali spreminjati.

### US-04 — Zaloga blaga

- **Funkcionalnost:** F2 · Morebitna zaloga.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim potrditi razpoložljivo zalogo blaga, da sistem pri pripravi osnutka preveri zahtevano količino.
- **Merila sprejema:**
  1. Za postavko vrste blago lahko ponudnik vnese nenegativno razpoložljivo količino; potrditev zabeleži čas preverjanja.
  2. Za postavko vrste storitev zapisa zaloge ni mogoče ustvariti.
  3. Če ponudnik za blago vodi zalogo, sistem ne označi nepokrite zahtevane količine kot preverjene zaloge.
  4. Zaloge drugega podjetja ponudnik ne more brati ali spreminjati.

### US-05 — Prodajna pravila

- **Funkcionalnost:** F2 · Pravila ponudnika.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim določiti veljavna prodajna pravila svojega podjetja, da predlogi ne presežejo dovoljenega popusta in roka ali kršijo marže.
- **Merila sprejema:**
  1. Nova različica pravil vsebuje najmanjšo maržo, največji popust, najdaljši dobavni rok in začetek veljavnosti.
  2. Za eno podjetje in isti trenutek velja največ ena različica pravil.
  3. Ponudnik ne more spremeniti pravil drugega podjetja; osnutek in odobritev uporabljata pravila istega podjetja kot ponudba.

### US-06 — Oddaja povpraševanja

- **Funkcionalnost:** F3 · RFQ s postavkami in dobavnimi zahtevami.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim oddati RFQ za svoje podjetje, da ponudniki prejmejo enako opisane zahteve.
- **Merila sprejema:**
  1. Osnutek lahko vsebuje več postavk, vsako z opisom, pozitivno količino in enoto, ter kraj in želeni datum dobave.
  2. RFQ brez vsaj ene veljavne postavke ni mogoče oddati; obrazec označi neveljavna polja.
  3. Ob oddaji sistem zapiše `oddano_ob`; določeni `rok_za_ponudbe` mora biti poznejši od oddaje.
  4. Nabavnik vidi stanje in postavke RFQ svojega podjetja, ne pa RFQ drugih podjetij.

### US-07 — Ročna izbira ponudnikov

- **Funkcionalnost:** F4 · Ročna izbira.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim sam izbrati registrirane ponudnike, da povpraševanje prejmejo podjetja, s katerimi želim sodelovati.
- **Merila sprejema:**
  1. Nabavnik lahko izbere eno ali več aktivnih registriranih podjetij, ne pa svojega podjetja.
  2. Po potrditvi nastane za vsako izbrano podjetje največ ena ponudba v stanju `povabljena` za isti RFQ.
  3. Ponovljena potrditev ne ustvari dvojnika; izvor izbire je `rocna`, razlog pa »izbral nabavnik«.
  4. Nabavnik vidi seznam izbranih podjetij, ne pa njihovih internih cen ali pravil.

### US-08 — Samodejna izbira ponudnikov

- **Funkcionalnost:** F4 · Samodejna izbira.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim dobiti sistemski izbor registriranih ponudnikov z razlogom ujemanja, da lahko RFQ pošljem primernim podjetjem.
- **Merila sprejema:**
  1. Sistem predlaga aktivna registrirana podjetja z ujemajočimi se aktivnimi, potrjenimi postavkami cenika.
  2. Pri vsakem predlogu pokaže razlog izbire; spletno odkritih in neregistriranih podjetij ne vključuje.
  3. Po potrditvi ustvari največ eno ponudbo v stanju `povabljena` za par RFQ–podjetje in shrani samodejni izvor ter razlog.
  4. Če ujemanja ni, to pove in ne ustvari praznega povabila.

### US-09 — Razumevanje RFQ

- **Funkcionalnost:** F5 · AI-analiza zahtev.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim videti agentov predlog razumevanja RFQ, da lahko preverim ujemanje s ponudbo svojega podjetja.
- **Merila sprejema:**
  1. Agent iz opisa RFQ vrne strukturiran predlog zahtevanih postavk, količin in enot.
  2. Za posameznega ponudnika predlaga samo postavke njegovega aktivnega, potrjenega cenika.
  3. Dvoumno ujemanje ali manjkajoč podatek označi za ročni pregled; agent ne izmisli cene, stroška ali zaloge.
  4. Ponudnik ne vidi predloga ali podatkov cenika drugega podjetja.

### US-10 — Izračunan osnutek

- **Funkcionalnost:** F5 · Ločen osnutek in deterministična preverjanja.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim dobiti izračunan osnutek za svoje povabilo, da lahko pred odobritvijo vidim cene in morebitne kršitve pravil.
- **Merila sprejema:**
  1. Za vsako povabljeno podjetje nastane ločen osnutek za isti RFQ; njegovi viri pripadajo temu podjetju.
  2. Programska logika preveri ceno, strošek, maržo, popust, dobavni rok in morebitno zalogo glede na veljavna pravila.
  3. Ob manjkajočem viru ali kršitvi osnutek navede konkretno težavo in zahteva ročni pregled; sistem ne ugiba vrednosti.
  4. Nabavnik osnutka ne vidi in agent ga ne more odobriti.

### US-11 — Popravek osnutka

- **Funkcionalnost:** F6 · Pregled in popravek.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim popraviti postavke svojega osnutka, da lahko pred odločitvijo odpravim napake ali dopolnim manjkajoče podatke.
- **Merila sprejema:**
  1. Aktivni ponudnik vidi le osnutke svojega podjetja z njihovimi postavkami in opozorili.
  2. Lahko spremeni količino, ceno, strošek ali popust ter shrani popravek le v stanju `osnutek` ali `v_pregledu`.
  3. Po shranjenem popravku sistem ponovno izračuna zneske in preveri maržo, popust, rok in morebitno zalogo.
  4. Shranjevanje popravka samo po sebi ne odobri ponudbe in je ne pokaže nabavniku.

### US-12 — Odobritev ali zavrnitev

- **Funkcionalnost:** F6 · Izrecna odločitev ponudnika.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim osnutek izrecno odobriti ali zavrniti, da v imenu podjetja nadzorujem izdajo ponudbe.
- **Merila sprejema:**
  1. Odločitev lahko sprejme le uporabnik z aktivno vlogo ponudnika pri podjetju te ponudbe.
  2. Pred odobritvijo sistem znova preveri popolnost postavk, cene, stroške, maržo, popust, rok in morebitno zalogo; ob kršitvi pokaže razlog in odobritev zavrne.
  3. Izrecni »Odobri« po uspešnem preverjanju nastavi `odobrena`; »Zavrni« nastavi `zavrnjena` in ponudbe ne objavi nabavniku.
  4. Ob odobritvi sistem zabeleži odobriteljevo vlogo in čas; agent tega dejanja ne more izvesti.

### US-13 — Vidnost odobrene ponudbe

- **Funkcionalnost:** F7 · Odobrena ponudba, sledljivost in zaklep.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim videti le odobrene ponudbe za svoj RFQ, da odločam na podlagi veljavnih podatkov brez vpogleda v ponudnikove interne stroške.
- **Merila sprejema:**
  1. Kupec za svoj RFQ vidi le ponudbe v stanju `odobrena`; povabila, osnutki in zavrnitve niso prikazani kot prejete ponudbe.
  2. Odobrena ponudba pokaže ponudnika, postavke, cene, skupni znesek, valuto, dobavni rok in čas odobritve, ne pa stroškov ali marž.
  3. Ob odobritvi se zabeležijo odobriteljeva vloga, čas in različica; odobrena ponudba s postavkami se zaklene.
  4. Uporabnik, ki ne pripada kupcu ali ponudniku te ponudbe, je ne more pridobiti s spremembo URL-ja ali identifikatorja.

## Predvidene poznejše funkcionalnosti

### US-14 — Primerjava ponudb

- **Funkcionalnost:** F8 · Primerjava odobrenih ponudb.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim primerjati odobrene ponudbe za isti RFQ, da lahko ocenim ceno in dobavne pogoje.
- **Merila sprejema:**
  1. Primerjava vsebuje le odobrene ponudbe za RFQ kupčevega podjetja.
  2. Prikazani so vsaj ponudnik, skupni znesek, valuta in dobavni rok vsake ponudbe.
  3. Pri manj kot dveh odobrenih ponudbah sistem pove, da primerjava še ni mogoča; ponudb v različnih valutah brez pretvorbe ne razvršča po znesku.
  4. Interni stroški in marže niso v prikazu ali njegovem podatkovnem odgovoru.

### US-15 — Izvoz ponudbe

- **Funkcionalnost:** F9 · PDF odobrene ponudbe.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim prenesti odobreno ponudbo v PDF, da jo lahko shranim v svojem podjetju.
- **Merila sprejema:**
  1. Izvoz je na voljo samo za odobreno ponudbo RFQ kupčevega podjetja.
  2. PDF vsebuje identifikator ponudbe, ponudnika, postavke, cene, skupni znesek, valuto in datum odobritve.
  3. PDF ne vsebuje internih stroškov, marž, pravil ali podatkov drugih podjetij.
  4. Zahteva za tuj ali neodobren zapis ne vrne dokumenta.

### US-16 — Obvestilo ponudniku

- **Funkcionalnost:** F10 · Obvestilo o novem osnutku.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim izvedeti, da je za moje podjetje pripravljen osnutek, da ga lahko pregledam.
- **Merila sprejema:**
  1. Ob nastanku osnutka sistem obvesti določeni aktivni kontakt ponudnika; če ta ni določen, obvesti aktivne ponudnike povabljenega podjetja.
  2. Obvestilo v aplikaciji vsebuje povezavo do ponudbe in stanje prebranosti.
  3. E-pošta vsebuje povezavo do aplikacije, ne pa internih cen ali stroškov.
  4. Ponovna obdelava istega dogodka ne ustvari dvojnika; neuspešna dostava ostane označena za ponovni poskus.

### US-17 — Obvestilo nabavniku

- **Funkcionalnost:** F10 · Obvestilo o odobreni ponudbi.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim izvedeti, da je ponudnik odobril ponudbo za moj RFQ, da jo lahko odprem.
- **Merila sprejema:**
  1. Ob odobritvi se obvestilo ustvari le za aktivne nabavnike podjetja, ki je oddalo RFQ.
  2. Obvestilo v aplikaciji in e-pošta vsebujeta povezavo do odobrene ponudbe.
  3. Obvestilo ne razkrije internih stroškov ponudnika in ni poslano drugemu kupčevemu podjetju.
  4. Ponovna obdelava iste odobritve ne povzroči podvojenega pošiljanja.

### US-18 — Zgodovina različic

- **Funkcionalnost:** F11 · Spremembe ponudbe in odločitve.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim videti spremembe med različicami svojega osnutka, da lahko pred odobritvijo preverim popravke.
- **Merila sprejema:**
  1. Shranjen popravek ustvari novo različico z datumom in vlogo izvajalca.
  2. Primerjava dveh različic pokaže spremembe postavk, cen, količin in popustov.
  3. Odobritev ali zavrnitev ostane v zgodovini z izvajalcem in časom.
  4. Ponudnik ne more brati zgodovine drugega podjetja; odobrena različica ostane nespremenjena.

### US-19 — Analitika procesa

- **Funkcionalnost:** F12 · Trajanje, odzivnost in popravki.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim spremljati trajanje priprave ponudb svojega podjetja, da lahko odkrijem ozka grla.
- **Merila sprejema:**
  1. Za izbrano obdobje pregled pokaže število povabil, odobritev in zavrnitev lastnega podjetja.
  2. Čas odziva se izračuna od nastanka ponudbe do odobritve ali zavrnitve; odprte ponudbe niso v povprečju zaključenih.
  3. Število popravkov se izračuna iz shranjenih različic.
  4. Pregled ne razkrije cenikov, stroškov ali ponudb drugih podjetij.

### US-20 — Predloga RFQ

- **Funkcionalnost:** F13 · Predloge pogostih povpraševanj.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim iz RFQ shraniti predlogo, da lahko podobno povpraševanje pripravim hitreje.
- **Merila sprejema:**
  1. Predloga za kupčevo podjetje shrani naziv, postavke in dobavne zahteve.
  2. Uporaba predloge ustvari nov osnutek RFQ, ne oddanega povpraševanja.
  3. Spremembe novega osnutka ne spremenijo predloge ali prejšnjega RFQ.
  4. Predloge drugega podjetja uporabnik ne more odpreti.

### US-21 — Opomnik ponudniku

- **Funkcionalnost:** F14 · Rok za odgovor na RFQ.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim prejeti opomnik pred rokom za odgovor, da ne spregledam odprtega povabila.
- **Merila sprejema:**
  1. Opomnik nastane 24 ur pred `rok_za_ponudbe`, če je rok določen in ponudba še ni odobrena ali zavrnjena; pri krajšem roku nastane ob povabilu.
  2. Vsebuje RFQ, rok in povezavo do ponudbe, ne pa podatkov drugih ponudnikov.
  3. Za isto ponudbo in rok se pošlje največ enkrat; po pretečenem roku se ne pošlje.

### US-22 — Opomnik nabavniku

- **Funkcionalnost:** F14 · Veljavnost odobrene ponudbe.
- **Vloga:** nabavnik.
- **Zgodba:** Kot nabavnik želim prejeti opomnik pred potekom veljavnosti odobrene ponudbe, da jo lahko pravočasno pregledam.
- **Merila sprejema:**
  1. Opomnik nastane 24 ur pred `velja_do` za odobreno ponudbo in RFQ kupčevega podjetja; če ob odobritvi ostane manj kot 24 ur, nastane takoj.
  2. Vsebuje ponudnika, čas poteka in povezavo do ponudbe, ne pa internih stroškov.
  3. Za isto ponudbo se pošlje največ enkrat; po poteku `velja_do` se ne pošlje.

### US-23 — Zasebno pojasnilo

- **Funkcionalnost:** F15 · Vprašanja in pojasnila glede RFQ.
- **Vloga:** ponudnik.
- **Zgodba:** Kot ponudnik želim nabavnika zasebno vprašati o nejasni zahtevi RFQ, da lahko pripravim ustrezno ponudbo.
- **Merila sprejema:**
  1. Vprašanje je vezano na konkretno povabilo in vidno le njegovemu ponudniku ter nabavnikovemu podjetju.
  2. Nabavnik lahko odgovori v isti niti; zapisa vsebujeta avtorja in čas.
  3. Ponudnik drugega podjetja niti ne vidi, četudi je povabljen na isti RFQ.
  4. Pojasnilo ne spremeni RFQ ali odobrene ponudbe brez ločenega dejanja uporabnika.
