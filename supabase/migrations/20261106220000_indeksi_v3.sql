-- Indexes for the v3 / US-08 tables, found missing by the plan review (measured on seeded volumes, rolled back).
-- vloga_uporabnika: the two unique indexes on (uporabnik_id, ...) are partial, so lookups by uporabnik_id alone
-- (quoteflow_private.zavrnjen_cilj admin check, FK check when an account is deleted) cannot use them and scan the table.
create index if not exists vloga_uporabnik_idx on quoteflow.vloga_uporabnika(uporabnik_id);
