-- Non-destructive V2 smoke test. Full cases: backend/tests/test_identity_database.py.
begin;
do $$ begin
 if (select count(*) from pg_tables where schemaname='quoteflow')<>17 then
  raise exception 'Expected seventeen documented entities';
 end if;
 if exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='quoteflow' and c.relkind='r' and not (c.relrowsecurity and c.relforcerowsecurity)) then
  raise exception 'All business tables must enforce RLS';
 end if;
 if exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='quoteflow_private' and has_function_privilege('anon',p.oid,'execute')) then
  raise exception 'Anonymous users must not execute business functions';
 end if;
 if has_schema_privilege('authenticated','quoteflow_legacy_20261103','usage')
 or has_schema_privilege('authenticated','quoteflow_private_legacy_20261103','usage') then
  raise exception 'The V1 archive must not be accessible to application users';
 end if;
end $$;
set local role authenticated;
select set_config('request.jwt.claim.sub','',true);
select set_config('request.jwt.claims','{}',true);
do $$ begin
 if exists(select 1 from quoteflow.podjetje) or exists(select 1 from quoteflow.ponudba) then
  raise exception 'No session must mean no business data';
 end if;
 begin
  insert into quoteflow.podjetje(naziv) values('FORBIDDEN');
  raise exception 'Direct write unexpectedly allowed';
 exception when insufficient_privilege then null;
 end;
end $$;
rollback;
