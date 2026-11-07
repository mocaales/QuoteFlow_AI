-- Non-destructive isolation check for the current model: 22 quoteflow tables (model v3) plus the US-08
-- audit/rate tables. Seeds two companies inside one transaction and rolls everything back.
-- Run against a local Supabase only. V1 -> V2 upgrade uses the frozen v2_upgrade_smoke.sql instead.
-- Full cases: backend/tests/test_*_database.py.
begin;

-- 1. Catalogue: exact table contract, forced RLS, grants, function ACL, archive.
do $$ declare
 expected text[]:=array['uporabnik','vloga_uporabnika','podjetje','prosnja_mojstra','projekt','ekipa','clan_ekipe','projekt_ekipa',
  'postavka_cenika','vrsta_materiala','material','zaloga','ponudba','postavka_ponudbe','material_ponudbe','racun',
  'vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'];
 private_tables text[]:=array['dogodek_vloge','poskus_delavca','povabilo_delavca','poskus_projekta','dogodek_dokumenta'];
 t text; r text; p text; extra text; missing text;
begin
 select string_agg(tablename,', ') into extra from pg_tables where schemaname='quoteflow' and tablename<>all(expected);
 select string_agg(e,', ') into missing from unnest(expected) e where not exists(select 1 from pg_tables where schemaname='quoteflow' and tablename=e);
 if extra is not null or missing is not null or (select count(*) from pg_tables where schemaname='quoteflow')<>22 then
  raise exception 'Expected exactly the 22 model v3 tables; unexpected: %, missing: %',coalesce(extra,'-'),coalesce(missing,'-');
 end if;
 select string_agg(c.relname,', ') into extra from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname in ('quoteflow','quoteflow_private') and c.relkind in ('r','p') and not (c.relrowsecurity and c.relforcerowsecurity);
 if extra is not null then raise exception 'RLS must be enabled and forced on: %',extra; end if;
 foreach t in array array['dogodek_vloge','poskus_delavca','povabilo_delavca'] loop
  if to_regclass('quoteflow_private.'||t) is null then raise exception 'Missing private table quoteflow_private.%',t; end if;
 end loop;
 foreach t in array expected loop
  foreach r in array array['anon','service_role','quoteflow_app'] loop
   continue when not exists(select 1 from pg_roles where rolname=r);
   foreach p in array array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] loop
    if has_table_privilege(r,'quoteflow.'||t,p) then raise exception '% must hold no privileges on quoteflow.%, has %',r,t,p; end if;
   end loop;
  end loop;
  if not has_table_privilege('authenticated','quoteflow.'||t,'SELECT') then raise exception 'authenticated must be able to SELECT quoteflow.% (through RLS)',t; end if;
  foreach p in array array['INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] loop
   if has_table_privilege('authenticated','quoteflow.'||t,p) then raise exception 'authenticated must only read quoteflow.%, has %',t,p; end if;
  end loop;
 end loop;
 foreach t in array private_tables loop
  continue when to_regclass('quoteflow_private.'||t) is null;
  foreach r in array array['anon','authenticated','service_role','quoteflow_app'] loop
   continue when not exists(select 1 from pg_roles where rolname=r);
   foreach p in array array['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'] loop
    if has_table_privilege(r,'quoteflow_private.'||t,p) then raise exception '% must hold no privileges on quoteflow_private.%, has %',r,t,p; end if;
   end loop;
  end loop;
 end loop;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='quoteflow_private' and has_function_privilege('anon',p.oid,'execute')) then
  raise exception 'Anonymous users must not execute business functions';
 end if;
 select string_agg(p.oid::regprocedure::text,', ') into extra from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='quoteflow_private' and exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee=0);
 if extra is not null then raise exception 'PUBLIC must not execute quoteflow_private functions: %',extra; end if;
 foreach t in array array['quoteflow_private.zavrnjen_cilj(uuid,uuid)','quoteflow_private.povabilo_potece(timestamptz)','quoteflow_private.osvezi_dodelitev()',
  'quoteflow_private.zabelezi_vlogo(boolean,quoteflow.vloga_uporabnika)','quoteflow_private.sync_uporabnik()'] loop
  if has_function_privilege('authenticated',t,'execute') then raise exception 'Internal helper % must not be executable by authenticated',t; end if;
 end loop;
 foreach t in array array['quoteflow_private.povabi_delavca(uuid,text)','quoteflow_private.povabila_podjetja(uuid)','quoteflow_private.preklici_povabilo(uuid,uuid)',
  'quoteflow_private.moja_povabila()','quoteflow_private.odgovori_povabilo(uuid,boolean)'] loop
  if not has_function_privilege('authenticated',t,'execute') then raise exception 'authenticated must execute %',t; end if;
 end loop;
 if pg_get_function_result('quoteflow_private.moja_povabila()'::regprocedure)
  <>'TABLE(id uuid, podjetje_id uuid, podjetje_naziv text, povabil text, poslano_ob timestamp with time zone)' then
  raise exception 'moja_povabila must expose only id, podjetje_id, podjetje_naziv, povabil, poslano_ob';
 end if;
 select string_agg(p.proname,', ') into extra from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='quoteflow_private' and p.prosecdef and not ('search_path=""'=any(coalesce(p.proconfig,'{}')));
 if extra is not null then raise exception 'Security definer functions need search_path='''': %',extra; end if;
 if has_schema_privilege('authenticated','quoteflow_legacy_20261103','usage')
 or has_schema_privilege('authenticated','quoteflow_private_legacy_20261103','usage')
 or has_schema_privilege('anon','quoteflow_legacy_20261103','usage')
 or has_schema_privilege('anon','quoteflow_private_legacy_20261103','usage') then
  raise exception 'The V1 archive must not be accessible to application users';
 end if;
end $$;

-- 2. Seed as the migration owner: A (owner_a, mojster2, worker), B (owner_b), a customer of A, an admin.
insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at)
select u::uuid,'tenant-iso-'||n||'-'||u||'@example.test','{"ime":"Ime","priimek":"Priimek"}'::jsonb,now() from (values
 ('0e5a0000-0000-4000-8000-000000000001','owner-a'),('0e5a0000-0000-4000-8000-000000000002','owner-b'),
 ('0e5a0000-0000-4000-8000-000000000003','mojster2'),('0e5a0000-0000-4000-8000-000000000004','worker'),
 ('0e5a0000-0000-4000-8000-000000000005','customer'),('0e5a0000-0000-4000-8000-000000000006','admin')) v(u,n);
insert into auth.sessions(id,user_id)
select ('0e5a0000-0000-4000-9000-00000000000'||i)::uuid,('0e5a0000-0000-4000-8000-00000000000'||i)::uuid from generate_series(1,6) i;
insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values('0e5a0000-0000-4000-8000-000000000006','admin');
insert into quoteflow.podjetje(id,lastnik_id,naziv,maticna_stevilka,naslov,davcna_stevilka) values
 ('0e5a0000-0000-4000-a000-00000000000a','0e5a0000-0000-4000-8000-000000000001','Izolacija A','TISO-A-'||left(md5(random()::text),20),'Naslov 1','SI12345678'),
 ('0e5a0000-0000-4000-a000-00000000000b','0e5a0000-0000-4000-8000-000000000002','Izolacija B','TISO-B-'||left(md5(random()::text),20),'Naslov 2','SI12345678');
insert into quoteflow.vloga_uporabnika(uporabnik_id,podjetje_id,vloga) values
 ('0e5a0000-0000-4000-8000-000000000001','0e5a0000-0000-4000-a000-00000000000a','mojster'),
 ('0e5a0000-0000-4000-8000-000000000002','0e5a0000-0000-4000-a000-00000000000b','mojster'),
 ('0e5a0000-0000-4000-8000-000000000003','0e5a0000-0000-4000-a000-00000000000a','mojster'),
 ('0e5a0000-0000-4000-8000-000000000004','0e5a0000-0000-4000-a000-00000000000a','delavec');
set constraints all immediate;
set constraints all deferred;
insert into quoteflow.projekt(id,podjetje_id,stranka_id,naziv,opis,lokacija_izvedbe) values
 ('0e5a0000-0000-4000-b000-000000000001','0e5a0000-0000-4000-a000-00000000000a','0e5a0000-0000-4000-8000-000000000005','Prenova','Opis','Maribor'),
 ('0e5a0000-0000-4000-b000-000000000002','0e5a0000-0000-4000-a000-00000000000a','0e5a0000-0000-4000-8000-000000000005','Kopalnica','Opis','Celje');
insert into quoteflow.vrsta_materiala(id,podjetje_id,naziv) values('0e5a0000-0000-4000-c000-000000000001','0e5a0000-0000-4000-a000-00000000000a','Lepila');
insert into quoteflow.material(id,vrsta_materiala_id,sifra,naziv,enota,cena_na_enoto) values
 ('0e5a0000-0000-4000-c000-000000000002','0e5a0000-0000-4000-c000-000000000001','LEP-1','Lepilo','kg',0.8);

-- 3. owner_a builds the v3 chain through the guarded functions (pinned G2 contract) and sends the quote.
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000001',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000001","session_id":"0e5a0000-0000-4000-9000-000000000001"}',true);
set local role authenticated;
do $$ declare
 a constant uuid:='0e5a0000-0000-4000-a000-00000000000a'; p constant uuid:='0e5a0000-0000-4000-b000-000000000001';
 va uuid; it uuid; q uuid; t text; n bigint;
begin
 select id into va from quoteflow_private.shrani_vrsto_dela(podjetje=>a,vrsta=>null::uuid,naziv=>'Polaganje ploščic'::text,opis=>'Keramika'::text,
  urna_postavka=>25::numeric,stevilo_ur=>8::numeric,stevilo_delavcev=>2,aktivna=>true);
 perform * from quoteflow_private.shrani_material_vrste(podjetje=>a,vrsta=>va,material=>'0e5a0000-0000-4000-c000-000000000002'::uuid,kolicina=>5::numeric);
 select id into it from quoteflow_private.shrani_postavko_projekta(podjetje=>a,projekt=>p,postavka=>null::uuid,vrsta_dela=>va,naziv=>'Polaganje'::text,
  opis=>'Keramika'::text,enota=>'m2'::text,cena=>10::numeric,kolicina=>1::numeric,popust=>0.1::numeric,stopnja_ddv=>0.22::numeric,
  urna_postavka=>null::numeric,stevilo_ur=>null::numeric,stevilo_delavcev=>null::integer);
 perform * from quoteflow_private.shrani_izmero(podjetje=>a,projekt=>p,postavka=>it,izmera=>null::uuid,odstej=>false,kosi=>1::numeric,
  dolzina=>5::numeric,visina=>4::numeric,sirina=>null::numeric);
 select id into q from quoteflow_private.ustvari_ponudbo(podjetje=>a,projekt=>p,velja_do=>(now() at time zone 'Europe/Ljubljana')::date+10);
 perform * from quoteflow_private.poslji_ponudbo(podjetje=>a,projekt=>p,ponudba=>q);
 -- Second project of the same customer keeps only an unsent draft.
 perform * from quoteflow_private.ustvari_ponudbo(podjetje=>a,projekt=>'0e5a0000-0000-4000-b000-000000000002'::uuid,
  velja_do=>(now() at time zone 'Europe/Ljubljana')::date+10);
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','postavka_ponudbe','izmera_ponudbe','delo_ponudbe','material_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n=0 then raise exception 'Positive control: the mojster of company A must see its own rows in %',t; end if;
 end loop;
end $$;
reset role;

-- 4. Authenticated without a session: nothing visible, no direct writes, no private tables.
select set_config('request.jwt.claim.sub','',true), set_config('request.jwt.claims','{}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['uporabnik','vloga_uporabnika','podjetje','prosnja_mojstra','projekt','ekipa','clan_ekipe','projekt_ekipa',
  'postavka_cenika','vrsta_materiala','material','zaloga','ponudba','postavka_ponudbe','material_ponudbe','racun',
  'vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'No session must mean no business data; % rows visible in %',n,t; end if;
 end loop;
 foreach t in array array['podjetje','vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  begin
   execute format('insert into quoteflow.%I default values',t);
   raise exception 'Direct insert into % unexpectedly allowed',t;
  exception when insufficient_privilege then null;
  end;
 end loop;
 foreach t in array array['dogodek_vloge','poskus_delavca','povabilo_delavca'] loop
  begin
   execute format('select count(*) from quoteflow_private.%I',t) into n;
   raise exception 'quoteflow_private.% must not be readable by authenticated',t;
  exception when insufficient_privilege then null;
  end;
 end loop;
end $$;
reset role;

-- 5. Mojster of company B sees none of A's catalogue, items, measurements or snapshots.
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000002',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000002","session_id":"0e5a0000-0000-4000-9000-000000000002"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe',
  'projekt','ponudba','postavka_ponudbe','material_ponudbe','material'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Mojster of company B sees % rows of company A in %',n,t; end if;
 end loop;
end $$;
reset role;

-- 6. Customer of A's project: sent lines and measurements yes; labour, materials, live items and catalogue never.
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000005',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000005","session_id":"0e5a0000-0000-4000-9000-000000000005"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['postavka_ponudbe','izmera_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n=0 then raise exception 'Positive control: the customer must see the sent quote rows in %',t; end if;
 end loop;
 foreach t in array array['postavka_projekta','izmera','vrsta_dela','material_vrste_dela','delo_ponudbe','material_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Customer must not read % (% rows visible, own project)',t,n; end if;
 end loop;
 if exists(select 1 from quoteflow.ponudba where projekt_id='0e5a0000-0000-4000-b000-000000000002' or stanje='osnutek') then
  raise exception 'Customer must not read a draft quote';
 end if;
end $$;
reset role;

-- 6b. Another customer (no project with A) sees nothing; A's customer loses the sent quote when his stranka role is revoked mid-session.
insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at)
 values('0e5a0000-0000-4000-8000-000000000007','tenant-iso-other-customer@example.test','{}'::jsonb,now());
insert into auth.sessions(id,user_id) values('0e5a0000-0000-4000-9000-000000000007','0e5a0000-0000-4000-8000-000000000007');
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000007',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000007","session_id":"0e5a0000-0000-4000-9000-000000000007"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['projekt','ponudba','postavka_ponudbe','izmera_ponudbe','racun'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Another customer must not read % of A (% rows)',t,n; end if;
 end loop;
end $$;
reset role;
update quoteflow.vloga_uporabnika set aktivna=false where uporabnik_id='0e5a0000-0000-4000-8000-000000000005' and vloga='stranka';
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000005',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000005","session_id":"0e5a0000-0000-4000-9000-000000000005"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['projekt','ponudba','postavka_ponudbe','izmera_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Customer with a revoked stranka role still reads % (% rows)',t,n; end if;
 end loop;
end $$;
reset role;
update quoteflow.vloga_uporabnika set aktivna=true where uporabnik_id='0e5a0000-0000-4000-8000-000000000005' and vloga='stranka';

-- 7. Worker of A (no team on the project) and the administrator: no costs, labour, items or snapshots.
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000004',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000004","session_id":"0e5a0000-0000-4000-9000-000000000004"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Worker must not read % (% rows visible)',t,n; end if;
 end loop;
end $$;
reset role;
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000006',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000006","session_id":"0e5a0000-0000-4000-9000-000000000006"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe',
  'ponudba','postavka_ponudbe','material_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Administrator must not read company costs or quotes in % (% rows visible)',t,n; end if;
 end loop;
end $$;
reset role;

-- 8. Role revoked mid-session: mojster2 sees A's catalogue, then loses it in the same session.
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000003',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000003","session_id":"0e5a0000-0000-4000-9000-000000000003"}',true);
set local role authenticated;
do $$ begin
 if not exists(select 1 from quoteflow.vrsta_dela) then raise exception 'Positive control: a second active mojster of A must see vrsta_dela'; end if;
end $$;
reset role;
update quoteflow.vloga_uporabnika set aktivna=false
 where uporabnik_id='0e5a0000-0000-4000-8000-000000000003' and podjetje_id='0e5a0000-0000-4000-a000-00000000000a' and vloga='mojster';
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Revoked mojster still reads % (% rows)',t,n; end if;
 end loop;
end $$;
reset role;

-- 8b. Worker invitations: only A's mojster lists or cancels A's invitations, the answer never depends on the address having an account,
-- and only the owner of the confirmed address sees and answers it.
insert into auth.users(id,email,raw_user_meta_data,email_confirmed_at)
 values('0e5a0000-0000-4000-8000-000000000008','tenant-iso-invitee@example.test','{}'::jsonb,now());
insert into auth.sessions(id,user_id) values('0e5a0000-0000-4000-9000-000000000008','0e5a0000-0000-4000-8000-000000000008');
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000001',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000001","session_id":"0e5a0000-0000-4000-9000-000000000001"}',true);
set local role authenticated;
do $$ declare a constant uuid:='0e5a0000-0000-4000-a000-00000000000a'; k quoteflow_private.povabilo_odgovor; u quoteflow_private.povabilo_odgovor; begin
 select * into k from quoteflow_private.povabi_delavca(podjetje=>a,e_posta=>' Tenant-Iso-Invitee@Example.test ');
 select * into u from quoteflow_private.povabi_delavca(podjetje=>a,e_posta=>'tenant-iso-nobody@example.test');
 if k.stanje<>'povabljen' or u.stanje<>'povabljen' or k.e_posta<>'tenant-iso-invitee@example.test' then
  raise exception 'An invitation must look the same for an existing account and an unknown address';
 end if;
 if (select count(*) from quoteflow_private.povabila_podjetja(podjetje=>a))<>2 then raise exception 'Positive control: A lists its two invitations'; end if;
 perform set_config('tenant_iso.povabilo',k.id::text,true);
end $$;
reset role;
do $$ begin
 if exists(select 1 from quoteflow.vloga_uporabnika where uporabnik_id='0e5a0000-0000-4000-8000-000000000008' and vloga<>'stranka') then
  raise exception 'Inviting must never grant a role';
 end if;
end $$;
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000002',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000002","session_id":"0e5a0000-0000-4000-9000-000000000002"}',true);
set local role authenticated;
do $$ declare a constant uuid:='0e5a0000-0000-4000-a000-00000000000a'; b constant uuid:='0e5a0000-0000-4000-a000-00000000000b';
 i constant uuid:=current_setting('tenant_iso.povabilo')::uuid; begin
 begin perform * from quoteflow_private.povabila_podjetja(podjetje=>a); raise exception 'Mojster of B lists invitations of A';
 exception when insufficient_privilege then null; end;
 begin perform * from quoteflow_private.preklici_povabilo(podjetje=>a,povabilo=>i); raise exception 'Mojster of B cancels an invitation of A';
 exception when insufficient_privilege then null; end;
 begin perform * from quoteflow_private.preklici_povabilo(podjetje=>b,povabilo=>i); raise exception 'Mojster of B cancels an invitation of A through B';
 exception when no_data_found then null; end;
 if exists(select 1 from quoteflow_private.povabila_podjetja(podjetje=>b)) then raise exception 'Invitations of A listed under B'; end if;
 if exists(select 1 from quoteflow_private.moja_povabila()) then raise exception 'Another address sees the invitation'; end if;
 begin perform * from quoteflow_private.odgovori_povabilo(povabilo=>i,sprejmi=>true); raise exception 'Another address answers the invitation';
 exception when no_data_found then null; end;
end $$;
reset role;
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000003',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000003","session_id":"0e5a0000-0000-4000-9000-000000000003"}',true);
set local role authenticated;
do $$ begin
 begin perform * from quoteflow_private.povabila_podjetja(podjetje=>'0e5a0000-0000-4000-a000-00000000000a'::uuid);
  raise exception 'Revoked mojster still lists invitations';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000008',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000008","session_id":"0e5a0000-0000-4000-9000-000000000008"}',true);
set local role authenticated;
do $$ declare i constant uuid:=current_setting('tenant_iso.povabilo')::uuid; begin
 if (select count(*) from quoteflow_private.moja_povabila() m where m.id=i and m.podjetje_naziv='Izolacija A')<>1
 or (select count(*) from quoteflow_private.moja_povabila())<>1 then raise exception 'The invitee must see exactly his own invitation'; end if;
 perform * from quoteflow_private.odgovori_povabilo(povabilo=>i,sprejmi=>true);
 if not quoteflow_private.clan('0e5a0000-0000-4000-a000-00000000000a','delavec') then raise exception 'Accepting must grant delavec in A'; end if;
end $$;
reset role;

-- 9. Expired session: owner_a with not_after in the past sees nothing.
update auth.sessions set not_after=now()-interval '1 second' where id='0e5a0000-0000-4000-9000-000000000001';
select set_config('request.jwt.claim.sub','0e5a0000-0000-4000-8000-000000000001',true),
 set_config('request.jwt.claims','{"sub":"0e5a0000-0000-4000-8000-000000000001","session_id":"0e5a0000-0000-4000-9000-000000000001"}',true);
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Expired session still reads % (% rows)',t,n; end if;
 end loop;
end $$;
reset role;
update auth.sessions set not_after=null where id='0e5a0000-0000-4000-9000-000000000001';

-- 10. Deactivated company: owner_a (live session) reads nothing and cannot write.
update quoteflow.podjetje set aktivno=false where id='0e5a0000-0000-4000-a000-00000000000a';
set local role authenticated;
do $$ declare t text; n bigint; begin
 foreach t in array array['vrsta_dela','material_vrste_dela','postavka_projekta','izmera','izmera_ponudbe','delo_ponudbe'] loop
  execute format('select count(*) from quoteflow.%I',t) into n;
  if n<>0 then raise exception 'Deactivated company still exposes % (% rows)',t,n; end if;
 end loop;
 begin
  perform * from quoteflow_private.shrani_vrsto_dela(podjetje=>'0e5a0000-0000-4000-a000-00000000000a'::uuid,vrsta=>null::uuid,naziv=>'Zavrnjeno'::text,
   opis=>''::text,urna_postavka=>0::numeric,stevilo_ur=>0::numeric,stevilo_delavcev=>1,aktivna=>true);
  raise exception 'Deactivated company must refuse guarded writes';
 exception when insufficient_privilege then null;
 end;
end $$;
reset role;

select 'ok' as tenant_isolation;
rollback;
