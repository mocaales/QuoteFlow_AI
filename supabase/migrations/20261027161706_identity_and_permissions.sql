-- Replaces the obsolete business schema at the user's explicit request.
-- auth.users and auth.sessions are preserved. Back up quoteflow before remote deployment.
drop schema if exists quoteflow cascade;
drop schema if exists quoteflow_private cascade;
create schema quoteflow;
create schema quoteflow_private;
revoke all on schema quoteflow, quoteflow_private from public, anon, service_role;
grant usage on schema quoteflow, quoteflow_private to authenticated;
create extension if not exists btree_gist with schema extensions;

create table quoteflow.uporabnik (
 id uuid primary key references auth.users(id) on delete restrict,
 e_posta text not null unique check(e_posta = lower(trim(e_posta)) and length(e_posta) > 3)
);
create table quoteflow.podjetje (
 id uuid primary key default gen_random_uuid(),
 naziv text not null check(length(trim(naziv)) between 1 and 200),
 stanje text not null default 'aktivno' check(stanje in ('aktivno','neaktivno'))
);
create table quoteflow.vloga_uporabnika (
 id uuid primary key default gen_random_uuid(),
 uporabnik_id uuid not null references quoteflow.uporabnik(id),
 podjetje_id uuid references quoteflow.podjetje(id),
 vloga text not null check(vloga in ('nabavnik','ponudnik','administrator')),
 aktivna boolean not null default true,
 check((vloga='administrator') = (podjetje_id is null))
);
create unique index vloga_poslovna_uq on quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null;
create unique index vloga_administrator_uq on quoteflow.vloga_uporabnika(uporabnik_id) where vloga='administrator';
create index vloga_podjetje_idx on quoteflow.vloga_uporabnika(podjetje_id);
create table quoteflow.pravila_ponudnika (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 najmanjsa_marza numeric(8,6) not null check(najmanjsa_marza>=0 and najmanjsa_marza<1),
 najvecji_popust numeric(8,6) not null check(najvecji_popust>=0 and najvecji_popust<1),
 najdaljsi_rok_dni integer not null check(najdaljsi_rok_dni>=0),
 velja_od timestamptz not null, velja_do timestamptz,
 check(velja_do is null or velja_do>velja_od), unique(id,podjetje_id),
 exclude using gist (podjetje_id extensions.gist_uuid_ops with =, tstzrange(velja_od,velja_do,'[)') with &&)
);
create table quoteflow.postavka_cenika (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 vrsta text not null check(vrsta in ('blago','storitev')), opis text not null check(length(trim(opis))>0),
 enota text not null check(length(trim(enota))>0),
 cena_na_enoto numeric(18,4) not null check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric),
 strosek_na_enoto numeric(18,4) not null check(strosek_na_enoto>=0 and strosek_na_enoto<'Infinity'::numeric),
 dobavni_rok_dni integer check(dobavni_rok_dni>=0), aktivna boolean not null default true,
 potrjeno_ob timestamptz
);
create index cenik_podjetje_idx on quoteflow.postavka_cenika(podjetje_id);
create table quoteflow.zaloga (
 postavka_cenika_id uuid primary key references quoteflow.postavka_cenika(id),
 razpolozljiva_kolicina numeric(18,4) not null check(razpolozljiva_kolicina>=0 and razpolozljiva_kolicina<'Infinity'::numeric),
 potrjeno_ob timestamptz not null
);
create table quoteflow.povprasevanje (
 id uuid primary key default gen_random_uuid(), podjetje_nabavnika_id uuid not null references quoteflow.podjetje(id),
 ustvaril_vloga_id uuid not null references quoteflow.vloga_uporabnika(id),
 stanje text not null default 'osnutek' check(stanje in ('osnutek','oddano','v_obdelavi','zakljuceno')),
 kraj_dobave text, zahtevani_datum date, oddano_ob timestamptz, rok_za_ponudbe timestamptz,
 check(stanje='osnutek' or oddano_ob is not null),
 check(oddano_ob is null or rok_za_ponudbe is null or rok_za_ponudbe>oddano_ob)
);
create index povprasevanje_podjetje_idx on quoteflow.povprasevanje(podjetje_nabavnika_id);
create index povprasevanje_vloga_idx on quoteflow.povprasevanje(ustvaril_vloga_id);
create table quoteflow.postavka_povprasevanja (
 id uuid primary key default gen_random_uuid(), povprasevanje_id uuid not null references quoteflow.povprasevanje(id),
 opis text not null check(length(trim(opis))>0),
 kolicina numeric(18,4) not null check(kolicina>0 and kolicina<'Infinity'::numeric),
 enota text not null check(length(trim(enota))>0)
);
create index postavka_rfq_idx on quoteflow.postavka_povprasevanja(povprasevanje_id);
create table quoteflow.ponudba (
 id uuid primary key default gen_random_uuid(), povprasevanje_id uuid not null references quoteflow.povprasevanje(id),
 podjetje_ponudnika_id uuid not null references quoteflow.podjetje(id),
 pravila_id uuid, kontakt_vloga_id uuid references quoteflow.vloga_uporabnika(id),
 odobril_vloga_id uuid references quoteflow.vloga_uporabnika(id),
 izvor_izbire text not null check(izvor_izbire in ('rocna','samodejna')), razlog_izbire text,
 stanje text not null default 'povabljena' check(stanje in ('povabljena','osnutek','v_pregledu','odobrena','zavrnjena')),
 razlicica integer not null default 1 check(razlicica>0), ustvarjeno_ob timestamptz not null default now(),
 odobreno_ob timestamptz, velja_do timestamptz, valuta text not null default 'EUR' check(valuta='EUR'),
 placilni_pogoji text, znesek_skupaj numeric(18,2) check(znesek_skupaj>=0 and znesek_skupaj<'Infinity'::numeric),
 unique(povprasevanje_id,podjetje_ponudnika_id),
 foreign key(pravila_id,podjetje_ponudnika_id) references quoteflow.pravila_ponudnika(id,podjetje_id),
 check((stanje='odobrena') = (odobreno_ob is not null and odobril_vloga_id is not null)),
 check(stanje<>'odobrena' or (pravila_id is not null and znesek_skupaj is not null)),
 check(odobreno_ob is null or velja_do is null or velja_do>odobreno_ob)
);
create index ponudba_podjetje_idx on quoteflow.ponudba(podjetje_ponudnika_id);
create index ponudba_pravila_idx on quoteflow.ponudba(pravila_id);
create index ponudba_kontakt_idx on quoteflow.ponudba(kontakt_vloga_id);
create index ponudba_odobril_idx on quoteflow.ponudba(odobril_vloga_id);
create table quoteflow.postavka_ponudbe (
 id uuid primary key default gen_random_uuid(), ponudba_id uuid not null references quoteflow.ponudba(id),
 postavka_povprasevanja_id uuid not null references quoteflow.postavka_povprasevanja(id),
 postavka_cenika_id uuid references quoteflow.postavka_cenika(id),
 opis text not null check(length(trim(opis))>0),
 kolicina numeric(18,4) not null check(kolicina>0 and kolicina<'Infinity'::numeric),
 enota text not null check(length(trim(enota))>0),
 cena_na_enoto numeric(18,4) check(cena_na_enoto>=0 and cena_na_enoto<'Infinity'::numeric),
 strosek_na_enoto numeric(18,4) check(strosek_na_enoto>=0 and strosek_na_enoto<'Infinity'::numeric),
 popust numeric(8,6) not null default 0 check(popust>=0 and popust<1),
 dobavni_rok_dni integer check(dobavni_rok_dni>=0)
);
create index postavka_ponudba_idx on quoteflow.postavka_ponudbe(ponudba_id);
create index postavka_izvor_idx on quoteflow.postavka_ponudbe(postavka_povprasevanja_id);
create index postavka_cenik_idx on quoteflow.postavka_ponudbe(postavka_cenika_id);

-- Sync only identity; no user-controlled metadata grants a role.
create function quoteflow_private.sync_uporabnik() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.email is not null and trim(new.email)<>'' then
  insert into quoteflow.uporabnik(id,e_posta) values(new.id,lower(trim(new.email)))
  on conflict(id) do update set e_posta=excluded.e_posta;
 end if;
 return new;
end $$;
create trigger quoteflow_sync_uporabnik after insert or update of email on auth.users
 for each row execute function quoteflow_private.sync_uporabnik();
insert into quoteflow.uporabnik(id,e_posta) select id,lower(trim(email)) from auth.users where email is not null and trim(email)<>'';

create function quoteflow_private.aktivna_seja() returns boolean language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and exists(select 1 from auth.sessions s
 where s.user_id=auth.uid() and s.id::text=coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb->>'session_id'
 and (s.not_after is null or s.not_after>now()))
$$;
create function quoteflow_private.administrator() returns boolean language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.vloga_uporabnika
 where uporabnik_id=auth.uid() and vloga='administrator' and aktivna)
$$;
create function quoteflow_private.clan(podjetje uuid, zahtevana_vloga text default null) returns boolean
 language sql stable security definer set search_path='' as $$
 select quoteflow_private.aktivna_seja() and exists(select 1 from quoteflow.vloga_uporabnika v
 join quoteflow.podjetje p on p.id=v.podjetje_id where v.uporabnik_id=auth.uid() and v.podjetje_id=podjetje
 and v.aktivna and p.stanje='aktivno' and (zahtevana_vloga is null or v.vloga=zahtevana_vloga))
$$;

-- Enforce documented cross-entity invariants even for privileged writers.
create function quoteflow_private.preveri_zalogo() returns trigger language plpgsql set search_path='' as $$
begin
 if (select vrsta from quoteflow.postavka_cenika where id=new.postavka_cenika_id)<>'blago' then
  raise exception 'Zaloga je dovoljena samo za blago' using errcode='23514';
 end if; return new;
end $$;
create trigger preveri_zalogo before insert or update on quoteflow.zaloga for each row execute function quoteflow_private.preveri_zalogo();
create function quoteflow_private.preveri_vrsto_cenika() returns trigger language plpgsql set search_path='' as $$
begin
 if new.vrsta='storitev' and exists(select 1 from quoteflow.zaloga where postavka_cenika_id=new.id) then
  raise exception 'Storitev ne sme imeti zaloge' using errcode='23514';
 end if; return new;
end $$;
create trigger preveri_vrsto before update of vrsta on quoteflow.postavka_cenika for each row execute function quoteflow_private.preveri_vrsto_cenika();
create function quoteflow_private.preveri_rfq() returns trigger language plpgsql set search_path='' as $$
begin
 if not exists(select 1 from quoteflow.vloga_uporabnika v join quoteflow.podjetje p on p.id=v.podjetje_id
 where v.id=new.ustvaril_vloga_id and v.podjetje_id=new.podjetje_nabavnika_id and v.vloga='nabavnik' and v.aktivna and p.stanje='aktivno') then
  raise exception 'Neveljavna vloga nabavnika' using errcode='23514';
 end if;
 if new.stanje<>'osnutek' and not exists(select 1 from quoteflow.postavka_povprasevanja where povprasevanje_id=new.id) then
  raise exception 'Oddani RFQ potrebuje postavko' using errcode='23514';
 end if; return new;
end $$;
create trigger preveri_rfq before insert or update on quoteflow.povprasevanje for each row execute function quoteflow_private.preveri_rfq();
create function quoteflow_private.preveri_postavko_rfq() returns trigger language plpgsql set search_path='' as $$
declare target uuid;
begin
 if tg_op<>'INSERT' then
  if (select stanje from quoteflow.povprasevanje where id=old.povprasevanje_id)<>'osnutek' then
   raise exception 'Oddani RFQ je zaklenjen' using errcode='55000';
  end if;
 end if;
 if tg_op='DELETE' then return old; end if;
 target:=new.povprasevanje_id;
 if (select stanje from quoteflow.povprasevanje where id=target)<>'osnutek' then
  raise exception 'Oddani RFQ je zaklenjen' using errcode='55000';
 end if; return new;
end $$;
create trigger preveri_postavko_rfq before insert or update or delete on quoteflow.postavka_povprasevanja
 for each row execute function quoteflow_private.preveri_postavko_rfq();
create function quoteflow_private.preveri_postavko_ponudbe() returns trigger language plpgsql set search_path='' as $$
declare target quoteflow.ponudba;
begin
 if tg_op<>'INSERT' and (select stanje from quoteflow.ponudba where id=old.ponudba_id)='odobrena' then
  raise exception 'Odobrena ponudba je zaklenjena' using errcode='55000';
 end if;
 if tg_op='DELETE' then return old; end if;
 select * into target from quoteflow.ponudba where id=new.ponudba_id for update;
 if target.stanje='odobrena' then raise exception 'Odobrena ponudba je zaklenjena' using errcode='55000'; end if;
 if not exists(select 1 from quoteflow.postavka_povprasevanja where id=new.postavka_povprasevanja_id and povprasevanje_id=target.povprasevanje_id)
 or (new.postavka_cenika_id is not null and not exists(select 1 from quoteflow.postavka_cenika where id=new.postavka_cenika_id and podjetje_id=target.podjetje_ponudnika_id)) then
  raise exception 'Postavka pripada drugemu RFQ ali ponudniku' using errcode='23514';
 end if; return new;
end $$;
create trigger preveri_postavko_ponudbe before insert or update or delete on quoteflow.postavka_ponudbe
 for each row execute function quoteflow_private.preveri_postavko_ponudbe();
create function quoteflow_private.preveri_ponudbo() returns trigger language plpgsql set search_path='' as $$
declare r quoteflow.pravila_ponudnika; total numeric;
begin
 if tg_op<>'INSERT' and old.stanje='odobrena' then raise exception 'Odobrena ponudba je zaklenjena' using errcode='55000'; end if;
 if tg_op='DELETE' then return old; end if;
 if exists(select 1 from quoteflow.povprasevanje where id=new.povprasevanje_id and podjetje_nabavnika_id=new.podjetje_ponudnika_id)
 or not exists(select 1 from quoteflow.podjetje where id=new.podjetje_ponudnika_id and stanje='aktivno') then
  raise exception 'Neveljavno podjetje ponudnika' using errcode='23514';
 end if;
 if new.kontakt_vloga_id is not null and not exists(select 1 from quoteflow.vloga_uporabnika where id=new.kontakt_vloga_id and podjetje_id=new.podjetje_ponudnika_id and vloga='ponudnik' and aktivna) then
  raise exception 'Neveljaven kontakt ponudnika' using errcode='23514';
 end if;
 if new.stanje='odobrena' then
  perform 1 from quoteflow.vloga_uporabnika where id=new.odobril_vloga_id and podjetje_id=new.podjetje_ponudnika_id and vloga='ponudnik' and aktivna for share;
  if not found then raise exception 'Neveljaven odobritelj' using errcode='23514'; end if;
  select * into r from quoteflow.pravila_ponudnika where id=new.pravila_id and podjetje_id=new.podjetje_ponudnika_id and velja_od<=now() and (velja_do is null or velja_do>now()) for share;
  if not found then raise exception 'Manjkajo veljavna pravila' using errcode='23514'; end if;
  if not exists(select 1 from quoteflow.postavka_ponudbe where ponudba_id=new.id) or exists(
   select 1 from quoteflow.postavka_ponudbe where ponudba_id=new.id and
    (cena_na_enoto is null or strosek_na_enoto is null or dobavni_rok_dni is null or cena_na_enoto<=0
     or popust>r.najvecji_popust or dobavni_rok_dni>r.najdaljsi_rok_dni
     or cena_na_enoto*(1-popust)*(1-r.najmanjsa_marza)<strosek_na_enoto)) then
   raise exception 'Nepopolne postavke ali krsitev pravil' using errcode='23514';
  end if;
  if exists(select 1 from quoteflow.postavka_ponudbe x join quoteflow.zaloga z on z.postavka_cenika_id=x.postavka_cenika_id
    where x.ponudba_id=new.id group by z.postavka_cenika_id,z.razpolozljiva_kolicina having sum(x.kolicina)>z.razpolozljiva_kolicina) then
   raise exception 'Nezadostna zaloga' using errcode='23514';
  end if;
  select sum(round(kolicina*cena_na_enoto*(1-popust),2)) into total from quoteflow.postavka_ponudbe where ponudba_id=new.id;
  if new.znesek_skupaj is distinct from total then raise exception 'Nepravilen znesek' using errcode='23514'; end if;
 end if; return new;
end $$;
create trigger preveri_ponudbo before insert or update or delete on quoteflow.ponudba for each row execute function quoteflow_private.preveri_ponudbo();

-- Every business table is private, RLS protected and read-only for ordinary sessions.
do $$ declare t text; begin
 foreach t in array array['uporabnik','podjetje','vloga_uporabnika','pravila_ponudnika','postavka_cenika','zaloga','povprasevanje','postavka_povprasevanja','ponudba','postavka_ponudbe'] loop
  execute format('alter table quoteflow.%I enable row level security',t);
  execute format('alter table quoteflow.%I force row level security',t);
  execute format('revoke all on quoteflow.%I from public, anon, authenticated, service_role, quoteflow_app',t);
  execute format('grant select on quoteflow.%I to authenticated',t);
 end loop;
end $$;
create policy read_own on quoteflow.uporabnik for select to authenticated using ((id=(select auth.uid()) and (select quoteflow_private.aktivna_seja())) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.podjetje for select to authenticated using (quoteflow_private.clan(id) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.vloga_uporabnika for select to authenticated using ((uporabnik_id=(select auth.uid()) and (select quoteflow_private.aktivna_seja())) or (select quoteflow_private.administrator()));
create policy read_own on quoteflow.pravila_ponudnika for select to authenticated using (quoteflow_private.clan(podjetje_id,'ponudnik'));
create policy read_own on quoteflow.postavka_cenika for select to authenticated using (quoteflow_private.clan(podjetje_id,'ponudnik'));
create policy read_own on quoteflow.zaloga for select to authenticated using (exists(select 1 from quoteflow.postavka_cenika c where c.id=postavka_cenika_id));
create policy read_own on quoteflow.povprasevanje for select to authenticated using (quoteflow_private.clan(podjetje_nabavnika_id,'nabavnik'));
create policy read_own on quoteflow.postavka_povprasevanja for select to authenticated using (exists(select 1 from quoteflow.povprasevanje r where r.id=povprasevanje_id));
-- Buyers must later use an explicit public projection; direct table reads never expose supplier costs.
create policy read_own on quoteflow.ponudba for select to authenticated using (quoteflow_private.clan(podjetje_ponudnika_id,'ponudnik'));
create policy read_own on quoteflow.postavka_ponudbe for select to authenticated using (exists(select 1 from quoteflow.ponudba p where p.id=ponudba_id));

-- Narrow administrative mutations; global role cannot be self-assigned through the API.
create function quoteflow_private.ustvari_podjetje(ime text) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare result quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 insert into quoteflow.podjetje(naziv) values(trim(ime)) returning * into result; return result;
end $$;
create function quoteflow_private.uredi_podjetje(target uuid,ime text,novo_stanje text) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare result quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 update quoteflow.podjetje set naziv=trim(ime),stanje=novo_stanje where id=target returning * into result;
 if not found then raise no_data_found; end if; return result;
end $$;
create function quoteflow_private.dodeli_vlogo(target uuid,podjetje uuid,naloga text) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare result quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 if naloga not in ('nabavnik','ponudnik') then raise check_violation; end if;
 if not exists(select 1 from quoteflow.podjetje where id=$2 and stanje='aktivno') then raise check_violation; end if;
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(target,$2,naloga)
 on conflict(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null do update set aktivna=true returning * into result;
 return result;
end $$;
create function quoteflow_private.aktiviraj_vlogo(target uuid,velja boolean) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare result quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 update quoteflow.vloga_uporabnika set aktivna=velja where id=target and vloga<>'administrator' returning * into result;
 if not found then raise no_data_found; end if; return result;
end $$;
revoke all on all functions in schema quoteflow_private from public,anon,authenticated,service_role,quoteflow_app;
grant execute on function quoteflow_private.aktivna_seja(),quoteflow_private.administrator(),quoteflow_private.clan(uuid,text),
 quoteflow_private.ustvari_podjetje(text),quoteflow_private.uredi_podjetje(uuid,text,text),
 quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.aktiviraj_vlogo(uuid,boolean) to authenticated;
comment on schema quoteflow is 'Ciljni model docs/03: uporabnik, podjetje, enotne vloge in poslovni tok RFQ. Auth identity preserved.';
