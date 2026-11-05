"""Operator utilities. Backups contain personal data and must be stored securely."""
import argparse, csv, os, sqlite3, sys
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
    sub.add_parser('check');survey=sub.add_parser('feedback-export');survey.add_argument('target');b=sub.add_parser('backup');b.add_argument('target')
    args=parser.parse_args()
    if args.command=='backup':backup(args.target);return
    if args.command=='feedback-export':
        fields=['source','rating','usefulness','willingness','persona','comments','created','updated']
        with server.conn() as c:data=[dict(r) for r in c.execute('SELECT '+','.join(fields)+' FROM feedback ORDER BY id')]
        fd=os.open(args.target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',newline='') as f:
            writer=csv.writer(f);writer.writerow(fields)
            for row in data:
                values=[row[k] for k in fields]
                writer.writerow(["'"+str(v) if isinstance(v,str) and v[:1] in ['=','+','-','@','\t','\r'] else v for v in values])
        print(str(len(data))+' survey responses exported privately. Responses are not unique-person or customer counts.');return
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
