# Arhitektura in tehnološki sklad

## Arhitektura

Aplikacijo sestavljajo spletni vmesnik, strežniški API, PostgreSQL v Supabase in omejen AI-agent. Vmesnik pošilja zahtevke API-ju; API preveri identiteto in pravice, nato dostopa do podatkov. Agent uporablja samo določene funkcije za branje potrjenih podatkov in pripravo osnutkov. Cene, zaloge, marže in pravila izračuna strežniška programska logika. Objavo ponudbe sproži le izrecna odobritev ponudnika.

```drawio
<mxfile>
  <diagram id="F5TcVpQF0bnYtdr55bpC" name="Page-1">
    <mxGraphModel dx="1318" dy="1097" grid="1" gridSize="10" guides="1" tooltips="0" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="uEDF05B4iM_XfAuLPrMw-0" />
        <mxCell id="uEDF05B4iM_XfAuLPrMw-1" parent="uEDF05B4iM_XfAuLPrMw-0" />
        <UserObject label="" mermaidData="{&#xa;  &quot;data&quot;: &quot;flowchart LR\n  B[Brskalnik: React] --&gt;|HTTPS/JSON| A[FastAPI]\n  A --&gt; I[Supabase Auth]\n  A --&gt; D[(Supabase PostgreSQL)]\n  A --&gt; P[Poslovna pravila in izračuni]\n  A --&gt; G[AI-agent z omejenimi orodji]\n  G --&gt; P\n  P --&gt; D&quot;,&#xa;  &quot;config&quot;: null&#xa;}" id="WcMXBpJxgXS3k31XFfvM-0">
          <mxCell connectable="0" parent="uEDF05B4iM_XfAuLPrMw-1" style="group;transparentBounds=1;editIcon=1;lockedGroup=0;groupPadding=10;" vertex="1">
            <mxGeometry as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Brskalnik: React" mermaidId="n:B" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Brskalnik: React" id="uEDF05B4iM_XfAuLPrMw-2">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="175" x="10" y="82" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="FastAPI" mermaidId="n:A" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="FastAPI" id="uEDF05B4iM_XfAuLPrMw-3">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="112" x="325" y="82" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Supabase Auth" mermaidId="n:I" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Supabase Auth" id="uEDF05B4iM_XfAuLPrMw-4">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="163" x="536" y="10" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Supabase PostgreSQL" mermaidId="n:D" mermaidBaseStyle="html=1;shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;strokeWidth=1;whiteSpace=wrap;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Supabase PostgreSQL" id="uEDF05B4iM_XfAuLPrMw-5">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;strokeWidth=1;whiteSpace=wrap;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="67" width="165" x="1103" y="107" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Poslovna pravila in izračuni" mermaidId="n:P" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Poslovna pravila in izračuni" id="uEDF05B4iM_XfAuLPrMw-6">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="255" x="798" y="144" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="AI-agent z omejenimi orodji" mermaidId="n:G" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="AI-agent z omejenimi orodji" id="uEDF05B4iM_XfAuLPrMw-7">
          <mxCell parent="WcMXBpJxgXS3k31XFfvM-0" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="261" x="487" y="175" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="HTTPS/JSON" mermaidId="e:B-&gt;A#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" mermaidBaseValue="HTTPS/JSON" id="uEDF05B4iM_XfAuLPrMw-8">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-2" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" target="uEDF05B4iM_XfAuLPrMw-3">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:A-&gt;I#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.77;exitY=0;entryX=0;entryY=0.5;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-9">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-3" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.77;exitY=0;entryX=0;entryY=0.5;" target="uEDF05B4iM_XfAuLPrMw-4">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="462" y="37" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:A-&gt;D#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.37;entryX=0;entryY=0.03;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-10">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-3" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.37;entryX=0;entryY=0.03;" target="uEDF05B4iM_XfAuLPrMw-5">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="462" y="99" />
                <mxPoint x="618" y="99" />
                <mxPoint x="773" y="99" />
                <mxPoint x="926" y="99" />
                <mxPoint x="1078" y="99" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:A-&gt;P#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.89;entryX=0;entryY=0.02;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-11">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-3" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.89;entryX=0;entryY=0.02;" target="uEDF05B4iM_XfAuLPrMw-6">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="462" y="140" />
                <mxPoint x="618" y="140" />
                <mxPoint x="773" y="140" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:A-&gt;G#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.71;exitY=1;entryX=0;entryY=0.5;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-12">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-3" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.71;exitY=1;entryX=0;entryY=0.5;" target="uEDF05B4iM_XfAuLPrMw-7">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="462" y="202" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:G-&gt;P#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.98;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-13">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-7" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.98;" target="uEDF05B4iM_XfAuLPrMw-6">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="773" y="202" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:P-&gt;D#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.85;" mermaidBaseValue="" id="uEDF05B4iM_XfAuLPrMw-14">
          <mxCell edge="1" parent="WcMXBpJxgXS3k31XFfvM-0" source="uEDF05B4iM_XfAuLPrMw-6" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.85;" target="uEDF05B4iM_XfAuLPrMw-5">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="1078" y="171" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>

```

Uporabniške identitete upravlja Supabase Auth. Vloge nabavnika, ponudnika in administratorja izhajajo iz članstev v podatkovni bazi; pravice preverja backend pri vsakem dostopu. Podatki različnih podjetij so ločeni tudi s pravili dostopa v bazi. Osnutki in interni stroški niso dostopni nabavniku.

## Tehnološki sklad

| Del | Tehnologija ali orodje | Namen |
|---|---|---|
| Frontend | React, TypeScript, Vite | Spletni obrazci in pregled podatkov. |
| Backend | Python, FastAPI | API, preverjanje pravic in poslovni postopki. |
| Podatkovna baza | Supabase PostgreSQL | Trajno shranjevanje, povezave med podatki in izolacija podjetij. |
| Avtentikacija | Supabase Auth | Registracija, prijava in identiteta uporabnika. |
| AI-agent | Jezikovni model s strukturiranim izhodom in omejenimi orodji | Analiza RFQ in priprava predlogov; brez pravice odobritve. |
| Lokalni razvoj | Docker Compose, Supabase CLI, pytest | Zagon storitev, migracije in preverjanje. |

## Arhitekturne odločitve

- En backend z ločenimi moduli poenostavi razvoj in ohranja skupno logiko za ročno ter samodejno izbiro ponudnikov.
- Vsak ponudnik ima lasten osnutek; odobritev in objava se zabeležita v eni podatkovni transakciji.
- Izračuni so deterministični. AI ne določa cen ali zalog brez potrjenih podatkov in ne more odobriti ponudbe.
- Spletno iskanje in dovoljeno pridobivanje javnih podatkov sta možni nadgradnji. Njuni rezultati niso potrjeni poslovni podatki ponudnika.
