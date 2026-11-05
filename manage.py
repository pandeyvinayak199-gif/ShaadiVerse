"""Operator utilities. Backups contain personal data and must be stored securely."""
import argparse, os, sqlite3, sys
from pathlib import Path
import server

def backup(target):
    if os.environ.get('DATABASE_URL'):
        raise ValueError('Use your PostgreSQL provider’s managed backups or pg_dump; this command backs up SQLite only.')
    if not Path(server.DB).is_file():raise ValueError('Database does not exist.')
    destination=Path(target).resolve()
    if destination==Path(server.DB).resolve():raise ValueError('Backup must use a different file.')
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(descriptor)
    try:
        source=sqlite3.connect('file:'+str(Path(server.DB).resolve())+'?mode=ro',uri=True)
        with sqlite3.connect(destination) as output:source.backup(output)
        source.close()
        check=sqlite3.connect(destination);result=check.execute('PRAGMA integrity_check').fetchone()[0];check.close()
        if result!='ok':raise ValueError('Backup failed its integrity check.')
    except BaseException:
        destination.unlink(missing_ok=True);raise
    print('Backup created and integrity checked. Store it outside the service disk, securely.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('check');b=sub.add_parser('backup');b.add_argument('target')
    args=parser.parse_args()
    if args.command=='backup':backup(args.target);return
    server.initialize()
    with server.conn() as c:c.execute('SELECT 1').fetchone()
    print('Database connection and additive migrations: OK')
    print('Storage: '+('PostgreSQL' if os.environ.get('DATABASE_URL') else 'SQLite (requires a mounted volume in hosting)'))
    print('Mode: '+('sandbox' if server.demo_mode() else 'verified-user access'))
    print('Phone OTP: '+('configured, live delivery not checked' if server.providers.sms_ready() else 'not configured'))
    print('WhatsApp: '+('configured, live delivery not checked' if server.providers.whatsapp_ready() else 'not configured'))
    print('Payments: '+('configured, live capture not checked' if server.providers.payments_ready() else 'not configured'))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print('Operation failed. Check storage permissions and secure configuration. No data was overwritten.',file=sys.stderr);sys.exit(1)
