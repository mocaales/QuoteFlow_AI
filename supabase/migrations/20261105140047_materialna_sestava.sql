-- US-02 (#35) material composition of a service item: a master adds, changes and removes active company materials
-- per unit of a catalogue item. QFP05 = inactive material cannot be added; a non-positive quantity hits the table check.
create function quoteflow_private.shrani_sestavo(podjetje uuid,postavka uuid,material uuid,kolicina numeric)
returns table(material_id uuid,sifra text,naziv text,enota text,aktiven boolean,kolicina_na_enoto numeric)
language plpgsql security definer set search_path='' as $$
declare m quoteflow.material; k numeric;
begin
 perform quoteflow_private.preveri_mojstra(shrani_sestavo.podjetje);
 perform 1 from quoteflow.postavka_cenika c where c.id=shrani_sestavo.postavka and c.podjetje_id=shrani_sestavo.podjetje for share;
 if not found then raise no_data_found; end if;
 if quoteflow_private.material_podjetje(shrani_sestavo.material) is distinct from shrani_sestavo.podjetje then raise no_data_found; end if;
 -- Held until commit so the material cannot be deactivated between this check and the upsert.
 select * into m from quoteflow.material x where x.id=shrani_sestavo.material for share;
 if not m.aktiven then raise exception 'Neaktivnega materiala ni mogoče dodati v sestavo' using errcode='QFP05'; end if;
 insert into quoteflow.sestava_cenika as s(postavka_cenika_id,material_id,kolicina_na_enoto) values(shrani_sestavo.postavka,m.id,shrani_sestavo.kolicina)
 on conflict on constraint sestava_cenika_pkey do update set kolicina_na_enoto=excluded.kolicina_na_enoto returning s.kolicina_na_enoto into k;
 return query select m.id,m.sifra,m.naziv,m.enota,m.aktiven,k;
end $$;
create function quoteflow_private.odstrani_sestavo(podjetje uuid,postavka uuid,material uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 perform quoteflow_private.preveri_mojstra(odstrani_sestavo.podjetje);
 perform 1 from quoteflow.postavka_cenika c where c.id=odstrani_sestavo.postavka and c.podjetje_id=odstrani_sestavo.podjetje for share;
 if not found then raise no_data_found; end if;
 if quoteflow_private.material_podjetje(odstrani_sestavo.material) is distinct from odstrani_sestavo.podjetje then raise no_data_found; end if;
 delete from quoteflow.sestava_cenika s where s.postavka_cenika_id=odstrani_sestavo.postavka and s.material_id=odstrani_sestavo.material;
 if not found then raise no_data_found; end if;
end $$;
revoke all on function quoteflow_private.shrani_sestavo(uuid,uuid,uuid,numeric),quoteflow_private.odstrani_sestavo(uuid,uuid,uuid) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.shrani_sestavo(uuid,uuid,uuid,numeric),quoteflow_private.odstrani_sestavo(uuid,uuid,uuid) to authenticated;
