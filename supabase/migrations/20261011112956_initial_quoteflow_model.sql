-- QuoteFlow AI initial schema. No application data and no client write permissions.
-- Supabase Auth owns credentials; all business objects stay outside exposed schemas.
create schema quoteflow;
create schema quoteflow_private;
revoke all on schema quoteflow, quoteflow_private from public, anon;
create role quoteflow_app nologin nosuperuser nocreatedb nocreaterole noinherit nobypassrls;
grant authenticated to quoteflow_app;
-- A future backend login must explicitly SET LOCAL ROLE authenticated after JWT verification.

grant usage on schema quoteflow, quoteflow_private to authenticated;

create table quoteflow.user_profiles (
 id uuid primary key references auth.users(id) on delete restrict,
 display_name text not null check (length(trim(display_name)) > 0),
 is_active boolean not null default true,
 created_at timestamptz not null default now()
);
create table quoteflow.companies (
 id uuid primary key default gen_random_uuid(), name text not null check(length(trim(name))>0),
 status text not null default 'active' check(status in ('active','suspended')),
 created_at timestamptz not null default now()
);
create table quoteflow.company_members (
 company_id uuid not null references quoteflow.companies(id),
 user_id uuid not null references quoteflow.user_profiles(id),
 role text not null check(role in ('buyer','supplier')), is_active boolean not null default true,
 primary key(company_id,user_id,role)
);
create index company_members_user_idx on quoteflow.company_members(user_id,company_id);
create table quoteflow.platform_admins (
 user_id uuid primary key references quoteflow.user_profiles(id), granted_at timestamptz not null default now()
);
create table quoteflow.supplier_profiles (
 company_id uuid primary key references quoteflow.companies(id),
 display_name text not null, regions text[] not null default '{}', categories text[] not null default '{}',
 is_active boolean not null default true
);
create table quoteflow.products (
 id uuid primary key default gen_random_uuid(), manufacturer text not null, code text not null, name text not null,
 unique(manufacturer,code), check(length(trim(code))>0 and length(trim(name))>0)
);
create table quoteflow.supplier_products (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references quoteflow.supplier_profiles(company_id),
 product_id uuid not null references quoteflow.products(id),
 cost numeric(18,4) check(cost>=0 and cost<'Infinity'::numeric),
 price numeric(18,4) check(price>0 and price<'Infinity'::numeric), stock integer check(stock>=0),
 lead_days integer check(lead_days>=0), confirmed_at timestamptz,
 version integer not null default 1 check(version>0), unique(company_id,product_id), unique(id,company_id)
);
create index supplier_products_product_idx on quoteflow.supplier_products(product_id);
create table quoteflow.pricing_policies (
 company_id uuid primary key references quoteflow.supplier_profiles(company_id),
 min_margin numeric(8,6) not null check(min_margin>=0 and min_margin<1),
 max_discount numeric(8,6) not null check(max_discount>=0 and max_discount<1),
 max_lead_days integer not null check(max_lead_days>=0), version integer not null default 1 check(version>0)
);
create table quoteflow.rfqs (
 id uuid primary key default gen_random_uuid(), buyer_company_id uuid not null references quoteflow.companies(id),
 created_by uuid not null references quoteflow.user_profiles(id),
 selection_mode text not null check(selection_mode in ('manual','automatic')),
 status text not null default 'draft' check(status in ('draft','submitted','processing','awaiting_quotes','closed')),
 delivery_location text not null, requested_date date not null, submitted_at timestamptz,
 version integer not null default 1 check(version>0), created_at timestamptz not null default now(),
 unique(id,buyer_company_id), check(status='draft' or submitted_at is not null)
);
create index rfqs_buyer_idx on quoteflow.rfqs(buyer_company_id,submitted_at);
create index rfqs_creator_idx on quoteflow.rfqs(created_by);
create table quoteflow.rfq_items (
 id uuid primary key default gen_random_uuid(), rfq_id uuid not null references quoteflow.rfqs(id),
 product_id uuid references quoteflow.products(id), description text not null check(length(trim(description))>0),
 quantity integer not null check(quantity>0), unique(id,rfq_id)
);
create index rfq_items_rfq_idx on quoteflow.rfq_items(rfq_id);
create index rfq_items_product_idx on quoteflow.rfq_items(product_id);
create table quoteflow.rfq_recipients (
 rfq_id uuid not null references quoteflow.rfqs(id),
 supplier_company_id uuid not null references quoteflow.supplier_profiles(company_id),
 reason text not null, status text not null default 'assigned' check(status in ('assigned','declined','completed')),
 primary key(rfq_id,supplier_company_id)
);
create index recipients_supplier_idx on quoteflow.rfq_recipients(supplier_company_id,rfq_id);
create table quoteflow.agent_runs (
 id uuid primary key default gen_random_uuid(), rfq_id uuid not null, supplier_company_id uuid not null,
 status text not null default 'pending' check(status in ('pending','running','succeeded','failed')),
 input_version integer not null check(input_version>0), idempotency_key text not null unique,
 error_code text, started_at timestamptz, ended_at timestamptz,
 foreign key(rfq_id,supplier_company_id) references quoteflow.rfq_recipients(rfq_id,supplier_company_id),
 check(ended_at is null or (started_at is not null and ended_at>=started_at))
);
create index agent_runs_recipient_idx on quoteflow.agent_runs(rfq_id,supplier_company_id);
create index agent_runs_supplier_idx on quoteflow.agent_runs(supplier_company_id,status);
create table quoteflow.quotes (
 id uuid primary key default gen_random_uuid(), rfq_id uuid not null, supplier_company_id uuid not null,
 status text not null default 'draft' check(status in ('draft','needs_review','approved','rejected')),
 version integer not null default 1 check(version>0), currency text not null default 'EUR' check(currency='EUR'),
 valid_until timestamptz not null, published_at timestamptz,
 foreign key(rfq_id,supplier_company_id) references quoteflow.rfq_recipients(rfq_id,supplier_company_id),
 unique(id,rfq_id,supplier_company_id), unique(id,supplier_company_id),
 check((status='approved')=(published_at is not null))
);
create index quotes_recipient_idx on quoteflow.quotes(rfq_id,supplier_company_id);
create index quotes_supplier_idx on quoteflow.quotes(supplier_company_id,status);
create table quoteflow.quote_items (
 id uuid primary key default gen_random_uuid(), quote_id uuid not null, rfq_id uuid not null, supplier_company_id uuid not null,
 rfq_item_id uuid not null, supplier_product_id uuid,
 quantity integer not null check(quantity>0), price numeric(18,4) check(price>0 and price<'Infinity'::numeric),
 discount numeric(8,6) not null default 0 check(discount>=0 and discount<1),
 cost_snapshot numeric(18,4) check(cost_snapshot>=0 and cost_snapshot<'Infinity'::numeric),
 lead_days integer check(lead_days>=0),
 foreign key(quote_id,rfq_id,supplier_company_id) references quoteflow.quotes(id,rfq_id,supplier_company_id),
 foreign key(rfq_item_id,rfq_id) references quoteflow.rfq_items(id,rfq_id),
 foreign key(supplier_product_id,supplier_company_id) references quoteflow.supplier_products(id,company_id),
 unique(quote_id,rfq_item_id)
);
create index quote_items_rfq_item_idx on quoteflow.quote_items(rfq_item_id,rfq_id);
create index quote_items_supplier_product_idx on quoteflow.quote_items(supplier_product_id,supplier_company_id);
create index quote_items_supplier_idx on quoteflow.quote_items(supplier_company_id);
create table quoteflow.quote_revisions (
 id uuid primary key default gen_random_uuid(), quote_id uuid not null, supplier_company_id uuid not null,
 version integer not null check(version>0), public_snapshot jsonb not null, private_snapshot jsonb not null,
 created_at timestamptz not null default now(),
 foreign key(quote_id,supplier_company_id) references quoteflow.quotes(id,supplier_company_id),
 unique(quote_id,version), unique(id,quote_id,supplier_company_id)
);
create index revisions_supplier_idx on quoteflow.quote_revisions(supplier_company_id);
create table quoteflow.approvals (
 id uuid primary key default gen_random_uuid(), quote_revision_id uuid not null, quote_id uuid not null,
 company_id uuid not null, actor_user_id uuid not null references quoteflow.user_profiles(id),
 actor_role text not null default 'supplier' check(actor_role='supplier'),
 decision text not null check(decision in ('approved','rejected')), decided_at timestamptz not null default now(),
 foreign key(quote_revision_id,quote_id,company_id) references quoteflow.quote_revisions(id,quote_id,supplier_company_id),
 foreign key(company_id,actor_user_id,actor_role) references quoteflow.company_members(company_id,user_id,role),
 unique(quote_revision_id), unique(id,quote_id,company_id,decision)
);
create index approvals_quote_idx on quoteflow.approvals(quote_id);
create index approvals_actor_idx on quoteflow.approvals(actor_user_id);
create index approvals_company_member_idx on quoteflow.approvals(company_id,actor_user_id,actor_role);
-- Buyer-facing rows are typed, not arbitrary internal JSON snapshots.
create table quoteflow.published_quotes (
 id uuid primary key, rfq_id uuid not null, supplier_company_id uuid not null, buyer_company_id uuid not null,
 approval_id uuid not null unique, approval_decision text not null default 'approved' check(approval_decision='approved'),
 currency text not null default 'EUR' check(currency='EUR'), total numeric(18,2) not null check(total>0 and total<'Infinity'::numeric),
 delivery_days integer not null check(delivery_days>=0), payment_terms text not null,
 valid_until timestamptz not null, published_at timestamptz not null default now(),
 foreign key(id,rfq_id,supplier_company_id) references quoteflow.quotes(id,rfq_id,supplier_company_id),
 foreign key(rfq_id,buyer_company_id) references quoteflow.rfqs(id,buyer_company_id),
 foreign key(approval_id,id,supplier_company_id,approval_decision) references quoteflow.approvals(id,quote_id,company_id,decision),
 check(valid_until>published_at)
);
create index published_quotes_rfq_idx on quoteflow.published_quotes(rfq_id,buyer_company_id);
create index published_quotes_supplier_idx on quoteflow.published_quotes(supplier_company_id);
create index published_quotes_buyer_idx on quoteflow.published_quotes(buyer_company_id,published_at);
create table quoteflow.published_quote_items (
 id uuid primary key default gen_random_uuid(), published_quote_id uuid not null references quoteflow.published_quotes(id),
 description text not null, quantity integer not null check(quantity>0),
 unit_price numeric(18,4) not null check(unit_price>0 and unit_price<'Infinity'::numeric),
 discount numeric(8,6) not null check(discount>=0 and discount<1),
 line_total numeric(18,2) not null check(line_total>0 and line_total<'Infinity'::numeric),
 delivery_days integer not null check(delivery_days>=0)
);
create index published_items_quote_idx on quoteflow.published_quote_items(published_quote_id);
create table quoteflow.audit_events (
 id uuid primary key default gen_random_uuid(), company_id uuid not null references quoteflow.companies(id),
 actor_id uuid references quoteflow.user_profiles(id), action text not null, entity_id uuid not null,
 created_at timestamptz not null default now()
);
create index audit_events_company_idx on quoteflow.audit_events(company_id,created_at);
create index audit_events_actor_idx on quoteflow.audit_events(actor_id);

-- Fixed search_path, no user-supplied identity, no dynamic SQL.
-- Definer lookups avoid recursive membership policies; only boolean results leave the private schema.
create function quoteflow_private.active_user() returns boolean language sql stable security definer set search_path = '' as $$
 select auth.uid() is not null and exists(select 1 from quoteflow.user_profiles where id=auth.uid() and is_active)
$$;
create function quoteflow_private.member_of(company uuid, required_role text default null) returns boolean
language sql stable security definer set search_path = '' as $$
 select quoteflow_private.active_user() and exists(
 select 1 from quoteflow.company_members m join quoteflow.companies c on c.id=m.company_id
 where m.user_id=auth.uid() and m.company_id=company and m.is_active and c.status='active'
 and (required_role is null or m.role=required_role))
$$;
create function quoteflow_private.can_read_rfq(target uuid) returns boolean
language sql stable security definer set search_path = '' as $$
 select auth.uid() is not null and exists(select 1 from quoteflow.rfqs r where r.id=target and (
 quoteflow_private.member_of(r.buyer_company_id,'buyer') or
 (r.status<>'draft' and exists(select 1 from quoteflow.rfq_recipients x where x.rfq_id=r.id
 and quoteflow_private.member_of(x.supplier_company_id,'supplier')))))
$$;
create function quoteflow_private.owns_rfq(target uuid) returns boolean
language sql stable security definer set search_path = '' as $$
 select auth.uid() is not null and exists(select 1 from quoteflow.rfqs r where r.id=target
 and quoteflow_private.member_of(r.buyer_company_id,'buyer'))
$$;
create function quoteflow_private.own_admin() returns boolean
language sql stable security definer set search_path = '' as $$
 select quoteflow_private.active_user() and exists(select 1 from quoteflow.platform_admins where user_id=auth.uid())
$$;
revoke all on all functions in schema quoteflow_private from public,anon;
grant execute on all functions in schema quoteflow_private to authenticated;

-- Published snapshots and approval/audit records cannot be silently rewritten.
create function quoteflow_private.reject_mutation() returns trigger language plpgsql set search_path = '' as $$
begin raise exception 'Immutable record: create a new version' using errcode='55000'; end
$$;
revoke all on function quoteflow_private.reject_mutation() from public,anon,authenticated;

create function quoteflow_private.active_company(company uuid) returns boolean language sql stable security definer set search_path = '' as $$
 select quoteflow_private.active_user() and exists(select 1 from quoteflow.companies where id=company and status='active')
$$;
revoke all on function quoteflow_private.active_company(uuid) from public,anon;
grant execute on function quoteflow_private.active_company(uuid) to authenticated;

alter table quoteflow.user_profiles enable row level security;
alter table quoteflow.user_profiles force row level security;
revoke all on quoteflow.user_profiles from public,anon,authenticated,service_role;
grant select on quoteflow.user_profiles to authenticated;
create policy read_authorized on quoteflow.user_profiles for select to authenticated using (id=(select auth.uid()) and is_active);

alter table quoteflow.companies enable row level security;
alter table quoteflow.companies force row level security;
revoke all on quoteflow.companies from public,anon,authenticated,service_role;
grant select on quoteflow.companies to authenticated;
create policy read_authorized on quoteflow.companies for select to authenticated using (quoteflow_private.member_of(id) or quoteflow_private.own_admin());

alter table quoteflow.company_members enable row level security;
alter table quoteflow.company_members force row level security;
revoke all on quoteflow.company_members from public,anon,authenticated,service_role;
grant select on quoteflow.company_members to authenticated;
create policy read_authorized on quoteflow.company_members for select to authenticated using (user_id=(select auth.uid()) and quoteflow_private.member_of(company_id) or quoteflow_private.own_admin());

alter table quoteflow.platform_admins enable row level security;
alter table quoteflow.platform_admins force row level security;
revoke all on quoteflow.platform_admins from public,anon,authenticated,service_role;
grant select on quoteflow.platform_admins to authenticated;
create policy read_authorized on quoteflow.platform_admins for select to authenticated using (user_id=(select auth.uid()) and quoteflow_private.active_user());

alter table quoteflow.supplier_profiles enable row level security;
alter table quoteflow.supplier_profiles force row level security;
revoke all on quoteflow.supplier_profiles from public,anon,authenticated,service_role;
grant select on quoteflow.supplier_profiles to authenticated;
create policy read_authorized on quoteflow.supplier_profiles for select to authenticated using (is_active and quoteflow_private.active_company(company_id));

alter table quoteflow.products enable row level security;
alter table quoteflow.products force row level security;
revoke all on quoteflow.products from public,anon,authenticated,service_role;
grant select on quoteflow.products to authenticated;
create policy read_authorized on quoteflow.products for select to authenticated using ((select quoteflow_private.active_user()));

alter table quoteflow.supplier_products enable row level security;
alter table quoteflow.supplier_products force row level security;
revoke all on quoteflow.supplier_products from public,anon,authenticated,service_role;
grant select on quoteflow.supplier_products to authenticated;
create policy read_authorized on quoteflow.supplier_products for select to authenticated using (quoteflow_private.member_of(company_id,'supplier'));

alter table quoteflow.pricing_policies enable row level security;
alter table quoteflow.pricing_policies force row level security;
revoke all on quoteflow.pricing_policies from public,anon,authenticated,service_role;
grant select on quoteflow.pricing_policies to authenticated;
create policy read_authorized on quoteflow.pricing_policies for select to authenticated using (quoteflow_private.member_of(company_id,'supplier'));

alter table quoteflow.rfqs enable row level security;
alter table quoteflow.rfqs force row level security;
revoke all on quoteflow.rfqs from public,anon,authenticated,service_role;
grant select on quoteflow.rfqs to authenticated;
create policy read_authorized on quoteflow.rfqs for select to authenticated using (quoteflow_private.can_read_rfq(id));

alter table quoteflow.rfq_items enable row level security;
alter table quoteflow.rfq_items force row level security;
revoke all on quoteflow.rfq_items from public,anon,authenticated,service_role;
grant select on quoteflow.rfq_items to authenticated;
create policy read_authorized on quoteflow.rfq_items for select to authenticated using (quoteflow_private.can_read_rfq(rfq_id));

alter table quoteflow.rfq_recipients enable row level security;
alter table quoteflow.rfq_recipients force row level security;
revoke all on quoteflow.rfq_recipients from public,anon,authenticated,service_role;
grant select on quoteflow.rfq_recipients to authenticated;
create policy read_authorized on quoteflow.rfq_recipients for select to authenticated using (quoteflow_private.owns_rfq(rfq_id) or quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.agent_runs enable row level security;
alter table quoteflow.agent_runs force row level security;
revoke all on quoteflow.agent_runs from public,anon,authenticated,service_role;
grant select on quoteflow.agent_runs to authenticated;
create policy read_authorized on quoteflow.agent_runs for select to authenticated using (quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.quotes enable row level security;
alter table quoteflow.quotes force row level security;
revoke all on quoteflow.quotes from public,anon,authenticated,service_role;
grant select on quoteflow.quotes to authenticated;
create policy read_authorized on quoteflow.quotes for select to authenticated using (quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.quote_items enable row level security;
alter table quoteflow.quote_items force row level security;
revoke all on quoteflow.quote_items from public,anon,authenticated,service_role;
grant select on quoteflow.quote_items to authenticated;
create policy read_authorized on quoteflow.quote_items for select to authenticated using (quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.quote_revisions enable row level security;
alter table quoteflow.quote_revisions force row level security;
revoke all on quoteflow.quote_revisions from public,anon,authenticated,service_role;
grant select on quoteflow.quote_revisions to authenticated;
create policy read_authorized on quoteflow.quote_revisions for select to authenticated using (quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.approvals enable row level security;
alter table quoteflow.approvals force row level security;
revoke all on quoteflow.approvals from public,anon,authenticated,service_role;
grant select on quoteflow.approvals to authenticated;
create policy read_authorized on quoteflow.approvals for select to authenticated using (quoteflow_private.member_of(company_id,'supplier'));

alter table quoteflow.published_quotes enable row level security;
alter table quoteflow.published_quotes force row level security;
revoke all on quoteflow.published_quotes from public,anon,authenticated,service_role;
grant select on quoteflow.published_quotes to authenticated;
create policy read_authorized on quoteflow.published_quotes for select to authenticated using (quoteflow_private.member_of(buyer_company_id,'buyer') or quoteflow_private.member_of(supplier_company_id,'supplier'));

alter table quoteflow.published_quote_items enable row level security;
alter table quoteflow.published_quote_items force row level security;
revoke all on quoteflow.published_quote_items from public,anon,authenticated,service_role;
grant select on quoteflow.published_quote_items to authenticated;
create policy read_authorized on quoteflow.published_quote_items for select to authenticated using (exists(select 1 from quoteflow.published_quotes q where q.id=published_quote_id));

alter table quoteflow.audit_events enable row level security;
alter table quoteflow.audit_events force row level security;
revoke all on quoteflow.audit_events from public,anon,authenticated,service_role;
grant select on quoteflow.audit_events to authenticated;
create policy read_authorized on quoteflow.audit_events for select to authenticated using (quoteflow_private.member_of(company_id));
create trigger immutable before update or delete on quoteflow.quote_revisions for each row execute function quoteflow_private.reject_mutation();
create trigger immutable before update or delete on quoteflow.approvals for each row execute function quoteflow_private.reject_mutation();
create trigger immutable before update or delete on quoteflow.published_quotes for each row execute function quoteflow_private.reject_mutation();
create trigger immutable before update or delete on quoteflow.published_quote_items for each row execute function quoteflow_private.reject_mutation();
create trigger immutable before update or delete on quoteflow.audit_events for each row execute function quoteflow_private.reject_mutation();

-- Explicitly no INSERT/UPDATE/DELETE policies or grants yet. Mutation workflows are a next step.
-- Do not use postgres/service_role for application request handling.
comment on schema quoteflow is 'QuoteFlow AI business model; private schema accessed through FastAPI with verified identity and RLS';
