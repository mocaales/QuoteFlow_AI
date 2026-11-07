# Delavci podjetja in skrbniški pregled vlog

- **Status:** sprejeto
- **Datum:** 2026-11-07
- **Izvedba:** izvedeno in uvedeno v oddaljeno bazo 2026-11-08 (zasnova potrjena v G1 2026-11-07, vabila po varnostnem pregledu G6 2026-11-07)

## Kontekst in problem

Uporabnik je ugotovil, da je plošča »Podjetja in pravice« slabo uporabna: vloge je mogoče samo dodajati (odvzem je le neoznačena ikona v dolgi tabeli), iskanje po podjetju ali uporabniku je težko. Zahteval je kompaktnejši, a bolj funkcionalen pregled in da lahko delavce dodaja tudi mojster. Odločil je: mojster upravlja delavce v svojem podjetju (US-08 / F8, vključen v obseg zdaj); administrator obdrži polni nadzor. `quoteflow_private.dodeli_vlogo` že dovoljuje mojstru dodelitev `delavec` v lastnem podjetju, a API poti in UI ni. Veljajo ADR-0004 in [ADR-0010](0010-projekti-podjetja-in-vec-vlog.md) (vloge po podjetju, lastnik je mojster) ter varnostna ocena (A1–A11).

## Obravnavane možnosti

- Ohranitev ravne tabele s filtri: zavrnjeno, ker ne reši navigacije po podjetjih in uporabnikih.
- Mojster dodeljuje tudi vlogo mojster: zavrnjeno, ker bi razširilo lastništvo brez administratorja.
- Različni odzivi pri neznanem, nepotrjenem ali neprimernem e-poštnem naslovu: zavrnjeno, ker razkrivajo obstoj računov.
- Takojšnje dodajanje (`dodaj_delavca`) z omejitvami hitrosti: zavrnjeno po varnostni ugotovitvi 1 (G6). Tudi z omejitvami mojster po dodajanju vidi ime in e-pošto tujega uporabnika, zato lahko z dovolj poskusi preverja, kdo ima račun in je stranka drugih podjetij.
- Takojšnje dodajanje, a ime skrito do prve prijave delavca: zavrnjeno, ker razlika v odzivu (uspeh/neuspeh) obstoj računa še vedno razkrije, delavec pa bi bil dodeljen brez privolitve.

## Izid odločitve

Izbrana možnost: **master-detail pregled in ozka mojstrova pot za delavce**.

- Administrator: pogleda »Po podjetjih« in »Po uporabnikih« ter zavihka »Prošnje mojstrov« (z številom) in »Podjetja« (prošnje in podjetja se premaknejo pod zavihke). Preklicane vloge so privzeto skrite (filter stanja »Aktivne«).
- Mojster: v svojem podjetju delavca povabi (glej »Odločitev o vabilih« spodaj; prvotno takojšnje dodajanje z `dodaj_delavca` je nadomeščeno) in z `uredi_delavca` odvzema ali obnavlja samo vlogo `delavec`; ime in e-pošto delavca vidi šele po sprejemu povabila (sprejeto preostalo tveganje zasebnosti, kot pri imenu stranke po M2).
- Za vsak e-poštni naslov je odgovor ob povabilu enak. Sprejem povabila zavrne uporabnika, ki je stranka odprtega (nezaključenega) projekta istega podjetja (D19); isto pravilo in preverba potrjene e-pošte veljata tudi pri skrbnikovih `dodeli_vlogo` in `aktiviraj_vlogo`, ki sta samo za administratorja.
- Kontrole: omejitev hitrosti (`poskus_delavca`, QFP30), revizija `dogodek_vloge` (`ob` privzeto `clock_timestamp()`), `vloga_uporabnika.dodeljeno_ob`, zavrnitev administratorja kot cilja. Odvzem edine vloge mojster lastniku podjetja: QFP33 »Lastniku podjetja ni mogoče odvzeti vloge mojster.« → 409 prek `CONFLICTS`.

### Odločitev o vabilih (2026-11-07)

Po ugotovitvi 1 (razkritje obstoja računov z imenom pri takojšnjem dodajanju) je uporabnik izbral **vabila**:

- Mojsterjev »Dodaj delavca« ustvari povabilo, nikoli vloge. Odgovor je za vsak naslov enak (`201`, brez imena in `uporabnik_id`), zato obstoja računa ni mogoče ugotoviti.
- Povabilo hrani zasebna tabela `quoteflow_private.povabilo_delavca` (stanja `povabljen`, `sprejeto`, `zavrnjeno`, `preklicano`, `poteklo`; poteče po 14 dneh); ni del pogodbe 22 poslovnih tabel. Odprto povabilo je na (podjetje, `lower(e_posta)`) eno. Omejitve `QFP30`: 20 na uro na podjetje in 50 na dan na mojstra.
- Povabljeni s potrjeno e-pošto, ki se ujema, povabilo sprejme ali zavrne v aplikaciji (brez pošiljanja e-pošte). Sprejem znova preveri pogoje (potrjena e-pošta, aktivna stranka, ni admin, pravilo D19, aktivno podjetje); neustrezen ali pretekel sprejem: `QFP34` (409).
- `dodaj_delavca` je odstranjena; `dodeli_vlogo` in `aktiviraj_vlogo` sta samo za admina (z D19 in preverbo potrjene e-pošte). Mojster ime vidi šele po sprejemu.
- Revizija `dogodek_vloge` dobi stolpec `dejanje` in `povabilo_id`; tuji ključi uporabnika so `ON DELETE SET NULL`, da je račun izbrisljiv (stranka s projekti in lastnik ostaneta neizbrisljiva do #104).

### Posledice

- **Pozitivno:** odvzem in iskanje vlog sta hitra; mojster dela brez administratorja; brez razkritja obstoja računov.
- **Negativno:** delavec mora povabilo sprejeti (en korak več); več SQL funkcij in tabel (skupaj z ADR-0012 pogodba 22 tabel); mojster vidi podatke delavcev (sprejeto).
- **Nadaljnje delo:** posodobitev `docs/02` in `docs/05` (US-08) ter README (G7); komponenta `features/workers/components/Workers.tsx`.

## Preverjanje

DB testi za `povabi_delavca`, `odgovori_povabilo`, `uredi_delavca`, QFP30 in QFP33, enak generični odgovor, pravilo odprtega projekta stranke, revizijo `dogodek_vloge` in tenant izolacijo; `test_access.py` za route guarde; Vitest za `Workers` in `Admin` (filtri, odvzem); Playwright 1440/390.
