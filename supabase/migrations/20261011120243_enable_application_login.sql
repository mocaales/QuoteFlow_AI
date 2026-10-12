-- Password is provisioned separately and never stored in a migration.
alter role quoteflow_app login noinherit connection limit 10;
alter role quoteflow_app set statement_timeout = '10s';
alter role quoteflow_app set idle_in_transaction_session_timeout = '10s';
