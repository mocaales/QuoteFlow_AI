# QuoteFlow – zasnova rešitve

**Ideja.** QuoteFlow AI je večpodjetniška spletna aplikacija za mojstre in njihove stranke, ki povezuje projekte, cenik, materiale, ponudbe in račune. Nadaljnji razvoj vključuje ekipe in AI-pomoč pri pripravi vsebine.

**Problem.** Ponudbe, dogovorjeni termini, ekipe in plačila se pogosto vodijo ločeno. Enoten proces omogoča spremljanje dela od pregleda zahteve do plačanega računa.

**Uporabniki.** Stranka sprejema ali zavrača ponudbe. Mojster vodi svoje podjetje in projekte. Delavec sodeluje v ekipah podjetja. Admin upravlja uporabnike, pravice in prošnje za mojstra. Isti uporabnik ima lahko več vlog; podjetniške pravice veljajo samo v določenem podjetju.

**Delovanje.** Admin odobri prošnjo za mojstra in registracijo podjetja. Mojster za stranko vodi projekt, sestavi ponudbo iz cenika in materialov ter jo pošlje v odločitev. Sprejem omogoči dogovor termina in izvedbo. Po zaključeni izvedbi se izda in pošlje račun; celotno plačilo zaključi projekt. Ponudbe ohranijo posnetek cen, da sprememba cenika ne spremeni že poslanega dokumenta.

Primer: podjetje pripravi ponudbo za rušenje estriha na strankinem objektu, določi količino v m², ceno, popust in DDV ter jo pošlje stranki. Po sprejemu ponudbe določi termin, po izvedbi izda račun in evidentira plačilo.

[Obseg](02-funkcionalnosti-in-obseg.md) določa 22 predvidenih funkcionalnosti, od tega 7 MVP, ter 5 možnih nadgradenj. [Uporabniške zgodbe](05-uporabniske-zgodbe.md) določajo pogoje sprejemljivosti. AI-pomoč F16–F20 sledi po MVP: analizira zahtevo projekta, predlaga osnutek iz cenika podjetja ter pomaga pri pregledu in opisu dela. Mojster vse predloge pregleda; finančne vrednosti izračuna programska logika.

Primarni [podatkovni model](03-podatkovni-model.md) podpira novi projektni proces. Načrtovane funkcionalnosti niso oznaka izvedenosti; trenutno stanje je opisano v [razvojni dokumentaciji](razvoj/podatkovni-model.md).
