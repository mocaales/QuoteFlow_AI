# Arhitektura in tehnološki sklad

## Poslovni tok

1. Nabavnik z aktivno pravico `buyer` odda RFQ za svoje podjetje. Zahteve so prosto opisane; niso vezane na cenik enega ponudnika.
2. Ročna izbira ali sistemsko ujemanje ustvari po eno ponudbo v stanju `povabljena` za vsako registrirano podjetje ponudnika. Neobvezni kontaktni uporabnik mora imeti pri njem aktivno pravico `supplier`.
3. Backend posreduje omejenemu AI-agentu besedilo RFQ in dovoljene podatke potrjenega cenika blaga ali storitev. Agent vrne strukturiran predlog razumevanja in ujemanja. Manjkajoče ali dvoumne podatke označi za pregled.
4. Backend za vsakega izbranega ponudnika pripravi ločen osnutek. Programska pravila preverijo ceno, strošek, maržo, morebitno zalogo, popust in rok; agent teh vrednosti ne potrjuje.
5. Ponudnik osnutek popravi, zavrne ali odobri. Ob odobritvi sistem še enkrat preveri pravice in izračune ter v eni transakciji zabeleži odobritelja, čas in stanje `odobrena` ter zaklene ponudbo s postavkami. Nabavnik vidi le odobreno ponudbo brez internih stroškov.
6. Obvestila v aplikaciji in po e-pošti so F10, poznejša funkcionalnost. Nastanejo iz zabeleženega dogodka in ne določajo veljavnosti odobritve.

## Deli sistema in komunikacija

```drawio
<mxfile>
  <diagram id="NcJ353IxQhQh3Pj6mGIt" name="Page-1">
    <mxGraphModel dx="1360" dy="1121" grid="1" gridSize="10" guides="1" tooltips="0" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <UserObject label="" mermaidData="{&#xa;  &quot;data&quot;: &quot;flowchart LR\n    U[Uporabnik] --&gt; WEB[React in TypeScript]\n    WEB --&gt;|HTTPS in JSON| API[FastAPI]\n    API --&gt;|identiteta| AUTH[Supabase Auth]\n    API --&gt;|poslovni podatki| DB[(Supabase PostgreSQL)]\n    API --&gt;|omejen vhod RFQ| AI[GPT-6 Luna prek Responses API]\n    AI --&gt;|strukturiran predlog| API\n    API --&gt; RULES[Deterministična pravila in odobritev]\n    RULES --&gt; DB\n    DB -.-&gt;|dogodek F10| OUTBOX[Vrsta obvestil]\n    OUTBOX -.-&gt; WORKER[Pošiljatelj]\n    WORKER -.-&gt;|F10| SMTP[SMTP storitev]&quot;,&#xa;  &quot;config&quot;: null&#xa;}" id="23">
          <mxCell connectable="0" parent="1" style="group;transparentBounds=1;editIcon=1;lockedGroup=0;groupPadding=10;" vertex="1">
            <mxGeometry as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Uporabnik" mermaidId="n:U" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Uporabnik" id="2">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="133" x="10" y="135" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="React in TypeScript" mermaidId="n:WEB" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="React in TypeScript" id="3">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="197" x="193" y="135" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="FastAPI" mermaidId="n:API" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="FastAPI" id="4">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="112" x="545" y="135" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Supabase Auth" mermaidId="n:AUTH" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Supabase Auth" id="5">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="163" x="929" y="10" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Supabase PostgreSQL" mermaidId="n:DB" mermaidBaseStyle="html=1;shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;strokeWidth=1;whiteSpace=wrap;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Supabase PostgreSQL" id="6">
          <mxCell parent="23" style="html=1;shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;strokeWidth=1;whiteSpace=wrap;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="67" width="165" x="1220" y="215" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="GPT-6 Luna prek Responses API" mermaidId="n:AI" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="GPT-6 Luna prek Responses API" id="7">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="281" x="870" y="114" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Deterministična pravila in odobritev" mermaidId="n:RULES" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Deterministična pravila in odobritev" id="8">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="319" x="851" y="257" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Vrsta obvestil" mermaidId="n:OUTBOX" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Vrsta obvestil" id="9">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="157" x="1525" y="221" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Pošiljatelj" mermaidId="n:WORKER" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="Pošiljatelj" id="10">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="132" x="1732" y="221" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="SMTP storitev" mermaidId="n:SMTP" mermaidBaseStyle="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" mermaidBaseValue="SMTP storitev" id="11">
          <mxCell parent="23" style="html=1;whiteSpace=wrap;strokeWidth=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontSize=16;" vertex="1">
            <mxGeometry height="54" width="157" x="1939" y="221" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:U-&gt;WEB#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" mermaidBaseValue="" id="12">
          <mxCell edge="1" parent="23" source="2" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" target="3">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="HTTPS in JSON" mermaidId="e:WEB-&gt;API#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" mermaidBaseValue="HTTPS in JSON" id="13">
          <mxCell edge="1" parent="23" source="3" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" target="4">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="identiteta" mermaidId="e:API-&gt;AUTH#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.79;exitY=0;entryX=0;entryY=0.5;" mermaidBaseValue="identiteta" id="14">
          <mxCell edge="1" parent="23" source="4" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.79;exitY=0;entryX=0;entryY=0.5;" target="5">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="754" y="37" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="poslovni podatki" mermaidId="e:API-&gt;DB#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.83;entryX=0;entryY=0.09;" mermaidBaseValue="poslovni podatki" id="15">
          <mxCell edge="1" parent="23" source="4" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.83;entryX=0;entryY=0.09;" target="6">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="754" y="213" />
                <mxPoint x="1011" y="213" />
                <mxPoint x="1195" y="213" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="omejen vhod RFQ" mermaidId="e:API-&gt;AI#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.7407407407407407;entryX=0;entryY=0.7407407407407407;curved=1;exitX=1;exitY=0.74;entryX=0;entryY=0.74;" mermaidBaseValue="omejen vhod RFQ" id="16">
          <mxCell edge="1" parent="23" source="4" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.74;entryX=0;entryY=0.74;" target="7">
            <mxGeometry relative="1" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="764" y="227" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="strukturiran predlog" mermaidId="e:AI-&gt;API#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.2592592592592593;entryX=1;entryY=0.2592592592592593;curved=1;exitX=0;exitY=0.26;entryX=1;entryY=0.26;" mermaidBaseValue="strukturiran predlog" id="17">
          <mxCell edge="1" parent="23" source="7" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.26;entryX=1;entryY=0.26;" target="4">
            <mxGeometry relative="1" as="geometry">
              <mxPoint as="offset" />
              <Array as="points">
                <mxPoint x="764" y="68" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:API-&gt;RULES#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.8;exitY=1;entryX=0;entryY=0.5;" mermaidBaseValue="" id="18">
          <mxCell edge="1" parent="23" source="4" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=0.8;exitY=1;entryX=0;entryY=0.5;" target="8">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="754" y="284" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:RULES-&gt;DB#0" mermaidBaseStyle="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.91;" mermaidBaseValue="" id="19">
          <mxCell edge="1" parent="23" source="8" style="curved=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.91;" target="6">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="1195" y="284" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="dogodek F10" mermaidId="e:DB-&gt;OUTBOX#0" mermaidBaseStyle="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.49;entryX=0;entryY=0.5;" mermaidBaseValue="dogodek F10" id="20">
          <mxCell edge="1" parent="23" source="6" style="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.49;entryX=0;entryY=0.5;" target="9">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="" mermaidId="e:OUTBOX-&gt;WORKER#0" mermaidBaseStyle="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" mermaidBaseValue="" id="21">
          <mxCell edge="1" parent="23" source="9" style="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" target="10">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="F10" mermaidId="e:WORKER-&gt;SMTP#0" mermaidBaseStyle="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" mermaidBaseValue="F10" id="22">
          <mxCell edge="1" parent="23" source="10" style="curved=1;dashed=1;dashPattern=2 3;fixDash=1;startArrow=none;endArrow=block;endSize=7;strokeColor=light-dark(#333333,#cccccc);html=1;fontSize=16;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.5;entryX=0;entryY=0.5;" target="11">
            <mxGeometry relative="1" as="geometry">
              <Array as="points" />
            </mxGeometry>
          </mxCell>
        </UserObject>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>

```

API pri vsakem zahtevku preveri uporabnika, aktivno dodelitev pravice in podjetje. PostgreSQL RLS je dodatna meja za branje podatkov med podjetji; za pisanje veljajo ozki strežniški postopki. AI uporablja le orodja za branje potrjenih podatkov, nima pravice odobritve ali pošiljanja e-pošte. SMTP-pošiljatelj dela šele po uspešnem zapisu poslovnega dogodka; ob napaki obvestilo poskusi znova brez podvojitve sporočila. E-pošta vsebuje le obvestilo in povezavo na prijavo v aplikacijo.

## Tehnološki sklad

| Del | Izbira | Razlog |
|---|---|---|
| Spletni vmesnik | React, TypeScript, Vite | Obrazci in pregled stanj z nadzorovanimi podatkovnimi tipi. |
| Strežniški del | Python, FastAPI | En API za pravice, poslovna pravila in integracijo modela. |
| Podatki in identiteta | Supabase PostgreSQL, Supabase Auth | Relacije, transakcije, RLS in en vir prijavne identitete. |
| AI-agent | [OpenAI GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), Responses API | Omejena analiza besedila; model podpira klicanje funkcij in strukturiran izhod. |
| E-pošta F10 | Vrsta obvestil, ločen pošiljatelj, SMTP | Dostava se lahko ponovi, ne da bi vplivala na odobreno ponudbo. |
| Lokalni razvoj | Docker Compose, Supabase CLI, pytest | Ponovljiv zagon, migracije in preverjanje pravil. |

## Arhitekturne odločitve

- **En poslovni proces za oba načina izbire:** oba ustvarita ponudbo v stanju `povabljena`; razlog in izvor izbire sta zapisana na njej. Ločena tabela vabil ni potrebna.
- **Ena tabela za dodelitve pravic:** uporabnik lahko pri različnih podjetjih opravlja različni nalogi; globalni administrator nima lažnega članstva v podjetju.
- **Ena ponudba od izbire do odobritve:** stanje in zapis odobritve sta na ponudbi. Ob odobritvi se ponudba in njene postavke zaklenejo; nabavnik dobi samo dovoljena javna polja.
- **AI predlaga, program preveri, človek odobri:** model ne določa poslovno zavezujočih cen ali zalog.
- **E-pošta ni transakcija odobritve:** odobrena ponudba ostane veljavna tudi ob začasni napaki SMTP; pošiljanje in stanje dostave se vodita ločeno.

Podrobne entitete, ključi in povezave so v [podatkovnem modelu](03-podatkovni-model.md). To je **ciljna arhitektura**. Trenutno ogrodje vsebuje demonstracijski kalkulator in starejšo shemo; opisani RFQ-proces, agent, odobritev ter e-pošta še niso v celoti implementirani. Spletno odkrivanje dodatnih ponudnikov in dovoljeno pridobivanje javnih podatkov ostajata nadgradnji; tak podatek ni potrjena ponudba.
