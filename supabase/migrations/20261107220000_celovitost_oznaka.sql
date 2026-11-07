-- Integrity memo hardening (G6 pre-review 2026-11-07). preveri_celovitost skipped its company-wide pass when the transaction-local
-- GUC quoteflow.cel_<company> was '1'. Any role can set such a GUC, so a caller able to run SQL could set it after a write and
-- suppress the deferred check; and projekt_ekipa cleared the team's company while the check keyed on the project's company, so an
-- earlier pass on the project's company hid a cross-company link. The mark now lives in quoteflow_private.preverjeno_podjetje
-- (forced RLS, no grants; only these definer triggers touch it), is valid only for the current transaction id, and projekt_ekipa
-- clears both companies. Rows roll back with savepoints exactly like the GUC did; one row per company at most, removed with it.
create table quoteflow_private.preverjeno_podjetje (
 podjetje_id uuid primary key references quoteflow.podjetje(id) on delete cascade, xid xid8 not null
);
alter table quoteflow_private.preverjeno_podjetje enable row level security;
alter table quoteflow_private.preverjeno_podjetje force row level security;
revoke all on quoteflow_private.preverjeno_podjetje from public,anon,authenticated,service_role,quoteflow_app;

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
 -- deletes the mark in zakleni_podjetje (a BEFORE trigger on every table carrying this one). Without it 20k izmere meant 20k full passes.
 if exists(select 1 from quoteflow_private.preverjeno_podjetje x where x.podjetje_id=company and x.xid=pg_current_xact_id()) then return null; end if;
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
 insert into quoteflow_private.preverjeno_podjetje(podjetje_id,xid) select company,pg_current_xact_id() where exists(select 1 from quoteflow.podjetje p where p.id=company)
 on conflict(podjetje_id) do update set xid=excluded.xid;
 return null;
end $$;

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
 delete from quoteflow_private.preverjeno_podjetje x where x.podjetje_id=company;
 -- preveri_celovitost keys projekt_ekipa on the project's company, so its mark must go as well.
 if tg_table_name='projekt_ekipa' then
  delete from quoteflow_private.preverjeno_podjetje x where x.podjetje_id=(select p.podjetje_id from quoteflow.projekt p where p.id=(d->>'projekt_id')::uuid);
 end if;
 if tg_table_name='clan_ekipe' and tg_op<>'DELETE' then
  select * into worker from quoteflow.vloga_uporabnika where id=(d->>'delavec_vloga_id')::uuid for share;
  if not found or worker.vloga<>'delavec' or not worker.aktivna or worker.podjetje_id is distinct from company then
   raise check_violation using message='Nov clan ekipe mora biti aktivni delavec istega podjetja'; end if;
 end if;
 if tg_op='DELETE' then return old; end if; return new;
end $$;
