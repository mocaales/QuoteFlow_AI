# Funkcionalnosti in obseg

Rešitev predvideva **15 funkcionalnosti**: sedem za prvo delujočo različico (MVP) in osem za poznejši razvoj. Ločeno je navedenih pet možnih nadgradenj. Skupaj je opisanih 20 funkcionalnosti.

## Uporabniške vloge

| Vloga | Možnosti in pravice |
|---|---|
| Nabavnik | Za svoje podjetje odda RFQ, izbere ponudnike, spremlja stanje in vidi samo odobrene ponudbe, naslovljene nanj. |
| Ponudnik | Za svoje podjetje ureja katalog in prodajna pravila ter vidi dodeljene RFQ in lastne osnutke. Ponudbo lahko popravi, zavrne ali odobri. |
| Administrator | Upravlja podjetja, članstva in uporabniški dostop. Nima privzete pravice odobriti ponudbe namesto ponudnika ali brati njegovih internih kalkulacij. |

AI-agent je **sistemski akter**, ne uporabniška vloga. Pripravi osnutke, vendar ne more odobriti ali objaviti ponudbe.

## Predvidene funkcionalnosti

| ID | Funkcionalnost | Obseg |
|---|---|---|
| F1 | Registracija, prijava, podjetja, članstva in uporabniške pravice. | **MVP** |
| F2 | Ponudnik vnese in potrdi izdelke, cene, stroške, zaloge, dobavne roke in prodajna pravila. | **MVP** |
| F3 | Nabavnik odda RFQ s postavkami, količinami in dobavnimi zahtevami ter spremlja njegovo stanje. | **MVP** |
| F4 | Nabavnik ročno izbere registrirane ponudnike ali sistem samodejno poišče ustrezne in zabeleži razloge izbire. | **MVP** |
| F5 | AI-agent analizira RFQ; sistem za vsakega ponudnika iz potrjenih podatkov pripravi ločen osnutek ter programsko preveri cene, zaloge, marže in pravila. | **MVP** |
| F6 | Ponudnik osnutek pregleda, popravi, zavrne ali izrecno odobri; po spremembi se izračuni ponovijo. | **MVP** |
| F7 | Nabavnik vidi samo odobrene ponudbe; sistem shrani različico, odločevalca in čas odobritve. | **MVP** |
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
| F18 | Povezava s ponudnikovim ERP za osveževanje kataloga in zalog. |
| F19 | Večstopenjska odobritev ponudb, ki odstopajo od poslovnih pravil. |
| F20 | Podpora več valutam in merskim enotam z določenimi pravili pretvorbe. |

## Izven obsega projekta

- Sprejem naročil in izvedba dobave.
- Računi, plačila in računovodstvo.
- Avtonomna odobritev ali sklepanje poslov v imenu ponudnika.
- Projektiranje izdelkov po meri.
