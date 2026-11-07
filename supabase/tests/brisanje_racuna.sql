-- Account deletion vs role audit (#104 tombstoning): a confirmed user with role events (as target and as actor) and decided
-- invitations can be deleted; the audit rows stay with the person nulled. A customer with a project (and therefore any quote or
-- invoice) stays non-deletable. Seeds inside one transaction and rolls back. Local Supabase only.
begin;

do $$ declare
 o uuid:=gen_random_uuid(); w uuid:=gen_random_uuid(); s uuid:=gen_random_uuid(); x uuid:=gen_random_uuid(); firma uuid; vw uuid;
 pin uuid; pout uuid; n bigint;
begin
 insert into auth.users(id,email,email_confirmed_at) values(o,'lastnik-'||o||'@example.test',now()),(w,'delavec-'||w||'@example.test',now()),
  (s,'stranka-'||s||'@example.test',now()),(x,'drugi-'||x||'@example.test',now());
 insert into quoteflow.podjetje(lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values(o,'Brisanje',left(replace(o::text,'-',''),30),'Naslov 1','SI12345678') returning id into firma;
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(o,firma,'mojster');
 insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values(w,firma,'delavec') returning id into vw;
 -- w accepted an invitation from o, and w (later mojster elsewhere) invited x, who declined.
 insert into quoteflow_private.povabilo_delavca(podjetje_id,e_posta,povabil_id,stanje,odloceno_ob,vloga_id)
  values(firma,'delavec-'||w||'@example.test',o,'sprejeto',now(),vw) returning id into pin;
 insert into quoteflow_private.povabilo_delavca(podjetje_id,e_posta,povabil_id,stanje,odloceno_ob)
  values(firma,'drugi-'||x||'@example.test',w,'zavrnjeno',now()) returning id into pout;
 insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,aktivna_prej,aktivna_potem) values(o,w,firma,'delavec',null,true),(w,x,firma,'delavec',null,true);
 insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,dejanje,povabilo_id) values(w,w,firma,'delavec','sprejeto',pin),(w,null,firma,'delavec','povabljen',pout);
 insert into quoteflow.projekt(podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values(firma,s,'Prenova','Opis','Maribor');

 -- Same deletion sequence as before the audit table existed: roles, profile, then the Auth account.
 delete from quoteflow.vloga_uporabnika where uporabnik_id=w;
 delete from quoteflow.uporabnik where id=w;
 delete from auth.users where id=w;
 if exists(select 1 from auth.users where id=w) or exists(select 1 from quoteflow.uporabnik where id=w) then raise exception 'Delavec ni izbrisan.'; end if;

 select count(*) into n from quoteflow_private.dogodek_vloge where podjetje_id=firma or (podjetje_id is null and uporabnik_id is null);
 if n<>5 then raise exception 'Dogodki vlog morajo ostati (5), ostalo jih je %.',n; end if;
 if exists(select 1 from quoteflow_private.dogodek_vloge where w in (izvajalec_id,uporabnik_id)) then raise exception 'Dogodki še kažejo na izbrisano osebo.'; end if;
 if (select count(*) from quoteflow_private.dogodek_vloge where podjetje_id=firma and izvajalec_id is null)<>3 then raise exception 'Izvajalec ni anonimiziran.'; end if;
 if not exists(select 1 from quoteflow_private.dogodek_vloge where podjetje_id=firma and dejanje='vloga' and izvajalec_id=o and uporabnik_id is null and aktivna_potem)
  then raise exception 'Ciljni uporabnik ni anonimiziran.'; end if;
 if (select povabil_id from quoteflow_private.povabilo_delavca where id=pout) is not null
  or not exists(select 1 from quoteflow_private.povabilo_delavca where id=pin and stanje='sprejeto' and vloga_id is null) then raise exception 'Povabila niso anonimizirana.'; end if;

 -- The insert-time invariant still holds: a role event needs its target.
 begin
  insert into quoteflow_private.dogodek_vloge(izvajalec_id,uporabnik_id,podjetje_id,vloga,aktivna_prej,aktivna_potem) values(o,null,firma,'delavec',null,true);
  raise exception 'Dogodek vloge brez uporabnika ne sme nastati.';
 exception when check_violation then null; end;

 -- Unchanged restriction: a customer with a project cannot be deleted (#104).
 delete from quoteflow.vloga_uporabnika where uporabnik_id=s;
 begin
  delete from quoteflow.uporabnik where id=s;
  raise exception 'Stranka s projektom ne sme biti izbrisana.';
 exception when foreign_key_violation then null; end;
 begin
  delete from auth.users where id=s;
  raise exception 'Auth račun stranke s projektom ne sme biti izbrisan.';
 exception when foreign_key_violation then null; end;
end $$;

select 'brisanje_racuna ok';
rollback;
