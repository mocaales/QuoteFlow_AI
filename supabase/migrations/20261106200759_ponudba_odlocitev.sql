-- US-05 (#44) sending and deciding on a quote: a master sends a draft (poslji_ponudbo), which snapshots the project's current
-- items in one transaction (model v3): every postavka_projekta becomes a postavka_ponudbe with its totals written once as plain
-- columns, plus its izmere (izmera_ponudbe), the materials of its vrsta dela with current name, unit and price (material_ponudbe)
-- and its labour inputs (delo_ponudbe, mojster-only). Later changes to items, izmere, vrste dela, the catalogue or material prices
-- never alter a sent snapshot. The project's customer accepts or rejects the sent version (odgovori_ponudbo); acceptance creates
-- the draft invoice and moves the project to termin in the same transaction. Every successful action writes one row to the
-- private audit table dogodek_dokumenta.
-- QFP07 wrong phase or project already has an accepted quote · QFP10 not a draft · QFP11 not decidable (decided or superseded
-- by a newer sent version) · QFP12 expired or without validity (sending; accepting only, an expired quote may still be
-- rejected; "today" is the Europe/Ljubljana date) · QFP13 project without items · QFP26 an item without a positive izmera_skupaj ·
-- a quote of another project -> no_data_found (L-1) · QFP17 company inactive. Drafts, foreign projects and D9 callers (active
-- master/worker of the company) -> no_data_found. Lock order: podjetje -> projekt -> ponudba (then the project's items for share).
create table quoteflow_private.dogodek_dokumenta (
 id uuid primary key default gen_random_uuid(), podjetje_id uuid not null references quoteflow.podjetje(id), projekt_id uuid not null references quoteflow.projekt(id),
 ponudba_id uuid references quoteflow.ponudba(id), racun_id uuid references quoteflow.racun(id),
 dejanje text not null check(dejanje in ('poslana','sprejeta','zavrnjena','termin','izvedba_koncana','izdan','placan')),
 -- No foreign key: the audit trail outlives the account that acted. clock_timestamp orders actions within one transaction.
 izvajalec_id uuid not null, ob timestamptz not null default clock_timestamp()
);
create index dogodek_dokumenta_podjetje_idx on quoteflow_private.dogodek_dokumenta(podjetje_id);
create index dogodek_dokumenta_projekt_idx on quoteflow_private.dogodek_dokumenta(projekt_id,ob);
create index dogodek_dokumenta_ponudba_idx on quoteflow_private.dogodek_dokumenta(ponudba_id) where ponudba_id is not null;
create index dogodek_dokumenta_racun_idx on quoteflow_private.dogodek_dokumenta(racun_id) where racun_id is not null;
alter table quoteflow_private.dogodek_dokumenta enable row level security;
alter table quoteflow_private.dogodek_dokumenta force row level security;
revoke all on quoteflow_private.dogodek_dokumenta from public,anon,authenticated,service_role,quoteflow_app;

-- Same rules as before, except that expiry blocks only acceptance: a customer may still reject an expired quote.
create or replace function quoteflow_private.preveri_ponudbo() returns trigger language plpgsql security definer set search_path='' as $$
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
  if (new.stanje='sprejeta' and new.velja_do<quoteflow_private.danes()) or exists(select 1 from quoteflow.ponudba where projekt_id=new.projekt_id and razlicica>new.razlicica and stanje<>'osnutek') then raise check_violation; end if;
 elsif new.stanje not in ('osnutek','poslana') then raise check_violation;
 end if;
 if new.stanje='poslana' and not exists(select 1 from quoteflow.postavka_ponudbe where ponudba_id=new.id) then raise check_violation using message='Ponudba potrebuje postavko'; end if;
 return new;
end $$;

drop function quoteflow_private.poslji_ponudbo(uuid);
drop function quoteflow_private.odgovori_ponudbo(uuid,boolean);

create function quoteflow_private.poslji_ponudbo(podjetje uuid,projekt uuid,ponudba uuid) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; it record; line uuid; n integer:=0;
begin
 perform quoteflow_private.preveri_mojstra(poslji_ponudbo.podjetje);
 -- Scoped project then quote locks; foreign, missing and other-project quotes are the same no_data_found; not a draft ->
 -- QFP10; accepted quote or wrong phase -> QFP07. The project lock also serialises against item and izmera writes.
 r:=quoteflow_private.preveri_osnutek(poslji_ponudbo.podjetje,poslji_ponudbo.projekt,poslji_ponudbo.ponudba);
 if not exists(select 1 from quoteflow.postavka_projekta x where x.projekt_id=r.projekt_id) then
  raise exception 'Projekt nima postavk' using errcode='QFP13'; end if;
 if exists(select 1 from quoteflow.postavka_projekta x where x.projekt_id=r.projekt_id and x.izmera_skupaj<=0) then
  raise exception 'Vsaka postavka mora imeti pozitivno količino izmer' using errcode='QFP26'; end if;
 if r.velja_do is null or r.velja_do<quoteflow_private.danes() then raise exception 'Veljavnost ponudbe je potekla' using errcode='QFP12'; end if;
 for it in select x.*,v.naziv as vrsta_naziv from quoteflow.postavka_projekta x join quoteflow.vrsta_dela v on v.id=x.vrsta_dela_id
  where x.projekt_id=r.projekt_id order by x.zaporedje for share of x,v loop
  n:=n+1;
  insert into quoteflow.postavka_ponudbe(ponudba_id,postavka_cenika_id,zaporedje,naziv,opis,vrsta_dela,enota,cena_na_enoto,kolicina,popust,stopnja_ddv,izmera_skupaj,neto,koncna_cena)
  values(r.id,it.postavka_cenika_id,n,it.naziv,it.opis,it.vrsta_naziv,it.enota,it.cena_na_enoto,it.kolicina,it.popust,it.stopnja_ddv,it.izmera_skupaj,it.neto,it.koncna_cena)
  returning id into line;
  insert into quoteflow.izmera_ponudbe(postavka_ponudbe_id,zaporedje,enota,odstej,kosi,dolzina,visina,sirina,vrednost)
  select line,row_number() over (order by i.zaporedje),i.enota,i.odstej,i.kosi,i.dolzina,i.visina,i.sirina,i.vrednost from quoteflow.izmera i where i.postavka_projekta_id=it.id;
  insert into quoteflow.delo_ponudbe(postavka_ponudbe_id,urna_postavka,stevilo_ur,stevilo_delavcev,cena_dela) values(line,it.urna_postavka,it.stevilo_ur,it.stevilo_delavcev,it.cena_dela);
  insert into quoteflow.material_ponudbe(postavka_ponudbe_id,material_id,naziv,enota,kolicina_na_enoto,cena_na_enoto)
  select line,m.id,m.naziv,m.enota,x.kolicina_na_enoto,m.cena_na_enoto from quoteflow.material_vrste_dela x join quoteflow.material m on m.id=x.material_id
  where x.vrsta_dela_id=it.vrsta_dela_id;
 end loop;
 update quoteflow.ponudba q set stanje='poslana',poslano_ob=now() where q.id=r.id returning * into r;
 update quoteflow.projekt p set faza='ponudba' where p.id=r.projekt_id and p.faza in ('pregled','ogled');
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,ponudba_id,dejanje,izvajalec_id) values(poslji_ponudbo.podjetje,r.projekt_id,r.id,'poslana',auth.uid());
 return r;
end $$;

create function quoteflow_private.odgovori_ponudbo(projekt uuid,ponudba uuid,sprejmi boolean) returns quoteflow.ponudba language plpgsql security definer set search_path='' as $$
declare r quoteflow.ponudba; company uuid; invoice uuid;
begin
 if sprejmi is null then raise null_value_not_allowed; end if;
 -- Drafts are invisible to the customer, so they are reported exactly like a missing or foreign quote.
 select p.podjetje_id into company from quoteflow.projekt p join quoteflow.ponudba q on q.projekt_id=p.id
 where p.id=odgovori_ponudbo.projekt and q.id=odgovori_ponudbo.ponudba and p.stranka_id=auth.uid() and q.stanje<>'osnutek' and quoteflow_private.stranka();
 if not found then raise no_data_found; end if;
 -- D9: a master or worker of the contractor must not decide on the contractor's own quote.
 if exists(select 1 from quoteflow.vloga_uporabnika v where v.uporabnik_id=auth.uid() and v.podjetje_id=company and v.vloga in ('mojster','delavec') and v.aktivna) then
  raise no_data_found; end if;
 -- Company first, as every write trigger does, then project and quote: no deadlock against a concurrent send.
 perform 1 from quoteflow.podjetje c where c.id=company and c.aktivno for update;
 if not found then raise exception 'Izvajalec trenutno ne posluje' using errcode='QFP17'; end if;
 perform 1 from quoteflow.projekt p where p.id=odgovori_ponudbo.projekt and p.stranka_id=auth.uid() for update;
 if not found then raise no_data_found; end if;
 select * into r from quoteflow.ponudba q where q.id=odgovori_ponudbo.ponudba and q.projekt_id=odgovori_ponudbo.projekt for update;
 if r.stanje<>'poslana' or exists(select 1 from quoteflow.ponudba q where q.projekt_id=r.projekt_id and q.razlicica>r.razlicica and q.stanje<>'osnutek') then
  raise exception 'O tej ponudbi ni več mogoče odločati' using errcode='QFP11'; end if;
 if sprejmi and r.velja_do<quoteflow_private.danes() then raise exception 'Veljavnost ponudbe je potekla' using errcode='QFP12'; end if;
 update quoteflow.ponudba q set stanje=case when sprejmi then 'sprejeta' else 'zavrnjena' end,odgovorjeno_ob=now() where q.id=r.id returning * into r;
 if sprejmi then
  insert into quoteflow.racun(ponudba_id) values(r.id) returning id into invoice;
  update quoteflow.projekt p set faza='termin' where p.id=r.projekt_id;
 end if;
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,ponudba_id,racun_id,dejanje,izvajalec_id)
 values(company,r.projekt_id,r.id,invoice,case when sprejmi then 'sprejeta' else 'zavrnjena' end,auth.uid());
 return r;
end $$;

revoke all on function quoteflow_private.poslji_ponudbo(uuid,uuid,uuid),quoteflow_private.odgovori_ponudbo(uuid,uuid,boolean) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.poslji_ponudbo(uuid,uuid,uuid),quoteflow_private.odgovori_ponudbo(uuid,uuid,boolean) to authenticated;
