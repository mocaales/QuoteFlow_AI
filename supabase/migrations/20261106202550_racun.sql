-- US-07 (#49) invoice and payment: a master issues the project's draft invoice after the finished work (number R-YYYY-NNN per
-- company per year; issuer snapshot from podjetje, recipient name and address entered by the master, trimmed, D4/D6) and
-- records its payment, which closes the project. Issued invoices stay immutable (preveri_racun) and a check keeps their
-- issuer and recipient non-blank. QFP07 wrong phase, no draft, already issued or paid · QFP15 company without tax number ·
-- QFP21 due date before today · blank/null recipient, name over 200 or address over 300 chars, due date over today+366 ->
-- 22023. "Today" and the number year use the Europe/Ljubljana date. One audit row per success.
-- L-9: the snapshots are text copies; every foreign key to auth.users/uporabnik is restrict/no action, so deleting an account
-- can never alter or cascade into quotes, invoices or projects. Lock order: podjetje (preveri_mojstra) -> projekt -> racun.
drop function quoteflow_private.izdaj_racun(uuid,text,text,text,date);
drop function quoteflow_private.placaj_racun(uuid);

alter table quoteflow.racun add constraint racun_izdan_neprazen check(stanje_dokumenta<>'izdan' or (trim(both from prejemnik_naziv)<>''
 and trim(both from prejemnik_naslov)<>'' and trim(both from izdajatelj_naziv)<>'' and trim(both from izdajatelj_davcna)<>''));

create function quoteflow_private.izdaj_racun(podjetje uuid,projekt uuid,prejemnik_naziv text,prejemnik_naslov text,zapade date) returns quoteflow.racun language plpgsql security definer set search_path='' as $$
declare r quoteflow.racun; p quoteflow.projekt; c quoteflow.podjetje; rec_ime text:=trim(izdaj_racun.prejemnik_naziv); rec_naslov text:=trim(izdaj_racun.prejemnik_naslov); n integer; y text;
begin
 perform quoteflow_private.preveri_mojstra(izdaj_racun.podjetje);
 select * into p from quoteflow.projekt x where x.id=izdaj_racun.projekt and x.podjetje_id=izdaj_racun.podjetje for update;
 if not found then raise no_data_found; end if;
 select i.* into r from quoteflow.racun i join quoteflow.ponudba q on q.id=i.ponudba_id where q.projekt_id=p.id and q.stanje='sprejeta' for update of i;
 if p.faza<>'izvedba' or p.izvedba_koncana_ob is null or r.id is null or r.stanje_dokumenta<>'osnutek' then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 select * into c from quoteflow.podjetje x where x.id=p.podjetje_id;
 if nullif(trim(c.davcna_stevilka),'') is null then raise exception 'Podjetje nima davčne številke' using errcode='QFP15'; end if;
 if coalesce(rec_ime,'')='' or coalesce(rec_naslov,'')='' or length(rec_ime)>200 or length(rec_naslov)>300 then
  raise invalid_parameter_value using message='Vnesite ime in naslov prejemnika'; end if;
 if izdaj_racun.zapade is null then raise null_value_not_allowed; end if;
 if izdaj_racun.zapade<quoteflow_private.danes() then raise exception 'Rok plačila ne sme biti pred datumom izdaje' using errcode='QFP21'; end if;
 if izdaj_racun.zapade>quoteflow_private.danes()+366 then raise invalid_parameter_value using message='Rok plačila je lahko največ 366 dni po izdaji'; end if;
 -- The company row lock held by preveri_mojstra serialises numbering within a company.
 y:=extract(year from quoteflow_private.danes())::text;
 select coalesce(max(split_part(i.stevilka,'-',3)::integer),0)+1 into n from quoteflow.racun i join quoteflow.ponudba q on q.id=i.ponudba_id
 join quoteflow.projekt x on x.id=q.projekt_id where x.podjetje_id=p.podjetje_id and i.stevilka ~ ('^R-'||y||'-[0-9]{1,9}$');
 update quoteflow.racun i set stanje_dokumenta='izdan',stevilka='R-'||y||'-'||lpad(n::text,greatest(3,length(n::text)),'0'),
 izdajatelj_naziv=c.naziv,izdajatelj_naslov=c.naslov,izdajatelj_davcna=trim(c.davcna_stevilka),prejemnik_naziv=rec_ime,prejemnik_naslov=rec_naslov,
 izdan_ob=now(),poslan_ob=now(),zapade_dne=izdaj_racun.zapade where i.id=r.id returning * into r;
 update quoteflow.projekt x set faza='obracun' where x.id=p.id;
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,ponudba_id,racun_id,dejanje,izvajalec_id) values(p.podjetje_id,p.id,r.ponudba_id,r.id,'izdan',auth.uid());
 return r;
end $$;

create function quoteflow_private.placaj_racun(podjetje uuid,projekt uuid) returns quoteflow.racun language plpgsql security definer set search_path='' as $$
declare r quoteflow.racun; p quoteflow.projekt;
begin
 perform quoteflow_private.preveri_mojstra(placaj_racun.podjetje);
 select * into p from quoteflow.projekt x where x.id=placaj_racun.projekt and x.podjetje_id=placaj_racun.podjetje for update;
 if not found then raise no_data_found; end if;
 select i.* into r from quoteflow.racun i join quoteflow.ponudba q on q.id=i.ponudba_id where q.projekt_id=p.id and q.stanje='sprejeta' for update of i;
 if p.faza<>'obracun' or r.id is null or r.stanje_dokumenta<>'izdan' or r.placano_ob is not null then
  raise exception 'V tej fazi projekta to dejanje ni dovoljeno' using errcode='QFP07'; end if;
 update quoteflow.racun i set placano_ob=now() where i.id=r.id returning * into r;
 update quoteflow.projekt x set faza='zakljucen',zakljuceno_ob=now() where x.id=p.id;
 insert into quoteflow_private.dogodek_dokumenta(podjetje_id,projekt_id,ponudba_id,racun_id,dejanje,izvajalec_id) values(p.podjetje_id,p.id,r.ponudba_id,r.id,'placan',auth.uid());
 return r;
end $$;

revoke all on function quoteflow_private.izdaj_racun(uuid,uuid,text,text,date),quoteflow_private.placaj_racun(uuid,uuid) from public,anon,service_role,quoteflow_app;
grant execute on function quoteflow_private.izdaj_racun(uuid,uuid,text,text,date),quoteflow_private.placaj_racun(uuid,uuid) to authenticated;
