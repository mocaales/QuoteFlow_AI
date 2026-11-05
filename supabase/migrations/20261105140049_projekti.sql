-- US-03 (#38) project start: a master opens a project for a registered customer, edits it while in pregled/ogled
-- and requests an inspection (pregled -> ogled). QFP07 = action not allowed in the current phase. QFP08 = more than 20
-- creation attempts per company per rolling hour (successful and not-found alike, recorded in quoteflow_private.poskus_projekta,
-- serialised by the company row lock). Not-found returns a row with null id (API maps it to 409 with the QFP06 message);
-- unknown and inactive customers are indistinguishable, but an approved master can still confirm that an e-mail belongs to an
-- active customer: accepted residual risk bounded by the rate limit (user decision 2026-11-05). A master reads customer data only
-- via stranke_projektov; a customer gets only the name of a company with their project via naziv_podjetja.
create table quoteflow_private.poskus_projekta (podjetje_id uuid not null references quoteflow.podjetje(id) on delete cascade, ob timestamptz not null default now());
create index poskus_projekta_podjetje_ob_idx on quoteflow_private.poskus_projekta(podjetje_id,ob);
alter table quoteflow_private.poskus_projekta enable row level security;
alter table quoteflow_private.poskus_projekta force row level security;
revoke all on quoteflow_private.poskus_projekta from public,anon,authenticated,service_role,quoteflow_app;
create function quoteflow_private.ustvari_projekt(podjetje uuid,e_posta text,naziv text,opis text,lokacija text) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt; customer uuid;
begin
 perform quoteflow_private.preveri_mojstra(ustvari_projekt.podjetje);
 -- preveri_mojstra holds the company row lock (for update), so concurrent attempts of one company count serially.
 delete from quoteflow_private.poskus_projekta x where x.podjetje_id=ustvari_projekt.podjetje and x.ob<=now()-interval '1 hour';
 if (select count(*) from quoteflow_private.poskus_projekta x where x.podjetje_id=ustvari_projekt.podjetje and x.ob>now()-interval '1 hour')>=20 then
  raise exception 'Preveč poskusov ustvarjanja projektov' using errcode='QFP08'; end if;
 insert into quoteflow_private.poskus_projekta(podjetje_id) values(ustvari_projekt.podjetje);
 -- Lock order company -> master role -> customer role; the held role cannot be revoked before the insert commits.
 select u.id into customer from quoteflow.uporabnik u join quoteflow.vloga_uporabnika v on v.uporabnik_id=u.id
 where u.e_posta=lower(trim(ustvari_projekt.e_posta)) and v.vloga='stranka' and v.podjetje_id is null and v.aktivna for share of v;
 -- Unknown and inactive customers return the same all-null row; raising would roll back the recorded attempt.
 if not found then return r; end if;
 insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe,faza)
 values(ustvari_projekt.podjetje,customer,trim(ustvari_projekt.naziv),coalesce(trim(ustvari_projekt.opis),''),coalesce(trim(ustvari_projekt.lokacija),''),'pregled') returning * into r;
 return r;
end $$;
create function quoteflow_private.uredi_projekt(podjetje uuid,projekt uuid,naziv text,opis text,lokacija text) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(uredi_projekt.podjetje);
 select * into r from quoteflow.projekt p where p.id=uredi_projekt.projekt and p.podjetje_id=uredi_projekt.podjetje for update;
 if not found then raise no_data_found; end if;
 if r.faza not in ('pregled','ogled') then raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 update quoteflow.projekt p set naziv=trim(uredi_projekt.naziv),opis=coalesce(trim(uredi_projekt.opis),''),lokacija_izvedbe=coalesce(trim(uredi_projekt.lokacija),'')
 where p.id=r.id returning * into r;
 return r;
end $$;
create function quoteflow_private.zahtevaj_ogled(podjetje uuid,projekt uuid) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(zahtevaj_ogled.podjetje);
 select * into r from quoteflow.projekt p where p.id=zahtevaj_ogled.projekt and p.podjetje_id=zahtevaj_ogled.podjetje for update;
 if not found then raise no_data_found; end if;
 if r.faza<>'pregled' then raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 update quoteflow.projekt p set faza='ogled' where p.id=r.id returning * into r;
 return r;
end $$;

-- Customers of the company's projects, for its active masters only; replaces any direct read of quoteflow.uporabnik.
create function quoteflow_private.stranke_projektov(podjetje uuid) returns table(id uuid,e_posta text,ime text,priimek text) language sql stable security definer set search_path='' as $$
 select u.id,u.e_posta,u.ime,u.priimek from quoteflow.uporabnik u where quoteflow_private.clan($1,'mojster')
 and exists(select 1 from quoteflow.projekt p where p.podjetje_id=$1 and p.stranka_id=u.id)
$$;
-- Exposes only the company name to its members and customers of its projects, never the whole row.
create function quoteflow_private.naziv_podjetja(podjetje uuid) returns text language sql stable security definer set search_path='' as $$
 select c.naziv from quoteflow.podjetje c where c.id=$1 and quoteflow_private.aktivna_seja() and (quoteflow_private.clan(c.id)
 or (quoteflow_private.stranka() and exists(select 1 from quoteflow.projekt p where p.podjetje_id=c.id and p.stranka_id=auth.uid())))
$$;

revoke all on function quoteflow_private.ustvari_projekt(uuid,text,text,text,text),quoteflow_private.uredi_projekt(uuid,uuid,text,text,text),quoteflow_private.zahtevaj_ogled(uuid,uuid),
 quoteflow_private.stranke_projektov(uuid),quoteflow_private.naziv_podjetja(uuid) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.ustvari_projekt(uuid,text,text,text,text),quoteflow_private.uredi_projekt(uuid,uuid,text,text,text),quoteflow_private.zahtevaj_ogled(uuid,uuid),
 quoteflow_private.stranke_projektov(uuid),quoteflow_private.naziv_podjetja(uuid) to authenticated;
