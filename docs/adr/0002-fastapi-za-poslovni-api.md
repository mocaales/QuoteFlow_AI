# Python in FastAPI za poslovni API

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** delna; API vključuje preverjanje identitete, sej, podjetij in administratorske postopke

## Kontekst in problem

En strežniški del mora preverjati uporabniške pravice, izolacijo podjetij, pravila cen in odobritev ter posredovati omejene podatke AI-agentu. Odločitve o ponudbi ne sme sprejeti brskalnik.

## Obravnavane možnosti

- Python + FastAPI.
- Java + Spring Boot.
- TypeScript + NestJS.

## Izid odločitve

Izberemo **Python + FastAPI** zaradi enotne validacije zahtevkov in enostavne povezave med API-jem, determinističnimi izračuni ter Pythonovo integracijo modela. Spring Boot in NestJS sta izvedljivi alternativi; v tem projektu ne odtehtata dodatnega prehoda obstoječega ogrodja in integracije AI v drug jezik.

### Posledice

- **Pozitivno:** en strežniški sloj je odgovoren za celoten poslovni proces.
- **Negativno:** manj statičnega preverjanja kot pri Javi; potrebni so tipi, testi in transakcijska preverjanja.

## Preverjanje

Poslovni API mora v testih zavrniti dostop tujega podjetja in odobritev brez aktivne vloge; `pytest` preverja izračune.
