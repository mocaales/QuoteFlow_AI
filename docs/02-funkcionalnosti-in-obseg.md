# Funkcionalnosti in obseg

Rešitev predvideva **15 funkcionalnosti**: sedem za prvo delujočo različico (MVP) in osem za poznejši razvoj. Ločeno je navedenih pet možnih nadgradenj. Skupaj je opisanih 20 funkcionalnosti.

## Uporabniške vloge

| Vloga | Možnosti in pravice |
|---|---|
| Nabavnik | Za podjetje, pri katerem ima pravico nabavnika, odda RFQ, izbere podjetja ponudnikov, spremlja stanje in vidi samo odobrene ponudbe za svoj RFQ. |
| Ponudnik | Za podjetje, pri katerem ima pravico ponudnika, ureja cenik blaga in storitev, morebitne zaloge ter pravila. Vidi povpraševanja, h katerim je podjetje povabljeno, in svoje osnutke; ponudbo lahko popravi, zavrne ali izrecno odobri. |
| Administrator | Kot globalna vloga upravlja podjetja in dodelitve pravic. Nima privzete pravice odobriti ponudbe ali brati internih kalkulacij ponudnika. |

AI-agent je **sistemski akter**, ne uporabniška vloga. Pripravi osnutke, vendar ne more odobriti ponudbe ali je narediti vidne nabavniku.

## Predvidene funkcionalnosti

| ID | Funkcionalnost | Obseg |
|---|---|---|
| F1 | Registracija, prijava, podjetja in enotne dodelitve pravic uporabnikom. | **MVP** |
| F2 | Ponudnik vnese in potrdi postavke cenika za blago ali storitve, cene, stroške, morebitne zaloge, dobavne roke in prodajna pravila. | **MVP** |
| F3 | Nabavnik odda RFQ s postavkami, količinami in dobavnimi zahtevami ter spremlja njegovo stanje. | **MVP** |
| F4 | Nabavnik ročno izbere registrirana podjetja ponudnikov ali jih sistem samodejno poišče; za vsako ustvari en zapis ponudbe v stanju `povabljena` in zabeleži razlog izbire. | **MVP** |
| F5 | AI-agent analizira RFQ; sistem za vsakega ponudnika iz potrjenih podatkov pripravi ločen osnutek ter programsko preveri cene, morebitne zaloge, marže in pravila. | **MVP** |
| F6 | Ponudnik osnutek pregleda, popravi, zavrne ali izrecno odobri; po spremembi se izračuni ponovijo. | **MVP** |
| F7 | Nabavnik vidi samo odobrene ponudbe brez internih stroškov; sistem shrani različico, odobritelja in čas odobritve ter zaklene ponudbo. | **MVP** |
| F8 | Nabavnik primerja odobrene ponudbe za isti RFQ po ceni in dobavnih pogojih. | Pozneje |
| F9 | Izvoz odobrene ponudbe v PDF brez internih stroškov ponudnika. | Pozneje |
| F10 | Obvestila v aplikaciji in po e-pošti ob novem osnutku ali odobreni ponudbi. | Pozneje |
| F11 | Pregled sprememb med različicami ponudbe in zgodovine odločitev. | Pozneje |
| F12 | Analitika trajanja obdelave, odzivnosti in popravkov za lastno podjetje. | Pozneje |
| F13 | Predloge pogostih povpraševanj za pripravo novega RFQ. | Pozneje |
| F14 | Opomniki ob bližajočem se roku odgovora ali poteku veljavnosti ponudbe. | Pozneje |
| F15 | Zasebna vprašanja in pojasnila med nabavnikom in posameznim ponudnikom glede RFQ. | Pozneje |

F4, F5 in F6 so domensko specifične funkcionalnosti, ki presegajo osnovno dodajanje, pregledovanje, urejanje in brisanje zapisov. F1–F7 tvorijo delujoč tok od povpraševanja do odobrene ponudbe.

## Pet možnih nadgradenj

| ID | Nadgradnja |
|---|---|
| F16 | Iskanje dodatnih ponudnikov po spletu z navedbo vira in časa; neregistrirano podjetje ne more izdati potrjene ponudbe v aplikaciji. |
| F17 | Dovoljeno pridobivanje javnih podatkov s spletnih strani; ti ostanejo nepotrjeni do ponudnikove potrditve. |
| F18 | Povezava s ponudnikovim ERP za osveževanje cenika in zalog blaga. |
| F19 | Večstopenjska odobritev ponudb, ki odstopajo od poslovnih pravil. |
| F20 | Podpora več valutam in merskim enotam z določenimi pravili pretvorbe. |

## Izven obsega projekta

- Sprejem naročil in izvedba dobave.
- Računi, plačila in računovodstvo.
- Avtonomna odobritev ali sklepanje poslov v imenu ponudnika.
- Projektiranje izdelkov po meri.
