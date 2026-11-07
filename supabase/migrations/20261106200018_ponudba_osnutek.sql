-- US-04 (#41) quote draft and project items (model v3): a master creates a quote (number P-YYYY-NNN per company per year, all
-- versions keep it); a draft is only a header with velja_do, its lines are snapshotted from the project items when it is sent.
-- Project items (postavka_projekta) are new or copied from the catalogue with the labour data of their vrsta dela (a copy, editable
-- per item); izmere determine izmera_skupaj, which only these functions write (full recompute, never negative).
-- Every write names company and project (and item/izmera); a row of another company or project is the same no_data_found as a
-- random id. "Today" is the Europe/Ljubljana date (danes). velja_do is null or within [today, today+366] -> otherwise 22023.
-- QFP07 wrong phase or accepted quote exists · QFP09 draft exists · QFP10 not a draft · QFP16 inactive catalogue item ·
-- QFP20 more than 200 items per project · QFP23 more than 50 versions · QFP25 izmere would give a negative quantity ·
-- QFP27 unit change of an item with izmere · QFP28 more than 100 izmere per item · QFP29 inactive vrsta dela.
-- Bounds are table checks (23514/22003). Lock order: podjetje -> projekt -> postavka_projekta -> izmera -> ponudba.

-- Business date of the company's jurisdiction, independent of the session time zone.
create function quoteflow_private.danes() returns date language sql stable set search_path='' as $$
 select (now() at time zone 'Europe/Ljubljana')::date
$$;

create function quoteflow_private.preveri_velja_do(velja_do date) returns void language plpgsql stable set search_path='' as $$
begin
 if velja_do<quoteflow_private.danes() or velja_do>quoteflow_private.danes()+366 then
  raise invalid_parameter_value using message='Veljavnost ponudbe mora biti med danes in 366 dni vnaprej'; end if;
end $$;

-- Internal helper (not granted): the caller already holds the company lock via preveri_mojstra.
create function quoteflow_private.preveri_osnutek(podjetje uuid,projekt uuid,ponudba uuid) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; f text;
begin
 -- The project first: preveri_ponudbo locks it on every quote update, so taking it after the quote could deadlock.
 select p.faza into f from quoteflow.projekt p where p.id=preveri_osnutek.projekt and p.podjetje_id=preveri_osnutek.podjetje for update;
 if not found then raise no_data_found; end if;
 select * into r from quoteflow.ponudba q where q.id=preveri_osnutek.ponudba and q.projekt_id=preveri_osnutek.projekt for update;
 if not found then raise no_data_found; end if;
 if r.stanje<>'osnutek' then raise exception 'Poslana ponudba je zaklenjena' using errcode='QFP10'; end if;
 if f not in ('pregled','ogled','ponudba') or exists(select 1 from quoteflow.ponudba q where q.projekt_id=r.projekt_id and q.stanje='sprejeta') then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 return r;
end $$;

create function quoteflow_private.ustvari_ponudbo(podjetje uuid,projekt uuid,velja_do date) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; prev quoteflow.ponudba; p quoteflow.projekt; n integer; y text;
begin
 perform quoteflow_private.preveri_mojstra(ustvari_ponudbo.podjetje);
 select * into p from quoteflow.projekt x where x.id=ustvari_ponudbo.projekt and x.podjetje_id=ustvari_ponudbo.podjetje for update;
 if not found then raise no_data_found; end if;
 if p.faza not in ('pregled','ogled','ponudba') or exists(select 1 from quoteflow.ponudba q where q.projekt_id=p.id and q.stanje='sprejeta') then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 if exists(select 1 from quoteflow.ponudba q where q.projekt_id=p.id and q.stanje='osnutek') then
  raise exception 'Projekt že ima osnutek ponudbe' using errcode='QFP09'; end if;
 select * into prev from quoteflow.ponudba q where q.projekt_id=p.id order by q.razlicica desc limit 1;
 if prev.razlicica>=50 then raise exception 'Projekt ima lahko največ 50 različic ponudbe' using errcode='QFP23'; end if;
 perform quoteflow_private.preveri_velja_do(ustvari_ponudbo.velja_do);
 if prev.id is null then
  -- The company row lock held by preveri_mojstra serialises numbering within a company.
  y:=extract(year from quoteflow_private.danes())::text;
  select coalesce(max(split_part(q.stevilka,'-',3)::integer),0)+1 into n from quoteflow.ponudba q join quoteflow.projekt x on x.id=q.projekt_id
  where x.podjetje_id=p.podjetje_id and q.stevilka ~ ('^P-'||y||'-[0-9]{1,9}$');
  insert into quoteflow.ponudba(projekt_id,stevilka,razlicica,velja_do) values(p.id,'P-'||y||'-'||lpad(n::text,greatest(3,length(n::text)),'0'),1,ustvari_ponudbo.velja_do) returning * into r;
 else
  -- A new version is a header only; sending snapshots the project's current items, never the previous version.
  insert into quoteflow.ponudba(projekt_id,stevilka,razlicica,velja_do) values(p.id,prev.stevilka,prev.razlicica+1,ustvari_ponudbo.velja_do) returning * into r;
 end if;
 return r;
end $$;

create function quoteflow_private.uredi_ponudbo(podjetje uuid,projekt uuid,ponudba uuid,velja_do date) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba;
begin
 perform quoteflow_private.preveri_mojstra(uredi_ponudbo.podjetje);
 r:=quoteflow_private.preveri_osnutek(uredi_ponudbo.podjetje,uredi_ponudbo.projekt,uredi_ponudbo.ponudba);
 perform quoteflow_private.preveri_velja_do(uredi_ponudbo.velja_do);
 update quoteflow.ponudba q set velja_do=uredi_ponudbo.velja_do where q.id=r.id returning * into r;
 return r;
end $$;

-- Internal helpers (not granted). The project is locked for update so item writes and sending serialise per project.
create function quoteflow_private.projekt_postavk(podjetje uuid,projekt uuid) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt;
begin
 select * into r from quoteflow.projekt p where p.id=projekt_postavk.projekt and p.podjetje_id=projekt_postavk.podjetje for update;
 if not found then raise no_data_found; end if;
 return r;
end $$;
create function quoteflow_private.preveri_fazo_postavk(p quoteflow.projekt) returns void language plpgsql security definer set search_path='' as $$
begin
 if p.faza not in ('pregled','ogled','ponudba') or exists(select 1 from quoteflow.ponudba q where q.projekt_id=p.id and q.stanje='sprejeta') then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
end $$;
-- Full recompute after every izmera write; a negative sum aborts the whole call, so nothing is written.
create function quoteflow_private.preracunaj_izmere(postavka uuid) returns void language plpgsql security definer set search_path='' as $$
declare s numeric;
begin
 select coalesce(sum(case when i.odstej then -i.vrednost else i.vrednost end),0) into s from quoteflow.izmera i where i.postavka_projekta_id=preracunaj_izmere.postavka;
 if s<0 then raise exception 'Izmere bi dale negativno količino' using errcode='QFP25'; end if;
 update quoteflow.postavka_projekta x set izmera_skupaj=s where x.id=preracunaj_izmere.postavka;
end $$;

create function quoteflow_private.shrani_postavko_projekta(podjetje uuid,projekt uuid,postavka uuid,vrsta_dela uuid,naziv text,opis text,enota text,cena numeric,kolicina numeric,
 popust numeric,stopnja_ddv numeric,urna_postavka numeric,stevilo_ur numeric,stevilo_delavcev integer) returns quoteflow.postavka_projekta
language plpgsql security definer set search_path='' as $$
declare p quoteflow.projekt; prev quoteflow.postavka_projekta; v quoteflow.vrsta_dela; r quoteflow.postavka_projekta; same boolean;
begin
 perform quoteflow_private.preveri_mojstra(shrani_postavko_projekta.podjetje);
 p:=quoteflow_private.projekt_postavk(shrani_postavko_projekta.podjetje,shrani_postavko_projekta.projekt);
 if shrani_postavko_projekta.postavka is not null then
  select * into prev from quoteflow.postavka_projekta x where x.id=shrani_postavko_projekta.postavka and x.projekt_id=p.id for update;
  if not found then raise no_data_found; end if;
 end if;
 select * into v from quoteflow.vrsta_dela x where x.id=shrani_postavko_projekta.vrsta_dela and x.podjetje_id=p.podjetje_id for share;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_fazo_postavk(p);
 same:=prev.id is not null and prev.vrsta_dela_id=v.id;
 -- An item keeps an inactive vrsta dela it already had, but cannot newly use one.
 if not v.aktivna and not same then raise exception 'Neaktivne vrste dela ni mogoče uporabiti' using errcode='QFP29'; end if;
 if prev.id is null then
  if (select count(*) from quoteflow.postavka_projekta x where x.projekt_id=p.id)>=200 then raise exception 'Projekt ima lahko največ 200 postavk' using errcode='QFP20'; end if;
  insert into quoteflow.postavka_projekta(projekt_id,vrsta_dela_id,zaporedje,naziv,opis,enota,cena_na_enoto,kolicina,popust,stopnja_ddv,urna_postavka,stevilo_ur,stevilo_delavcev)
  values(p.id,v.id,(select coalesce(max(x.zaporedje),0)+1 from quoteflow.postavka_projekta x where x.projekt_id=p.id),trim(shrani_postavko_projekta.naziv),
  coalesce(trim(shrani_postavko_projekta.opis),''),shrani_postavko_projekta.enota,shrani_postavko_projekta.cena,coalesce(shrani_postavko_projekta.kolicina,1),
  coalesce(shrani_postavko_projekta.popust,0),shrani_postavko_projekta.stopnja_ddv,coalesce(shrani_postavko_projekta.urna_postavka,v.urna_postavka),
  coalesce(shrani_postavko_projekta.stevilo_ur,v.stevilo_ur),coalesce(shrani_postavko_projekta.stevilo_delavcev,v.stevilo_delavcev)) returning * into r;
 else
  if shrani_postavko_projekta.enota is distinct from prev.enota and exists(select 1 from quoteflow.izmera i where i.postavka_projekta_id=prev.id) then
   raise exception 'Mersko enoto lahko spremenite le, ko postavka nima izmer' using errcode='QFP27'; end if;
  -- Omitted labour fields keep the item's values; a new vrsta dela supplies its defaults.
  update quoteflow.postavka_projekta x set vrsta_dela_id=v.id,naziv=trim(shrani_postavko_projekta.naziv),opis=coalesce(trim(shrani_postavko_projekta.opis),''),
  enota=shrani_postavko_projekta.enota,cena_na_enoto=shrani_postavko_projekta.cena,kolicina=coalesce(shrani_postavko_projekta.kolicina,1),
  popust=coalesce(shrani_postavko_projekta.popust,0),stopnja_ddv=shrani_postavko_projekta.stopnja_ddv,
  urna_postavka=coalesce(shrani_postavko_projekta.urna_postavka,case when same then prev.urna_postavka else v.urna_postavka end),
  stevilo_ur=coalesce(shrani_postavko_projekta.stevilo_ur,case when same then prev.stevilo_ur else v.stevilo_ur end),
  stevilo_delavcev=coalesce(shrani_postavko_projekta.stevilo_delavcev,case when same then prev.stevilo_delavcev else v.stevilo_delavcev end)
  where x.id=prev.id returning * into r;
 end if;
 return r;
end $$;

create function quoteflow_private.dodaj_postavko_iz_cenika(podjetje uuid,projekt uuid,postavka_cenika uuid,kolicina numeric,popust numeric) returns quoteflow.postavka_projekta
language plpgsql security definer set search_path='' as $$
declare p quoteflow.projekt; c quoteflow.postavka_cenika; v quoteflow.vrsta_dela; r quoteflow.postavka_projekta;
begin
 perform quoteflow_private.preveri_mojstra(dodaj_postavko_iz_cenika.podjetje);
 p:=quoteflow_private.projekt_postavk(dodaj_postavko_iz_cenika.podjetje,dodaj_postavko_iz_cenika.projekt);
 -- Held until commit so the item and its vrsta dela cannot change between these checks and the copy.
 select * into c from quoteflow.postavka_cenika x where x.id=dodaj_postavko_iz_cenika.postavka_cenika and x.podjetje_id=p.podjetje_id for share;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_fazo_postavk(p);
 if not c.aktivna then raise exception 'Neaktivne postavke cenika ni mogoče dodati' using errcode='QFP16'; end if;
 select * into v from quoteflow.vrsta_dela x where x.id=c.vrsta_dela_id for share;
 if not v.aktivna then raise exception 'Neaktivne vrste dela ni mogoče uporabiti' using errcode='QFP29'; end if;
 if (select count(*) from quoteflow.postavka_projekta x where x.projekt_id=p.id)>=200 then raise exception 'Projekt ima lahko največ 200 postavk' using errcode='QFP20'; end if;
 insert into quoteflow.postavka_projekta(projekt_id,postavka_cenika_id,vrsta_dela_id,zaporedje,naziv,opis,enota,cena_na_enoto,kolicina,popust,stopnja_ddv,urna_postavka,stevilo_ur,stevilo_delavcev)
 values(p.id,c.id,v.id,(select coalesce(max(x.zaporedje),0)+1 from quoteflow.postavka_projekta x where x.projekt_id=p.id),c.naziv,c.opis,c.enota,c.cena_na_enoto,
 coalesce(dodaj_postavko_iz_cenika.kolicina,1),coalesce(dodaj_postavko_iz_cenika.popust,0),c.stopnja_ddv,v.urna_postavka,v.stevilo_ur,v.stevilo_delavcev) returning * into r;
 return r;
end $$;

create function quoteflow_private.odstrani_postavko_projekta(podjetje uuid,projekt uuid,postavka uuid) returns void language plpgsql security definer set search_path='' as $$
declare p quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(odstrani_postavko_projekta.podjetje);
 p:=quoteflow_private.projekt_postavk(odstrani_postavko_projekta.podjetje,odstrani_postavko_projekta.projekt);
 perform 1 from quoteflow.postavka_projekta x where x.id=odstrani_postavko_projekta.postavka and x.projekt_id=p.id for update;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_fazo_postavk(p);
 delete from quoteflow.izmera i where i.postavka_projekta_id=odstrani_postavko_projekta.postavka;
 delete from quoteflow.postavka_projekta x where x.id=odstrani_postavko_projekta.postavka;
end $$;

create function quoteflow_private.shrani_izmero(podjetje uuid,projekt uuid,postavka uuid,izmera uuid,odstej boolean,kosi numeric,dolzina numeric,visina numeric,sirina numeric)
returns quoteflow.izmera language plpgsql security definer set search_path='' as $$
declare p quoteflow.projekt; it quoteflow.postavka_projekta; r quoteflow.izmera;
begin
 perform quoteflow_private.preveri_mojstra(shrani_izmero.podjetje);
 p:=quoteflow_private.projekt_postavk(shrani_izmero.podjetje,shrani_izmero.projekt);
 select * into it from quoteflow.postavka_projekta x where x.id=shrani_izmero.postavka and x.projekt_id=p.id for update;
 if not found then raise no_data_found; end if;
 if shrani_izmero.izmera is not null then
  perform 1 from quoteflow.izmera i where i.id=shrani_izmero.izmera and i.postavka_projekta_id=it.id for update;
  if not found then raise no_data_found; end if;
 end if;
 perform quoteflow_private.preveri_fazo_postavk(p);
 -- The unit always comes from the item; the table checks decide which fields that unit allows.
 if shrani_izmero.izmera is null then
  if (select count(*) from quoteflow.izmera i where i.postavka_projekta_id=it.id)>=100 then raise exception 'Postavka ima lahko največ 100 izmer' using errcode='QFP28'; end if;
  insert into quoteflow.izmera(postavka_projekta_id,enota,zaporedje,odstej,kosi,dolzina,visina,sirina)
  values(it.id,it.enota,(select coalesce(max(i.zaporedje),0)+1 from quoteflow.izmera i where i.postavka_projekta_id=it.id),coalesce(shrani_izmero.odstej,false),
  coalesce(shrani_izmero.kosi,1),shrani_izmero.dolzina,shrani_izmero.visina,shrani_izmero.sirina) returning * into r;
 else
  update quoteflow.izmera i set odstej=coalesce(shrani_izmero.odstej,false),kosi=coalesce(shrani_izmero.kosi,1),dolzina=shrani_izmero.dolzina,visina=shrani_izmero.visina,
  sirina=shrani_izmero.sirina where i.id=shrani_izmero.izmera returning * into r;
 end if;
 perform quoteflow_private.preracunaj_izmere(it.id);
 return r;
end $$;

create function quoteflow_private.odstrani_izmero(podjetje uuid,projekt uuid,postavka uuid,izmera uuid) returns void language plpgsql security definer set search_path='' as $$
declare p quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(odstrani_izmero.podjetje);
 p:=quoteflow_private.projekt_postavk(odstrani_izmero.podjetje,odstrani_izmero.projekt);
 perform 1 from quoteflow.postavka_projekta x where x.id=odstrani_izmero.postavka and x.projekt_id=p.id for update;
 if not found then raise no_data_found; end if;
 perform 1 from quoteflow.izmera i where i.id=odstrani_izmero.izmera and i.postavka_projekta_id=odstrani_izmero.postavka for update;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_fazo_postavk(p);
 delete from quoteflow.izmera i where i.id=odstrani_izmero.izmera;
 perform quoteflow_private.preracunaj_izmere(odstrani_izmero.postavka);
end $$;

revoke all on function quoteflow_private.preveri_osnutek(uuid,uuid,uuid),quoteflow_private.danes(),quoteflow_private.preveri_velja_do(date),
 quoteflow_private.projekt_postavk(uuid,uuid),quoteflow_private.preveri_fazo_postavk(quoteflow.projekt),quoteflow_private.preracunaj_izmere(uuid)
 from public,anon,authenticated,service_role,quoteflow_app;
revoke all on function quoteflow_private.ustvari_ponudbo(uuid,uuid,date),quoteflow_private.uredi_ponudbo(uuid,uuid,uuid,date),
 quoteflow_private.shrani_postavko_projekta(uuid,uuid,uuid,uuid,text,text,text,numeric,numeric,numeric,numeric,numeric,numeric,integer),
 quoteflow_private.dodaj_postavko_iz_cenika(uuid,uuid,uuid,numeric,numeric),quoteflow_private.odstrani_postavko_projekta(uuid,uuid,uuid),
 quoteflow_private.shrani_izmero(uuid,uuid,uuid,uuid,boolean,numeric,numeric,numeric,numeric),quoteflow_private.odstrani_izmero(uuid,uuid,uuid,uuid)
 from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.ustvari_ponudbo(uuid,uuid,date),quoteflow_private.uredi_ponudbo(uuid,uuid,uuid,date),
 quoteflow_private.shrani_postavko_projekta(uuid,uuid,uuid,uuid,text,text,text,numeric,numeric,numeric,numeric,numeric,numeric,integer),
 quoteflow_private.dodaj_postavko_iz_cenika(uuid,uuid,uuid,numeric,numeric),quoteflow_private.odstrani_postavko_projekta(uuid,uuid,uuid),
 quoteflow_private.shrani_izmero(uuid,uuid,uuid,uuid,boolean,numeric,numeric,numeric,numeric),quoteflow_private.odstrani_izmero(uuid,uuid,uuid,uuid) to authenticated;
