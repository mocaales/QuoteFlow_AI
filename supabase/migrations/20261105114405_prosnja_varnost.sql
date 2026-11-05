-- US-01 security fixes for prosnja_mojstra: one pending request per user, approval only for an eligible applicant,
-- explicit SQLSTATEs (QFP01 decided, QFP02 pending exists, QFP03 ineligible applicant, QFP04 maticna taken) mapped centrally by the API.
-- Fail loudly instead of silently resolving existing duplicates; an administrator must decide them first.
do $$ begin
 if exists(select 1 from quoteflow.prosnja_mojstra where stanje='oddana' group by uporabnik_id having count(*)>1) then
  raise exception 'Uporabnik ima več oddanih prošenj; pred migracijo jih obravnava administrator' using errcode='55000';
 end if;
end $$;
create unique index prosnja_uporabnik_oddana_uq on quoteflow.prosnja_mojstra(uporabnik_id) where stanje='oddana';

create or replace function quoteflow_private.oddaj_prosnjo(ime text,maticna text,davcna text,naslov_v text) returns quoteflow.prosnja_mojstra language plpgsql security definer set search_path='' as $$
declare r quoteflow.prosnja_mojstra;
begin
 if not quoteflow_private.aktivna_seja() or not exists(select 1 from quoteflow.vloga_uporabnika where uporabnik_id=auth.uid() and aktivna and vloga in ('stranka','delavec')) then raise insufficient_privilege; end if;
 -- Serialise submissions per user so the pending check is reliable; no key update keeps FK inserts unblocked.
 perform 1 from quoteflow.uporabnik where id=auth.uid() for no key update;
 if exists(select 1 from quoteflow.prosnja_mojstra where uporabnik_id=auth.uid() and stanje='oddana') then
  raise exception 'Uporabnik že ima oddano prošnjo' using errcode='QFP02'; end if;
 if exists(select 1 from quoteflow.podjetje where maticna_stevilka=trim(maticna))
  or exists(select 1 from quoteflow.prosnja_mojstra where maticna_stevilka=trim(maticna) and stanje='oddana') then
  raise exception 'Matična številka je zasedena' using errcode='QFP04'; end if;
 insert into quoteflow.prosnja_mojstra(uporabnik_id,naziv_podjetja,maticna_stevilka,davcna_stevilka,naslov_podjetja) values(auth.uid(),trim(ime),trim(maticna),nullif(trim(davcna),''),trim(naslov_v)) returning * into r; return r;
end $$;

create or replace function quoteflow_private.odloci_prosnjo(target uuid,odobri boolean) returns quoteflow.prosnja_mojstra language plpgsql security definer set search_path='' as $$
declare r quoteflow.prosnja_mojstra; p quoteflow.podjetje;
begin
 if not quoteflow_private.administrator() then raise insufficient_privilege; end if;
 select * into r from quoteflow.prosnja_mojstra where id=target for update;
 if not found then raise no_data_found; end if;
 if r.stanje<>'oddana' then raise exception 'Prošnja je že obravnavana' using errcode='QFP01'; end if;
 if odobri then
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

revoke all on function quoteflow_private.oddaj_prosnjo(text,text,text,text),quoteflow_private.odloci_prosnjo(uuid,boolean) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.oddaj_prosnjo(text,text,text,text),quoteflow_private.odloci_prosnjo(uuid,boolean) to authenticated;
