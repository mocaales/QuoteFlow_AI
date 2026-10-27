"""Assign the first global administrator to an existing confirmed account.

Run explicitly: backend/.venv/bin/python scripts/bootstrap_admin.py user@example.com
Never called during application startup or registration.
"""
import argparse
from pathlib import Path
import sys
import psycopg
from dotenv import dotenv_values
from psycopg.conninfo import conninfo_to_dict

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description='Dodeli globalnega administratorja potrjenemu uporabniku.')
    parser.add_argument('email')
    args=parser.parse_args()
    values=dotenv_values(ROOT/'.env',interpolate=False)
    url=values.get('DATABASE_MIGRATION_URL')
    if not url:
        raise ValueError('Manjka DATABASE_MIGRATION_URL v .env.')
    options=conninfo_to_dict(url)
    if options.get('sslmode') not in ('require','verify-ca','verify-full'):
        options['sslmode']='require'
    with psycopg.connect(**options,connect_timeout=8,prepare_threshold=None) as connection:
        user=connection.execute('''select u.id from quoteflow.uporabnik u join auth.users a on a.id=u.id
            where u.e_posta=%s and a.email_confirmed_at is not null''',(args.email.strip().lower(),)).fetchone()
        if user is None:
            raise ValueError('Račun ne obstaja ali e-pošta še ni potrjena. Najprej opravite registracijo.')
        connection.execute("""insert into quoteflow.vloga_uporabnika(uporabnik_id,vloga) values(%s,'administrator')
            on conflict(uporabnik_id) where vloga='administrator' do update set aktivna=true""",(user[0],))
    print('Vloga administratorja je dodeljena. V aplikaciji osvežite pravice.')

if __name__=='__main__':
    try:main()
    except ValueError as error:
        print(str(error),file=sys.stderr);sys.exit(1)
    except psycopg.Error:
        print('Povezava ali dodelitev ni uspela; preverite skrbniško povezavo in migracije.',file=sys.stderr);sys.exit(1)
