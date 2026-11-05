-- Approved V2: company-scoped roles, projects, teams, service catalogue, material stock and documents.
-- Preserve Auth and archive V1 without granting application access or guessing legal ownership.
drop trigger if exists quoteflow_sync_uporabnik on auth.users;
alter schema quoteflow rename to quoteflow_legacy_20261103;
alter schema quoteflow_private rename to quoteflow_private_legacy_20261103;
revoke all on schema quoteflow_legacy_20261103,quoteflow_private_legacy_20261103 from public,anon,authenticated,service_role,quoteflow_app;
revoke all on all tables in schema quoteflow_legacy_20261103 from public,anon,authenticated,service_role,quoteflow_app;
revoke all on all functions in schema quoteflow_legacy_20261103 from public,anon,authenticated,service_role,quoteflow_app;
revoke all on all functions in schema quoteflow_private_legacy_20261103 from public,anon,authenticated,service_role,quoteflow_app;
create schema quoteflow;
create schema quoteflow_private;
revoke all on schema quoteflow,quoteflow_private from public,anon,authenticated,service_role,quoteflow_app;
grant usage on schema quoteflow,quoteflow_private to authenticated;
alter default privileges in schema quoteflow_private revoke execute on functions from public;
create table quoteflow.uporabnik (
 id uuid primary key references auth.users(id) on delete restrict,
 e_posta text not null unique check(e_posta=lower(trim(e_posta)) and length(e_posta)>3),
 ime text not null default '', priimek text not null default ''
);
create table quoteflow.podjetje (
 id uuid primary key default gen_random_uuid(), lastnik_id uuid not null references quoteflow.uporabnik(id),
 naziv text not null check(length(trim(naziv)) between 1 and 200),
 maticna_stevilka text not null unique check(length(trim(maticna_stevilka))>0),
 davcna_stevilka text, naslov text not null check(length(trim(naslov))>0), aktivno boolean not null default true
);
create index podjetje_lastnik_idx on quoteflow.podjetje(lastnik_id);
create table quoteflow.vloga_uporabnika (
 id uuid primary key default gen_random_uuid(), uporabnik_id uuid not null references quoteflow.uporabnik(id),
 podjetje_id uuid references quoteflow.podjetje(id),
 vloga text not null check(vloga in ('admin','mojster','delavec','stranka')), aktivna boolean not null default true,
 check((vloga in ('admin','stranka'))=(podjetje_id is null))
);
create unique index vloga_globalna_uq on quoteflow.vloga_uporabnika(uporabnik_id,vloga) where podjetje_id is null;
create unique index vloga_podjetniska_uq on quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null;
create index vloga_podjetje_idx on quoteflow.vloga_uporabnika(podjetje_id);
create table quoteflow.prosnja_mojstra (
 id uuid primary key default gen_random_uuid(), uporabnik_id uuid not null references quoteflow.uporabnik(id),
 naziv_podjetja text not null check(length(trim(naziv_podjetja))>0), maticna_stevilka text not null check(length(trim(maticna_stevilka))>0),
 davcna_stevilka text, naslov_podjetja text not null check(length(trim(naslov_podjetja))>0),
 stanje text not null default 'oddana' check(stanje in ('oddana','odobrena','zavrnjena')),
 podjetje_id uuid unique references quoteflow.podjetje(id), odlocil_id uuid references quoteflow.uporabnik(id),
 oddano_ob timestamptz not null default now(), odloceno_ob timestamptz,
 check((stanje='oddana' and odloceno_ob is null and odlocil_id is null and podjetje_id is null)
 or (stanje<>'oddana' and odloceno_ob is not null and odlocil_id is not null and (stanje='odobrena')=(podjetje_id is not null)))
);
create unique index prosnja_maticna_uq on quoteflow.prosnja_mojstra(maticna_stevilka) where stanje='oddana';
create index prosnja_uporabnik_idx on quoteflow.prosnja_mojstra(uporabnik_id);
create index prosnja_odlocil_idx on quoteflow.prosnja_mojstra(odlocil_id);
create table quoteflow.projekt (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 stranka_id uuid not null references quoteflow.uporabnik(id), naziv text not null check(length(trim(naziv))>0),
 opis text not null default '', lokacija_izvedbe text not null default '',
 faza text not null default 'pregled' check(faza in ('pregled','ogled','ponudba','termin','izvedba','obracun','zakljucen')),
 termin_od timestamptz, termin_do timestamptz, izvedba_koncana_ob timestamptz, zakljuceno_ob timestamptz,
 check((termin_od is null and termin_do is null) or (termin_od is not null and termin_do>termin_od)),
 check((faza='zakljucen')=(zakljuceno_ob is not null))
);
create index projekt_podjetje_idx on quoteflow.projekt(podjetje_id);
create index projekt_stranka_idx on quoteflow.projekt(stranka_id);
create table quoteflow.ekipa (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 naziv text not null check(length(trim(naziv))>0), aktivna boolean not null default true, unique(podjetje_id,naziv)
);
create table quoteflow.clan_ekipe (
 ekipa_id uuid references quoteflow.ekipa(id), delavec_vloga_id uuid references quoteflow.vloga_uporabnika(id), primary key(ekipa_id,delavec_vloga_id)
);
create index clan_delavec_idx on quoteflow.clan_ekipe(delavec_vloga_id);
create table quoteflow.projekt_ekipa (
 projekt_id uuid references quoteflow.projekt(id), ekipa_id uuid references quoteflow.ekipa(id), primary key(projekt_id,ekipa_id)
);
create index projekt_ekipa_ekipa_idx on quoteflow.projekt_ekipa(ekipa_id);
create table quoteflow.postavka_cenika (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 naziv text not null check(length(trim(naziv))>0), opis text not null default '', vrsta_dela text not null check(length(trim(vrsta_dela))>0),
 enota text not null check(length(trim(enota))>0), cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric),
 stopnja_ddv numeric(7,6) not null default 0.22 check(stopnja_ddv between 0 and 1), aktivna boolean not null default true
);
create index cenik_podjetje_idx on quoteflow.postavka_cenika(podjetje_id);
create table quoteflow.vrsta_materiala (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 naziv text not null check(length(trim(naziv))>0), unique(podjetje_id,naziv)
);
create table quoteflow.material (
 id uuid primary key default gen_random_uuid(), vrsta_materiala_id uuid not null references quoteflow.vrsta_materiala(id),
 sifra text not null check(length(trim(sifra))>0), naziv text not null check(length(trim(naziv))>0),
 enota text not null check(length(trim(enota))>0), cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric), aktiven boolean not null default true
);
create index material_vrsta_idx on quoteflow.material(vrsta_materiala_id);
create table quoteflow.zaloga (
 material_id uuid references quoteflow.material(id), lokacija text check(length(trim(lokacija))>0),
 kolicina numeric(18,4) not null check(kolicina>=0 and kolicina<'Infinity'::numeric), primary key(material_id,lokacija)
);
create table quoteflow.sestava_cenika (
 postavka_cenika_id uuid references quoteflow.postavka_cenika(id), material_id uuid references quoteflow.material(id),
 kolicina_na_enoto numeric(18,4) not null check(kolicina_na_enoto>0 and kolicina_na_enoto<'Infinity'::numeric), primary key(postavka_cenika_id,material_id)
);
create index sestava_material_idx on quoteflow.sestava_cenika(material_id);
create table quoteflow.ponudba (
 id uuid primary key default gen_random_uuid(), projekt_id uuid not null references quoteflow.projekt(id), stevilka text not null check(length(trim(stevilka))>0),
 razlicica integer not null default 1 check(razlicica>0), stanje text not null default 'osnutek' check(stanje in ('osnutek','poslana','sprejeta','zavrnjena')),
 poslano_ob timestamptz, odgovorjeno_ob timestamptz, velja_do date, valuta char(3) not null default 'EUR' check(valuta='EUR'),
 unique(projekt_id,razlicica), check((stanje='osnutek')=(poslano_ob is null)), check((stanje in ('sprejeta','zavrnjena'))=(odgovorjeno_ob is not null))
);
create unique index ponudba_sprejeta_uq on quoteflow.ponudba(projekt_id) where stanje='sprejeta';
create table quoteflow.postavka_ponudbe (
 id uuid primary key default gen_random_uuid(), ponudba_id uuid not null references quoteflow.ponudba(id), postavka_cenika_id uuid references quoteflow.postavka_cenika(id),
 zaporedje integer not null check(zaporedje>0), naziv text not null check(length(trim(naziv))>0), opis text not null default '',
 vrsta_dela text not null check(length(trim(vrsta_dela))>0), enota text not null check(length(trim(enota))>0),
 cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric),
 kolicina numeric(18,4) not null check(kolicina>0 and kolicina<'Infinity'::numeric),
 popust numeric(7,6) not null default 0 check(popust>=0 and popust<1), stopnja_ddv numeric(7,6) not null default 0.22 check(stopnja_ddv between 0 and 1),
 koncna_cena numeric(18,2) generated always as (round(kolicina*cena_na_enoto*(1-popust),2)+round(round(kolicina*cena_na_enoto*(1-popust),2)*stopnja_ddv,2)) stored,
 unique(ponudba_id,zaporedje)
);
create index postavka_cenik_idx on quoteflow.postavka_ponudbe(postavka_cenika_id);
create table quoteflow.material_ponudbe (
 postavka_ponudbe_id uuid references quoteflow.postavka_ponudbe(id), material_id uuid references quoteflow.material(id),
 naziv text not null check(length(trim(naziv))>0), enota text not null check(length(trim(enota))>0),
 kolicina_na_enoto numeric(18,4) not null check(kolicina_na_enoto>0 and kolicina_na_enoto<'Infinity'::numeric),
 cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric), primary key(postavka_ponudbe_id,material_id)
);
create index ponudba_material_idx on quoteflow.material_ponudbe(material_id);
create table quoteflow.racun (
 id uuid primary key default gen_random_uuid(), ponudba_id uuid not null unique references quoteflow.ponudba(id), stevilka text,
 stanje_dokumenta text not null default 'osnutek' check(stanje_dokumenta in ('osnutek','izdan')),
 izdajatelj_naziv text, izdajatelj_naslov text, izdajatelj_davcna text, prejemnik_naziv text, prejemnik_naslov text,
 izdan_ob timestamptz, poslan_ob timestamptz, zapade_dne date, placano_ob timestamptz,
 stanje_placila text generated always as (case when placano_ob is null then 'neplacan' else 'placan' end) stored,
 check((stanje_dokumenta='osnutek' and izdan_ob is null and poslan_ob is null and placano_ob is null)
 or (stanje_dokumenta='izdan' and izdan_ob is not null and stevilka is not null and length(trim(stevilka))>0 and zapade_dne is not null
 and izdajatelj_naziv is not null and izdajatelj_naslov is not null and izdajatelj_davcna is not null and prejemnik_naziv is not null and prejemnik_naslov is not null)),
 check(poslan_ob is null or poslan_ob>=izdan_ob), check(placano_ob is null or placano_ob>=izdan_ob)
);

-- The authorization source is the live database, never editable metadata or stale role claims.
create function quoteflow_private.aktivna_seja() returns boolean language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and exists(select 1 from auth.sessions s where s.user_id=auth.uid()
 and s.id::text=coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb->>'session_id'
 and (s.not_after is null or s.not_after>now()))
$$;
create function quoteflow_private.administrator() returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.vloga_uporabnika where uporabnik_id=auth.uid() and vloga='admin' and aktivna)
$$;
create function quoteflow_private.stranka() returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.vloga_uporabnika where uporabnik_id=auth.uid() and vloga='stranka' and aktivna)
$$;
create function quoteflow_private.clan(podjetje uuid,zahtevana_vloga text default null) returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.vloga_uporabnika v join quoteflow.podjetje p on p.id=v.podjetje_id
 where p.id=$1 and p.aktivno and v.uporabnik_id=auth.uid() and v.aktivna and ($2 is null or v.vloga=$2))
$$;
create function quoteflow_private.preveri_mojstra(podjetje uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 perform 1 from quoteflow.podjetje p join quoteflow.vloga_uporabnika v on v.podjetje_id=p.id
 where p.id=$1 and p.aktivno and v.uporabnik_id=auth.uid() and v.vloga='mojster' and v.aktivna for update of p for share of v;
 if not found then raise insufficient_privilege; end if;
end $$;
create function quoteflow_private.vidi_projekt(target uuid) returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.projekt p where p.id=$1 and
 ((p.stranka_id=auth.uid() and quoteflow_private.stranka()) or quoteflow_private.clan(p.podjetje_id,'mojster') or exists(
 select 1 from quoteflow.projekt_ekipa pe join quoteflow.ekipa e on e.id=pe.ekipa_id join quoteflow.clan_ekipe ce on ce.ekipa_id=e.id
 join quoteflow.vloga_uporabnika v on v.id=ce.delavec_vloga_id join quoteflow.podjetje c on c.id=p.podjetje_id
 where pe.projekt_id=p.id and e.podjetje_id=p.podjetje_id and e.aktivna and c.aktivno and v.podjetje_id=p.podjetje_id and v.vloga='delavec' and v.aktivna and v.uporabnik_id=auth.uid())))
$$;
create function quoteflow_private.vidi_ponudbo(target uuid) returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id
 where q.id=$1 and (quoteflow_private.clan(p.podjetje_id,'mojster') or (p.stranka_id=auth.uid() and quoteflow_private.stranka() and q.stanje<>'osnutek')))
$$;
create function quoteflow_private.material_podjetje(target uuid) returns uuid language sql stable security definer set search_path='' as $$
 select v.podjetje_id from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id
 where m.id=$1 and quoteflow_private.clan(v.podjetje_id,'mojster')
$$;

-- Owner/member and cross-company constraints also protect privileged data imports.
create function quoteflow_private.preveri_celovitost() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from quoteflow.podjetje p where not exists(select 1 from quoteflow.vloga_uporabnika v where v.uporabnik_id=p.lastnik_id and v.podjetje_id=p.id and v.vloga='mojster' and v.aktivna)) then
  raise exception 'Lastnik potrebuje aktivno vlogo mojster pri svojem podjetju' using errcode='23514'; end if;
 if exists(select 1 from quoteflow.clan_ekipe c join quoteflow.ekipa e on e.id=c.ekipa_id join quoteflow.vloga_uporabnika v on v.id=c.delavec_vloga_id where v.vloga<>'delavec' or v.podjetje_id<>e.podjetje_id) then
  raise exception 'Clan ekipe mora biti aktivni delavec istega podjetja' using errcode='23514'; end if;
 if exists(select 1 from quoteflow.projekt_ekipa x join quoteflow.projekt p on p.id=x.projekt_id join quoteflow.ekipa e on e.id=x.ekipa_id where p.podjetje_id<>e.podjetje_id)
 or exists(select 1 from quoteflow.sestava_cenika x join quoteflow.postavka_cenika c on c.id=x.postavka_cenika_id where c.podjetje_id<>(select v.podjetje_id from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where m.id=x.material_id))
 or exists(select 1 from quoteflow.postavka_ponudbe x join quoteflow.ponudba q on q.id=x.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id join quoteflow.postavka_cenika c on c.id=x.postavka_cenika_id where c.podjetje_id<>p.podjetje_id)
 or exists(select 1 from quoteflow.material_ponudbe x join quoteflow.postavka_ponudbe l on l.id=x.postavka_ponudbe_id join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id<>(select v.podjetje_id from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where m.id=x.material_id)) then
  raise exception 'Povezave med razlicnimi podjetji niso dovoljene' using errcode='23514'; end if;
 return null;
end $$;
do $$ declare t text; begin
 foreach t in array array['podjetje','vloga_uporabnika','clan_ekipe','ekipa','projekt_ekipa','projekt','sestava_cenika','postavka_cenika','material','vrsta_materiala','postavka_ponudbe','material_ponudbe'] loop
  execute format('create constraint trigger celovitost after insert or update or delete on quoteflow.%I deferrable initially deferred for each row execute function quoteflow_private.preveri_celovitost()',t);
 end loop;
end $$;
create function quoteflow_private.zakleni_reference() returns trigger language plpgsql set search_path='' as $$
declare cols text[]; c text;
begin
 cols:=string_to_array(tg_argv[0],',');
 foreach c in array cols loop
  if to_jsonb(new)->c is distinct from to_jsonb(old)->c then raise exception 'Referenca ali merska enota je nespremenljiva' using errcode='23514'; end if;
 end loop;
 return new;
end $$;
do $$ declare x text[]; begin
 foreach x slice 1 in array array[
 ['vloga_uporabnika','uporabnik_id,podjetje_id,vloga'],['ekipa','podjetje_id'],['vrsta_materiala','podjetje_id'],['material','vrsta_materiala_id,enota'],
 ['postavka_cenika','podjetje_id'],['projekt','podjetje_id,stranka_id'],['ponudba','projekt_id'],['postavka_ponudbe','ponudba_id'],['racun','ponudba_id']] loop
  execute format('create trigger zakleni_reference before update on quoteflow.%I for each row execute function quoteflow_private.zakleni_reference(%L)',x[1],x[2]);
 end loop;
end $$;
create function quoteflow_private.preveri_material() returns trigger language plpgsql security definer set search_path='' as $$
declare company uuid;
begin
 select podjetje_id into company from quoteflow.vrsta_materiala where id=new.vrsta_materiala_id;
 perform 1 from quoteflow.podjetje where id=company for update;
 if exists(select 1 from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where v.podjetje_id=company and m.sifra=new.sifra and m.id<>new.id) then
  raise unique_violation using message='Sifra materiala je ze uporabljena v podjetju'; end if;
 return new;
end $$;
create trigger preveri_material before insert or update on quoteflow.material for each row execute function quoteflow_private.preveri_material();

-- Lock the company before checking cross-row invariants: concurrent writes cannot create
-- conflicting material/invoice numbers or revoke ownership while its company is being changed.
create function quoteflow_private.zakleni_podjetje() returns trigger language plpgsql security definer set search_path='' as $$
declare d jsonb; company uuid; worker quoteflow.vloga_uporabnika;
begin
 d:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 case tg_table_name
 when 'podjetje' then company:=(d->>'id')::uuid;
 when 'vloga_uporabnika','projekt','ekipa','postavka_cenika','vrsta_materiala' then company:=(d->>'podjetje_id')::uuid;
 when 'clan_ekipe','projekt_ekipa' then select podjetje_id into company from quoteflow.ekipa where id=(d->>'ekipa_id')::uuid;
 when 'material' then select podjetje_id into company from quoteflow.vrsta_materiala where id=(d->>'vrsta_materiala_id')::uuid;
 when 'zaloga' then select v.podjetje_id into company from quoteflow.material m join quoteflow.vrsta_materiala v on v.id=m.vrsta_materiala_id where m.id=(d->>'material_id')::uuid;
 when 'sestava_cenika' then select podjetje_id into company from quoteflow.postavka_cenika where id=(d->>'postavka_cenika_id')::uuid;
 when 'ponudba' then select podjetje_id into company from quoteflow.projekt where id=(d->>'projekt_id')::uuid;
 when 'postavka_ponudbe','racun' then select p.podjetje_id into company from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.id=(d->>'ponudba_id')::uuid;
 when 'material_ponudbe' then select p.podjetje_id into company from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where l.id=(d->>'postavka_ponudbe_id')::uuid;
 end case;
 perform 1 from quoteflow.podjetje where id=company for update;
 if tg_table_name='clan_ekipe' and tg_op<>'DELETE' then
  select * into worker from quoteflow.vloga_uporabnika where id=(d->>'delavec_vloga_id')::uuid for share;
  if not found or worker.vloga<>'delavec' or not worker.aktivna or worker.podjetje_id is distinct from company then
   raise check_violation using message='Nov clan ekipe mora biti aktivni delavec istega podjetja'; end if;
 end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;
do $$ declare t text; begin
 foreach t in array array['podjetje','vloga_uporabnika','projekt','ekipa','clan_ekipe','projekt_ekipa','postavka_cenika','vrsta_materiala','material','zaloga','sestava_cenika','ponudba','postavka_ponudbe','material_ponudbe','racun'] loop
  execute format('create trigger a_zakleni_podjetje before insert or update or delete on quoteflow.%I for each row execute function quoteflow_private.zakleni_podjetje()',t);
 end loop;
end $$;

-- Snapshot documents cannot be edited after sending, even through an owner connection.
create function quoteflow_private.zakleni_postavko() returns trigger language plpgsql security definer set search_path='' as $$
declare parent uuid; state text;
begin
 if tg_table_name='postavka_ponudbe' then parent:=case when tg_op='DELETE' then old.ponudba_id else new.ponudba_id end;
 else
  if tg_op='UPDATE' and (new.postavka_ponudbe_id is distinct from old.postavka_ponudbe_id or new.material_id is distinct from old.material_id) then raise check_violation; end if;
  select ponudba_id into parent from quoteflow.postavka_ponudbe where id=case when tg_op='DELETE' then old.postavka_ponudbe_id else new.postavka_ponudbe_id end;
 end if;
 select stanje into state from quoteflow.ponudba where id=parent for update;
 if state<>'osnutek' then raise exception 'Poslana ponudba je zaklenjena' using errcode='55000'; end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;
create trigger zakleni_postavko before insert or update or delete on quoteflow.postavka_ponudbe for each row execute function quoteflow_private.zakleni_postavko();
create trigger zakleni_material_ponudbe before insert or update or delete on quoteflow.material_ponudbe for each row execute function quoteflow_private.zakleni_postavko();
create function quoteflow_private.preveri_ponudbo() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_op='DELETE' then
  if old.stanje<>'osnutek' then raise exception 'Poslana ponudba je zaklenjena' using errcode='55000'; end if; return old;
 end if;
 perform 1 from quoteflow.projekt where id=new.projekt_id for update;
 if exists(select 1 from quoteflow.ponudba where projekt_id=new.projekt_id and id<>new.id and stevilka<>new.stevilka) then raise check_violation using message='Razlicice projekta ohranijo stevilko ponudbe'; end if;
 if tg_op='INSERT' then
  if new.stanje<>'osnutek' or exists(select 1 from quoteflow.ponudba where projekt_id=new.projekt_id and stanje='sprejeta') then raise check_violation; end if;
 elsif old.stanje<>'osnutek' then
  if old.stanje<>'poslana' or new.stanje not in ('sprejeta','zavrnjena') or (to_jsonb(new)-'stanje'-'odgovorjeno_ob') is distinct from (to_jsonb(old)-'stanje'-'odgovorjeno_ob') then
   raise exception 'Poslana ponudba je zaklenjena' using errcode='55000'; end if;
  if new.velja_do<current_date or exists(select 1 from quoteflow.ponudba where projekt_id=new.projekt_id and razlicica>new.razlicica and stanje<>'osnutek') then raise check_violation; end if;
 elsif new.stanje not in ('osnutek','poslana') then raise check_violation;
 end if;
 if new.stanje='poslana' and not exists(select 1 from quoteflow.postavka_ponudbe where ponudba_id=new.id) then raise check_violation using message='Ponudba potrebuje postavko'; end if;
 return new;
end $$;
create trigger preveri_ponudbo before insert or update or delete on quoteflow.ponudba for each row execute function quoteflow_private.preveri_ponudbo();
create function quoteflow_private.preveri_racun() returns trigger language plpgsql security definer set search_path='' as $$
declare company uuid;
begin
 if tg_op='DELETE' then
  if old.stanje_dokumenta='izdan' then raise exception 'Izdani racun je zaklenjen' using errcode='55000'; end if; return old;
 end if;
 select p.podjetje_id into company from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.id=new.ponudba_id and q.stanje='sprejeta';
 if company is null then raise check_violation using message='Racun zahteva sprejeto ponudbo'; end if;
 perform 1 from quoteflow.podjetje where id=company for update;
 if tg_op='UPDATE' and old.stanje_dokumenta='izdan' then
  if (to_jsonb(new)-'placano_ob'-'stanje_placila') is distinct from (to_jsonb(old)-'placano_ob'-'stanje_placila') or old.placano_ob is not null then
   raise exception 'Izdani racun je zaklenjen' using errcode='55000'; end if;
 end if;
 if new.stevilka is not null and exists(select 1 from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where p.podjetje_id=company and r.stevilka=new.stevilka and r.id<>new.id) then raise unique_violation; end if;
 return new;
end $$;
create trigger preveri_racun before insert or update or delete on quoteflow.racun for each row execute function quoteflow_private.preveri_racun();
create function quoteflow_private.preveri_projekt() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_op='INSERT' then
  if new.faza<>'pregled' then raise check_violation; end if;
  perform 1 from quoteflow.vloga_uporabnika v where v.uporabnik_id=new.stranka_id and v.vloga='stranka' and v.aktivna for share;
  if not found then raise check_violation using message='Nov projekt zahteva aktivno stranko'; end if;
 end if;
 if tg_op='UPDATE' and old.faza<>new.faza then
  if not ((old.faza='pregled' and new.faza in ('ogled','ponudba')) or (old.faza='ogled' and new.faza='ponudba') or (old.faza='ponudba' and new.faza='termin')
  or (old.faza='termin' and new.faza='izvedba') or (old.faza='izvedba' and new.faza='obracun') or (old.faza='obracun' and new.faza='zakljucen')) then raise check_violation; end if;
 end if;
 if new.faza='ponudba' and not exists(select 1 from quoteflow.ponudba where projekt_id=new.id and stanje<>'osnutek') then raise check_violation; end if;
 if new.faza in ('termin','izvedba','obracun','zakljucen') and not exists(select 1 from quoteflow.ponudba where projekt_id=new.id and stanje='sprejeta') then raise check_violation; end if;
 if new.faza in ('izvedba','obracun','zakljucen') and new.termin_od is null then raise check_violation; end if;
 if new.faza in ('obracun','zakljucen') and (new.izvedba_koncana_ob is null or not exists(select 1 from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id where q.projekt_id=new.id and r.stanje_dokumenta='izdan' and r.poslan_ob is not null)) then raise check_violation; end if;
 if new.faza='zakljucen' and not exists(select 1 from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id where q.projekt_id=new.id and r.placano_ob is not null) then raise check_violation; end if;
 return new;
end $$;
create trigger preveri_projekt before insert or update on quoteflow.projekt for each row execute function quoteflow_private.preveri_projekt();

-- Registration preserves identity only; system code grants stranka, never requested metadata roles.
create function quoteflow_private.sync_uporabnik() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.email is not null and trim(new.email)<>'' then
  insert into quoteflow.uporabnik(id,e_posta,ime,priimek) values(new.id,lower(trim(new.email)),left(coalesce(new.raw_user_meta_data->>'ime',''),200),left(coalesce(new.raw_user_meta_data->>'priimek',''),200))
  on conflict(id) do update set e_posta=excluded.e_posta,ime=excluded.ime,priimek=excluded.priimek;
  if new.email_confirmed_at is not null then
   insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(new.id,'stranka') on conflict(uporabnik_id,vloga) where podjetje_id is null do nothing;
  end if;
 end if;
 return new;
end $$;
create trigger quoteflow_sync_uporabnik after insert or update of email,email_confirmed_at,raw_user_meta_data on auth.users for each row execute function quoteflow_private.sync_uporabnik();
insert into quoteflow.uporabnik(id,e_posta,ime,priimek) select id,lower(trim(email)),left(coalesce(raw_user_meta_data->>'ime',''),200),left(coalesce(raw_user_meta_data->>'priimek',''),200) from auth.users where email is not null and trim(email)<>'';
insert into quoteflow.vloga_uporabnika(id,uporabnik_id,vloga,aktivna) select id,uporabnik_id,'admin',aktivna from quoteflow_legacy_20261103.vloga_uporabnika where vloga='administrator';
insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) select u.id,'stranka' from quoteflow.uporabnik u join auth.users a on a.id=u.id where a.email_confirmed_at is not null;

-- Administrative/company mutations. No public function can grant admin.
create function quoteflow_private.ustvari_podjetje(lastnik uuid,ime text,maticna text,davcna text,naslov_v text) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare r quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 if not exists(select 1 from auth.users where id=lastnik and email_confirmed_at is not null) then raise check_violation; end if;
 insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,davcna_stevilka,naslov) values(lastnik,trim(ime),trim(maticna),nullif(trim(davcna),''),trim(naslov_v)) returning * into r;
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(lastnik,r.id,'mojster'); return r;
end $$;
create function quoteflow_private.uredi_podjetje(target uuid,ime text,maticna text,davcna text,naslov_v text,aktivno_v boolean) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare r quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then
  perform quoteflow_private.preveri_mojstra(target);
  if exists(select 1 from quoteflow.podjetje where id=target and aktivno<>aktivno_v) then raise insufficient_privilege; end if;
 end if;
 update quoteflow.podjetje set naziv=trim(ime),maticna_stevilka=trim(maticna),davcna_stevilka=nullif(trim(davcna),''),naslov=trim(naslov_v),aktivno=aktivno_v where id=target returning * into r;
 if not found then raise no_data_found; end if; return r;
end $$;
create function quoteflow_private.dodeli_vlogo(target uuid,podjetje uuid,naloga text) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.administrator() then
  if naloga<>'delavec' or podjetje is null then raise insufficient_privilege; end if;
  perform quoteflow_private.preveri_mojstra(podjetje);
 end if;
 if naloga not in ('stranka','mojster','delavec') then raise check_violation; end if;
 if not exists(select 1 from auth.users where id=target and email_confirmed_at is not null) then raise check_violation; end if;
 if podjetje is not null then
  perform 1 from quoteflow.podjetje where id=$2 and aktivno for update;
  if not found then raise check_violation; end if;
  insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(target,podjetje,naloga)
  on conflict(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null do update set aktivna=true returning * into r;
 else
  insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(target,naloga)
  on conflict(uporabnik_id,vloga) where podjetje_id is null do update set aktivna=true returning * into r;
 end if; return r;
end $$;
create function quoteflow_private.aktiviraj_vlogo(target uuid,velja boolean) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select * into r from quoteflow.vloga_uporabnika where id=target;
 if not found then raise no_data_found; end if;
 if r.vloga='admin' then raise insufficient_privilege; end if;
 if not quoteflow_private.administrator() then
  if r.vloga<>'delavec' then raise insufficient_privilege; end if;
  perform quoteflow_private.preveri_mojstra(r.podjetje_id);
 end if;
 if r.podjetje_id is not null then
  perform 1 from quoteflow.podjetje where id=r.podjetje_id for update;
 end if;
 if not velja and r.vloga='mojster' and exists(
  select 1 from quoteflow.podjetje where id=r.podjetje_id and lastnik_id=r.uporabnik_id
 ) then raise check_violation using message='Lastnik potrebuje aktivno vlogo mojster pri svojem podjetju'; end if;
 update quoteflow.vloga_uporabnika set aktivna=velja where id=target returning * into r; return r;
end $$;
create function quoteflow_private.oddaj_prosnjo(ime text,maticna text,davcna text,naslov_v text) returns quoteflow.prosnja_mojstra language plpgsql security definer set search_path='' as $$
declare r quoteflow.prosnja_mojstra;
begin
 if not quoteflow_private.aktivna_seja() or not exists(select 1 from quoteflow.vloga_uporabnika where uporabnik_id=auth.uid() and aktivna and vloga in ('stranka','delavec')) then raise insufficient_privilege; end if;
 if exists(select 1 from quoteflow.podjetje where maticna_stevilka=trim(maticna)) then raise unique_violation; end if;
 insert into quoteflow.prosnja_mojstra(uporabnik_id,naziv_podjetja,maticna_stevilka,davcna_stevilka,naslov_podjetja) values(auth.uid(),trim(ime),trim(maticna),nullif(trim(davcna),''),trim(naslov_v)) returning * into r; return r;
end $$;
create function quoteflow_private.odloci_prosnjo(target uuid,odobri boolean) returns quoteflow.prosnja_mojstra language plpgsql security definer set search_path='' as $$
declare r quoteflow.prosnja_mojstra; p quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 select * into r from quoteflow.prosnja_mojstra where id=target for update;
 if not found then raise no_data_found; end if;
 if r.stanje<>'oddana' then raise check_violation; end if;
 if odobri then p:=quoteflow_private.ustvari_podjetje(r.uporabnik_id,r.naziv_podjetja,r.maticna_stevilka,r.davcna_stevilka,r.naslov_podjetja); end if;
 update quoteflow.prosnja_mojstra set stanje=case when odobri then 'odobrena' else 'zavrnjena' end,podjetje_id=p.id,odlocil_id=auth.uid(),odloceno_ob=now() where id=target returning * into r; return r;
end $$;
create function quoteflow_private.shrani_cenik(podjetje uuid,target uuid,ime text,opis_v text,vrsta_dela_v text,enota_v text,cena numeric,ddv numeric,aktivna_v boolean) returns quoteflow.postavka_cenika language plpgsql security definer set search_path='' as $$
declare r quoteflow.postavka_cenika;
begin
 perform quoteflow_private.preveri_mojstra(podjetje);
 if target is null then
  insert into quoteflow.postavka_cenika(podjetje_id,naziv,opis,vrsta_dela,enota,cena_na_enoto,stopnja_ddv,aktivna) values(podjetje,trim(ime),trim(opis_v),trim(vrsta_dela_v),trim(enota_v),cena,ddv,aktivna_v) returning * into r;
 else
  update quoteflow.postavka_cenika set naziv=trim(ime),opis=trim(opis_v),vrsta_dela=trim(vrsta_dela_v),enota=trim(enota_v),cena_na_enoto=cena,stopnja_ddv=ddv,aktivna=aktivna_v where id=target and podjetje_id=podjetje returning * into r;
  if not found then raise no_data_found; end if;
 end if; return r;
end $$;
create function quoteflow_private.shrani_vrsto_materiala(podjetje uuid,target uuid,ime text) returns quoteflow.vrsta_materiala language plpgsql security definer set search_path='' as $$
declare r quoteflow.vrsta_materiala;
begin
 perform quoteflow_private.preveri_mojstra(podjetje);
 if target is null then insert into quoteflow.vrsta_materiala(podjetje_id,naziv) values(podjetje,trim(ime)) returning * into r;
 else update quoteflow.vrsta_materiala set naziv=trim(ime) where id=target and podjetje_id=podjetje returning * into r; if not found then raise no_data_found; end if; end if;
 return r;
end $$;
create function quoteflow_private.shrani_material(podjetje uuid,target uuid,vrsta uuid,sifra_v text,ime text,enota_v text,cena numeric,aktiven_v boolean) returns quoteflow.material language plpgsql security definer set search_path='' as $$
declare r quoteflow.material;
begin
 perform quoteflow_private.preveri_mojstra(podjetje);
 if not exists(select 1 from quoteflow.vrsta_materiala where id=vrsta and podjetje_id=podjetje) then raise no_data_found; end if;
 if target is null then insert into quoteflow.material(vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto,aktiven) values(vrsta,trim(sifra_v),trim(ime),trim(enota_v),cena,aktiven_v) returning * into r;
 else update quoteflow.material set sifra=trim(sifra_v),naziv=trim(ime),enota=trim(enota_v),cena_na_enoto=cena,aktiven=aktiven_v where id=target and vrsta_materiala_id=vrsta returning * into r;
 if not found then raise no_data_found; end if; end if; return r;
end $$;
create function quoteflow_private.shrani_zalogo(podjetje uuid,material_v uuid,lokacija_v text,kolicina_v numeric) returns quoteflow.zaloga language plpgsql security definer set search_path='' as $$
declare r quoteflow.zaloga;
begin
 perform quoteflow_private.preveri_mojstra(podjetje);
 if quoteflow_private.material_podjetje(material_v) is distinct from podjetje then raise no_data_found; end if;
 insert into quoteflow.zaloga(material_id,lokacija,kolicina) values(material_v,trim(lokacija_v),kolicina_v) on conflict(material_id,lokacija) do update set kolicina=excluded.kolicina returning * into r; return r;
end $$;
create function quoteflow_private.odstrani_zalogo(podjetje uuid,material_v uuid,lokacija_v text) returns void language plpgsql security definer set search_path='' as $$
begin
 perform quoteflow_private.preveri_mojstra(podjetje);
 if quoteflow_private.material_podjetje(material_v) is distinct from podjetje then raise no_data_found; end if;
 delete from quoteflow.zaloga where material_id=material_v and lokacija=lokacija_v;
 if not found then raise no_data_found; end if;
end $$;

-- Atomic lifecycle actions; customers decide, company masters schedule/issue/record full payment.
create function quoteflow_private.poslji_ponudbo(target uuid) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; p quoteflow.projekt;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select p1.* into p from quoteflow.projekt p1 join quoteflow.ponudba q on q.projekt_id=p1.id where q.id=target;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_mojstra(p.podjetje_id);
 perform 1 from quoteflow.projekt where id=p.id for update;
 update quoteflow.ponudba set stanje='poslana',poslano_ob=now() where id=target and stanje='osnutek' returning * into r;
 if not found then raise check_violation; end if;
 update quoteflow.projekt set faza='ponudba' where id=p.id and faza in ('pregled','ogled'); return r;
end $$;
create function quoteflow_private.odgovori_ponudbo(target uuid,sprejmi boolean) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; p quoteflow.projekt;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select p1.* into p from quoteflow.projekt p1 join quoteflow.ponudba q on q.projekt_id=p1.id where q.id=target and p1.stranka_id=auth.uid() and quoteflow_private.stranka() for update of p1;
 if not found then raise insufficient_privilege; end if;
 update quoteflow.ponudba set stanje=case when sprejmi then 'sprejeta' else 'zavrnjena' end,odgovorjeno_ob=now() where id=target and stanje='poslana' returning * into r;
 if not found then raise check_violation; end if;
 if sprejmi then
  insert into quoteflow.racun(ponudba_id) values(target);
  update quoteflow.projekt set faza='termin' where id=p.id;
 end if; return r;
end $$;
create function quoteflow_private.doloci_termin(target uuid,zacetek timestamptz,konec timestamptz) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select * into r from quoteflow.projekt where id=target;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_mojstra(r.podjetje_id);
 select * into r from quoteflow.projekt where id=target for update;
 if r.faza<>'termin' then raise check_violation; end if;
 update quoteflow.projekt set termin_od=zacetek,termin_do=konec,faza='izvedba' where id=target returning * into r; return r;
end $$;
create function quoteflow_private.izdaj_racun(target uuid,stevilka_v text,prejemnik text,naslov_v text,zapade date) returns quoteflow.racun language plpgsql security definer set search_path='' as $$
declare r quoteflow.racun; p quoteflow.projekt; c quoteflow.podjetje;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select p1.* into p from quoteflow.projekt p1 join quoteflow.ponudba q on q.projekt_id=p1.id join quoteflow.racun r1 on r1.ponudba_id=q.id where r1.id=target;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_mojstra(p.podjetje_id);
 select * into p from quoteflow.projekt where id=p.id for update;
 if p.faza<>'izvedba' or p.izvedba_koncana_ob is null then raise check_violation; end if;
 select * into c from quoteflow.podjetje where id=p.podjetje_id;
 update quoteflow.racun set stanje_dokumenta='izdan',stevilka=trim(stevilka_v),izdajatelj_naziv=c.naziv,izdajatelj_naslov=c.naslov,izdajatelj_davcna=c.davcna_stevilka,
 prejemnik_naziv=trim(prejemnik),prejemnik_naslov=trim(naslov_v),izdan_ob=now(),poslan_ob=now(),zapade_dne=zapade where id=target and stanje_dokumenta='osnutek' returning * into r;
 if not found then raise check_violation; end if;
 update quoteflow.projekt set faza='obracun' where id=p.id; return r;
end $$;
create function quoteflow_private.placaj_racun(target uuid) returns quoteflow.racun language plpgsql security definer set search_path='' as $$
declare r quoteflow.racun; p quoteflow.projekt;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select p1.* into p from quoteflow.projekt p1 join quoteflow.ponudba q on q.projekt_id=p1.id join quoteflow.racun r1 on r1.ponudba_id=q.id where r1.id=target;
 if not found then raise no_data_found; end if;
 perform quoteflow_private.preveri_mojstra(p.podjetje_id);
 select * into p from quoteflow.projekt where id=p.id for update;
 if p.faza<>'obracun' then raise check_violation; end if;
 update quoteflow.racun set placano_ob=now() where id=target and stanje_dokumenta='izdan' and placano_ob is null returning * into r;
 if not found then raise check_violation; end if;
 update quoteflow.projekt set faza='zakljucen',zakljuceno_ob=now() where id=p.id; return r;
end $$;

-- Backfilled roles queue deferred integrity triggers. Drain them before ALTER TABLE:
-- populated V1 databases otherwise reject the RLS DDL with pending trigger events.
set constraints all immediate;

-- Read-only application role, independent of schema exposure configuration.
do $$ declare t text; begin
 foreach t in array array['uporabnik','podjetje','vloga_uporabnika','prosnja_mojstra','projekt','ekipa','clan_ekipe','projekt_ekipa','postavka_cenika','vrsta_materiala','material','zaloga','sestava_cenika','ponudba','postavka_ponudbe','material_ponudbe','racun'] loop
  execute format('alter table quoteflow.%I enable row level security',t);
  execute format('alter table quoteflow.%I force row level security',t);
  execute format('revoke all on quoteflow.%I from public,anon,authenticated,service_role,quoteflow_app',t);
  execute format('grant select on quoteflow.%I to authenticated',t);
 end loop;
end $$;
create policy read_own on quoteflow.uporabnik for select to authenticated using ((id=(select auth.uid()) and (select quoteflow_private.aktivna_seja())) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.vloga_uporabnika for select to authenticated using ((uporabnik_id=(select auth.uid()) and (select quoteflow_private.aktivna_seja())) or (select quoteflow_private.administrator()) or quoteflow_private.clan(podjetje_id,'mojster'));
create policy read_own on quoteflow.podjetje for select to authenticated using (quoteflow_private.clan(id) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.prosnja_mojstra for select to authenticated using ((uporabnik_id=(select auth.uid()) and (select quoteflow_private.aktivna_seja())) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.projekt for select to authenticated using (quoteflow_private.vidi_projekt(id));
create policy read_own on quoteflow.ekipa for select to authenticated using (quoteflow_private.clan(podjetje_id));
create policy read_own on quoteflow.clan_ekipe for select to authenticated using (exists(select 1 from quoteflow.ekipa e where e.id=ekipa_id));
create policy read_own on quoteflow.projekt_ekipa for select to authenticated using (quoteflow_private.vidi_projekt(projekt_id));
create policy read_own on quoteflow.postavka_cenika for select to authenticated using (quoteflow_private.clan(podjetje_id,'mojster'));
create policy read_own on quoteflow.vrsta_materiala for select to authenticated using (quoteflow_private.clan(podjetje_id,'mojster'));
create policy read_own on quoteflow.material for select to authenticated using (quoteflow_private.clan(quoteflow_private.material_podjetje(id),'mojster'));
create policy read_own on quoteflow.zaloga for select to authenticated using (quoteflow_private.clan(quoteflow_private.material_podjetje(material_id),'mojster'));
create policy read_own on quoteflow.sestava_cenika for select to authenticated using (exists(select 1 from quoteflow.postavka_cenika c where c.id=postavka_cenika_id));
create policy read_own on quoteflow.ponudba for select to authenticated using (quoteflow_private.vidi_ponudbo(id));
create policy read_own on quoteflow.postavka_ponudbe for select to authenticated using (quoteflow_private.vidi_ponudbo(ponudba_id));
-- Composition carries internal material prices, never exposed with a customer's offer.
create policy read_own on quoteflow.material_ponudbe for select to authenticated using (exists(select 1 from quoteflow.postavka_ponudbe l join quoteflow.ponudba q on q.id=l.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where l.id=postavka_ponudbe_id and quoteflow_private.clan(p.podjetje_id,'mojster')));
create policy read_own on quoteflow.racun for select to authenticated using (exists(select 1 from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.id=ponudba_id and (quoteflow_private.clan(p.podjetje_id,'mojster') or (p.stranka_id=(select auth.uid()) and (select quoteflow_private.stranka()) and stanje_dokumenta='izdan' and poslan_ob is not null))));
revoke all on all functions in schema quoteflow_private from public,anon,authenticated,service_role,quoteflow_app;
grant execute on function quoteflow_private.aktivna_seja(),quoteflow_private.administrator(),quoteflow_private.stranka(),quoteflow_private.clan(uuid,text),quoteflow_private.vidi_projekt(uuid),quoteflow_private.vidi_ponudbo(uuid),quoteflow_private.material_podjetje(uuid) to authenticated;
grant execute on function quoteflow_private.ustvari_podjetje(uuid,text,text,text,text),quoteflow_private.uredi_podjetje(uuid,text,text,text,text,boolean),quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.aktiviraj_vlogo(uuid,boolean),quoteflow_private.oddaj_prosnjo(text,text,text,text),quoteflow_private.odloci_prosnjo(uuid,boolean),
 quoteflow_private.shrani_cenik(uuid,uuid,text,text,text,text,numeric,numeric,boolean),quoteflow_private.shrani_vrsto_materiala(uuid,uuid,text),quoteflow_private.shrani_material(uuid,uuid,uuid,text,text,text,numeric,boolean),quoteflow_private.shrani_zalogo(uuid,uuid,text,numeric),quoteflow_private.odstrani_zalogo(uuid,uuid,text),
 quoteflow_private.poslji_ponudbo(uuid),quoteflow_private.odgovori_ponudbo(uuid,boolean),quoteflow_private.doloci_termin(uuid,timestamptz,timestamptz),quoteflow_private.izdaj_racun(uuid,text,text,text,date),quoteflow_private.placaj_racun(uuid) to authenticated;
comment on schema quoteflow is 'Primarni relacijski model docs/03: 17 tabel, admin/mojster/delavec/stranka, projekti in poslovni dokumenti.';

-- Deferred document integrity allows only atomic multi-row lifecycle transitions.
create function quoteflow_private.preveri_dokumente() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.stanje='sprejeta' and
 (p.faza not in ('termin','izvedba','obracun','zakljucen') or not exists(select 1 from quoteflow.racun r where r.ponudba_id=q.id)))
 or exists(select 1 from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where
 q.stanje<>'sprejeta' or (r.stanje_dokumenta='izdan' and p.faza not in ('obracun','zakljucen')) or (r.placano_ob is not null and p.faza<>'zakljucen')) then
  raise exception 'Dokumenti in faza projekta morajo biti usklajeni v isti transakciji' using errcode='23514'; end if;
 return null;
end $$;
create constraint trigger dokumenti after insert or update or delete on quoteflow.ponudba deferrable initially deferred for each row execute function quoteflow_private.preveri_dokumente();
create constraint trigger dokumenti after insert or update or delete on quoteflow.racun deferrable initially deferred for each row execute function quoteflow_private.preveri_dokumente();
create constraint trigger dokumenti after insert or update or delete on quoteflow.projekt deferrable initially deferred for each row execute function quoteflow_private.preveri_dokumente();
revoke all on function quoteflow_private.preveri_dokumente() from public,anon,authenticated,service_role,quoteflow_app;
