# QuoteFlow AI

## Organizacija agentov: Claude in OpenAI

- Glavna seja je Chief of Staff v Claude Code ter ChatGPT Work/Codex. Pred usmerjanjem preberi `.claude/team/CHIEF-OF-STAFF.md`, `ROSTER.md` in `MODELS.md` ter jim sledi v okviru dovoljenj trenutnega okolja. Odgovor začni z vrstico **Routing:**. Za vprašanja in upravljanje agentov zadošča način Direct; vseh ekip ne zaganjaj samodejno.
- **Skupni spomin:** na začetku vsake seje preberi `.agent-memory/MEMORY.md` (protokol in kazalo) in `.agent-memory/status.md` (trenutno stanje dela), preden raziskuješ projekt. Ko se stanje dela spremeni, posodobi `status.md`; trajna dejstva (želje uporabnika, popravki, odločitve) zapiši v `.agent-memory/` po protokolu iz `MEMORY.md`. Zasebni spomin posameznega okolja drugemu ni viden. Mapa je lokalna (gitignore); če v svežem klonu manjka, to povej in nadaljuj brez nje.
- Claude Code uporablja `.claude/agents/<team>/*.md` in `CLAUDE.md`; Codex uporablja `.codex/agents/*.toml`. Telo navodil v ustrezni Claude datoteki je skupni vir odgovornosti. Tehnični kontekst iz `CLAUDE.md` preberi enkrat; sklic `@AGENTS.md` ne pomeni ponovnega krožnega nalaganja.
- Modeli in Claude hooki niso prenosljivi samodejno. Uporabi native konfiguracijo trenutnega okolja, dejansko razpoložljiva orodja in preslikavo v `MODELS.md`. Ne trdi, da so dovoljenja, spomin ali hooki vključeni, če niso.
- Če lokalni paket `.claude/` ali `.codex/` v svežem klonu manjka, to jasno povej; uporabljaj razpoložljiva projektna navodila in javno dokumentacijo, ne domnevaj nameščenih agentov ali hookov.
- Izbira modela razvojnega pomočnika ne spreminja modela ali ponudnika AI v aplikaciji QuoteFlow. Poslovne odločitve določa potrjena arhitektura in ADR.

- Vse razvojno delo projekta opravljaj v tem repozitoriju.
- RIRIS in uporabnikovi dogovori določajo zahteve aplikacije. OPP je ločena študija in ne omejuje razvoja.
- Pred implementacijo preberi docs/01–04. README mora jasno ločevati izvedene in načrtovane funkcije.
- Uporabljaj primarni projektni model iz docs/03: 17 tabel, podjetja, projekti, ekipe, cenik, materiali, ponudbe in računi. Starega RFQ-modela ne vračaj.
- Potrjeni obseg določa docs/02: F1–F7 MVP, F8–F22 pozneje in F23–F27 možne nadgradnje. AI pomoč pri projektih (F16–F20) je načrtovana po MVP. Nove zgodbe v docs/05 niso samodejna preslikava starih GitHub nalog.
- Cene, količine, popuste, DDV, stanja projektov in izolacijo podjetij preverja programska logika ter omejitve baze. Poslane ponudbe in izdani računi so nespremenljivi.
- Poslovni dostop preverjaj na backendu za vsako podjetje. Globalni vlogi sta admin in stranka; mojster in delavec veljata pri določenem podjetju. Stranka ne vidi osnutkov ali internih materialnih sestav.
- Pred uvajanjem poslovnih tabel pripravi migracije, neprivilegirano aplikacijsko vlogo in teste izolacije.

- Git remote origin: https://github.com/mocaales/QuoteFlow_AI.git. Ne izvajaj commit ali push brez novega izrecnega navodila uporabnika.
- Baza: Supabase QuoteFlow_AI, ref pexllfgutqiormnabzxp. Poslovna shema quoteflow, interne funkcije quoteflow_private.
- Supabase Auth je vir identitete. Vloge določajo poslovna članstva, ne user_metadata.
- Edini vir migracij je supabase/migrations; ne uvajaj Alembic vzporedno.
- Primarni model je opisan v docs/03 in migraciji 20261103211654_v2_projects_roles_catalog.sql. Arhiv quoteflow_legacy_20261103 je dostopen le skrbniški povezavi in ni aplikacijski model.
- authenticated ima samo branje z RLS; pisanje poteka prek ozkih funkcij v quoteflow_private s preverjanjem seje in vloge. Nove uporabniške postopke uvedi z ločeno migracijo in testi.
- Cenik opisuje storitve oziroma delo; material in njegova zaloga po lokaciji sta ločena. Zaloga ne pripada postavki storitve.
- Vsak poslovni zahtevek preveri žeton pri Supabase Auth, aktivno auth.sessions sejo in trenutne dodelitve vlog v bazi.
- Frontend organiziraj po docs/razvoj/frontend-arhitektura.md: funkcionalnosti v features, sestava v app/pages, skupna infrastruktura v lib/services; poslovna pravila ostanejo na backendu.

- Najprej testi, nato koda: pred vsako spremembo kode napiši test, ki opisuje želeno vedenje, in preveri, da pred implementacijo pade. To velja za backend, bazo in frontend.
- Frontend in videz preverjaj tudi v brskalniku: zaženi aplikacijo, zajemi posnetke zaslona na namizni in mobilni širini ter jih primerjaj z docs/wireframes in vizualnim sistemom. Delo je končano šele, ko vsi testi uspejo in posnetki ustrezajo pričakovanemu.
