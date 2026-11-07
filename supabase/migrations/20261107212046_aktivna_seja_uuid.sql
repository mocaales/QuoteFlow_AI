-- Scope: aktivna_seja() compared s.id::text with the session_id claim, which cannot use the auth.sessions primary key (measured: seq scan over
-- all sessions of a user, 8.7 ms per call at 20k sessions, 0.01 ms with the key). The claim is now cast to uuid only when it looks like one, so a
-- malformed claim yields false and never raises. Signature, security definer, search_path and grants are unchanged (create or replace keeps the ACL).
create or replace function quoteflow_private.aktivna_seja() returns boolean language sql stable security definer set search_path='' as $$
 select auth.uid() is not null and exists(select 1 from auth.sessions s where s.user_id=auth.uid()
 and s.id=(select case when c ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then c::uuid end
  from (select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb->>'session_id' as c) x)
 and (s.not_after is null or s.not_after>now()))
$$;
