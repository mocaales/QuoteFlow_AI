# Projekti podjetij, več vlog in materialna zaloga

- **Status:** sprejeto
- **Datum:** 2026-11-03
- **Izvedba:** shema uvedena v Supabase 2026-11-04; API in vmesnik prilagojena za identiteto, administracijo, cenik in materialno zalogo. Preostali postopki so naslednji sklop; [stanje](../razvoj/podatkovni-model.md).

## Kontekst in problem

Uporabnik je potrdil nov proces podjetij, projektov, ekip, ponudb in računov. Prejšnji RFQ-model ne zajame delavcev, osebne stranke in materialne zaloge ter ne sme ostati osnova nove sheme.

## Obravnavane možnosti

- Razširitev RFQ-modela: zavrnjena, ker ohrani neveljavne povezave in pravila.
- Nova relacijska shema s 17 tabelami: izbrana kot neposreden zapis potrjenega procesa.
- Ločene identitete za vsako vlogo: zavrnjene zaradi podvojenih računov in križanja pravic.

## Izid odločitve

Uporabimo [novi model](../03-podatkovni-model.md). Globalni vlogi sta `admin/stranka`, podjetniški `mojster/delavec`. Podjetje ima lastnika z aktivno dodelitvijo mojstra. Projekt poveže podjetje, stranko, ekipe in različice ponudb; sprejeta ponudba je vir računa. Cenik dela in materialna zaloga sta ločena. Ob sprejemu nastane osnutek računa, izdaja in pošiljanje sledita izvedbi.

Nadomešča ADR-0005 in ADR-0009; ADR-0004 ohrani načelo ločene identitete in poslovnih vlog, vendar dobi nove vloge in obseg. Stari poslovni podatki se pred zamenjavo ohranijo v nedostopnem arhivu; identitete in seje Supabase Auth ostanejo.

### Posledice

- **Pozitivno:** pravice so omejene na podjetje, brez podvojenih vlog ali starih RFQ-entitet; dokumenti ohranijo svoje vrednosti.
- **Negativno:** stari uporabniški postopki in funkcionalne zahteve potrebujejo uskladitev. Uvedena shema ne pomeni izvedenih novih ekranov.

## Preverjanje

Migracija in podatkovni testi preverjajo 17 tabel, ključe, izolacijo podjetij, lastništvo, vloge, nespremenljivost dokumentov in življenjski cikel. Preverjanje arhiva in ponovnega administratorskega dostopa je del uvajanja.
