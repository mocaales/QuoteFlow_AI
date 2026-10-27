# Ena ponudba za par RFQ–ponudnik skozi celoten potek

- **Status:** sprejeto
- **Datum:** 2026-10-20
- **Izvedba:** delna; enotna tabela ponudba je uvedena, uporabniški postopek ponudb sledi v naslednjih sklopih

## Kontekst in problem

Ročna in samodejna izbira morata voditi v isti proces. Osnutek je ločen za vsakega ponudnika, kupcu pa je ponudba vidna šele po izrecni odobritvi.

## Obravnavane možnosti

- En zapis `Ponudba` za par RFQ–podjetje ponudnika s stanji in podatkom o odobritvi.
- Ločene tabele za vabilo, osnutek, odobritev in objavljeno ponudbo.

## Izid odločitve

Izberemo **en zapis ponudbe s pripadajočimi postavkami** in enoličnostjo `(povprasevanje_id, podjetje_ponudnika_id)`. Stanja `povabljena`, `osnutek`, `v_pregledu`, `odobrena` in `zavrnjena` opisujejo potek. Ob odobritvi transakcija ponovno preveri pravila, zapiše odobritelja ter čas in zaklene ponudbo. Kupčev API vrne samo odobrene javne podatke.

### Posledice

- **Pozitivno:** oba načina izbire delita isti postopek; manj podvojenih entitet in jasna sled od RFQ do ponudbe.
- **Negativno:** prehodi stanj in sočasne spremembe zahtevajo stroge omejitve ter transakcijske teste; prenos stare sheme ni trivialen.

## Preverjanje

Testi preverijo enoličnost para, prepoved urejanja odobrene ponudbe, odsotnost osnutkov v kupčevem API-ju in ponovni izračun ob odobritvi.
