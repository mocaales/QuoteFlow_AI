-- US-03–US-05: scoped supplier writes. Tables and existing RLS remain unchanged.
-- Serialize writes per company, and hold the role until commit so a concurrent
-- revocation/deactivation cannot be bypassed between authorization and mutation.
create function quoteflow_private.preveri_ponudnika(podjetje uuid) returns void
language plpgsql security definer set search_path='' as $$
begin
 if not quoteflow_private.aktivna_seja() then raise insufficient_privilege; end if;
 perform 1 from quoteflow.podjetje p join quoteflow.vloga_uporabnika v on v.podjetje_id=p.id
 where p.id=$1 and p.stanje='aktivno' and v.uporabnik_id=auth.uid() and v.vloga='ponudnik' and v.aktivna
 for update of p for share of v;
 if not found then raise insufficient_privilege; end if;
end $$;

create function quoteflow_private.shrani_cenik(
 podjetje uuid, target uuid, tip text, opis_v text, enota_v text,
 cena numeric, strosek numeric, rok integer, aktivna_v boolean
) returns quoteflow.postavka_cenika
language plpgsql security definer set search_path='' as $$
declare result quoteflow.postavka_cenika; previous quoteflow.postavka_cenika;
begin
 perform quoteflow_private.preveri_ponudnika(podjetje);
 if target is null then
  insert into quoteflow.postavka_cenika(podjetje_id,vrsta,opis,enota,cena_na_enoto,strosek_na_enoto,dobavni_rok_dni,aktivna)
  values(podjetje,tip,trim(opis_v),trim(enota_v),cena,strosek,rok,aktivna_v) returning * into result;
 else
  select * into previous from quoteflow.postavka_cenika where id=target and podjetje_id=podjetje for update;
  if not found then raise no_data_found; end if;
  -- A quantity in a different unit has no valid meaning. Switching to a service
  -- also removes the optional stock record; existing offer snapshots stay intact.
  if previous.enota<>trim(enota_v) or previous.vrsta<>tip then
   delete from quoteflow.zaloga where postavka_cenika_id=target;
  end if;
  update quoteflow.postavka_cenika set vrsta=tip,opis=trim(opis_v),enota=trim(enota_v),
   cena_na_enoto=cena,strosek_na_enoto=strosek,dobavni_rok_dni=rok,aktivna=aktivna_v,potrjeno_ob=null
   where id=target and podjetje_id=podjetje returning * into result;
 end if;
 return result;
end $$;

create function quoteflow_private.potrdi_cenik(podjetje uuid,target uuid) returns quoteflow.postavka_cenika
language plpgsql security definer set search_path='' as $$
declare result quoteflow.postavka_cenika;
begin
 perform quoteflow_private.preveri_ponudnika(podjetje);
 select * into result from quoteflow.postavka_cenika where id=target and podjetje_id=podjetje for update;
 if not found then raise no_data_found; end if;
 if not result.aktivna then raise check_violation; end if;
 update quoteflow.postavka_cenika set potrjeno_ob=clock_timestamp() where id=target returning * into result;
 return result;
end $$;

create function quoteflow_private.shrani_zalogo(podjetje uuid,target uuid,kolicina numeric) returns void
language plpgsql security definer set search_path='' as $$
declare item quoteflow.postavka_cenika;
begin
 perform quoteflow_private.preveri_ponudnika(podjetje);
 select * into item from quoteflow.postavka_cenika where id=target and podjetje_id=podjetje for update;
 if not found then raise no_data_found; end if;
 if item.vrsta<>'blago' then raise check_violation; end if;
 if kolicina is null then
  delete from quoteflow.zaloga where postavka_cenika_id=target;
 else
  if not item.aktivna then raise check_violation; end if;
  insert into quoteflow.zaloga(postavka_cenika_id,razpolozljiva_kolicina,potrjeno_ob)
  values(target,kolicina,clock_timestamp()) on conflict(postavka_cenika_id)
  do update set razpolozljiva_kolicina=excluded.razpolozljiva_kolicina,potrjeno_ob=excluded.potrjeno_ob;
 end if;
end $$;

create function quoteflow_private.nova_pravila(
 podjetje uuid,marza numeric,popust numeric,rok integer,zacetek timestamptz,konec timestamptz
) returns quoteflow.pravila_ponudnika
language plpgsql security definer set search_path='' as $$
declare result quoteflow.pravila_ponudnika; starts timestamptz;
begin
 perform quoteflow_private.preveri_ponudnika(podjetje);
 starts:=coalesce(zacetek,clock_timestamp());
 if konec is not null and konec<=starts then raise check_violation; end if;
 -- No retroactive rewriting of business conditions.
 if zacetek is not null and zacetek<statement_timestamp() then raise check_violation; end if;
 -- A new version can finish its predecessor, but cannot overwrite a scheduled
 -- version. Exclusion constraint remains the final guard for every writer.
 if exists(select 1 from quoteflow.pravila_ponudnika where podjetje_id=podjetje
  and velja_od>=starts and tstzrange(velja_od,velja_do,'[)') && tstzrange(starts,konec,'[)')) then
  raise exclusion_violation;
 end if;
 update quoteflow.pravila_ponudnika set velja_do=starts where podjetje_id=podjetje
  and velja_od<starts and (velja_do is null or velja_do>starts);
 insert into quoteflow.pravila_ponudnika(podjetje_id,najmanjsa_marza,najvecji_popust,najdaljsi_rok_dni,velja_od,velja_do)
 values(podjetje,marza,popust,rok,starts,konec) returning * into result;
 return result;
end $$;

revoke all on function quoteflow_private.preveri_ponudnika(uuid),
 quoteflow_private.shrani_cenik(uuid,uuid,text,text,text,numeric,numeric,integer,boolean),
 quoteflow_private.potrdi_cenik(uuid,uuid),quoteflow_private.shrani_zalogo(uuid,uuid,numeric),
 quoteflow_private.nova_pravila(uuid,numeric,numeric,integer,timestamptz,timestamptz)
 from public,anon,authenticated,service_role,quoteflow_app;
-- The assertion helper is internal. Only narrow operations are executable.
grant execute on function
 quoteflow_private.shrani_cenik(uuid,uuid,text,text,text,numeric,numeric,integer,boolean),
 quoteflow_private.potrdi_cenik(uuid,uuid),quoteflow_private.shrani_zalogo(uuid,uuid,numeric),
 quoteflow_private.nova_pravila(uuid,numeric,numeric,integer,timestamptz,timestamptz) to authenticated;
