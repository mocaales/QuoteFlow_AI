# QuoteFlow AI

## Organizacija agentov: Claude in OpenAI

- Glavna seja je Chief of Staff v Claude Code ter ChatGPT Work/Codex. Pred usmerjanjem preberi `.claude/team/CHIEF-OF-STAFF.md`, `ROSTER.md` in `MODELS.md` ter jim sledi v okviru dovoljenj trenutnega okolja. Odgovor začni z vrstico **Routing:**. Za vprašanja in upravljanje agentov zadošča način Direct; vseh ekip ne zaganjaj samodejno.
- Claude Code uporablja `.claude/agents/<team>/*.md` in `CLAUDE.md`; Codex uporablja `.codex/agents/*.toml`. Telo navodil v ustrezni Claude datoteki je skupni vir odgovornosti. Tehnični kontekst iz `CLAUDE.md` preberi enkrat; sklic `@AGENTS.md` ne pomeni ponovnega krožnega nalaganja.
- Modeli in Claude hooki niso prenosljivi samodejno. Uporabi native konfiguracijo trenutnega okolja, dejansko razpoložljiva orodja in preslikavo v `MODELS.md`. Ne trdi, da so dovoljenja, spomin ali hooki vključeni, če niso.
- Če lokalni paket `.claude/` ali `.codex/` v svežem klonu manjka, to jasno povej; uporabljaj razpoložljiva projektna navodila in javno dokumentacijo, ne domnevaj nameščenih agentov ali hookov.
- Izbira modela razvojnega pomočnika ne spreminja modela ali ponudnika AI v aplikaciji QuoteFlow. Poslovne odločitve določa potrjena arhitektura in ADR.

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
- authenticated ima samo branje z RLS in omejene funkcije za administracijo ter podatke ponudnika (US-03–US-05). Druge pisalne postopke uvedi z ločeno migracijo in testi.
- Popravek cenika razveljavi potrditev; menjava vrste/enote odstrani zalogo. Pravila so časovne različice brez prekrivanja in retroaktivnih sprememb.
- Vsak poslovni zahtevek preveri žeton pri Supabase Auth, aktivno auth.sessions sejo in trenutne dodelitve vlog v bazi.
- Frontend organiziraj po docs/razvoj/frontend-arhitektura.md: funkcionalnosti v features, sestava v app/pages, skupna infrastruktura v lib/services; poslovna pravila ostanejo na backendu.

- Najprej testi, nato koda: pred vsako spremembo kode napiši test, ki opisuje želeno vedenje, in preveri, da pred implementacijo pade. To velja za backend, bazo in frontend.
- Frontend in videz preverjaj tudi v brskalniku: zaženi aplikacijo, zajemi posnetke zaslona na namizni in mobilni širini ter jih primerjaj z docs/wireframes in vizualnim sistemom. Delo je končano šele, ko vsi testi uspejo in posnetki ustrezajo pričakovanemu.
