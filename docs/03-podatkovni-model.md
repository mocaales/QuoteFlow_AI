# Podatkovni model

Podatki se hranijo v PostgreSQL projekta Supabase. Poslovni zapisi so ločeni po podjetjih. Spodnja tabela prikazuje glavne povezane entitete in njihova ključna polja; dodatne tehnične tabele podpirajo različice, agente in revizijsko sled.

| Entiteta | Glavna polja | Povezava |
|---|---|---|
| Podjetje (`companies`) | id, naziv, stanje | Ima člane, katalog, RFQ ali ponudbe. |
| Uporabnik (`auth.users`, `user_profiles`) | id, e-pošta, prikazno ime, stanje | S članstvom pripada podjetju. Gesla upravlja Supabase Auth. |
| Članstvo (`company_members`) | podjetje_id, uporabnik_id, vloga, aktivno | Poveže uporabnika in podjetje ter določa pravice. |
| Izdelek (`products`) | id, proizvajalec, šifra, naziv | Ponudniki ga vključijo v svoj katalog. |
| Ponudnikov izdelek (`supplier_products`) | podjetje_id, izdelek_id, cena, strošek, zaloga, rok, čas potrditve | Interni podatki posameznega ponudnika. |
| Cenovna pravila (`pricing_policies`) | podjetje_id, najmanjša marža, največji popust, najdaljši rok | Veljajo za enega ponudnika. |
| Povpraševanje (`rfqs`) | id, podjetje kupca, način izbire, stanje, dobavni pogoji | Ima postavke in izbrane ponudnike. |
| Postavka RFQ (`rfq_items`) | rfq_id, izdelek oziroma opis, količina | Pripada enemu RFQ. |
| Prejemnik RFQ (`rfq_recipients`) | rfq_id, podjetje ponudnika, razlog izbire | Povezuje RFQ z dodeljenim ponudnikom. |
| Ponudba (`quotes`, `quote_items`) | rfq_id, podjetje ponudnika, stanje, različica; postavke in cene | Vsak ponudnik pripravi svojo ponudbo za dodeljeni RFQ. |
| Odobritev (`approvals`) | ponudba/različica, uporabnik, odločitev, čas | Izrecna odločitev pooblaščenega ponudnika. |
| Objavljena ponudba (`published_quotes`, `published_quote_items`) | odobritev, javni pogoji in postavke | Nabavniku dostopna različica brez internih stroškov. |

```drawio
<mxfile>
  <diagram id="g5OaCl21tBsDj3Bu2whL" name="Page-1">
    <mxGraphModel dx="1117" dy="930" grid="1" gridSize="10" guides="1" tooltips="0" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="HwzSsednXKhmdOzrmkGr-0" />
        <mxCell id="HwzSsednXKhmdOzrmkGr-1" parent="HwzSsednXKhmdOzrmkGr-0" />
        <UserObject label="" mermaidData="{&#xa;  &quot;data&quot;: &quot;erDiagram\n  Podjetje ||--o{ Clanstvo : ima\n  Uporabnik ||--o{ Clanstvo : pripada\n  Podjetje ||--o{ PonudnikovIzdelek : potrdi\n  Izdelek ||--o{ PonudnikovIzdelek : opisuje\n  Podjetje ||--o{ RFQ : odda\n  RFQ ||--|{ PostavkaRFQ : vsebuje\n  RFQ ||--o{ PrejemnikRFQ : dodeli\n  PrejemnikRFQ ||--o{ Ponudba : prejme\n  Ponudba ||--o{ Odobritev : potrdi\n  Odobritev ||--o| ObjavljenaPonudba : objavi&quot;,&#xa;  &quot;config&quot;: null&#xa;}" id="anVGzbdLQnlef04BkbXN-0">
          <mxCell connectable="0" parent="HwzSsednXKhmdOzrmkGr-1" style="group;transparentBounds=1;editIcon=1;lockedGroup=0;groupPadding=10;" vertex="1">
            <mxGeometry as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Podjetje" mermaidId="n:Podjetje" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Podjetje" id="HwzSsednXKhmdOzrmkGr-2">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="101" x="218" y="10" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Clanstvo" mermaidId="n:Clanstvo" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Clanstvo" id="HwzSsednXKhmdOzrmkGr-3">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="101" x="16" y="209" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Uporabnik" mermaidId="n:Uporabnik" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Uporabnik" id="HwzSsednXKhmdOzrmkGr-4">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="113" x="10" y="10" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="PonudnikovIzdelek" mermaidId="n:PonudnikovIzdelek" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="PonudnikovIzdelek" id="HwzSsednXKhmdOzrmkGr-5">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="172" x="210" y="209" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Izdelek" mermaidId="n:Izdelek" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Izdelek" id="HwzSsednXKhmdOzrmkGr-6">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="100" x="525" y="10" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="RFQ" mermaidId="n:RFQ" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="RFQ" id="HwzSsednXKhmdOzrmkGr-7">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="100" x="462" y="209" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="PostavkaRFQ" mermaidId="n:PostavkaRFQ" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="PostavkaRFQ" id="HwzSsednXKhmdOzrmkGr-8">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="131" x="401" y="408" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="PrejemnikRFQ" mermaidId="n:PrejemnikRFQ" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="PrejemnikRFQ" id="HwzSsednXKhmdOzrmkGr-9">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="141" x="612" y="408" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Ponudba" mermaidId="n:Ponudba" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Ponudba" id="HwzSsednXKhmdOzrmkGr-10">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="100" x="633" y="607" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="Odobritev" mermaidId="n:Odobritev" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="Odobritev" id="HwzSsednXKhmdOzrmkGr-11">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="111" x="627" y="806" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="ObjavljenaPonudba" mermaidId="n:ObjavljenaPonudba" mermaidBaseStyle="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" mermaidBaseValue="ObjavljenaPonudba" id="HwzSsednXKhmdOzrmkGr-12">
          <mxCell parent="anVGzbdLQnlef04BkbXN-0" style="shape=table;startSize=80;container=1;collapsible=0;childLayout=tableLayout;fixedRows=1;rowLines=1;fontSize=16;fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;strokeWidth=1;align=center;resizeLast=1;html=1;fillColor=light-dark(#ECECFF,#1f2020);strokeColor=light-dark(#9370DB,#cccccc);fontColor=light-dark(#333333,#cccccc);" vertex="1">
            <mxGeometry height="80" width="179" x="593" y="1005" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="ima" mermaidId="e:Podjetje-&gt;Clanstvo#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.84;entryX=1;entryY=0.16;" mermaidBaseValue="ima" id="HwzSsednXKhmdOzrmkGr-13">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-2" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.84;entryX=1;entryY=0.16;" target="HwzSsednXKhmdOzrmkGr-3">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="168" y="222" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="pripada" mermaidId="e:Uporabnik-&gt;Clanstvo#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="pripada" id="HwzSsednXKhmdOzrmkGr-14">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-4" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-3">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="potrdi" mermaidId="e:Podjetje-&gt;PonudnikovIzdelek#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.16;entryY=0;" mermaidBaseValue="potrdi" id="HwzSsednXKhmdOzrmkGr-15">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-2" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.16;entryY=0;" target="HwzSsednXKhmdOzrmkGr-5">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="238" y="150" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="opisuje" mermaidId="e:Izdelek-&gt;PonudnikovIzdelek#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.5;entryX=1;entryY=0.16;" mermaidBaseValue="opisuje" id="HwzSsednXKhmdOzrmkGr-16">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-6" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0;exitY=0.5;entryX=1;entryY=0.16;" target="HwzSsednXKhmdOzrmkGr-5">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="454" y="50" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="odda" mermaidId="e:Podjetje-&gt;RFQ#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0;entryY=0.5;" mermaidBaseValue="odda" id="HwzSsednXKhmdOzrmkGr-17">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-2" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=1;exitY=0.84;entryX=0;entryY=0.5;" target="HwzSsednXKhmdOzrmkGr-7">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="391" y="249" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="vsebuje" mermaidId="e:RFQ-&gt;PostavkaRFQ#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERoneToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="vsebuje" id="HwzSsednXKhmdOzrmkGr-18">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-7" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERoneToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.16;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-8">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="467" y="349" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="dodeli" mermaidId="e:RFQ-&gt;PrejemnikRFQ#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="dodeli" id="HwzSsednXKhmdOzrmkGr-19">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-7" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.84;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-9">
            <mxGeometry relative="1" as="geometry">
              <Array as="points">
                <mxPoint x="683" y="349" />
              </Array>
            </mxGeometry>
          </mxCell>
        </UserObject>
        <UserObject label="prejme" mermaidId="e:PrejemnikRFQ-&gt;Ponudba#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="prejme" id="HwzSsednXKhmdOzrmkGr-20">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-9" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-10">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="potrdi" mermaidId="e:Ponudba-&gt;Odobritev#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="potrdi" id="HwzSsednXKhmdOzrmkGr-21">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-10" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToMany;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-11">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
        <UserObject label="objavi" mermaidId="e:Odobritev-&gt;ObjavljenaPonudba#0" mermaidBaseStyle="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToOne;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" mermaidBaseValue="objavi" id="HwzSsednXKhmdOzrmkGr-22">
          <mxCell edge="1" parent="anVGzbdLQnlef04BkbXN-0" source="HwzSsednXKhmdOzrmkGr-11" style="curved=1;startArrow=ERmandOne;startSize=14;endArrow=ERzeroToOne;endSize=14;strokeColor=light-dark(#333333,#cccccc);strokeWidth=1;html=1;fontSize=14;labelBackgroundColor=light-dark(#F8FFEC4D,#2a2a2a4D);fontFamily=Trebuchet MS,Verdana,Arial,sans-serif;fontColor=light-dark(#333333,#cccccc);exitX=0.5;exitY=1;entryX=0.5;entryY=0;" target="HwzSsednXKhmdOzrmkGr-12">
            <mxGeometry relative="1" as="geometry" />
          </mxCell>
        </UserObject>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>

```

Povezave s tujimi ključi zagotavljajo, da ponudba pripada dodeljenemu RFQ in pravemu ponudniku. Politike dostopa v bazi omejijo vpogled po podjetju. Nabavnik vidi svojo objavljeno ponudbo, ne vidi pa ponudnikovega osnutka, nabavne cene ali marže. Manjkajoči podatki so označeni kot neznani in jih sistem ne izmišlja.
