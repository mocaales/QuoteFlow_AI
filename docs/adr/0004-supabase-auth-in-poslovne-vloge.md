# Supabase Auth za identiteto, ločena tabela za poslovne vloge

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** izvedena; Auth, aktivne seje in enotne poslovne vloge so vključeni v API in vmesnik

## Kontekst in problem

Isti človek lahko deluje v več podjetjih in v različnih vlogah; lahko je tudi registriran brez članstva. Globalni administrator ni član vsakega podjetja. Prijavna identiteta in poslovna pooblastila imata različni življenjski dobi.

## Obravnavane možnosti

- Supabase Auth + dodelitve vlog v poslovni tabeli + strežniško preverjanje in RLS.
- Lastna prijava in lastni žetoni.
- Vloge samo v `user_metadata` ali v eni vrstici uporabnika.

## Izid odločitve

Izberemo **Supabase Auth za identiteto** in **ločene dodelitve uporabnik–podjetje–vloga**. En račun lahko tako dobi več članstev, pravico pa je mogoče odvzeti brez spreminjanja identitete. Backend pri vsakem poslovnem dejanju preveri aktivno vlogo in podjetje; RLS je dodatna meja, ne edina zaščita. Internih stroškov ne razkrivamo skozi kupčeve odgovore API-ja.

### Posledice

- **Pozitivno:** poslovna pooblastila so sledljiva in ne temeljijo na uporabnikovem profilu ali zaupanju v brskalnik.
- **Negativno:** uskladiti je treba identiteto, dodelitve in RLS; napačna politika bi lahko razkrila podatke med podjetji.

## Preverjanje

Testi zajamejo uporabnika brez članstva, več članstev, odvzem vloge, kupčev dostop do osnutka ter prepoved odobritve s samo administratorsko vlogo.
