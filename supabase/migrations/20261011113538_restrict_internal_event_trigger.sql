-- Existing hosted-project event trigger is not a callable application API.
-- Optional because a fresh local Supabase stack may not provide this function.
do $$
begin
 if to_regprocedure('public.rls_auto_enable()') is not null then
   revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
 end if;
end $$;
