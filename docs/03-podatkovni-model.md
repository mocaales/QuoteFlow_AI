# Podatkovni model QuoteFlow AI

## Osnovna logika

**Uporabnik** je človek s prijavo in e-pošto. **Podjetje** lahko kupuje, prodaja ali oboje. Tabela **Vloga uporabnika** pove, za katero podjetje sme človek delovati kot nabavnik ali ponudnik. Uporabnik ima lahko več takih vlog; lahko je tudi registriran brez članstva in tedaj ne sme poslovno ukrepati. Vloga administratorja je globalna in zato nima podjetja. Agent AI ni uporabnik ali poslovna vloga.

**Povpraševanje (RFQ)** odda uporabnik z vlogo nabavnika za svoje podjetje. Vsebuje eno ali več postavk, opisanih z besedilom, količino in enoto. Za vsako ročno ali samodejno izbrano podjetje ponudnika nastane ena **ponudba** v stanju `povabljena`. Tako povpraševanje lahko dobi več ponudb, posamezna ponudba pa odgovarja na natanko eno povpraševanje. Podjetje ponudnika je neposredno zapisano na ponudbi; ločena tabela za vabilo ni potrebna.

Agent iz aktivnih, potrjenih **postavk cenika** (blaga ali storitev) predlaga postavke ponudbe. Pri blagu preveri tudi **zalogo**, če jo ponudnik vodi; pri storitvi zaloge ni. **Pravila ponudnika** določajo dovoljene marže, popuste in roke. Ponudba kaže na uporabljeno različico pravil. Manjkajoče cene ali stroške mora dopolniti ponudnik; agent jih ne ugiba.

Ponudnik osnutek pregleda, uredi in izrecno odobri. Odobritev se zabeleži s stanjem `odobrena`, dodeljeno vlogo odobritelja in časom. Takrat se ponudba in njene postavke zaklenejo; nabavnik jih vidi šele po odobritvi in nikoli ne vidi internih stroškov. **»Odobrena« pomeni odobritev ponudnika**, ne sprejema ponudbe s strani nabavnika; naročanje ni del tega projekta.

**Primer:** Ana je nabavnica podjetja A in odda povpraševanje za 100 ležajev. Izbrani podjetji B in C dobita vsaka svoj zapis ponudbe za **isto** povpraševanje. Pri B agent preveri potrjeno ceno, pravila in zalogo blaga. Če C ponuja storitev, ima postavko cenika brez zaloge. Ponudbo B lahko odobri samo uporabnik z aktivno vlogo ponudnika pri B.

## Entitete in ključni atributi

`PK` = primarni ključ, `FK` = tuji ključ, `UQ` = enoličnost, `?` = neobvezno. Imena atributov so zaradi tehnične berljivosti zapisana brez šumnikov. To je **ciljni model**, ne trenutno stanje podatkovne baze.

| Entiteta | Ključni atributi | Zakaj obstaja |
|---|---|---|
| **Uporabnik** | `id PK`, `e_posta UQ` | Identiteta in prijava v Supabase Auth; poslovnih vlog nima v svoji vrstici. |
| **Podjetje** | `id PK`, `naziv`, `stanje` | Poslovni kupec ali ponudnik. Isto podjetje lahko opravlja obe nalogi. |
| **Vloga uporabnika** | `id PK`, `uporabnik_id FK → Uporabnik`, `podjetje_id? FK → Podjetje`, `vloga`, `aktivna` | `nabavnik` in `ponudnik` zahtevata podjetje; `administrator` ga nima. En uporabnik lahko dobi več vlog, vsaka dodelitev je enolična. |
| **Pravila ponudnika** | `id PK`, `podjetje_id FK → Podjetje`, `najmanjsa_marza`, `najvecji_popust`, `najdaljsi_rok_dni`, `velja_od`, `velja_do?` | Različica poslovnih pravil podjetja; hkrati velja največ ena aktivna različica. |
| **Postavka cenika** | `id PK`, `podjetje_id FK → Podjetje`, `vrsta` (blago/storitev), `opis`, `enota`, `cena_na_enoto`, `strosek_na_enoto`, `dobavni_rok_dni?`, `aktivna`, `potrjeno_ob?` | Ponudnikov vir cene in stroška za blago **ali** storitev. Neaktivna postavka ostane v zgodovini, agent pa je ne uporablja. Ne obstaja posebna entiteta »Izdelek«. |
| **Zaloga** | `postavka_cenika_id PK/FK → Postavka cenika`, `razpolozljiva_kolicina`, `potrjeno_ob` | Neobvezen trenutni podatek samo za blago; storitev nima vrstice zaloge. |
| **Povpraševanje** | `id PK`, `podjetje_nabavnika_id FK → Podjetje`, `ustvaril_vloga_id FK → Vloga uporabnika`, `stanje`, `kraj_dobave?`, `zahtevani_datum?`, `oddano_ob?`, `rok_za_ponudbe?` | Kupčeva zahteva; ustvarjalec mora imeti aktivno vlogo nabavnika pri tem podjetju. Čas oddaje loči osnutek od oddanega RFQ, rok določa, do kdaj ponudnik odgovori. |
| **Postavka povpraševanja** | `id PK`, `povprasevanje_id FK → Povpraševanje`, `opis`, `kolicina`, `enota` | Ena zahtevana vrsta blaga ali storitve, neodvisna od ponudnikovega cenika. |
| **Ponudba** | `id PK`, `povprasevanje_id FK → Povpraševanje`, `podjetje_ponudnika_id FK → Podjetje`, `pravila_id? FK → Pravila ponudnika`, `kontakt_vloga_id? FK → Vloga uporabnika`, `odobril_vloga_id? FK → Vloga uporabnika`, `izvor_izbire`, `razlog_izbire?`, `stanje`, `razlicica`, `ustvarjeno_ob`, `odobreno_ob?`, `velja_do?`, `valuta`, `placilni_pogoji?`, `znesek_skupaj?` | En zapis za izbranega ponudnika skozi celoten potek. `UQ(povprasevanje_id, podjetje_ponudnika_id)`. Čas nastanka omogoča merjenje odziva; kontakt je neobvezen, odobritelj in čas pa obvezna pri stanju `odobrena`. |
| **Postavka ponudbe** | `id PK`, `ponudba_id FK → Ponudba`, `postavka_povprasevanja_id FK → Postavka povpraševanja`, `postavka_cenika_id? FK → Postavka cenika`, `opis`, `kolicina`, `enota`, `cena_na_enoto?`, `strosek_na_enoto?`, `popust`, `dobavni_rok_dni?` | Ponudnikov odgovor na kupčevo postavko. Cena in strošek sta lahko med pripravo neznana, pred odobritvijo pa obvezna. Dogovorjene vrednosti se nato zaklenejo; notranji strošek ni viden nabavniku. |

## ER-diagram

Vsaka povezava je označena z **imenom tujega ključa v podrejeni tabeli**. `||` pomeni natanko eno, `o|` nič ali eno, `o{` nič ali več. V diagramu se podjetje pojavi le enkrat: pri povpraševanju je kupec, pri ponudbi in ceniku ponudnik.

```drawio
<mxfile>
  <diagram id="qGeClXosYejH9kJHyeTg" name="Page-1">
    <mxGraphModel dx="3042" dy="2377" grid="1" gridSize="10" guides="1" tooltips="0" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <UserObject label="" mermaidData="{&#xa;  &quot;data&quot;: &quot;erDiagram\n    direction TB\n    UPORABNIK[\&quot;Uporabnik\&quot;] {\n        uuid id PK\n        text e_posta UK\n    }\n    PODJETJE[\&quot;Podjetje\&quot;] {\n        uuid id PK\n        text naziv\n    }\n    VLOGA_UPORABNIKA[\&quot;Vloga uporabnika\&quot;] {\n        uuid id PK\n        uuid uporabnik_id FK\n        uuid podjetje_id FK \&quot;prazno samo za administratorja\&quot;\n        text vloga\n        boolean aktivna\n    }\n    PRAVILA_PONUDNIKA[\&quot;Pravila ponudnika\&quot;] {\n        uuid id PK\n        uuid podjetje_id FK\n        numeric najmanjsa_marza\n        numeric najvecji_popust\n        int najdaljsi_rok_dni\n    }\n    POSTAVKA_CENIKA[\&quot;Postavka cenika\&quot;] {\n        uuid id PK\n        uuid podjetje_id FK\n        text vrsta \&quot;blago ali storitev\&quot;\n        numeric cena_na_enoto\n        numeric strosek_na_enoto\n        text opis\n        boolean aktivna\n        timestamp potrjeno_ob\n    }\n    ZALOGA[\&quot;Zaloga\&quot;] {\n        uuid postavka_cenika_id PK, FK\n        numeric razpolozljiva_kolicina\n        timestamp potrjeno_ob\n    }\n    POVPRASEVANJE[\&quot;Povpraševanje\&quot;] {\n        uuid id PK\n        uuid podjetje_nabavnika_id FK\n        uuid ustvaril_vloga_id FK\n        text stanje\n        timestamp oddano_ob\n        timestamp rok_za_ponudbe\n    }\n    POSTAVKA_POVPRASEVANJA[\&quot;Postavka povpraševanja\&quot;] {\n        uuid id PK\n        uuid povprasevanje_id FK\n        text opis\n        numeric kolicina\n        text enota\n    }\n    PONUDBA[\&quot;Ponudba\&quot;] {\n        uuid id PK\n        uuid povprasevanje_id FK\n        uuid podjetje_ponudnika_id FK\n        uuid pravila_id FK \&quot;obvezno ob odobritvi\&quot;\n        uuid kontakt_vloga_id FK \&quot;neobvezno\&quot;\n        uuid odobril_vloga_id FK \&quot;obvezno ob odobritvi\&quot;\n        text stanje\n        int razlicica\n        timestamp ustvarjeno_ob\n        timestamp odobreno_ob\n    }\n    POSTAVKA_PONUDBE[\&quot;Postavka ponudbe\&quot;] {\n        uuid id PK\n        uuid ponudba_id FK\n        uuid postavka_povprasevanja_id FK\n        uuid postavka_cenika_id FK \&quot;neobvezno\&quot;\n        numeric cena_na_enoto \&quot;obvezno ob odobritvi\&quot;\n        numeric strosek_na_enoto \&quot;obvezno ob odobritvi\&quot;\n        numeric kolicina\n    }\n\n    UPORABNIK ||--o{ VLOGA_UPORABNIKA : uporabnik_id\n    PODJETJE |o--o{ VLOGA_UPORABNIKA : podjetje_id\n    PODJETJE ||--o{ PRAVILA_PONUDNIKA : podjetje_id\n    PODJETJE ||--o{ POSTAVKA_CENIKA : podjetje_id\n    POSTAVKA_CENIKA ||--o| ZALOGA : postavka_cenika_id\n    PODJETJE ||--o{ POVPRASEVANJE : podjetje_nabavnika_id\n    VLOGA_UPORABNIKA ||--o{ POVPRASEVANJE : ustvaril_vloga_id\n    POVPRASEVANJE ||--o{ POSTAVKA_POVPRASEVANJA : povprasevanje_id\n    POVPRASEVANJE ||--o{ PONUDBA : povprasevanje_id\n    PODJETJE ||--o{ PONUDBA : podjetje_ponudnika_id\n    PRAVILA_PONUDNIKA |o--o{ PONUDBA : pravila_id\n    VLOGA_UPORABNIKA |o--o{ PONUDBA : kontakt_vloga_id\n    VLOGA_UPORABNIKA |o--o{ PONUDBA : odobril_vloga_id\n    PONUDBA ||--o{ POSTAVKA_PONUDBE : ponudba_id\n    POSTAVKA_POVPRASEVANJA ||--o{ POSTAVKA_PONUDBE : postavka_povprasevanja_id\n    POSTAVKA_CENIKA |o--o{ POSTAVKA_PONUDBE : postavka_cenika_id&quot;,&#xa;  &quot;config&quot;: null&#xa;}" id="224">
          <mxCell connectable="0" parent="1" style="group;transparentBounds=1;editIcon=1;lockedGroup=0;groupPadding=10;" vertex="1">
            <mxGeometry as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Uporabnik" mermaidId="n:UPORABNIK" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Uporabnik" id="2">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="129" width="182" x="40" y="-170" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="3" parent="2" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="182" y="43" as="geometry" />
        </mxCell>
        <mxCell id="4" parent="3" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="5" parent="3" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="81" x="56" as="geometry">
            <mxRectangle height="43" width="81" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="6" parent="3" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="45" x="137" as="geometry">
            <mxRectangle height="43" width="45" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="7" parent="2" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="182" y="86" as="geometry" />
        </mxCell>
        <mxCell id="8" parent="7" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="9" parent="7" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="e_posta" vertex="1">
          <mxGeometry height="43" width="81" x="56" as="geometry">
            <mxRectangle height="43" width="81" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="10" parent="7" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="UK" vertex="1">
          <mxGeometry height="43" width="45" x="137" as="geometry">
            <mxRectangle height="43" width="45" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Podjetje" mermaidId="n:PODJETJE" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Podjetje" id="11">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="129" width="161" x="990" y="230" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="12" parent="11" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="161" y="43" as="geometry" />
        </mxCell>
        <mxCell id="13" parent="12" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="14" parent="12" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="62" x="56" as="geometry">
            <mxRectangle height="43" width="62" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="15" parent="12" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="118" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="16" parent="11" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="161" y="86" as="geometry" />
        </mxCell>
        <mxCell id="17" parent="16" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="18" parent="16" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="naziv" vertex="1">
          <mxGeometry height="43" width="62" x="56" as="geometry">
            <mxRectangle height="43" width="62" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="19" parent="16" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="118" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Vloga uporabnika" mermaidId="n:VLOGA_UPORABNIKA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Vloga uporabnika" id="20">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="258" width="495" x="400" y="-70" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="21" parent="20" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="495" y="43" as="geometry" />
        </mxCell>
        <mxCell id="22" parent="21" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="82" as="geometry">
            <mxRectangle height="43" width="82" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="23" parent="21" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="118" x="82" as="geometry">
            <mxRectangle height="43" width="118" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="24" parent="21" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="200" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="25" parent="21" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="252" x="243" as="geometry">
            <mxRectangle height="43" width="252" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="26" parent="20" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="495" y="86" as="geometry" />
        </mxCell>
        <mxCell id="27" parent="26" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="82" as="geometry">
            <mxRectangle height="43" width="82" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="28" parent="26" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uporabnik_id" vertex="1">
          <mxGeometry height="43" width="118" x="82" as="geometry">
            <mxRectangle height="43" width="118" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="29" parent="26" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="200" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="30" parent="26" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="252" x="243" as="geometry">
            <mxRectangle height="43" width="252" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="31" parent="20" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="495" y="129" as="geometry" />
        </mxCell>
        <mxCell id="32" parent="31" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="82" as="geometry">
            <mxRectangle height="43" width="82" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="33" parent="31" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="podjetje_id" vertex="1">
          <mxGeometry height="43" width="118" x="82" as="geometry">
            <mxRectangle height="43" width="118" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="34" parent="31" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="200" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="35" parent="31" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="prazno samo za administratorja" vertex="1">
          <mxGeometry height="43" width="252" x="243" as="geometry">
            <mxRectangle height="43" width="252" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="36" parent="20" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="495" y="172" as="geometry" />
        </mxCell>
        <mxCell id="37" parent="36" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="82" as="geometry">
            <mxRectangle height="43" width="82" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="38" parent="36" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="vloga" vertex="1">
          <mxGeometry height="43" width="118" x="82" as="geometry">
            <mxRectangle height="43" width="118" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="39" parent="36" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="200" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="40" parent="36" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="252" x="243" as="geometry">
            <mxRectangle height="43" width="252" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="41" parent="20" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="495" y="215" as="geometry" />
        </mxCell>
        <mxCell id="42" parent="41" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="boolean" vertex="1">
          <mxGeometry height="43" width="82" as="geometry">
            <mxRectangle height="43" width="82" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="43" parent="41" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="aktivna" vertex="1">
          <mxGeometry height="43" width="118" x="82" as="geometry">
            <mxRectangle height="43" width="118" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="44" parent="41" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="200" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="45" parent="41" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="252" x="243" as="geometry">
            <mxRectangle height="43" width="252" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Pravila ponudnika" mermaidId="n:PRAVILA_PONUDNIKA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Pravila ponudnika" id="46">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="258" width="278" x="-30" y="410" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="47" parent="46" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="278" y="43" as="geometry" />
        </mxCell>
        <mxCell id="48" parent="47" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="49" parent="47" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="152" x="83" as="geometry">
            <mxRectangle height="43" width="152" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="50" parent="47" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="235" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="51" parent="46" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="278" y="86" as="geometry" />
        </mxCell>
        <mxCell id="52" parent="51" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="53" parent="51" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="podjetje_id" vertex="1">
          <mxGeometry height="43" width="152" x="83" as="geometry">
            <mxRectangle height="43" width="152" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="54" parent="51" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="235" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="55" parent="46" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="278" y="129" as="geometry" />
        </mxCell>
        <mxCell id="56" parent="55" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="57" parent="55" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="najmanjsa_marza" vertex="1">
          <mxGeometry height="43" width="152" x="83" as="geometry">
            <mxRectangle height="43" width="152" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="58" parent="55" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="235" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="59" parent="46" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="278" y="172" as="geometry" />
        </mxCell>
        <mxCell id="60" parent="59" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="61" parent="59" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="najvecji_popust" vertex="1">
          <mxGeometry height="43" width="152" x="83" as="geometry">
            <mxRectangle height="43" width="152" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="62" parent="59" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="235" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="225" parent="46" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="278" y="215" as="geometry" />
        </mxCell>
        <mxCell id="226" parent="225" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="int" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="227" parent="225" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="najdaljsi_rok_dni" vertex="1">
          <mxGeometry height="43" width="152" x="83" as="geometry">
            <mxRectangle height="43" width="152" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="228" parent="225" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="235" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Postavka cenika" mermaidId="n:POSTAVKA_CENIKA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Postavka cenika" id="63">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="387" width="423" x="1380" y="600" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="64" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="43" as="geometry" />
        </mxCell>
        <mxCell id="65" parent="64" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="66" parent="64" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="67" parent="64" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="68" parent="64" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="69" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="86" as="geometry" />
        </mxCell>
        <mxCell id="70" parent="69" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="71" parent="69" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="podjetje_id" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="72" parent="69" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="73" parent="69" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="74" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="129" as="geometry" />
        </mxCell>
        <mxCell id="75" parent="74" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="76" parent="74" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="vrsta" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="77" parent="74" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="78" parent="74" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="blago ali storitev" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="79" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="172" as="geometry" />
        </mxCell>
        <mxCell id="80" parent="79" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="81" parent="79" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="cena_na_enoto" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="82" parent="79" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="83" parent="79" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="84" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="215" as="geometry" />
        </mxCell>
        <mxCell id="85" parent="84" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="86" parent="84" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="strosek_na_enoto" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="87" parent="84" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="88" parent="84" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="229" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="258" as="geometry" />
        </mxCell>
        <mxCell id="230" parent="229" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="231" parent="229" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="opis" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="232" parent="229" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="233" parent="229" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="234" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="301" as="geometry" />
        </mxCell>
        <mxCell id="235" parent="234" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="boolean" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="236" parent="234" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="aktivna" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="237" parent="234" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="238" parent="234" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="239" parent="63" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="423" y="344" as="geometry" />
        </mxCell>
        <mxCell id="240" parent="239" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="241" parent="239" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="potrjeno_ob" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="242" parent="239" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="243" parent="239" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="146" x="277" as="geometry">
            <mxRectangle height="43" width="146" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Zaloga" mermaidId="n:ZALOGA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Zaloga" id="89">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="172" width="349" x="1654" y="1130" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="90" parent="89" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="349" y="43" as="geometry" />
        </mxCell>
        <mxCell id="91" parent="90" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="101" as="geometry">
            <mxRectangle height="43" width="101" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="92" parent="90" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="postavka_cenika_id" vertex="1">
          <mxGeometry height="43" width="181" x="101" as="geometry">
            <mxRectangle height="43" width="181" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="93" parent="90" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK,FK" vertex="1">
          <mxGeometry height="43" width="67" x="282" as="geometry">
            <mxRectangle height="43" width="67" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="94" parent="89" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="349" y="86" as="geometry" />
        </mxCell>
        <mxCell id="95" parent="94" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="101" as="geometry">
            <mxRectangle height="43" width="101" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="96" parent="94" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="razpolozljiva_kolicina" vertex="1">
          <mxGeometry height="43" width="181" x="101" as="geometry">
            <mxRectangle height="43" width="181" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="97" parent="94" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="67" x="282" as="geometry">
            <mxRectangle height="43" width="67" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="98" parent="89" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="349" y="129" as="geometry" />
        </mxCell>
        <mxCell id="99" parent="98" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="101" as="geometry">
            <mxRectangle height="43" width="101" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="100" parent="98" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="potrjeno_ob" vertex="1">
          <mxGeometry height="43" width="181" x="101" as="geometry">
            <mxRectangle height="43" width="181" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="101" parent="98" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="67" x="282" as="geometry">
            <mxRectangle height="43" width="67" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Povpraševanje" mermaidId="n:POVPRASEVANJE" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Povpraševanje" id="102">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="301" width="288" x="720" y="477" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="103" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="43" as="geometry" />
        </mxCell>
        <mxCell id="104" parent="103" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="105" parent="103" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="106" parent="103" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="107" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="86" as="geometry" />
        </mxCell>
        <mxCell id="108" parent="107" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="109" parent="107" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="podjetje_nabavnika_id" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="110" parent="107" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="111" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="129" as="geometry" />
        </mxCell>
        <mxCell id="112" parent="111" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="113" parent="111" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="ustvaril_vloga_id" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="114" parent="111" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="115" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="172" as="geometry" />
        </mxCell>
        <mxCell id="116" parent="115" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="117" parent="115" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="stanje" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="118" parent="115" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="244" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="215" as="geometry" />
        </mxCell>
        <mxCell id="245" parent="244" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="246" parent="244" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="oddano_ob" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="247" parent="244" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="248" parent="102" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="288" y="258" as="geometry" />
        </mxCell>
        <mxCell id="249" parent="248" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="250" parent="248" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="rok_za_ponudbe" vertex="1">
          <mxGeometry height="43" width="189" x="56" as="geometry">
            <mxRectangle height="43" width="189" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="251" parent="248" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="245" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Postavka povpraševanja" mermaidId="n:POSTAVKA_POVPRASEVANJA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Postavka povpraševanja" id="119">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="258" width="277" x="940" y="820" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="120" parent="119" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="277" y="43" as="geometry" />
        </mxCell>
        <mxCell id="121" parent="120" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="122" parent="120" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="123" parent="120" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="124" parent="119" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="277" y="86" as="geometry" />
        </mxCell>
        <mxCell id="125" parent="124" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="126" parent="124" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="povprasevanje_id" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="127" parent="124" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="128" parent="119" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="277" y="129" as="geometry" />
        </mxCell>
        <mxCell id="129" parent="128" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="130" parent="128" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="opis" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="131" parent="128" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="132" parent="119" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="277" y="172" as="geometry" />
        </mxCell>
        <mxCell id="133" parent="132" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="134" parent="132" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="kolicina" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="135" parent="132" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="252" parent="119" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="277" y="215" as="geometry" />
        </mxCell>
        <mxCell id="253" parent="252" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="254" parent="252" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="enota" vertex="1">
          <mxGeometry height="43" width="151" x="83" as="geometry">
            <mxRectangle height="43" width="151" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="255" parent="252" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="234" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Ponudba" mermaidId="n:PONUDBA" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Ponudba" id="136">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="473" width="466" x="110" y="830" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="137" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="43" as="geometry" />
        </mxCell>
        <mxCell id="138" parent="137" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="139" parent="137" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="140" parent="137" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="141" parent="137" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="142" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="86" as="geometry" />
        </mxCell>
        <mxCell id="143" parent="142" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="144" parent="142" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="povprasevanje_id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="145" parent="142" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="146" parent="142" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="147" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="129" as="geometry" />
        </mxCell>
        <mxCell id="148" parent="147" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="149" parent="147" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="podjetje_ponudnika_id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="150" parent="147" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="151" parent="147" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="152" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="172" as="geometry" />
        </mxCell>
        <mxCell id="153" parent="152" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="154" parent="152" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="pravila_id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="155" parent="152" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="156" parent="152" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="obvezno ob odobritvi" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="157" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="215" as="geometry" />
        </mxCell>
        <mxCell id="158" parent="157" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="159" parent="157" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="kontakt_vloga_id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="160" parent="157" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="161" parent="157" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="neobvezno" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="162" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="258" as="geometry" />
        </mxCell>
        <mxCell id="163" parent="162" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="164" parent="162" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="odobril_vloga_id" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="165" parent="162" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="166" parent="162" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="obvezno ob odobritvi" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="167" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="301" as="geometry" />
        </mxCell>
        <mxCell id="168" parent="167" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="text" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="169" parent="167" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="stanje" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="170" parent="167" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="171" parent="167" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="172" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="344" as="geometry" />
        </mxCell>
        <mxCell id="173" parent="172" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="int" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="174" parent="172" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="razlicica" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="175" parent="172" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="176" parent="172" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="256" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="387" as="geometry" />
        </mxCell>
        <mxCell id="257" parent="256" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="258" parent="256" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="ustvarjeno_ob" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="259" parent="256" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="260" parent="256" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="261" parent="136" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="466" y="430" as="geometry" />
        </mxCell>
        <mxCell id="262" parent="261" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="timestamp" vertex="1">
          <mxGeometry height="43" width="56" as="geometry">
            <mxRectangle height="43" width="56" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="263" parent="261" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="odobreno_ob" vertex="1">
          <mxGeometry height="43" width="191" x="56" as="geometry">
            <mxRectangle height="43" width="191" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="264" parent="261" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="247" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="265" parent="261" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="290" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="Postavka ponudbe" mermaidId="n:POSTAVKA_PONUDBE" mermaidBaseStyle="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Postavka ponudbe" id="177">
          <mxCell parent="224" style="shape=table;startSize=43;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="344" width="524" x="740" y="1250" as="geometry" />
          </mxCell>
        </UserObject>
        <mxCell id="178" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="43" as="geometry" />
        </mxCell>
        <mxCell id="179" parent="178" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="180" parent="178" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="id" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="181" parent="178" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="PK" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="182" parent="178" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="183" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="86" as="geometry" />
        </mxCell>
        <mxCell id="184" parent="183" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="185" parent="183" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="ponudba_id" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="186" parent="183" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="187" parent="183" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="188" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="129" as="geometry" />
        </mxCell>
        <mxCell id="189" parent="188" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="190" parent="188" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="postavka_povprasevanja_id" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="191" parent="188" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="192" parent="188" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="193" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="172" as="geometry" />
        </mxCell>
        <mxCell id="194" parent="193" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="uuid" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="195" parent="193" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="postavka_cenika_id" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="196" parent="193" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="FK" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="197" parent="193" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="neobvezno" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="198" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="215" as="geometry" />
        </mxCell>
        <mxCell id="199" parent="198" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="200" parent="198" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="cena_na_enoto" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="201" parent="198" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="202" parent="198" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="obvezno ob odobritvi" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="203" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#F1F1FF,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="258" as="geometry" />
        </mxCell>
        <mxCell id="204" parent="203" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="205" parent="203" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="strosek_na_enoto" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="206" parent="203" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="207" parent="203" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="obvezno ob odobritvi" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="266" parent="177" style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=1;fillColor=light-dark(#ffffff,#1f2020);strokeColor=inherit;strokeWidth=1;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" vertex="1">
          <mxGeometry height="43" width="524" y="301" as="geometry" />
        </mxCell>
        <mxCell id="267" parent="266" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="numeric" vertex="1">
          <mxGeometry height="43" width="83" as="geometry">
            <mxRectangle height="43" width="83" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="268" parent="266" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="kolicina" vertex="1">
          <mxGeometry height="43" width="222" x="83" as="geometry">
            <mxRectangle height="43" width="222" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="269" parent="266" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="43" x="305" as="geometry">
            <mxRectangle height="43" width="43" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <mxCell id="270" parent="266" style="shape=partialRectangle;connectable=0;fillColor=none;strokeColor=light-dark(#9370DB,#cccccc);strokeWidth=1;fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;top=1;left=1;bottom=1;right=1;align=left;spacingLeft=8;overflow=hidden;fontSize=16;" value="" vertex="1">
          <mxGeometry height="43" width="176" x="348" as="geometry">
            <mxRectangle height="43" width="176" as="alternateBounds" />
          </mxGeometry>
        </mxCell>
        <UserObject label="uporabnik_id" mermaidId="e:UPORABNIK-&gt;VLOGA_UPORABNIKA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="uporabnik_id" id="208">
          <mxCell edge="1" parent="224" source="3" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;entryDx=0;entryDy=0;exitDx=0;exitDy=0;" target="21">
            <mxGeometry relative="1" x="-0.0499" y="28" as="geometry">
              <mxPoint as="offset" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="podjetje_id" mermaidId="e:PODJETJE-&gt;VLOGA_UPORABNIKA#0" mermaidBaseStyle="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0;entryY=0.16;" mermaidBaseValue="podjetje_id" id="209">
          <mxCell edge="1" parent="224" source="11" style="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.75;exitY=0;entryX=1;entryY=0.5;exitDx=0;exitDy=0;entryDx=0;entryDy=0;" target="26">
            <mxGeometry relative="1" x="-0.3303" y="2" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="1100" y="80" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="podjetje_id" mermaidId="e:PODJETJE-&gt;PRAVILA_PONUDNIKA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="podjetje_id" id="210">
          <mxCell edge="1" parent="224" source="12" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.5;entryX=0.5;entryY=0;exitDx=0;exitDy=0;" target="46">
            <mxGeometry relative="1" x="0.4384" y="55" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="170" y="250" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="podjetje_id" mermaidId="e:PODJETJE-&gt;POSTAVKA_CENIKA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0;entryY=0.5;" mermaidBaseValue="podjetje_id" id="211">
          <mxCell edge="1" parent="224" source="11" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" target="63">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="1500" y="350" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="postavka_cenika_id" mermaidId="e:POSTAVKA_CENIKA-&gt;ZALOGA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToOne;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="postavka_cenika_id" id="212">
          <mxCell edge="1" parent="224" source="63" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToOne;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.5;entryY=0;" target="89">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="podjetje_nabavnika_id" mermaidId="e:PODJETJE-&gt;POVPRASEVANJE#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.16;entryY=0;" mermaidBaseValue="podjetje_nabavnika_id" id="213">
          <mxCell edge="1" parent="224" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);entryX=1;entryY=0;entryDx=0;entryDy=0;" target="102">
            <mxGeometry relative="1" x="-0.3242" y="5.26" as="geometry">
              <Array as="points" />
              <mxPoint x="1050" y="360" as="sourcePoint" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="ustvaril_vloga_id" mermaidId="e:VLOGA_UPORABNIKA-&gt;POVPRASEVANJE#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.84;entryX=1;entryY=0.16;" mermaidBaseValue="ustvaril_vloga_id" id="214">
          <mxCell edge="1" parent="224" source="41" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.492;exitY=1.066;entryX=0.25;entryY=0;entryDx=0;entryDy=0;exitDx=0;exitDy=0;exitPerimeter=0;" target="102">
            <mxGeometry relative="1" x="-0.1233" y="33" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="730" y="400" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="povprasevanje_id" mermaidId="e:POVPRASEVANJE-&gt;POSTAVKA_POVPRASEVANJA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0;entryY=0.5;" mermaidBaseValue="povprasevanje_id" id="215">
          <mxCell edge="1" parent="224" source="115" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.503;exitY=1.14;entryX=0;entryY=0.5;exitDx=0;exitDy=0;exitPerimeter=0;" target="119">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="864.86" y="840" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="povprasevanje_id" mermaidId="e:POVPRASEVANJE-&gt;PONUDBA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.84;entryY=0;" mermaidBaseValue="povprasevanje_id" id="216">
          <mxCell edge="1" parent="224" source="102" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=1;entryY=0.5;entryDx=0;entryDy=0;" target="137">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="760" y="840" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="podjetje_ponudnika_id" mermaidId="e:PODJETJE-&gt;PONUDBA#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.84;entryY=0;" mermaidBaseValue="podjetje_ponudnika_id" id="217">
          <mxCell edge="1" parent="224" source="11" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.84;entryY=0;" target="136">
            <mxGeometry relative="1" x="0.0652" y="75" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="550" y="420" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="pravila_id" mermaidId="e:PRAVILA_PONUDNIKA-&gt;PONUDBA#0" mermaidBaseStyle="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="pravila_id" id="218">
          <mxCell edge="1" parent="224" source="59" style="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.01;exitY=1.011;entryX=0;entryY=0.5;exitDx=0;exitDy=0;exitPerimeter=0;entryDx=0;entryDy=0;" target="142">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="kontakt_vloga_id" mermaidId="e:VLOGA_UPORABNIKA-&gt;PONUDBA#0" mermaidBaseStyle="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.84;entryY=0;" mermaidBaseValue="kontakt_vloga_id" id="219">
          <mxCell edge="1" parent="224" source="20" style="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" target="136">
            <mxGeometry relative="1" x="-0.0933" y="-29.35" as="geometry">
              <Array as="points">
                <mxPoint x="510" y="590" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="odobril_vloga_id" mermaidId="e:VLOGA_UPORABNIKA-&gt;PONUDBA#1" mermaidBaseStyle="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.84;entryY=0;" mermaidBaseValue="odobril_vloga_id" id="220">
          <mxCell edge="1" parent="224" source="41" style="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.012;exitY=0.96;entryX=0.25;entryY=0;entryDx=0;entryDy=0;exitDx=0;exitDy=0;exitPerimeter=0;" target="136">
            <mxGeometry relative="1" x="0.1795" y="12" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="310" y="690" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="ponudba_id" mermaidId="e:PONUDBA-&gt;POSTAVKA_PONUDBE#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.16;" mermaidBaseValue="ponudba_id" id="221">
          <mxCell edge="1" parent="224" source="136" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.16;" target="177">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="681" y="1131" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="postavka_povprasevanja_id" mermaidId="e:POSTAVKA_POVPRASEVANJA-&gt;POSTAVKA_PONUDBE#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="postavka_povprasevanja_id" id="222">
          <mxCell edge="1" parent="224" source="119" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" target="177">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="1030" y="1130" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="postavka_cenika_id" mermaidId="e:POSTAVKA_CENIKA-&gt;POSTAVKA_PONUDBE#0" mermaidBaseStyle="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.84;entryX=1;entryY=0.16;" mermaidBaseValue="postavka_cenika_id" id="223">
          <mxCell edge="1" parent="224" source="63" style="curved=1;startArrow=ERzeroToOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.84;entryX=1;entryY=0.16;" target="177">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="1300" y="1000" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>

```

## Pravila povezav in stanj

- Vloga je vez med uporabnikom in podjetjem, ne lastnost podjetja. Poslovni vlogi zahtevata podjetje; globalni administrator ga nima. Trojica `(uporabnik_id, podjetje_id, vloga)` je enolična, dodelitev administratorja brez podjetja pa potrebuje ločeno enoličnost. Registriran uporabnik brez aktivne poslovne vloge ne more oddati povpraševanja ali odobriti ponudbe. Administrator sam po sebi ne more odobriti ponudbe.
- `Povpraševanje.ustvaril_vloga_id` mora kazati na aktivnega nabavnika pri `podjetje_nabavnika_id`. Oddano povpraševanje mora imeti vsaj eno postavko in `oddano_ob`; `rok_za_ponudbe`, če je določen, mora biti poznejši od časa oddaje.
- `Ponudba.podjetje_ponudnika_id` se mora razlikovati od kupčevega podjetja pri istem povpraševanju. `kontakt_vloga_id` in `odobril_vloga_id` lahko kažeta samo na aktivnega ponudnika pri tem podjetju. `pravila_id` mora pripadati istemu podjetju.
- Postavka ponudbe mora odgovarjati na postavko **istega** povpraševanja. Če kaže na postavko cenika, mora ta pripadati **istem** podjetju ponudnika. Agent uporabi samo aktivno postavko z `potrjeno_ob`; postavka vrste `storitev` ne sme imeti vrstice zaloge, za blago pa se zaloga preveri, kadar jo ponudnik vodi. Če podatki niso potrjeni ali manjkajo, osnutek zahteva ročni pregled.
- Ob izbiri ponudnika nastane ponudba v stanju `povabljena`; sledijo `osnutek` in po potrebi `v_pregledu`. Ponudnik jo lahko `zavrne` ali `odobri`. Pred odobritvijo mora imeti vsaj eno popolno postavko. Samo `odobrena` ponudba je vidna nabavniku. Zavrnitev ne pomeni kupčeve zavrnitve, temveč odločitev ponudnika, da ponudbe ne izda.
- Ob odobritvi strežniški postopek ponovno preveri aktivno vlogo, aktualno različico pravil, ceno, strošek, maržo, popust in morebitno zalogo; `pravila_id` nastavi na uporabljeno različico. V isti transakciji zapiše odobritelja, čas, skupni znesek in stanje ter zaklene ponudbo in postavke. Tako poznejša sprememba cenika ali zaloge ne spremeni že odobrene ponudbe.
- Nabavnik bere samo odobrene javne podatke ponudbe. RLS loči podjetja, strežniški API ali izrecno omejen pogled pa izloči `strosek_na_enoto`; samo filtriranje vrstic z RLS ne bi skrilo tega stolpca. Pravila, ki primerjajo več tabel, se uveljavijo v transakcijskem postopku oziroma ustreznem sprožilcu.

**Poznejša nadgradnja F10 – Obvestilo:** `id PK`, `ponudba_id FK → Ponudba`, `prejemnik_vloga_id FK → Vloga uporabnika`, `dogodek`, `kanal`, `stanje_dostave`, `kljuc_brez_podvajanja UQ`, `poslano_ob?`. Dogodek razlikuje novo povabilo, osnutek in odobreno ponudbo. Prejemnik mora imeti ustrezno aktivno vlogo pri kupcu ali ponudniku. Obvestilo je ločen zapis o dostavi, ne odločitev o ponudbi; e-pošta vsebuje povezavo do aplikacije, ne cen ali internih stroškov.

## Povezava z obstoječo bazo

Ta model **še ni uveden** v Supabase. Trenutne migracije imajo drugačne tabele, med drugim ločen `products`, `rfq_recipients`, `approvals` in `published_quotes`. Zato ta dokument ne pomeni, da so te tabele že odstranjene: za uvedbo novega modela so potrebni migracija, prenos podatkov in testi dostopa med podjetji.
