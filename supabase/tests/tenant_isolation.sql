-- Non-destructive smoke test for the documented model. Full cases: backend/tests/test_identity_database.py.
begin;
do $$ begin
 if (select count(*) from pg_tables where schemaname='quoteflow')<>10 then
  raise exception 'Expected ten documented entities';
 end if;
 if exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='quoteflow' and c.relkind='r' and not (c.relrowsecurity and c.relforcerowsecurity)) then
  raise exception 'All business tables must enforce RLS';
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
