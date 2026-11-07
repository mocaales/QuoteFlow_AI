-- Step 0 before US-04–US-07: the deferred document trigger keeps its semantics but checks only the changed row's project
-- (preveri_dokumente) instead of scanning every tenant on each write. The company-scoped preveri_celovitost, which also covers
-- the model v3 tables, is defined in 20261106100000_model_v3_postavke_izmere.sql.
-- D8/M-2: an administrator cannot give himself a company role by assigning or activating it, by creating a company he owns or
-- by approving his own master application (QFP22; rejecting it stays allowed). D9: a master cannot open a project for himself or for an
-- active master/worker of the same company; that customer is reported exactly like an unknown one (null row, API QFP06 409).
create or replace function quoteflow_private.preveri_dokumente() returns trigger language plpgsql security definer set search_path='' as $$
declare d jsonb; project uuid;
begin
 d:=case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
 case tg_table_name
 when 'projekt' then project:=(d->>'id')::uuid;
 when 'ponudba' then project:=(d->>'projekt_id')::uuid;
 when 'racun' then select q.projekt_id into project from quoteflow.ponudba q where q.id=(d->>'ponudba_id')::uuid;
 end case;
 if project is null then return null; end if;
 if exists(select 1 from quoteflow.ponudba q join quoteflow.projekt p on p.id=q.projekt_id where q.projekt_id=project and q.stanje='sprejeta' and
 (p.faza not in ('termin','izvedba','obracun','zakljucen') or not exists(select 1 from quoteflow.racun r where r.ponudba_id=q.id)))
 or exists(select 1 from quoteflow.racun r join quoteflow.ponudba q on q.id=r.ponudba_id join quoteflow.projekt p on p.id=q.projekt_id where q.projekt_id=project and
 (q.stanje<>'sprejeta' or (r.stanje_dokumenta='izdan' and p.faza not in ('obracun','zakljucen')) or (r.placano_ob is not null and p.faza<>'zakljucen'))) then
  raise exception 'Dokumenti in faza projekta morajo biti usklajeni v isti transakciji' using errcode='23514'; end if;
 return null;
end $$;

create or replace function quoteflow_private.dodeli_vlogo(target uuid,podjetje uuid,naloga text) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.administrator() then
  if naloga<>'delavec' or podjetje is null then raise insufficient_privilege; end if;
  perform quoteflow_private.preveri_mojstra(podjetje);
 elsif target=auth.uid() and naloga in ('mojster','delavec') then
  -- An administrator must not grant himself access to a company's business data.
  raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22';
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

create or replace function quoteflow_private.ustvari_projekt(podjetje uuid,e_posta text,naziv text,opis text,lokacija text) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt; customer uuid;
begin
 perform quoteflow_private.preveri_mojstra(ustvari_projekt.podjetje);
 -- preveri_mojstra holds the company row lock (for update), so concurrent attempts of one company count serially.
 delete from quoteflow_private.poskus_projekta x where x.podjetje_id=ustvari_projekt.podjetje and x.ob<=now()-interval '1 hour';
 if (select count(*) from quoteflow_private.poskus_projekta x where x.podjetje_id=ustvari_projekt.podjetje and x.ob>now()-interval '1 hour')>=20 then
  raise exception 'Preveč poskusov ustvarjanja projektov' using errcode='QFP08'; end if;
 insert into quoteflow_private.poskus_projekta(podjetje_id) values(ustvari_projekt.podjetje);
 -- Lock order company -> master role -> customer role. Role grants also lock the company row, so the D9 exclusion
 -- (self, or an active master/worker of this company) cannot change before the insert commits.
 select u.id into customer from quoteflow.uporabnik u join quoteflow.vloga_uporabnika v on v.uporabnik_id=u.id
 where u.e_posta=lower(trim(ustvari_projekt.e_posta)) and v.vloga='stranka' and v.podjetje_id is null and v.aktivna and u.id<>auth.uid()
 and not exists(select 1 from quoteflow.vloga_uporabnika w where w.uporabnik_id=u.id and w.podjetje_id=ustvari_projekt.podjetje and w.vloga in ('mojster','delavec') and w.aktivna)
 for share of v;
 -- Unknown, inactive and excluded customers return the same all-null row; raising would roll back the recorded attempt.
 if not found then return r; end if;
 insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe,faza)
 values(ustvari_projekt.podjetje,customer,trim(ustvari_projekt.naziv),coalesce(trim(ustvari_projekt.opis),''),coalesce(trim(ustvari_projekt.lokacija),''),'pregled') returning * into r;
 return r;
end $$;

create or replace function quoteflow_private.ustvari_podjetje(lastnik uuid,ime text,maticna text,davcna text,naslov_v text) returns quoteflow.podjetje language plpgsql security definer set search_path='' as $$
declare r quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 -- The owner receives an active mojster role, so an administrator must not be the owner (M-2).
 if lastnik=auth.uid() then raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22'; end if;
 if not exists(select 1 from auth.users where id=lastnik and email_confirmed_at is not null) then raise check_violation; end if;
 insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,davcna_stevilka,naslov) values(lastnik,trim(ime),trim(maticna),nullif(trim(davcna),''),trim(naslov_v)) returning * into r;
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(lastnik,r.id,'mojster'); return r;
end $$;

create or replace function quoteflow_private.aktiviraj_vlogo(target uuid,velja boolean) returns quoteflow.vloga_uporabnika language plpgsql security definer set search_path='' as $$
declare r quoteflow.vloga_uporabnika;
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 select * into r from quoteflow.vloga_uporabnika where id=target;
 if not found then raise no_data_found; end if;
 if r.vloga='admin' then raise insufficient_privilege; end if;
 if not quoteflow_private.administrator() then
  if r.vloga<>'delavec' then raise insufficient_privilege; end if;
  perform quoteflow_private.preveri_mojstra(r.podjetje_id);
 elsif velja and r.uporabnik_id=auth.uid() and r.vloga in ('mojster','delavec') then
  raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22';
 end if;
 if r.podjetje_id is not null then
  perform 1 from quoteflow.podjetje where id=r.podjetje_id for update;
 end if;
 if not velja and r.vloga='mojster' and exists(
  select 1 from quoteflow.podjetje where id=r.podjetje_id and lastnik_id=r.uporabnik_id
 ) then raise check_violation using message='Lastnik potrebuje aktivno vlogo mojster pri svojem podjetju'; end if;
 update quoteflow.vloga_uporabnika set aktivna=velja where id=target returning * into r; return r;
end $$;

create or replace function quoteflow_private.odloci_prosnjo(target uuid,odobri boolean) returns quoteflow.prosnja_mojstra language plpgsql security definer set search_path='' as $$
declare r quoteflow.prosnja_mojstra; p quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 select * into r from quoteflow.prosnja_mojstra where id=target for update;
 if not found then raise no_data_found; end if;
 if r.stanje<>'oddana' then raise exception 'Prošnja je že obravnavana' using errcode='QFP01'; end if;
 if odobri then
  if r.uporabnik_id=auth.uid() then raise exception 'Skrbnik si ne more sam dodeliti vloge v podjetju.' using errcode='QFP22'; end if;
  -- Same source of truth as ustvari_podjetje; the role row is held so it cannot be revoked mid-approval.
  if not exists(select 1 from auth.users where id=r.uporabnik_id and email_confirmed_at is not null) then
   raise exception 'Vlagatelj nima potrjene e-pošte' using errcode='QFP03'; end if;
  perform 1 from quoteflow.vloga_uporabnika where uporabnik_id=r.uporabnik_id and aktivna and vloga in ('stranka','delavec') for share;
  if not found then raise exception 'Vlagatelj nima aktivne vloge stranke ali delavca' using errcode='QFP03'; end if;
  if exists(select 1 from quoteflow.podjetje where maticna_stevilka=r.maticna_stevilka) then
   raise exception 'Matična številka je zasedena' using errcode='QFP04'; end if;
  p:=quoteflow_private.ustvari_podjetje(r.uporabnik_id,r.naziv_podjetja,r.maticna_stevilka,r.davcna_stevilka,r.naslov_podjetja);
 end if;
 update quoteflow.prosnja_mojstra set stanje=case when odobri then 'odobrena' else 'zavrnjena' end,podjetje_id=p.id,odlocil_id=auth.uid(),odloceno_ob=now() where id=target returning * into r; return r;
end $$;

revoke all on function quoteflow_private.preveri_dokumente() from public,anon,authenticated,service_role,quoteflow_app;
revoke all on function quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.ustvari_projekt(uuid,text,text,text,text),quoteflow_private.ustvari_podjetje(uuid,text,text,text,text),
 quoteflow_private.aktiviraj_vlogo(uuid,boolean),quoteflow_private.odloci_prosnjo(uuid,boolean) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.dodeli_vlogo(uuid,uuid,text),quoteflow_private.ustvari_projekt(uuid,text,text,text,text),quoteflow_private.ustvari_podjetje(uuid,text,text,text,text),
 quoteflow_private.aktiviraj_vlogo(uuid,boolean),quoteflow_private.odloci_prosnjo(uuid,boolean) to authenticated;
