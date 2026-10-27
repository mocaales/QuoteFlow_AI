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
- Model iz docs/03 je uveden: uporabnik, podjetje, vloga_uporabnika in preostalih sedem poslovnih entitet s slovenskimi imeni. Ne vračaj starega modela products/company_members/platform_admins.
- authenticated ima samo branje z RLS in izrecne administratorske funkcije za podjetja ter vloge. Druge pisalne postopke uvedi z ločeno migracijo in testi.
- Vsak poslovni zahtevek preveri žeton pri Supabase Auth, aktivno auth.sessions sejo in trenutne dodelitve vlog v bazi.
- Frontend organiziraj po docs/razvoj/frontend-arhitektura.md: funkcionalnosti v features, sestava v app/pages, skupna infrastruktura v lib/services; poslovna pravila ostanejo na backendu.
