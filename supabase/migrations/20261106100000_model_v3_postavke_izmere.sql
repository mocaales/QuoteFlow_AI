-- Model v3 (G1 2026-11-07): vrste dela with optional materials replace sestava_cenika; the catalogue references a vrsta dela
-- and one of four units (m, m2, m3, kos); items with izmere live on the project (postavka_projekta, izmera); a sent quote is a
-- snapshot (postavka_ponudbe with plain totals written once, izmera_ponudbe, material_ponudbe and the mojster-only labour
-- snapshot delo_ponudbe). 17 -> 22 tables, all with forced RLS and SELECT-only grants to authenticated.
-- Lossless conversion of the deployed catalogue (X1): every catalogue item without composition gets the shared vrsta dela of
-- its (podjetje, trim(vrsta_dela)) with 0 EUR labour; every item with composition gets its own vrsta dela carrying that
-- composition. m²/m³ become m2/m3, any other unknown unit and any existing quote line stop the migration (nothing changes).
-- Formula A: neto = round((izmera_skupaj*kolicina*cena_na_enoto + urna_postavka*stevilo_ur*stevilo_delavcev)*(1-popust),2),
-- koncna_cena = neto + round(neto*stopnja_ddv,2). QFP05 inactive material · QFP29 inactive vrsta dela · QFP31 more than 500 vrst
-- dela per company · QFP32 more than 50 materials per vrsta dela. Bounds M7 are table checks (23514).
-- Deferred integrity events must fire per statement here: ALTER TABLE refuses tables with pending trigger events.
set constraints all immediate;

do $$ begin
 if exists(select 1 from quoteflow.postavka_ponudbe) or exists(select 1 from quoteflow.material_ponudbe) then
  raise exception 'Model v3 zahteva prazne postavke ponudb; obstoječe vrstice je treba obravnavati pred migracijo' using errcode='55000'; end if;
 if exists(select 1 from quoteflow.postavka_cenika where trim(enota) not in ('m','m2','m3','kos','m²','m³')) then
  raise exception 'Cenik vsebuje neznane merske enote: %', (select string_agg(distinct enota,', ') from quoteflow.postavka_cenika where trim(enota) not in ('m','m2','m3','kos','m²','m³'))
  using errcode='23514'; end if;
end $$;

-- Live catalogue of work types; materials are optional and internal to the company.
create table quoteflow.vrsta_dela (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 naziv text not null check(length(trim(naziv)) between 1 and 200), opis text not null default '',
 urna_postavka numeric(18,4) not null default 0 check(urna_postavka>=0 and urna_postavka<=10000),
 stevilo_ur numeric(18,4) not null default 0 check(stevilo_ur>=0 and stevilo_ur<=100000),
 stevilo_delavcev integer not null default 1 check(stevilo_delavcev between 1 and 1000), aktivna boolean not null default true,
 cena_dela numeric(18,2) generated always as (round(urna_postavka*stevilo_ur*stevilo_delavcev,2)) stored
);
create index vrsta_dela_podjetje_idx on quoteflow.vrsta_dela(podjetje_id);
create table quoteflow.material_vrste_dela (
 vrsta_dela_id uuid references quoteflow.vrsta_dela(id), material_id uuid references quoteflow.material(id),
 kolicina_na_enoto numeric(18,4) not null check(kolicina_na_enoto>0 and kolicina_na_enoto<=1000000), primary key(vrsta_dela_id,material_id)
);
create index material_vrste_dela_material_idx on quoteflow.material_vrste_dela(material_id);
alter table quoteflow.postavka_cenika add column vrsta_dela_id uuid references quoteflow.vrsta_dela(id);
create index cenik_vrsta_dela_idx on quoteflow.postavka_cenika(vrsta_dela_id);

-- Editable project items. izmera_skupaj is written only by the izmera functions (full recompute, never negative).
create table quoteflow.postavka_projekta (
 id uuid primary key default gen_random_uuid(), projekt_id uuid not null references quoteflow.projekt(id),
 postavka_cenika_id uuid references quoteflow.postavka_cenika(id), vrsta_dela_id uuid not null references quoteflow.vrsta_dela(id),
 zaporedje integer not null check(zaporedje>0), naziv text not null check(length(trim(naziv)) between 1 and 200), opis text not null default '',
 enota text not null check(enota in ('m','m2','m3','kos')),
 cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<=1000000),
 kolicina numeric(18,4) not null default 1 check(kolicina>0 and kolicina<=1000000),
 popust numeric(7,6) not null default 0 check(popust>=0 and popust<1), stopnja_ddv numeric(7,6) not null default 0.22 check(stopnja_ddv between 0 and 1),
 urna_postavka numeric(18,4) not null check(urna_postavka>=0 and urna_postavka<=10000),
 stevilo_ur numeric(18,4) not null check(stevilo_ur>=0 and stevilo_ur<=100000),
 stevilo_delavcev integer not null default 1 check(stevilo_delavcev between 1 and 1000),
 izmera_skupaj numeric(18,4) not null default 0 check(izmera_skupaj>=0 and izmera_skupaj<=100000000),
 cena_dela numeric(18,2) generated always as (round(urna_postavka*stevilo_ur*stevilo_delavcev,2)) stored,
 neto numeric(18,2) generated always as (round((izmera_skupaj*kolicina*cena_na_enoto+urna_postavka*stevilo_ur*stevilo_delavcev)*(1-popust),2)) stored check(neto<=1000000000),
 koncna_cena numeric(18,2) generated always as (round((izmera_skupaj*kolicina*cena_na_enoto+urna_postavka*stevilo_ur*stevilo_delavcev)*(1-popust),2)
  +round(round((izmera_skupaj*kolicina*cena_na_enoto+urna_postavka*stevilo_ur*stevilo_delavcev)*(1-popust),2)*stopnja_ddv,2)) stored,
 unique(projekt_id,zaporedje), unique(id,enota)
);
create index postavka_projekta_vrsta_idx on quoteflow.postavka_projekta(vrsta_dela_id);
create index postavka_projekta_cenik_idx on quoteflow.postavka_projekta(postavka_cenika_id);
-- The composite key keeps every izmera in its item's unit; the unit decides which fields exist (kosi multiplies every unit).
create table quoteflow.izmera (
 id uuid primary key default gen_random_uuid(), postavka_projekta_id uuid not null, enota text not null check(enota in ('m','m2','m3','kos')),
 zaporedje integer not null check(zaporedje>0), odstej boolean not null default false,
 kosi numeric(18,4) not null default 1 check(kosi>0 and kosi<=100000),
 dolzina numeric(18,4) check(dolzina>0 and dolzina<=100000), visina numeric(18,4) check(visina>0 and visina<=100000), sirina numeric(18,4) check(sirina>0 and sirina<=100000),
 vrednost numeric(18,4) generated always as (kosi*coalesce(dolzina,1)*coalesce(visina,1)*coalesce(sirina,1)) stored check(vrednost>0 and vrednost<=1000000),
 check(case enota when 'm' then dolzina is not null and visina is null and sirina is null when 'm2' then dolzina is not null and visina is not null and sirina is null
  when 'm3' then dolzina is not null and visina is not null and sirina is not null else dolzina is null and visina is null and sirina is null end),
 foreign key(postavka_projekta_id,enota) references quoteflow.postavka_projekta(id,enota), unique(postavka_projekta_id,zaporedje)
);

-- Sent snapshot: totals are plain columns written once at sending; labour inputs stay in the mojster-only delo_ponudbe.
alter table quoteflow.postavka_ponudbe drop column koncna_cena;
alter table quoteflow.postavka_ponudbe add column izmera_skupaj numeric(18,4) not null check(izmera_skupaj>0 and izmera_skupaj<=100000000),
 add column neto numeric(18,2) not null check(neto>=0 and neto<=1000000000),
 add column koncna_cena numeric(18,2) not null,
 add constraint postavka_ponudbe_koncna_check check(koncna_cena=neto+round(neto*stopnja_ddv,2)),
 add constraint postavka_ponudbe_enota_v3_check check(enota in ('m','m2','m3','kos')),
 add constraint postavka_ponudbe_meje_check check(cena_na_enoto<=1000000 and kolicina<=1000000),
 add constraint postavka_ponudbe_id_enota_key unique(id,enota);
create table quoteflow.izmera_ponudbe (
 postavka_ponudbe_id uuid not null, zaporedje integer not null check(zaporedje>0), enota text not null check(enota in ('m','m2','m3','kos')),
 odstej boolean not null default false, kosi numeric(18,4) not null check(kosi>0 and kosi<=100000),
 dolzina numeric(18,4) check(dolzina>0 and dolzina<=100000), visina numeric(18,4) check(visina>0 and visina<=100000), sirina numeric(18,4) check(sirina>0 and sirina<=100000),
 vrednost numeric(18,4) not null check(vrednost>0 and vrednost<=1000000),
 check(case enota when 'm' then dolzina is not null and visina is null and sirina is null when 'm2' then dolzina is not null and visina is not null and sirina is null
  when 'm3' then dolzina is not null and visina is not null and sirina is not null else dolzina is null and visina is null and sirina is null end),
 primary key(postavka_ponudbe_id,zaporedje), foreign key(postavka_ponudbe_id,enota) references quoteflow.postavka_ponudbe(id,enota)
);
create table quoteflow.delo_ponudbe (
 postavka_ponudbe_id uuid primary key references quoteflow.postavka_ponudbe(id),
 urna_postavka numeric(18,4) not null check(urna_postavka>=0 and urna_postavka<=10000), stevilo_ur numeric(18,4) not null check(stevilo_ur>=0 and stevilo_ur<=100000),
 stevilo_delavcev integer not null check(stevilo_delavcev between 1 and 1000), cena_dela numeric(18,2) not null,
 check(cena_dela=round(urna_postavka*stevilo_ur*stevilo_delavcev,2))
);

-- Cross-company links are checked under the company that owns the changed row; parent references are immutable.
create or replace function quoteflow_private.preveri_celovitost() returns trigger language plpgsql security definer set search_path='' as $$
declare d jsonb; company uuid;
begin
 d:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 case tg_table_name
 when 'podjetje' then company:=(d->>'id')::uuid;
 when 'vloga_uporabnika','ekipa','projekt','postavka_cenika','vrsta_materiala','vrsta_dela' then company:=(d->>'podjetje_id')::uuid;
 when 'clan_ekipe' then select e.podjetje_id into company from quoteflow.ekipa e where e.id=(d->>'ekipa_id')::uuid;
 when 'projekt_ekipa','postavka_projekta' then select p.podjetje_id into company from quoteflow.projekt p where p.id=(d->>'projekt_id')::uuid;
 when 'material_vrste_dela' then select v.podjetje_id into company from quoteflow.vrsta_dela v where v.id=(d->>'vrsta_dela_id')::uuid;
 when 'izmera' then select p.podjetje_id into company from quoteflow.postavka_projekta x join quoteflow.projekt p on p.id=x.projekt_id where x.id=(d->>'postavka_projekta_id')::uuid;
 when 'material' then select v.podjetje_id into company from quoteflow.vrsta_materiala v where v.id=(d->>'vrsta_materiala_id')::uuid;
 when 'postavka_ponudbe' then select p.podjetje_id into company from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.id=(d->>'ponudba_id')::uuid;
 when 'material_ponudbe','izmera_ponudbe','delo_ponudbe' then select p.podjetje_id into company from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id
  join quoteflow.projekt p on p.id=q.projekt_id where l.id=(d->>'postavka_ponudbe_id')::uuid;
 end case;
 if company is null then return null; end if;
 -- The checks below are company-wide, so one pass per company covers every queued row event of it; any later write to the company
 -- clears the mark in zakleni_podjetje (a BEFORE trigger on every table carrying this one). Without it 20k izmere meant 20k full passes.
 if coalesce(current_setting('quoteflow.cel_'||replace(company::text,'-',''),true),'')='1' then return null; end if;
 if exists(select 1 from quoteflow.podjetje p where p.id=company and not exists(select 1 from quoteflow.vloga_uporabnika v where v.uporabnik_id=p.lastnik_id and v.podjetje_id=p.id and v.vloga='mojster' and v.aktivna)) then
  raise exception 'Lastnik potrebuje aktivno vlogo mojster pri svojem podjetju' using errcode='23514'; end if;
 if exists(select 1 from quoteflow.clan_ekipe c join quoteflow.ekipa e on e.id=c.ekipa_id join quoteflow.vloga_uporabnika v on v.id=c.delavec_vloga_id
  where e.podjetje_id=company and (v.vloga<>'delavec' or v.podjetje_id<>e.podjetje_id)) then
  raise exception 'Clan ekipe mora biti aktivni delavec istega podjetja' using errcode='23514'; end if;
 if exists(select 1 from quoteflow.projekt_ekipa x join quoteflow.projekt p on p.id=x.projekt_id join quoteflow.ekipa e on e.id=x.ekipa_id where p.podjetje_id=company and e.podjetje_id<>company)
 or exists(select 1 from quoteflow.material_vrste_dela x join quoteflow.vrsta_dela w on w.id=x.vrsta_dela_id join quoteflow.material m on m.id=x.material_id
  join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where w.podjetje_id=company and v.podjetje_id<>company)
 or exists(select 1 from quoteflow.postavka_cenika c join quoteflow.vrsta_dela w on w.id=c.vrsta_dela_id where c.podjetje_id=company and w.podjetje_id<>company)
 or exists(select 1 from quoteflow.postavka_projekta x join quoteflow.projekt p on p.id=x.projekt_id join quoteflow.vrsta_dela w on w.id=x.vrsta_dela_id
  left join quoteflow.postavka_cenika c on c.id=x.postavka_cenika_id where p.podjetje_id=company and (w.podjetje_id<>company or c.podjetje_id<>company))
 or exists(select 1 from quoteflow.postavka_ponudbe x join quoteflow.ponudba q on q.id=x.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id
  join quoteflow.postavka_cenika c on c.id=x.postavka_cenika_id where p.podjetje_id=company and c.podjetje_id<>company)
 or exists(select 1 from quoteflow.material_ponudbe x join quoteflow.postavka_ponudbe l on l.id=x.postavka_ponudbe_id join quoteflow.ponudba q on q.id=l.ponudba_id
  join quoteflow.projekt p on p.id=q.projekt_id join quoteflow.material m on m.id=x.material_id join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id
  where p.podjetje_id=company and v.podjetje_id<>company) then
  raise exception 'Povezave med razlicnimi podjetji niso dovoljene' using errcode='23514'; end if;
 perform set_config('quoteflow.cel_'||replace(company::text,'-',''),'1',true);
 return null;
end $$;

-- Every write locks its company first, so cross-row invariants and numbering are serialised per company.
create or replace function quoteflow_private.zakleni_podjetje() returns trigger language plpgsql security definer set search_path='' as $$
declare d jsonb; company uuid; worker quoteflow.vloga_uporabnika;
begin
 d:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 case tg_table_name
 when 'podjetje' then company:=(d->>'id')::uuid;
 when 'vloga_uporabnika','projekt','ekipa','postavka_cenika','vrsta_materiala','vrsta_dela' then company:=(d->>'podjetje_id')::uuid;
 when 'clan_ekipe','projekt_ekipa' then select podjetje_id into company from quoteflow.ekipa where id=(d->>'ekipa_id')::uuid;
 when 'material' then select podjetje_id into company from quoteflow.vrsta_materiala where id=(d->>'vrsta_materiala_id')::uuid;
 when 'zaloga' then select v.podjetje_id into company from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where m.id=(d->>'material_id')::uuid;
 when 'material_vrste_dela' then select podjetje_id into company from quoteflow.vrsta_dela where id=(d->>'vrsta_dela_id')::uuid;
 when 'ponudba','postavka_projekta' then select podjetje_id into company from quoteflow.projekt where id=(d->>'projekt_id')::uuid;
 when 'izmera' then select p.podjetje_id into company from quoteflow.postavka_projekta x join quoteflow.projekt p on p.id=x.projekt_id where x.id=(d->>'postavka_projekta_id')::uuid;
 when 'postavka_ponudbe','racun' then select p.podjetje_id into company from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.id=(d->>'ponudba_id')::uuid;
 when 'material_ponudbe','izmera_ponudbe','delo_ponudbe' then select p.podjetje_id into company from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id
  join quoteflow.projekt p on p.id=q.projekt_id where l.id=(d->>'postavka_ponudbe_id')::uuid;
 end case;
 perform 1 from quoteflow.podjetje where id=company for update;
 if company is not null then perform set_config('quoteflow.cel_'||replace(company::text,'-',''),'0',true); end if;
 if tg_table_name='clan_ekipe' and tg_op<>'DELETE' then
  select * into worker from quoteflow.vloga_uporabnika where id=(d->>'delavec_vloga_id')::uuid for share;
  if not found or worker.vloga<>'delavec' or not worker.aktivna or worker.podjetje_id is distinct from company then
   raise check_violation using message='Nov clan ekipe mora biti aktivni delavec istega podjetja'; end if;
 end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;

-- Snapshot rows (lines, izmere, materials, labour) cannot change once their quote left the draft state.
create or replace function quoteflow_private.zakleni_postavko() returns trigger language plpgsql security definer set search_path='' as $$
declare d jsonb; parent uuid; state text;
begin
 d:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 if tg_table_name='postavka_ponudbe' then parent:=(d->>'ponudba_id')::uuid;
 else
  if tg_op='UPDATE' and ((to_jsonb(new)->'postavka_ponudbe_id') is distinct from (to_jsonb(old)->'postavka_ponudbe_id')
   or (to_jsonb(new)->'material_id') is distinct from (to_jsonb(old)->'material_id')) then raise check_violation; end if;
  select l.ponudba_id into parent from quoteflow.postavka_ponudbe l where l.id=(d->>'postavka_ponudbe_id')::uuid;
 end if;
 select q.stanje into state from quoteflow.ponudba q where q.id=parent for update;
 if state<>'osnutek' then raise exception 'Poslana ponudba je zaklenjena' using errcode='55000'; end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;

do $$ declare t text; x text[]; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('create constraint trigger celovitost after insert or update or delete on quoteflow.%I deferrable initially deferred for each row execute function quoteflow_private.preveri_celovitost()',t);
  execute format('create trigger a_zakleni_podjetje before insert or update or delete on quoteflow.%I for each row execute function quoteflow_private.zakleni_podjetje()',t);
 end loop;
 foreach x slice 1 in array array[['vrsta_dela','podjetje_id'],['material_vrste_dela','vrsta_dela_id,material_id'],['postavka_projekta','projekt_id'],['izmera','postavka_projekta_id,enota']] loop
  execute format('create trigger zakleni_reference before update on quoteflow.%I for each row execute function quoteflow_private.zakleni_reference(%L)',x[1],x[2]);
 end loop;
end $$;
create trigger zakleni_izmera_ponudbe before insert or update or delete on quoteflow.izmera_ponudbe for each row execute function quoteflow_private.zakleni_postavko();
create trigger zakleni_delo_ponudbe before insert or update or delete on quoteflow.delo_ponudbe for each row execute function quoteflow_private.zakleni_postavko();

-- X1 conversion. One mapping row per catalogue item; the grouping key always contains the company.
create temporary table v3_vrsta (postavka_id uuid primary key, vrsta_id uuid not null, podjetje_id uuid not null, naziv text not null);
insert into pg_temp.v3_vrsta(postavka_id,vrsta_id,podjetje_id,naziv)
 with g as (select c.podjetje_id,trim(c.vrsta_dela) as kljuc,gen_random_uuid() as vrsta_id from quoteflow.postavka_cenika c
  where not exists(select 1 from quoteflow.sestava_cenika s where s.postavka_cenika_id=c.id) group by c.podjetje_id,trim(c.vrsta_dela))
 select c.id,g.vrsta_id,c.podjetje_id,left(g.kljuc,200) from quoteflow.postavka_cenika c join g on g.podjetje_id=c.podjetje_id and g.kljuc=trim(c.vrsta_dela)
 where not exists(select 1 from quoteflow.sestava_cenika s where s.postavka_cenika_id=c.id)
 union all
 select c.id,gen_random_uuid(),c.podjetje_id,left(trim(c.vrsta_dela)||' – '||trim(c.naziv),200) from quoteflow.postavka_cenika c
 where exists(select 1 from quoteflow.sestava_cenika s where s.postavka_cenika_id=c.id);
insert into quoteflow.vrsta_dela(id,podjetje_id,naziv) select distinct m.vrsta_id,m.podjetje_id,m.naziv from pg_temp.v3_vrsta m;
insert into quoteflow.material_vrste_dela(vrsta_dela_id,material_id,kolicina_na_enoto)
 select m.vrsta_id,s.material_id,s.kolicina_na_enoto from quoteflow.sestava_cenika s join pg_temp.v3_vrsta m on m.postavka_id=s.postavka_cenika_id;
update quoteflow.postavka_cenika c set vrsta_dela_id=m.vrsta_id,enota=case trim(c.enota) when 'm²' then 'm2' when 'm³' then 'm3' else trim(c.enota) end
 from pg_temp.v3_vrsta m where m.postavka_id=c.id;
do $$ begin
 if (select count(*) from pg_temp.v3_vrsta)<>(select count(*) from quoteflow.postavka_cenika)
 or exists(select 1 from quoteflow.postavka_cenika where vrsta_dela_id is null or enota not in ('m','m2','m3','kos')) then
  raise exception 'Pretvorba cenika ni preslikala vseh postavk' using errcode='55000'; end if;
 if (select count(*) from quoteflow.material_vrste_dela)<>(select count(*) from quoteflow.sestava_cenika)
 or exists(select 1 from quoteflow.sestava_cenika s join quoteflow.postavka_cenika c on c.id=s.postavka_cenika_id
  where not exists(select 1 from quoteflow.material_vrste_dela x where x.vrsta_dela_id=c.vrsta_dela_id and x.material_id=s.material_id and x.kolicina_na_enoto=s.kolicina_na_enoto)) then
  raise exception 'Pretvorba cenika ni preslikala vseh sestav' using errcode='55000'; end if;
 if exists(select 1 from quoteflow.postavka_cenika c join quoteflow.vrsta_dela v on v.id=c.vrsta_dela_id where v.podjetje_id<>c.podjetje_id) then
  raise exception 'Pretvorba cenika je povezala različna podjetja' using errcode='55000'; end if;
end $$;
drop table pg_temp.v3_vrsta;

drop function quoteflow_private.shrani_sestavo(uuid,uuid,uuid,numeric);
drop function quoteflow_private.odstrani_sestavo(uuid,uuid,uuid);
drop function quoteflow_private.shrani_cenik(uuid,uuid,text,text,text,text,numeric,numeric,boolean);
drop policy read_own on quoteflow.sestava_cenika;
drop table quoteflow.sestava_cenika;
alter table quoteflow.postavka_cenika drop column vrsta_dela, alter column vrsta_dela_id set not null,
 add constraint postavka_cenika_enota_v3_check check(enota in ('m','m2','m3','kos'));

do $$ declare t text; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('alter table quoteflow.%I enable row level security',t);
  execute format('alter table quoteflow.%I force row level security',t);
  execute format('revoke all on quoteflow.%I from public,anon,authenticated,service_role,quoteflow_app',t);
  execute format('grant select on quoteflow.%I to authenticated',t);
 end loop;
end $$;

-- Read helpers for policies. A per-row definer call inside a hashed policy subquery runs once for EVERY row of the scanned table, tenants
-- included (measured: 800 foreign items made a 200x100 read take 4.5 s and a customer's 20k izmere 28 s). So the policies below compare
-- against sets that are built once per statement from the caller's own companies/projects; the guard is aktivna_seja + the live role rows.
create function quoteflow_private.mojstrova_podjetja() returns setof uuid language sql stable security definer set search_path='' as $$
 select v.podjetje_id from quoteflow.vloga_uporabnika v join quoteflow.podjetje p on p.id=v.podjetje_id
 where quoteflow_private.aktivna_seja() and v.uporabnik_id=auth.uid() and v.vloga='mojster' and v.aktivna and p.aktivno
$$;
create function quoteflow_private.mojstrovi_projekti() returns setof uuid language sql stable security definer set search_path='' as $$
 select p.id from quoteflow.projekt p where p.podjetje_id in (select quoteflow_private.mojstrova_podjetja())
$$;
-- Lines of quotes visible as by vidi_ponudbo: any quote of an own company (master) or a non-draft quote of an own project (active stranka).
create function quoteflow_private.vidne_postavke_ponudbe(samo_mojster boolean default false) returns setof uuid language sql stable security definer set search_path='' as $$
 select l.id from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id
 where p.podjetje_id in (select quoteflow_private.mojstrova_podjetja())
 union
 select l.id from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id
 where not $1 and quoteflow_private.aktivna_seja() and p.stranka_id=auth.uid() and q.stanje<>'osnutek' and quoteflow_private.stranka()
$$;
create policy read_own on quoteflow.vrsta_dela for select to authenticated using (quoteflow_private.clan(podjetje_id,'mojster'));
create policy read_own on quoteflow.material_vrste_dela for select to authenticated using (exists(select 1 from quoteflow.vrsta_dela v where v.id=vrsta_dela_id and quoteflow_private.clan(v.podjetje_id,'mojster')));
create policy read_own on quoteflow.postavka_projekta for select to authenticated using (projekt_id in (select quoteflow_private.mojstrovi_projekti()));
create policy read_own on quoteflow.izmera for select to authenticated using (postavka_projekta_id in (select x.id from quoteflow.postavka_projekta x where x.projekt_id in (select quoteflow_private.mojstrovi_projekti())));
-- The customer sees the izmere of a sent quote; labour inputs (delo_ponudbe) stay with the company's masters only.
create policy read_own on quoteflow.izmera_ponudbe for select to authenticated using (postavka_ponudbe_id in (select quoteflow_private.vidne_postavke_ponudbe()));
create policy read_own on quoteflow.delo_ponudbe for select to authenticated using (postavka_ponudbe_id in (select quoteflow_private.vidne_postavke_ponudbe(true)));

create function quoteflow_private.shrani_vrsto_dela(podjetje uuid,vrsta uuid,naziv text,opis text,urna_postavka numeric,stevilo_ur numeric,stevilo_delavcev integer,aktivna boolean)
returns quoteflow.vrsta_dela language plpgsql security definer set search_path='' as $$
declare r quoteflow.vrsta_dela;
begin
 perform quoteflow_private.preveri_mojstra(shrani_vrsto_dela.podjetje);
 if shrani_vrsto_dela.vrsta is null then
  -- The company row lock held by preveri_mojstra serialises this count.
  if (select count(*) from quoteflow.vrsta_dela v where v.podjetje_id=shrani_vrsto_dela.podjetje)>=500 then
   raise exception 'Podjetje ima lahko največ 500 vrst dela' using errcode='QFP31'; end if;
  insert into quoteflow.vrsta_dela(podjetje_id,naziv,opis,urna_postavka,stevilo_ur,stevilo_delavcev,aktivna)
  values(shrani_vrsto_dela.podjetje,trim(shrani_vrsto_dela.naziv),coalesce(trim(shrani_vrsto_dela.opis),''),shrani_vrsto_dela.urna_postavka,shrani_vrsto_dela.stevilo_ur,
  shrani_vrsto_dela.stevilo_delavcev,coalesce(shrani_vrsto_dela.aktivna,true)) returning * into r;
 else
  update quoteflow.vrsta_dela v set naziv=trim(shrani_vrsto_dela.naziv),opis=coalesce(trim(shrani_vrsto_dela.opis),''),urna_postavka=shrani_vrsto_dela.urna_postavka,
  stevilo_ur=shrani_vrsto_dela.stevilo_ur,stevilo_delavcev=shrani_vrsto_dela.stevilo_delavcev,aktivna=coalesce(shrani_vrsto_dela.aktivna,true)
  where v.id=shrani_vrsto_dela.vrsta and v.podjetje_id=shrani_vrsto_dela.podjetje returning * into r;
  if not found then raise no_data_found; end if;
 end if;
 return r;
end $$;

create function quoteflow_private.shrani_material_vrste(podjetje uuid,vrsta uuid,material uuid,kolicina numeric) returns quoteflow.material_vrste_dela
language plpgsql security definer set search_path='' as $$
declare r quoteflow.material_vrste_dela; active boolean;
begin
 perform quoteflow_private.preveri_mojstra(shrani_material_vrste.podjetje);
 perform 1 from quoteflow.vrsta_dela v where v.id=shrani_material_vrste.vrsta and v.podjetje_id=shrani_material_vrste.podjetje for update;
 if not found then raise no_data_found; end if;
 if quoteflow_private.material_podjetje(shrani_material_vrste.material) is distinct from shrani_material_vrste.podjetje then raise no_data_found; end if;
 -- Held until commit so the material cannot be deactivated between this check and the upsert.
 select m.aktiven into active from quoteflow.material m where m.id=shrani_material_vrste.material for share;
 if not active then raise exception 'Neaktivnega materiala ni mogoče dodati' using errcode='QFP05'; end if;
 if not exists(select 1 from quoteflow.material_vrste_dela x where x.vrsta_dela_id=shrani_material_vrste.vrsta and x.material_id=shrani_material_vrste.material)
 and (select count(*) from quoteflow.material_vrste_dela x where x.vrsta_dela_id=shrani_material_vrste.vrsta)>=50 then
  raise exception 'Vrsta dela ima lahko največ 50 materialov' using errcode='QFP32'; end if;
 insert into quoteflow.material_vrste_dela as x(vrsta_dela_id,material_id,kolicina_na_enoto) values(shrani_material_vrste.vrsta,shrani_material_vrste.material,shrani_material_vrste.kolicina)
 on conflict on constraint material_vrste_dela_pkey do update set kolicina_na_enoto=excluded.kolicina_na_enoto returning * into r;
 return r;
end $$;

create function quoteflow_private.odstrani_material_vrste(podjetje uuid,vrsta uuid,material uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 perform quoteflow_private.preveri_mojstra(odstrani_material_vrste.podjetje);
 perform 1 from quoteflow.vrsta_dela v where v.id=odstrani_material_vrste.vrsta and v.podjetje_id=odstrani_material_vrste.podjetje for update;
 if not found then raise no_data_found; end if;
 if quoteflow_private.material_podjetje(odstrani_material_vrste.material) is distinct from odstrani_material_vrste.podjetje then raise no_data_found; end if;
 delete from quoteflow.material_vrste_dela x where x.vrsta_dela_id=odstrani_material_vrste.vrsta and x.material_id=odstrani_material_vrste.material;
 if not found then raise no_data_found; end if;
end $$;

-- Catalogue item ("že ustvarjena postavka"): references an active vrsta dela of the same company and one of the four units.
create function quoteflow_private.shrani_cenik(podjetje uuid,target uuid,ime text,opis_v text,vrsta_dela_v uuid,enota_v text,cena numeric,ddv numeric,aktivna_v boolean)
returns quoteflow.postavka_cenika language plpgsql security definer set search_path='' as $$
declare r quoteflow.postavka_cenika; v quoteflow.vrsta_dela;
begin
 perform quoteflow_private.preveri_mojstra(shrani_cenik.podjetje);
 select * into v from quoteflow.vrsta_dela x where x.id=shrani_cenik.vrsta_dela_v and x.podjetje_id=shrani_cenik.podjetje for share;
 if not found then raise no_data_found; end if;
 if shrani_cenik.cena>1000000 then raise numeric_value_out_of_range using message='Vrednost presega dovoljeno mejo'; end if;
 if shrani_cenik.target is null then
  if not v.aktivna then raise exception 'Neaktivne vrste dela ni mogoče uporabiti' using errcode='QFP29'; end if;
  insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela_id,enota,cena_na_enoto,stopnja_ddv,aktivna)
  values(shrani_cenik.podjetje,trim(shrani_cenik.ime),coalesce(trim(shrani_cenik.opis_v),''),v.id,trim(shrani_cenik.enota_v),shrani_cenik.cena,shrani_cenik.ddv,shrani_cenik.aktivna_v) returning * into r;
 else
  perform 1 from quoteflow.postavka_cenika c where c.id=shrani_cenik.target and c.podjetje_id=shrani_cenik.podjetje for update;
  if not found then raise no_data_found; end if;
  -- An inactive work type may stay on a deactivated item, but cannot back an active one.
  if not v.aktivna and shrani_cenik.aktivna_v then raise exception 'Neaktivne vrste dela ni mogoče uporabiti' using errcode='QFP29'; end if;
  update quoteflow.postavka_cenika c set naziv=trim(shrani_cenik.ime),opis=coalesce(trim(shrani_cenik.opis_v),''),vrsta_dela_id=v.id,enota=trim(shrani_cenik.enota_v),
  cena_na_enoto=shrani_cenik.cena,stopnja_ddv=shrani_cenik.ddv,aktivna=shrani_cenik.aktivna_v where c.id=shrani_cenik.target returning * into r;
 end if;
 return r;
end $$;

revoke all on function quoteflow_private.preveri_celovitost(),quoteflow_private.zakleni_podjetje(),quoteflow_private.zakleni_postavko() from public,anon,authenticated,service_role,quoteflow_app;
revoke all on function quoteflow_private.mojstrova_podjetja(),quoteflow_private.mojstrovi_projekti(),quoteflow_private.vidne_postavke_ponudbe(boolean),quoteflow_private.shrani_vrsto_dela(uuid,uuid,text,text,numeric,numeric,integer,boolean),
 quoteflow_private.shrani_material_vrste(uuid,uuid,uuid,numeric),quoteflow_private.odstrani_material_vrste(uuid,uuid,uuid),
 quoteflow_private.shrani_cenik(uuid,uuid,text,text,uuid,text,numeric,numeric,boolean) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.mojstrova_podjetja(),quoteflow_private.mojstrovi_projekti(),quoteflow_private.vidne_postavke_ponudbe(boolean),quoteflow_private.shrani_vrsto_dela(uuid,uuid,text,text,numeric,numeric,integer,boolean),
 quoteflow_private.shrani_material_vrste(uuid,uuid,uuid,numeric),quoteflow_private.odstrani_material_vrste(uuid,uuid,uuid),
 quoteflow_private.shrani_cenik(uuid,uuid,text,text,uuid,text,numeric,numeric,boolean) to authenticated;
comment on schema quoteflow is 'Primarni relacijski model docs/03 (model v3): 22 tabel, admin/mojster/delavec/stranka, projekti s postavkami in izmerami, vrste dela ter poslovni dokumenti.';
