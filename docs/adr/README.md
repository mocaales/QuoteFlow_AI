# Arhitekturne odločitve (ADR)

Vsak zapis opisuje eno arhitekturno odločitev. Status odločitve in stanje njene izvedbe sta ločena; ciljna arhitektura še ni v celoti implementirana. Slovenska [predloga](adr-template.md) sledi [minimalni predlogi MADR](https://github.com/adr/madr/blob/develop/template/adr-template-minimal.md): kontekst in problem, obravnavane možnosti, izid odločitve ter podrejene pozitivne in negativne posledice. Status, datum, stanje izvedbe in preverjanje so dodatna pojasnila. Mapa `docs/adr/` sledi navodilom predmeta; [MADR dopušča tudi druge lokacije](https://adr.github.io/madr/#applying-madr-to-your-project).

Za nov ADR kopirajte predlogo in uporabite naslednjo štirimestno številko. Spremembo sprejete odločitve zapišite v nov ADR ter v prejšnjem navedite, da ga novi nadomešča.

| ADR | Odločitev |
|---|---|
| [0001](0001-react-typescript-vite.md) | React, TypeScript in Vite za spletni vmesnik |
| [0002](0002-fastapi-za-poslovni-api.md) | Python in FastAPI za poslovni API |
| [0003](0003-supabase-postgresql-in-migracije.md) | Supabase PostgreSQL in ena pot migracij |
| [0004](0004-supabase-auth-in-poslovne-vloge.md) | Supabase Auth in ločene poslovne vloge |
| [0005](0005-ena-ponudba-za-rfq-in-ponudnika.md) | Ena ponudba za par RFQ–ponudnik |
| [0006](0006-omejen-ai-in-cloveska-odobritev.md) | Omejen AI, programsko preverjanje, človeška odobritev |
| [0007](0007-obvestila-po-poslovnem-dogodku.md) | Obvestila po poslovnem dogodku (F10) |
