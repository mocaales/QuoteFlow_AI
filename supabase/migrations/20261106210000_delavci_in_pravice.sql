-- Admin "Podjetja in pravice" + US-08 with worker invitations (G1 decisions 13-19, controls A1-A11, G6 findings 1-4 and 11).
-- A master never grants a role directly: povabi_delavca stores an invitation in quoteflow_private.povabilo_delavca (forced RLS, no grants,
-- not part of the 22-table contract) and answers identically for every e-mail, so nobody can enumerate accounts. The invitee whose
-- confirmed auth e-mail matches sees it (moja_povabila) and accepts or declines it (odgovori_povabilo); acceptance re-checks every
-- eligibility rule and only then creates or reactivates the delavec role. Invitations expire after 14 Europe/Ljubljana days. Rate limit
-- quoteflow_private.poskus_delavca: 20/hour per company and 50/day per inviting master across companies (QFP30); ineligible answer QFP34.
-- dodeli_vlogo / aktiviraj_vlogo are admin-only and authorise before reading any row (finding 3); the admin path now also applies
-- D19 (customer of an open project of the company), active stranka and confirmed e-mail on grant and reactivation (finding 2).
-- Owner-protection QFP33, uredi_delavca / delavci_podjetja for accepted workers, potrjeni_uporabniki for administrators.
-- Audit quoteflow_private.dogodek_vloge records every role change, including the owner's mojster role from ustvari_podjetje and the
-- automatic stranka role from registration, plus invitation events (finding 4). Its user FKs are ON DELETE RESTRICT on purpose: deleting an
-- account with audit history fails until tombstoning/erasure and retention are implemented in #104.
-- postavka_cenika gets CHECKs cena_na_enoto <= 1 000 000 and trimmed naziv 1..200 (finding 11); existing rows outside the bounds make
-- this migration fail loudly (23514 with the row count) instead of being silently altered.
alter table quoteflow.vloga_uporabnika add dodeljeno_ob timestamptz not null default now();

-- Reactivation is a new assignment, whichever function performs it.
create function quoteflow_private.osvezi_dodelitev() returns trigger language plpgsql set search_path='' as $$
begin
 if new.aktivna and not old.aktivna then new.dodeljeno_ob:=now(); end if;
 return new;
end $$;
create trigger osvezi_dodelitev before update of aktivna on quoteflow.vloga_uporabnika for each row execute function quoteflow_private.osvezi_dodelitev();

create table quoteflow_private.povabilo_delavca (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id),
 e_posta text not null check(length(e_posta) between 3 and 254 and e_posta=lower(btrim(e_posta,E' \t\r\n'))),
 povabil_id uuid not null references quoteflow.uporabnik(id) on delete restrict,
 stanje text not null default 'povabljen' check(stanje in ('povabljen','sprejeto','zavrnjeno','preklicano','poteklo')),
 poslano_ob timestamptz not null default now(), odloceno_ob timestamptz, vloga_id uuid references quoteflow.vloga_uporabnika(id),
 check((stanje='povabljen')=(odloceno_ob is null)), check((stanje='sprejeto')=(vloga_id is not null))
);
create unique index povabilo_delavca_odprto_uidx on quoteflow_private.povabilo_delavca(podjetje_id,e_posta) where stanje='povabljen';
create index povabilo_delavca_podjetje_idx on quoteflow_private.povabilo_delavca(podjetje_id,poslano_ob);
create index povabilo_delavca_e_posta_idx on quoteflow_private.povabilo_delavca(e_posta) where stanje='povabljen';
create index povabilo_delavca_povabil_idx on quoteflow_private.povabilo_delavca(povabil_id);
create index povabilo_delavca_vloga_idx on quoteflow_private.povabilo_delavca(vloga_id) where vloga_id is not null;

create table quoteflow_private.dogodek_vloge (
 id uuid primary key default gen_random_uuid(), izvajalec_id uuid not null references quoteflow.uporabnik(id) on delete restrict,
 uporabnik_id uuid references quoteflow.uporabnik(id) on delete restrict, podjetje_id uuid references quoteflow.podjetje(id),
 vloga text not null check(vloga in ('admin','mojster','delavec','stranka')), aktivna_prej boolean, aktivna_potem boolean,
 dejanje text not null default 'vloga' check(dejanje in ('vloga','povabljen','sprejeto','zavrnjeno','preklicano')),
 povabilo_id uuid references quoteflow_private.povabilo_delavca(id), ob timestamptz not null default clock_timestamp(),
 check((dejanje='vloga')=(uporabnik_id is not null and aktivna_potem is not null and povabilo_id is null)), check(dejanje='vloga' or povabilo_id is not null)
);
create index dogodek_vloge_uporabnik_idx on quoteflow_private.dogodek_vloge(uporabnik_id,ob);
create index dogodek_vloge_podjetje_idx on quoteflow_private.dogodek_vloge(podjetje_id,ob);
create index dogodek_vloge_izvajalec_idx on quoteflow_private.dogodek_vloge(izvajalec_id);
create index dogodek_vloge_povabilo_idx on quoteflow_private.dogodek_vloge(povabilo_id) where povabilo_id is not null;
create table quoteflow_private.poskus_delavca (
 podjetje_id uuid not null references quoteflow.podjetje(id) on delete cascade, uporabnik_id uuid not null references quoteflow.uporabnik(id) on delete cascade,
 ob timestamptz not null default now()
);
create index poskus_delavca_podjetje_ob_idx on quoteflow_private.poskus_delavca(podjetje_id,ob);
create index poskus_delavca_uporabnik_ob_idx on quoteflow_private.poskus_delavca(uporabnik_id,ob);
alter table quoteflow_private.povabilo_delavca enable row level security;
alter table quoteflow_private.povabilo_delavca force row level security;
alter table quoteflow_private.dogodek_vloge enable row level security;
alter table quoteflow_private.dogodek_vloge force row level security;
alter table quoteflow_private.poskus_delavca enable row level security;
alter table quoteflow_private.poskus_delavca force row level security;
revoke all on quoteflow_private.povabilo_delavca,quoteflow_private.dogodek_vloge,quoteflow_private.poskus_delavca from public,anon,authenticated,service_role,quoteflow_app;

-- Finding 11: legacy rows outside the bounds must be fixed by hand, never clamped silently.
do $$ declare n bigint; begin
 select count(*) into n from quoteflow.postavka_cenika where cena_na_enoto>1000000 or length(trim(naziv)) not between 1 and 200;
 if n>0 then raise exception 'Cenik vsebuje % postavk s ceno nad 1000000 ali nazivom zunaj 1-200 znakov; popravite jih pred migracijo.',n using errcode='23514'; end if;
end $$;
alter table quoteflow.postavka_cenika add constraint postavka_cenika_cena_meja_check check(cena_na_enoto<=1000000),
 add constraint postavka_cenika_naziv_dolzina_check check(length(trim(naziv)) between 1 and 200);

create type quoteflow_private.delavec_podjetja as (id uuid,uporabnik_id uuid,e_posta text,ime text,priimek text,aktivna boolean,dodeljeno_ob timestamptz);
-- A composite result, because the e_posta parameter of povabi_delavca cannot share its name with an output column.
create type quoteflow_private.povabilo_odgovor as (id uuid,e_posta text,stanje text,poslano_ob timestamptz);

create function quoteflow_private.zabelezi_vlogo(prej boolean,r quoteflow.vloga_uporabnika) returns void language plpgsql set search_path='' as $$
begin
 if prej is distinct from r.aktivna then
  insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,aktivna_prej,aktivna_potem)
  values(auth.uid(),r.uporabnik_id,r.podjetje_id,r.vloga,prej,r.aktivna);
 end if;
end $$;

create function quoteflow_private.povabilo_potece(poslano timestamptz) returns timestamptz language sql immutable set search_path='' as $$
 select ((poslano at time zone 'Europe/Ljubljana')+interval '14 days') at time zone 'Europe/Ljubljana'
$$;

-- Rejects an active administrator, the customer of an open project of the company (D19) and anyone without an active global
-- stranka role and a confirmed e-mail, on every grant path. Called only from definer functions (reads auth.users). Callers hold the
-- company row lock, so the project condition cannot change before their write commits (project inserts and role grants lock it first).
create function quoteflow_private.zavrnjen_cilj(uporabnik uuid,podjetje uuid) returns boolean language sql stable set search_path='' as $$
 select exists(select 1 from quoteflow.vloga_uporabnika a where a.uporabnik_id=$1 and a.vloga='admin' and a.aktivna)
 or exists(select 1 from quoteflow.projekt p where p.podjetje_id=$2 and p.stranka_id=$1 and p.faza<>'zakljucen')
 or not exists(select 1 from quoteflow.vloga_uporabnika s join auth.users u on u.id=s.uporabnik_id
  where s.uporabnik_id=$1 and s.vloga='stranka' and s.podjetje_id is null and s.aktivna and u.email_confirmed_at is not null)
$$;

create function quoteflow_private.povabi_delavca(podjetje uuid,e_posta text) returns quoteflow_private.povabilo_odgovor language plpgsql security definer set search_path='' as $$
declare naslov text:=lower(btrim(povabi_delavca.e_posta,E' \t\r\n')); p quoteflow_private.povabilo_delavca; r quoteflow_private.povabilo_odgovor;
begin
 perform quoteflow_private.preveri_mojstra(povabi_delavca.podjetje);
 if naslov is null or length(naslov) not between 3 and 254 or naslov !~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' then
  raise invalid_parameter_value using message='Neveljaven e-poštni naslov.'; end if;
 -- Lock order podjetje -> uporabnik: the inviter row lock serialises his daily count across companies (no key update keeps FK inserts free).
 perform 1 from quoteflow.uporabnik u where u.id=auth.uid() for no key update;
 delete from quoteflow_private.poskus_delavca x where (x.podjetje_id=povabi_delavca.podjetje or x.uporabnik_id=auth.uid()) and x.ob<=now()-interval '1 day';
 if (select count(*) from quoteflow_private.poskus_delavca x where x.podjetje_id=povabi_delavca.podjetje and x.ob>now()-interval '1 hour')>=20
 or (select count(*) from quoteflow_private.poskus_delavca x where x.uporabnik_id=auth.uid() and x.ob>now()-interval '1 day')>=50 then
  raise exception 'Preveč povabil. Poskusite znova pozneje.' using errcode='QFP30'; end if;
 insert into quoteflow_private.poskus_delavca(podjetje_id,uporabnik_id) values(povabi_delavca.podjetje,auth.uid());
 update quoteflow_private.povabilo_delavca x set stanje='poteklo',odloceno_ob=quoteflow_private.povabilo_potece(x.poslano_ob)
 where x.podjetje_id=povabi_delavca.podjetje and x.e_posta=naslov and x.stanje='povabljen' and quoteflow_private.povabilo_potece(x.poslano_ob)<=now();
 -- Never resolves the address to an account: the answer is the same for every e-mail (A1).
 select x.* into p from quoteflow_private.povabilo_delavca x where x.podjetje_id=povabi_delavca.podjetje and x.e_posta=naslov and x.stanje='povabljen';
 if not found then
  insert into quoteflow_private.povabilo_delavca(podjetje_id,e_posta,povabil_id) values(povabi_delavca.podjetje,naslov,auth.uid()) returning * into p;
  insert into quoteflow_private.dogodek_vloge(izvajalec_id,podjetje_id,vloga,dejanje,povabilo_id) values(auth.uid(),p.podjetje_id,'delavec','povabljen',p.id);
 end if;
 r:=(p.id,p.e_posta,p.stanje,p.poslano_ob); return r;
end $$;

create function quoteflow_private.povabila_podjetja(podjetje uuid) returns table(id uuid,e_posta text,stanje text,poslano_ob timestamptz,odloceno_ob timestamptz)
language plpgsql stable security definer set search_path='' as $$
#variable_conflict use_column
begin
 if not quoteflow_private.clan(povabila_podjetja.podjetje,'mojster') then raise insufficient_privilege; end if;
 return query select x.id,x.e_posta,case when t.poteklo then 'poteklo' else x.stanje end,x.poslano_ob,case when t.poteklo then t.potece else x.odloceno_ob end
 from quoteflow_private.povabilo_delavca x
 cross join lateral (select quoteflow_private.povabilo_potece(x.poslano_ob) as potece,x.stanje='povabljen' and quoteflow_private.povabilo_potece(x.poslano_ob)<=now() as poteklo) t
 where x.podjetje_id=povabila_podjetja.podjetje and ((x.stanje='povabljen' and not t.poteklo) or coalesce(case when t.poteklo then t.potece end,x.odloceno_ob)>now()-interval '30 days')
 order by x.poslano_ob desc,x.id;
end $$;

create function quoteflow_private.preklici_povabilo(podjetje uuid,povabilo uuid) returns table(id uuid,e_posta text,stanje text,poslano_ob timestamptz,odloceno_ob timestamptz)
language plpgsql security definer set search_path='' as $$
#variable_conflict use_column
declare p quoteflow_private.povabilo_delavca;
begin
 perform quoteflow_private.preveri_mojstra(preklici_povabilo.podjetje);
 -- Foreign, unknown, decided and expired invitations are indistinguishable.
 select x.* into p from quoteflow_private.povabilo_delavca x where x.id=preklici_povabilo.povabilo and x.podjetje_id=preklici_povabilo.podjetje
 and x.stanje='povabljen' and quoteflow_private.povabilo_potece(x.poslano_ob)>now() for update;
 if not found then raise no_data_found; end if;
 update quoteflow_private.povabilo_delavca x set stanje='preklicano',odloceno_ob=now() where x.id=p.id returning x.* into p;
 insert into quoteflow_private.dogodek_vloge(izvajalec_id,podjetje_id,vloga,dejanje,povabilo_id) values(auth.uid(),p.podjetje_id,'delavec','preklicano',p.id);
 return query select p.id,p.e_posta,p.stanje,p.poslano_ob,p.odloceno_ob;
end $$;

create function quoteflow_private.moja_povabila() returns table(id uuid,podjetje_id uuid,podjetje_naziv text,povabil text,poslano_ob timestamptz)
language plpgsql stable security definer set search_path='' as $$
#variable_conflict use_column
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 return query select x.id,x.podjetje_id,c.naziv,btrim(concat_ws(' ',m.ime,m.priimek)),x.poslano_ob
 from auth.users a join quoteflow_private.povabilo_delavca x on x.e_posta=lower(btrim(a.email,E' \t\r\n')) and x.stanje='povabljen'
 join quoteflow.podjetje c on c.id=x.podjetje_id and c.aktivno join quoteflow.uporabnik m on m.id=x.povabil_id
 where a.id=auth.uid() and a.email_confirmed_at is not null and quoteflow_private.povabilo_potece(x.poslano_ob)>now()
 order by x.poslano_ob desc,x.id;
end $$;

create function quoteflow_private.odgovori_povabilo(povabilo uuid,sprejmi boolean) returns table(id uuid,stanje text) language plpgsql security definer set search_path='' as $$
#variable_conflict use_column
declare naslov text; potrjen timestamptz; firma uuid; p quoteflow_private.povabilo_delavca; v quoteflow.vloga_uporabnika; prej boolean;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 if odgovori_povabilo.sprejmi is null then raise null_value_not_allowed; end if;
 select a.email,a.email_confirmed_at into naslov,potrjen from auth.users a where a.id=auth.uid();
 -- Foreign and unknown ids are indistinguishable; the confirmation check comes after, as QFP34.
 select x.podjetje_id into firma from quoteflow_private.povabilo_delavca x where x.id=odgovori_povabilo.povabilo and x.e_posta=lower(btrim(naslov,E' \t\r\n'));
 if not found then raise no_data_found; end if;
 -- Lock order podjetje -> povabilo -> vloga, as on every other grant path.
 perform 1 from quoteflow.podjetje c where c.id=firma for update;
 select x.* into p from quoteflow_private.povabilo_delavca x where x.id=odgovori_povabilo.povabilo for update;
 if potrjen is null or p.stanje<>'povabljen' or quoteflow_private.povabilo_potece(p.poslano_ob)<=now()
 or (odgovori_povabilo.sprejmi and (not exists(select 1 from quoteflow.podjetje c where c.id=firma and c.aktivno) or quoteflow_private.zavrnjen_cilj(auth.uid(),firma))) then
  raise exception 'Povabila ni mogoče sprejeti.' using errcode='QFP34'; end if;
 if odgovori_povabilo.sprejmi then
  select x.aktivna into prej from quoteflow.vloga_uporabnika x where x.uporabnik_id=auth.uid() and x.podjetje_id=firma and x.vloga='delavec' for update;
  insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(auth.uid(),firma,'delavec')
  on conflict(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null do update set aktivna=true returning * into v;
  perform quoteflow_private.zabelezi_vlogo(prej,v);
  update quoteflow_private.povabilo_delavca x set stanje='sprejeto',odloceno_ob=now(),vloga_id=v.id where x.id=p.id returning x.* into p;
 else
  update quoteflow_private.povabilo_delavca x set stanje='zavrnjeno',odloceno_ob=now() where x.id=p.id returning x.* into p;
 end if;
 insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,dejanje,povabilo_id) values(auth.uid(),auth.uid(),firma,'delavec',p.stanje,p.id);
 return query select p.id,p.stanje;
end $$;

create function quoteflow_private.uredi_delavca(podjetje uuid,vloga uuid,aktivna boolean) returns quoteflow_private.delavec_podjetja language plpgsql security definer set search_path='' as $$
declare r quoteflow_private.delavec_podjetja; u quoteflow.uporabnik; v quoteflow.vloga_uporabnika; prej boolean;
begin
 perform quoteflow_private.preveri_mojstra(uredi_delavca.podjetje);
 if uredi_delavca.aktivna is null then raise null_value_not_allowed; end if;
 -- Foreign, master, global and random ids are indistinguishable (A5).
 select x.* into v from quoteflow.vloga_uporabnika x where x.id=uredi_delavca.vloga and x.podjetje_id=uredi_delavca.podjetje and x.vloga='delavec' for update;
 if not found then raise no_data_found; end if;
 if uredi_delavca.aktivna and quoteflow_private.zavrnjen_cilj(v.uporabnik_id,v.podjetje_id) then
  raise check_violation using message='Uporabniku ni mogoče dodeliti vloge v podjetju.'; end if;
 prej:=v.aktivna;
 update quoteflow.vloga_uporabnika x set aktivna=uredi_delavca.aktivna where x.id=v.id returning * into v;
 perform quoteflow_private.zabelezi_vlogo(prej,v);
 select x.* into u from quoteflow.uporabnik x where x.id=v.uporabnik_id;
 r:=(v.id,u.id,u.e_posta,u.ime,u.priimek,v.aktivna,v.dodeljeno_ob); return r;
end $$;

create function quoteflow_private.delavci_podjetja(podjetje uuid) returns setof quoteflow_private.delavec_podjetja language plpgsql stable security definer set search_path='' as $$
begin
 if not quoteflow_private.clan(delavci_podjetja.podjetje,'mojster') then raise insufficient_privilege; end if;
 return query select v.id,u.id,u.e_posta,u.ime,u.priimek,v.aktivna,v.dodeljeno_ob from quoteflow.vloga_uporabnika v join quoteflow.uporabnik u on u.id=v.uporabnik_id
 where v.podjetje_id=delavci_podjetja.podjetje and v.vloga='delavec' order by u.e_posta,v.id;
end $$;

create or replace function quoteflow_private.dodeli_vlogo(target uuid,podjetje uuid,naloga text) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika; prej boolean;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 -- An administrator must not grant himself access to a company's business data.
 if target=auth.uid() and naloga in ('mojster','delavec') then raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22'; end if;
 if naloga is null or naloga not in ('stranka','mojster','delavec') then raise check_violation; end if;
 if not exists(select 1 from auth.users where id=target and email_confirmed_at is not null) then raise check_violation; end if;
 if podjetje is not null then
  perform 1 from quoteflow.podjetje where id=$2 and aktivno for update;
  if not found then raise check_violation; end if;
  if naloga in ('mojster','delavec') and quoteflow_private.zavrnjen_cilj(target,podjetje) then
   raise check_violation using message='Uporabniku ni mogoče dodeliti vloge v podjetju.'; end if;
  select x.aktivna into prej from quoteflow.vloga_uporabnika x where x.uporabnik_id=target and x.podjetje_id=$2 and x.vloga=naloga for update;
  insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(target,podjetje,naloga)
  on conflict(uporabnik_id,podjetje_id,vloga) where podjetje_id is not null do update set aktivna=true returning * into r;
 else
  select x.aktivna into prej from quoteflow.vloga_uporabnika x where x.uporabnik_id=target and x.podjetje_id is null and x.vloga=naloga for update;
  insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(target,naloga)
  on conflict(uporabnik_id,vloga) where podjetje_id is null do update set aktivna=true returning * into r;
 end if;
 perform quoteflow_private.zabelezi_vlogo(prej,r);
 return r;
end $$;

create or replace function quoteflow_private.aktiviraj_vlogo(target uuid,velja boolean) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika; prej boolean;
begin
 -- Authorise before reading the row, so a non-administrator learns nothing about role ids.
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 if velja is null then raise null_value_not_allowed; end if;
 select * into r from quoteflow.vloga_uporabnika where id=target;
 if not found then raise no_data_found; end if;
 if r.vloga='admin' then raise insufficient_privilege; end if;
 if velja and r.uporabnik_id=auth.uid() and r.vloga in ('mojster','delavec') then
  raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22'; end if;
 -- Lock order company -> role row; re-read the row under both locks.
 if r.podjetje_id is not null then
  perform 1 from quoteflow.podjetje where id=r.podjetje_id for update;
 end if;
 select * into r from quoteflow.vloga_uporabnika where id=target for update;
 if not velja and r.vloga='mojster' and exists(select 1 from quoteflow.podjetje where id=r.podjetje_id and lastnik_id=r.uporabnik_id) then
  raise exception 'Lastniku podjetja ni mogoče odvzeti vloge mojster.' using errcode='QFP33'; end if;
 if velja then
  if not exists(select 1 from auth.users where id=r.uporabnik_id and email_confirmed_at is not null) then raise check_violation; end if;
  if r.podjetje_id is not null and quoteflow_private.zavrnjen_cilj(r.uporabnik_id,r.podjetje_id) then
   raise check_violation using message='Uporabniku ni mogoče dodeliti vloge v podjetju.'; end if;
 end if;
 prej:=r.aktivna;
 update quoteflow.vloga_uporabnika set aktivna=velja where id=target returning * into r;
 perform quoteflow_private.zabelezi_vlogo(prej,r);
 return r;
end $$;

create or replace function quoteflow_private.ustvari_podjetje(lastnik uuid,ime text,maticna text,davcna text,naslov_v text) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare r quoteflow.podjetje; v quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 -- The owner receives an active mojster role, so an administrator must not be the owner (M-2).
 if lastnik=auth.uid() then raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22'; end if;
 if not exists(select 1 from auth.users where id=lastnik and email_confirmed_at is not null) then raise check_violation; end if;
 insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,davcna_stevilka,naslov) values(lastnik,trim(ime),trim(maticna),nullif(trim(davcna),''),trim(naslov_v)) returning * into r;
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(lastnik,r.id,'mojster') returning * into v;
 perform quoteflow_private.zabelezi_vlogo(null,v); return r;
end $$;

-- Registration preserves identity only; system code grants stranka, never requested metadata roles. The grant is audited as the
-- user's own (self-registration, auth.uid() is not set in GoTrue's connection).
create or replace function quoteflow_private.sync_uporabnik() returns trigger language plpgsql security definer set search_path='' as $$
declare v quoteflow.vloga_uporabnika;
begin
 if new.email is not null and trim(new.email)<>'' then
  insert into quoteflow.uporabnik(id,e_posta,ime,priimek) values(new.id,lower(trim(new.email)),left(coalesce(new.raw_user_meta_data->>'ime',''),200),left(coalesce(new.raw_user_meta_data->>'priimek',''),200))
  on conflict(id) do update set e_posta=excluded.e_posta,ime=excluded.ime,priimek=excluded.priimek;
  if new.email_confirmed_at is not null then
   insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(new.id,'stranka') on conflict(uporabnik_id,vloga) where podjetje_id is null do nothing returning * into v;
   if v.id is not null then
    insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,aktivna_prej,aktivna_potem) values(new.id,new.id,null,'stranka',null,true);
   end if;
  end if;
 end if;
 return new;
end $$;

-- Admin user list: e-mail confirmation lives in auth.users, which authenticated cannot read.
create function quoteflow_private.potrjeni_uporabniki() returns table(id uuid,potrjen boolean) language plpgsql stable security definer set search_path='' as $$
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 return query select x.id,a.email_confirmed_at is not null from quoteflow.uporabnik x left join auth.users a on a.id=x.id order by x.id;
end $$;

revoke all on function quoteflow_private.osvezi_dodelitev(),quoteflow_private.zabelezi_vlogo(boolean,quoteflow.vloga_uporabnika),
 quoteflow_private.zavrnjen_cilj(uuid,uuid),quoteflow_private.povabilo_potece(timestamptz) from public,anon,authenticated,service_role,quoteflow_app;
revoke all on function quoteflow_private.povabi_delavca(uuid,text),quoteflow_private.povabila_podjetja(uuid),quoteflow_private.preklici_povabilo(uuid,uuid),
 quoteflow_private.moja_povabila(),quoteflow_private.odgovori_povabilo(uuid,boolean),quoteflow_private.uredi_delavca(uuid,uuid,boolean),quoteflow_private.delavci_podjetja(uuid),
 quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.aktiviraj_vlogo(uuid,boolean),quoteflow_private.potrjeni_uporabniki() from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.povabi_delavca(uuid,text),quoteflow_private.povabila_podjetja(uuid),quoteflow_private.preklici_povabilo(uuid,uuid),
 quoteflow_private.moja_povabila(),quoteflow_private.odgovori_povabilo(uuid,boolean),quoteflow_private.uredi_delavca(uuid,uuid,boolean),quoteflow_private.delavci_podjetja(uuid),
 quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.aktiviraj_vlogo(uuid,boolean),quoteflow_private.potrjeni_uporabniki() to authenticated;
