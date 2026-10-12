-- Run with supabase db query --linked --file supabase/tests/tenant_isolation.sql
-- Test fixtures are ALWAYS rolled back; no business data remains.
begin;
create function pg_temp.assert_true(ok boolean, label text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception 'FAILED: %', label; end if; end $$;
create function pg_temp.expect_error(stmt text, expected_state text) returns void language plpgsql as $$
begin
 begin execute stmt; exception when others then
   if sqlstate = expected_state then return; end if;
   raise;
 end;
 raise exception 'Expected SQLSTATE % for %',expected_state,stmt;
end $$;

insert into auth.users(id,email) values
 ('10000000-0000-0000-0000-000000000001','qf-test-buyer-a@example.invalid'),
 ('10000000-0000-0000-0000-000000000002','qf-test-buyer-b@example.invalid'),
 ('10000000-0000-0000-0000-000000000003','qf-test-supplier-a@example.invalid'),
 ('10000000-0000-0000-0000-000000000004','qf-test-supplier-b@example.invalid'),
 ('10000000-0000-0000-0000-000000000005','qf-test-admin@example.invalid');
insert into quoteflow.user_profiles(id,display_name) select id,email from auth.users where email like 'qf-test-%@example.invalid';
insert into quoteflow.companies(id,name) values
 ('20000000-0000-0000-0000-000000000001','Buyer A'),('20000000-0000-0000-0000-000000000002','Buyer B'),
 ('20000000-0000-0000-0000-000000000003','Supplier A'),('20000000-0000-0000-0000-000000000004','Supplier B');
insert into quoteflow.company_members(company_id,user_id,role) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','buyer'),
 ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','buyer'),
 ('20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','supplier'),
 ('20000000-0000-0000-0000-000000000004','10000000-0000-0000-0000-000000000004','supplier');
insert into quoteflow.platform_admins(user_id) values ('10000000-0000-0000-0000-000000000005');
insert into quoteflow.supplier_profiles(company_id,display_name) select id,name from quoteflow.companies where name like 'Supplier %';
insert into quoteflow.products(id,manufacturer,code,name) values ('30000000-0000-0000-0000-000000000001','TEST','6205','Test bearing');
insert into quoteflow.supplier_products(id,company_id,product_id,cost,price,stock,lead_days,confirmed_at) values
 ('40000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','30000000-0000-0000-0000-000000000001',80,110,50,5,now()),
 ('40000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000004','30000000-0000-0000-0000-000000000001',70,100,50,5,now());
insert into quoteflow.rfqs(id,buyer_company_id,created_by,selection_mode,status,delivery_location,requested_date,submitted_at) values
 ('50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','automatic','submitted','SI',current_date+7,now()),
 ('50000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','manual','draft','SI',current_date+7,null);
insert into quoteflow.rfq_items(id,rfq_id,description,quantity) values
 ('60000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','Bearing',50),
 ('60000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000002','Other buyer',10);
insert into quoteflow.rfq_recipients(rfq_id,supplier_company_id,reason) values
 ('50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','match'),
 ('50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004','match');
insert into quoteflow.quotes(id,rfq_id,supplier_company_id,valid_until) values
 ('70000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003',now()+interval '14 days'),
 ('70000000-0000-0000-0000-000000000002','50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000004',now()+interval '14 days');
insert into quoteflow.quote_revisions(id,quote_id,supplier_company_id,version,public_snapshot,private_snapshot) values
 ('80000000-0000-0000-0000-000000000001','70000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003',1,'{}','{"cost":4000}');

-- Cross-tenant and cross-RFQ references must fail even for privileged writers.
select pg_temp.expect_error($s$insert into quoteflow.quote_items(quote_id,rfq_id,supplier_company_id,rfq_item_id,supplier_product_id,quantity) values ('70000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','60000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000002',50)$s$,'23503');
select pg_temp.expect_error($s$insert into quoteflow.quote_items(quote_id,rfq_id,supplier_company_id,rfq_item_id,quantity) values ('70000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','60000000-0000-0000-0000-000000000002',50)$s$,'23503');

set local role authenticated;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
select pg_temp.assert_true((select count(*)=1 from quoteflow.rfqs),'buyer sees own RFQ');
select pg_temp.assert_true((select count(*)=0 from quoteflow.quotes),'buyer cannot read drafts');
select pg_temp.assert_true((select count(*)=0 from quoteflow.quote_revisions),'buyer cannot read private revision');
select pg_temp.assert_true((select count(*)=0 from quoteflow.supplier_products),'buyer cannot read internal catalog');
select pg_temp.assert_true((select count(*)=2 from quoteflow.supplier_profiles),'buyer discovers suppliers');
select pg_temp.assert_true((select count(*)=0 from quoteflow.published_quotes),'no publication before approval');
select pg_temp.expect_error('insert into quoteflow.companies(name) values (''Forged'')','42501');
select pg_temp.expect_error('update quoteflow.quotes set status=''approved'', published_at=now()','42501');
select pg_temp.expect_error('delete from quoteflow.company_members','42501');
select pg_temp.expect_error('insert into quoteflow.platform_admins(user_id) values (auth.uid())','42501');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000003',true);
select pg_temp.assert_true((select count(*)=1 from quoteflow.supplier_products),'supplier sees own catalog');
select pg_temp.assert_true((select count(*)=1 from quoteflow.quotes),'supplier sees own draft');
select pg_temp.assert_true((select count(*)=1 from quoteflow.rfqs),'supplier sees assigned RFQ only');
select pg_temp.assert_true((select count(*)=1 from quoteflow.rfq_recipients),'supplier cannot see competitor recipients');
select pg_temp.expect_error('update quoteflow.supplier_products set price=1','42501');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000004',true);
select pg_temp.assert_true((select count(*)=0 from quoteflow.quote_revisions),'competitor cannot read revisions');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000005',true);
select pg_temp.assert_true((select count(*)=4 from quoteflow.companies),'admin reads company directory');
select pg_temp.assert_true((select count(*)=0 from quoteflow.quotes),'admin cannot read business drafts');
set local role anon;
select pg_temp.expect_error('select * from quoteflow.companies','42501');
select pg_temp.expect_error('insert into quoteflow.companies(name) values (''Forged'')','42501');
select pg_temp.expect_error('update quoteflow.quotes set version=2','42501');
select pg_temp.expect_error('delete from quoteflow.rfqs','42501');
reset role;

insert into quoteflow.approvals(id,quote_revision_id,quote_id,company_id,actor_user_id,decision) values
 ('90000000-0000-0000-0000-000000000001','80000000-0000-0000-0000-000000000001','70000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','approved');
update quoteflow.quotes set status='approved', published_at=now() where id='70000000-0000-0000-0000-000000000001';
insert into quoteflow.published_quotes(id,rfq_id,supplier_company_id,buyer_company_id,approval_id,total,delivery_days,payment_terms,valid_until) values
 ('70000000-0000-0000-0000-000000000001','50000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000001','90000000-0000-0000-0000-000000000001',5500,5,'30 days',now()+interval '14 days');
insert into quoteflow.published_quote_items(published_quote_id,description,quantity,unit_price,discount,line_total,delivery_days) values
 ('70000000-0000-0000-0000-000000000001','Bearing',50,110,0,5500,5);
select pg_temp.expect_error('update quoteflow.quote_revisions set public_snapshot=''{}''','55000');
select pg_temp.expect_error('delete from quoteflow.published_quotes','55000');
set local role authenticated;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
select pg_temp.assert_true((select count(*)=1 from quoteflow.published_quotes),'buyer sees approved quote');
select pg_temp.assert_true((select count(*)=1 from quoteflow.published_quote_items),'buyer sees approved items');
select pg_temp.assert_true((select count(*)=0 from quoteflow.quote_revisions),'approval does not expose private snapshot');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000002',true);
select pg_temp.assert_true((select count(*)=0 from quoteflow.published_quotes),'other buyer cannot read publication');
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000004',true);
select pg_temp.assert_true((select count(*)=0 from quoteflow.published_quotes),'competitor cannot read publication');
reset role;
update quoteflow.user_profiles set is_active=false where id='10000000-0000-0000-0000-000000000001';
set local role authenticated;
select set_config('request.jwt.claim.sub','10000000-0000-0000-0000-000000000001',true);
select pg_temp.assert_true((select count(*)=0 from quoteflow.rfqs),'disabled user loses access immediately');
select pg_temp.assert_true((select count(*)=0 from quoteflow.published_quotes),'disabled user loses publication access');
reset role;
select 'All tenant-isolation and constraint assertions passed; transaction rolled back.' as result;
rollback;
