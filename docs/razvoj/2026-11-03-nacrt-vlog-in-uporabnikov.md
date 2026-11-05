# Predlog: nove vloge, osebna stranka in pregled uporabnikov

> **Zgodovinski razvojni zapis:** novi primarni model in stanje uvedbe sta v [podatkovni-model.md](podatkovni-model.md). Opisi starih vlog, RFQ, cenika in pravil spodaj ne določajo nove sheme.


**Datum:** 2026-11-03 · **Stanje:** zasnova za potrditev, brez implementacije.

## 1. Vprašanje in omejitve

Sprememba podjetniškega nabavnika v osebno stranko zahteva prenovo lastništva povpraševanj, ne samo preimenovanja. Ohranimo React/FastAPI/Supabase, eno zgodovino migracij, deset poslovnih entitet in preverjanje seje ter pravic ob vsakem zahtevku. Pravice ostajajo v poslovni tabeli, ne v uporabniških metapodatkih Auth.

Pregledani so CLAUDE.md, AGENTS.md, agenti v `.claude/agents/`, relevantni skilli za Supabase/PostgreSQL in oblikovanje aplikacij, dokumentirani model, trenutne migracije ter frontend in backend. CLAUDE.md zahteva potrditev arhitekture pred kodo ter najprej padajoče teste. Ta datoteka je samo predlog; dokument 03 še opisuje trenutno izvedbo.

Uporabnik je že potrdil: **vsak novoregistrirani račun samodejno dobi vlogo stranka**. Dodelitev izvaja sistem, ne podatki iz obrazca ali `user_metadata`; potrditev e-pošte in veljavna seja ostaneta potrebni za uporabo poslovnih postopkov.

## 2. Poslovni tok in vloge

| Vloga | Podjetje | Dovoljenja v tem sklopu |
|---|---|---|
| `admin` | Brez podjetja | Upravljanje podjetij, pregled vseh uporabnikov in poslovnih dodelitev. Brez privzetega dostopa do internih kalkulacij. |
| `stranka` | Brez podjetja | Osebni račun in lastna povpraševanja oziroma odobrene ponudbe, ko bodo ti postopki implementirani. |
| `mojster` | Obvezno | Podatki lastnega podjetja, cenik, zaloge, pravila in delavci; pozneje tudi odobritve ponudb. |
| `delavec` | Obvezno | Lastno članstvo in osnovni kontekst podjetja. Brez privzetega dostopa do stroškov, cenika, pravil ali odobritve. |

En človek ima lahko več vlog, tudi mojster in delavec pri istem podjetju. Podjetje ima lahko več mojstrov; omejitve na enega ne uvajamo.

Dodelitve: `ne obstaja → aktivna → odvzeta → aktivna`. Ponovljena dodelitev ne ustvari dvojnika. Deaktivacija podjetja blokira njegovi podjetniški vlogi, ne osebne vloge stranke.

Mojster doda oziroma odvzame samo vlogo `delavec` pri svojem podjetju, tudi sebi. V tem sklopu dodaja že registrirane, potrjene račune po točni e-pošti. Ne dobi imenika vseh uporabnikov. Povabila novim računom niso vključena. Mojstre dodeljuje admin; globalni admin ostane omejen na namenski skrbniški postopek. Mojster lahko ureja naziv podjetja; globalno aktivacijo/deaktivacijo podjetja obdrži admin.

Stanja RFQ in ponudb ostanejo obstoječa. Ta sklop ne odpira še neimplementiranih postopkov oddaje RFQ ali odobritve. Odobreno ponudbo pozneje odobri samo aktivni mojster podjetja; ostane zaklenjena.

## 3. Spremembe po plasteh

### Podatkovni model in migracija

Ohranimo `uporabnik`, `podjetje` in `vloga_uporabnika`. Nova omejitev na dodelitvi:

- `admin` in `stranka`: `podjetje_id = NULL`.
- `mojster` in `delavec`: podjetje je obvezno.
- Enoličnost globalno po uporabniku in vlogi, podjetniško po uporabniku, podjetju in vlogi.

Na `povprasevanje` uvedemo **`stranka_id → uporabnik.id`** kot edinega osebnega lastnika namesto `podjetje_nabavnika_id` in `ustvaril_vloga_id`. Obstoječa povpraševanja pripadejo izvornemu ustvarjalcu. Ostali člani nekdanjega kupčevega podjetja jih ne podedujejo.

`ponudba.podjetje_ponudnika_id` in `pravila_ponudnika` ostaneta: ponudnik v teh imenih pomeni poslovno stran oziroma podjetje, ne uporabniške vloge. Kontakti in odobritelj kažejo na mojstrovo dodelitev pri istem podjetju. Ne ustvarjamo tabel Mojster, Delavec ali Stranka.

Nova migracija, brez spreminjanja že uvedenih migracij in brez brisanja poslovne sheme:

1. Popis in varnostna kopija pred morebitno oddaljeno uvedbo.
2. Prenos osebnega lastništva RFQ skozi obstoječo dodelitev njegovega ustvarjalca.
3. `administrator → admin`, `ponudnik → mojster`, z ohranjenimi UUID dodelitev.
4. Stare nabavniške dodelitve iste osebe združimo v eno globalno `stranka`; aktivna ostane, če je bila vsaj ena aktivna. Povsem odvzetih pravic ne reaktiviramo.
5. Obstoječi računi brez nabavniške vloge ohranijo svoje pravice; ne dobijo dodatnih vlog samo zaradi migracije. Novi računi dobijo stranko s sistemsko dodelitvijo ob registraciji.
6. Po preverjenem prenosu odstranimo stare RFQ povezave in odvečne dodelitve; preslikava ostane v varnostni kopiji/poročilu.
7. Atomska zamenjava omejitev, indeksov, funkcij, triggerjev in RLS; preverjanje števila dokumentov ter ohranjenih zneskov, povezav in odobritev.

Lokalna pravila agenta `supabase-db` prepovedujejo oddaljeno uvedbo. V tem sklopu migracijo pripravimo in preverimo lokalno; pred oddaljeno uvedbo prikažemo preflight in njen vpliv na obstoječe podatke.

### SQL in backend

Ohranimo `session_database` in `aktivna_seja()`. Posodobimo `administrator()`, `clan()`, podjetniške guarde, potrjevanje cenika ter postopke zalog, pravil in ponudb za novo vlogo mojster. RLS ostane omogočen in prisiljen; neposrednih pisalnih pravic na tabelah ne dodajamo.

Namenski postopki za delavce preverijo mojstra in zaklenejo podjetje ter dodelitve do konca transakcije. Ne sprejemajo poljubne ciljne vloge. Postopki stranke preverjajo osebno lastništvo, ne članstva podjetja.

| Pot | Namen / dostop |
|---|---|
| `GET /api/me` | Trenutne lastne globalne in podjetniške vloge. |
| `GET /api/vloge` | Seznam dovoljenih vlog, nazivov in obsega; vir izbir in filtrov v vmesniku. Zahteva prijavo. |
| `GET /api/admin/uporabniki` | Admin: vsi uporabniki, tudi brez dodelitev, z njihovimi vlogami in podjetji. |
| `POST /api/admin/vloge` | Admin: stranka brez podjetja, mojster/delavec z obveznim podjetjem. |
| `PATCH /api/admin/vloge/{id}` | Aktivacija/odvzem; zaščita globalnega admina ostane. |
| `GET /api/podjetja/{id}/delavci` | Mojster: delavci tega podjetja. |
| `POST /api/podjetja/{id}/delavci` | Mojster: dodelitev registrirani osebi po e-pošti. |
| `PATCH /api/podjetja/{id}/delavci/{vloga_id}` | Mojster: aktivacija/odvzem samo dodelitve delavca tega podjetja. |
| `PUT /api/podjetja/{id}` | Mojster: urejanje naziva lastnega podjetja. |

Dodajanje sebe kot delavca uporabi isti omejeni postopek z lastno potrjeno e-pošto. Interni stroški, marže, pravila in osnutki se ne vračajo stranki ali delavcu.

### Frontend in geslo

Ohranimo sedanji vizualni sistem in organizacijo po funkcionalnostih. Administracija dobi tabelo z eno vrstico na uporabnika ter panel za njegove dodelitve. Filtri: e-pošta, vloga, podjetje, aktivna/odvzeta dodelitev in uporabniki brez dodelitev; dodamo razvrščanje, število rezultatov in ponastavitev. Kombinirana filtra vloge in podjetja preverjata isto dodelitev, da vloga iz drugega podjetja ne povzroči napačnega ujemanja.

Po spremembi vloge se podatki takoj ponovno preberejo s strežnika, brez ponovnega nalaganja strani. Spremembe iz drugih oken se preverjajo tiho ob vrnitvi fokusa in z omejenim preverjanjem, ko je pregled odprt in viden. Filtri, obrazec in panel ostanejo; odvzem pravic odstrani nedovoljeni pogled. Supabase Realtime ni potreben samo za ta pregled.

Registracija dobi generator varnega gesla z `crypto.getRandomValues`, najmanj 20 znaki in preverjeno skladnostjo s politiko Auth. Omogočimo ponovno generiranje ter prikaz/skritje. Geslo se ne zapisuje v dnevnike, URL ali trajno shrambo. Ohranimo lepljenje in pravilne `autocomplete` oznake za uporabniško ime ter novo/trenutno geslo. S tem podpremo Apple Passwords; shranjevanje in prikaz sistemskega predloga upravlja uporabnikov brskalnik oziroma Passwords, ne aplikacija.

## 4. Invariante in preverjanje

Najprej napišemo in zaženemo padajoče teste, šele nato kodo:

- pravilne štiri vloge, obseg, enoličnost, kombinacija mojster/delavec;
- avtomatska sistemska vloga stranke brez možnosti samopovišanja;
- osebno lastništvo RFQ in ohranitev obstoječih dokumentov po migraciji;
- mojster ne podeli mojstra/admina in ne spreminja delavcev tujega podjetja;
- stranka in delavec ne prebereta stroškov, pravil ali osnutkov; admin jih ne dobi samodejno;
- ena ponudba na RFQ in podjetje, človek odobri, AI ne odobri, potrjeni dokumenti ostanejo zaklenjeni;
- ustrezni filtri in seznam uporabnikov brez dodelitev;
- dinamične spremembe brez izgube odprtega obrazca;
- kriptografski generator in uspešna oddaja generiranega gesla;
- namizni in mobilni e2e, tipkovnica, fokus, napake in vizualni pregled posnetkov.

Polne zbirke: pytest, lokalni Supabase/RLS testi, Vitest, TypeScript/Vite in obstoječi Playwright e2e. Oddaljenih podatkov ne uporabljamo za testne zapise.

## 5. Možnosti in priporočilo

Priporočilo je ena tabela globalnih in podjetniških dodelitev. Ločene tabele za vsako vlogo bi podvojile identiteto in zapletle kombiniranje vlog. Ena tabela uporabnikov in ena tabela dodelitev pokrijeta zahteve.

Delovnih nalogov, evidence ur in statusov dela zdaj ne dodajamo; pravila sledijo. GitHub issues, obseg funkcionalnosti in reorganizacijo projekta obravnavamo po tem sklopu, kot je zahteval uporabnik.

## 6. ADR in dokumentacija

Po potrditvi pripravimo ADR-0010 za osebno stranko in novi model dodelitev. Uskladimo dokument 03 in ER-diagram, tehnične opise pravic, razvojne vodiče ter navodila agentov. Zgodovinskih odločitev in migracij ne prepisujemo: relevantni del ADR-0004 označimo kot nadomeščen. V dokumentih jasno ločimo izvedene postopke od prihodnjih evidenc dela.

Viri za Apple Passwords: [samodejna močna gesla](https://support.apple.com/en-gb/guide/security/secc84c811c4/web), [Apple Password Rules](https://developer.apple.com/password-rules/).
