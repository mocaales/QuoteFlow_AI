-- Account deletion with role audit (G6 fix, first step of #104 tombstoning). Supersedes the ON DELETE RESTRICT note in
-- 20261106210000_delavci_in_pravice.sql: the user FKs of quoteflow_private.dogodek_vloge (izvajalec_id, uporabnik_id) and
-- quoteflow_private.povabilo_delavca (povabil_id, plus vloga_id to the deleted person's role) become ON DELETE SET NULL, so deleting
-- an account keeps the audit event and the invitation without the person. Every registered user has an audit row (automatic stranka),
-- so RESTRICT made every account undeletable. The insert-time rules (actor, target of a role event, inviter, role of an accepted
-- invitation) stay enforced by BEFORE triggers, because a CHECK cannot tell an insert from the FK's null-out. All other user FKs are
-- unchanged: a customer with a project, quote or invoice and the owner of a company remain non-deletable until #104 adds erasure and
-- retention. The invitee e-mail in povabilo_delavca is retained; its erasure is part of #104.
alter table quoteflow_private.dogodek_vloge alter izvajalec_id drop not null,
 drop constraint dogodek_vloge_izvajalec_id_fkey, add constraint dogodek_vloge_izvajalec_id_fkey foreign key(izvajalec_id) references quoteflow.uporabnik(id) on delete set null,
 drop constraint dogodek_vloge_uporabnik_id_fkey, add constraint dogodek_vloge_uporabnik_id_fkey foreign key(uporabnik_id) references quoteflow.uporabnik(id) on delete set null,
 drop constraint dogodek_vloge_check, add constraint dogodek_vloge_check check((dejanje='vloga')=(aktivna_potem is not null and povabilo_id is null));
alter table quoteflow_private.povabilo_delavca alter povabil_id drop not null,
 drop constraint povabilo_delavca_povabil_id_fkey, add constraint povabilo_delavca_povabil_id_fkey foreign key(povabil_id) references quoteflow.uporabnik(id) on delete set null,
 drop constraint povabilo_delavca_vloga_id_fkey, add constraint povabilo_delavca_vloga_id_fkey foreign key(vloga_id) references quoteflow.vloga_uporabnika(id) on delete set null,
 drop constraint povabilo_delavca_check1, add constraint povabilo_delavca_check1 check(vloga_id is null or stanje='sprejeto');

create function quoteflow_private.preveri_dogodek_vloge() returns trigger language plpgsql set search_path='' as $$
begin
 if new.izvajalec_id is null or (new.dejanje='vloga' and new.uporabnik_id is null) then
  raise check_violation using message='Dogodek vloge potrebuje izvajalca in ciljnega uporabnika.';
 end if;
 return new;
end $$;
create trigger preveri_dogodek_vloge before insert on quoteflow_private.dogodek_vloge for each row execute function quoteflow_private.preveri_dogodek_vloge();

-- Fires on inserts and on state changes only; the FK's set-null touches vloga_id alone and therefore passes.
create function quoteflow_private.preveri_povabilo_delavca() returns trigger language plpgsql set search_path='' as $$
begin
 if (tg_op='INSERT' and new.povabil_id is null) or (new.stanje='sprejeto' and new.vloga_id is null) then
  raise check_violation using message='Povabilo potrebuje povabitelja, sprejeto povabilo pa dodeljeno vlogo.';
 end if;
 return new;
end $$;
create trigger preveri_povabilo_delavca before insert or update of stanje on quoteflow_private.povabilo_delavca for each row execute function quoteflow_private.preveri_povabilo_delavca();
revoke all on function quoteflow_private.preveri_dogodek_vloge(),quoteflow_private.preveri_povabilo_delavca() from public,anon,authenticated,service_role;
