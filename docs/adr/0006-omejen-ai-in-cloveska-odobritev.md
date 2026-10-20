# Omejen AI predlaga, program preveri, ponudnik odobri

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** načrtovana; AI-agent še ni povezan z aplikacijo

## Kontekst in problem

Besedilo RFQ je lahko prosto in dvoumno. AI lahko pomaga pri razumevanju in ujemanju, ne sme pa ustvariti poslovno zavezujoče cene, ugibati zaloge ali odobriti ponudbe.

## Obravnavane možnosti

- GPT-6 Luna prek Responses API s strukturiranim izhodom in omejenimi orodji samo za branje; ločen programski validator.
- Neomejen agent, ki sam izračuna in objavi ponudbo.
- Izključno ročna priprava brez AI.

## Izid odločitve

Izberemo **GPT-6 Luna prek Responses API** za predlog razumevanja RFQ in ujemanja s potrjenimi podatki posameznega ponudnika. Model je izbran za omejeno, ponavljajočo se nalogo; [uradna dokumentacija OpenAI](https://developers.openai.com/api/docs/models/gpt-6-luna) potrjuje podporo klicanju funkcij in strukturiranemu izhodu. Backend modelu izpostavi le dovoljena bralna orodja. Cene, stroške, marže, popuste, roke in morebitne zaloge preveri deterministična logika; samo pooblaščen ponudnik lahko odobri.

### Posledice

- **Pozitivno:** hitrejša priprava osnutka brez prenosa končne odločitve na model.
- **Negativno:** strošek in odvisnost od zunanjega API-ja; dvoumne ali nepopolne zahteve še vedno terjajo ročni pregled.

## Preverjanje

Testi zavrnejo izmišljene ali nepotrjene vrednosti, preverijo izolacijo podatkov med ponudniki in dokažejo, da agent nima postopka za odobritev ali pošiljanje e-pošte.
