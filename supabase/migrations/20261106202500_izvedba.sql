-- US-06 (#46) termin and execution: a master sets the termin of a project with an accepted quote (faza termin -> izvedba) and
-- may reschedule it in izvedba until the work is finished (D3); zakljuci_izvedbo records the finished work, faza stays izvedba.
-- Termin (D10): finite, do > od, at most 366 days long and starting at most 366 days after today (class 22 -> 422), start
-- not before today's Europe/Ljubljana midnight (QFP18). QFP07 wrong phase, no accepted quote or work already finished ·
-- QFP14 finishing before termin_od · QFP24 more than 10 termin changes per project per Ljubljana day (counted from the
-- audit rows). One audit row per success.
-- Lock order: podjetje (preveri_mojstra) -> projekt.
drop function quoteflow_private.doloci_termin(uuid,timestamptz,timestamptz);

create function quoteflow_private.doloci_termin(podjetje uuid,projekt uuid,od timestamptz,"do" timestamptz) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt; d0 timestamptz:=(date_trunc('day',now() at time zone 'Europe/Ljubljana') at time zone 'Europe/Ljubljana');
begin
 perform quoteflow_private.preveri_mojstra(doloci_termin.podjetje);
 select * into r from quoteflow.projekt p where p.id=doloci_termin.projekt and p.podjetje_id=doloci_termin.podjetje for update;
 if not found then raise no_data_found; end if;
 if not (r.faza='termin' or (r.faza='izvedba' and r.izvedba_koncana_ob is null))
 or not exists(select 1 from quoteflow.ponudba q where q.projekt_id=r.id and q.stanje='sprejeta') then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 if doloci_termin.od is null or doloci_termin."do" is null or not isfinite(doloci_termin.od) or not isfinite(doloci_termin."do") then
  raise invalid_parameter_value using message='Termin mora imeti končen začetek in konec'; end if;
 if doloci_termin."do"<=doloci_termin.od or doloci_termin."do">doloci_termin.od+interval '366 days' then
  raise invalid_parameter_value using message='Konec termina mora biti po začetku in največ 366 dni pozneje'; end if;
 if doloci_termin.od>d0+interval '366 days' then
  raise invalid_parameter_value using message='Termin se lahko začne največ 366 dni vnaprej'; end if;
 if doloci_termin.od<d0 then raise exception 'Termin se ne sme začeti v preteklosti' using errcode='QFP18'; end if;
 -- The project row lock above serialises this count.
 if (select count(*) from quoteflow_private.dogodek_dokumenta x where x.projekt_id=r.id and x.dejanje='termin' and x.ob>=d0)>=10 then
  raise exception 'Termin projekta je danes mogoče spremeniti največ 10-krat' using errcode='QFP24'; end if;
 update quoteflow.projekt p set termin_od=doloci_termin.od,termin_do=doloci_termin."do",faza='izvedba' where p.id=r.id returning * into r;
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,dejanje,izvajalec_id) values(r.podjetje_id,r.id,'termin',auth.uid());
 return r;
end $$;

create function quoteflow_private.zakljuci_izvedbo(podjetje uuid,projekt uuid) returns quoteflow.projekt language plpgsql security definer set search_path='' as $$
declare r quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(zakljuci_izvedbo.podjetje);
 select * into r from quoteflow.projekt p where p.id=zakljuci_izvedbo.projekt and p.podjetje_id=zakljuci_izvedbo.podjetje for update;
 if not found then raise no_data_found; end if;
 if r.faza<>'izvedba' or r.izvedba_koncana_ob is not null then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 if now()<r.termin_od then raise exception 'Izvedbe ni mogoče zaključiti pred začetkom termina' using errcode='QFP14'; end if;
 update quoteflow.projekt p set izvedba_koncana_ob=now() where p.id=r.id returning * into r;
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,dejanje,izvajalec_id) values(r.podjetje_id,r.id,'izvedba_koncana',auth.uid());
 return r;
end $$;

revoke all on function quoteflow_private.doloci_termin(uuid,uuid,timestamptz,timestamptz),quoteflow_private.zakljuci_izvedbo(uuid,uuid) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.doloci_termin(uuid,uuid,timestamptz,timestamptz),quoteflow_private.zakljuci_izvedbo(uuid,uuid) to authenticated;
