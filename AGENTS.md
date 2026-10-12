# QuoteFlow AI

- Vse razvojno delo projekta opravljaj v tem repozitoriju.
- RIRIS in uporabnikovi dogovori določajo zahteve aplikacije. OPP je ločena študija in ne omejuje razvoja.
- Pred implementacijo preberi docs/01–04. README mora jasno ločevati izvedene in načrtovane funkcije.
- Nikoli ne objavi osnutka brez izrecne odobritve pooblaščenega ponudnika.
- Cene, zaloge, marže in poslovna pravila preverja programska logika; AI ne izmišljuje manjkajočih podatkov.
- Poslovni dostop preverjaj na backendu za vsako podjetje; nabavniku ne vračaj internih stroškov ali osnutkov.
- Pred uvajanjem poslovnih tabel pripravi migracije, neprivilegirano aplikacijsko vlogo in teste izolacije.

- Git remote origin: https://github.com/mocaales/QuoteFlow_AI.git. Ne izvajaj commit ali push brez novega izrecnega navodila uporabnika.
- Baza: Supabase QuoteFlow_AI, ref pexllfgutqiormnabzxp. Poslovna shema quoteflow, interne funkcije quoteflow_private.
- Supabase Auth je vir identitete. Vloge določajo poslovna članstva, ne user_metadata.
- Edini vir migracij je supabase/migrations; ne uvajaj Alembic vzporedno.
- authenticated trenutno dovoljuje samo branje z RLS. Pisalne postopke uvedi z ločeno migracijo in testi.
