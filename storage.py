"""Durable SQLite volume or PostgreSQL. All migrations are additive."""
import os, sqlite3
from contextlib import contextmanager
from pathlib import Path

APP_TABLES=['records','audit','users','memberships','sessions','challenges','settings','limits','purchases','outbox','event_codes','webhook_events','feedback']

class PGConnection:
    def __init__(self, url):
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.conninfo import conninfo_to_dict
        options=conninfo_to_dict(url)
        if options.get('host','') not in ['localhost','127.0.0.1','::1'] and not options.get('host','').startswith('/'):
            if options.get('sslmode','verify-full')!='verify-full':
                raise ValueError('Remote PostgreSQL connections require sslmode=verify-full.')
            options.setdefault('sslmode','verify-full')
            options.setdefault('sslrootcert',os.environ.get('PGSSLROOTCERT','system'))
        self.raw = psycopg.connect(row_factory=dict_row, prepare_threshold=None, **options)
        self.raw.execute("SELECT set_config('search_path','shaadi_sync, pg_catalog',true)")
    def execute(self, sql, params=()):
        return self.raw.execute(sql.replace('?', '%s'), params)
    def executescript(self, sql):
        for statement in sql.split(';'):
            if statement.strip(): self.execute(statement)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()

@contextmanager
def connect(path, write=False):
    url = os.environ.get('DATABASE_URL', '')
    if url:
        c = PGConnection(url)
    else:
        Path(path).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        c = sqlite3.connect(path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        if write: c.execute('BEGIN IMMEDIATE')
    try:
        yield c
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally: c.close()

def migrate(path):
    pg = bool(os.environ.get('DATABASE_URL'))
    pk = 'BIGSERIAL PRIMARY KEY' if pg else 'INTEGER PRIMARY KEY'
    with connect(path, True) as c:
        if pg:
            c.execute('SELECT pg_advisory_xact_lock(823917822)')
            c.execute('CREATE SCHEMA IF NOT EXISTS shaadi_sync')
            c.execute('REVOKE ALL ON SCHEMA shaadi_sync FROM PUBLIC')
            legacy=c.execute("SELECT to_regclass('public.records') AS records,to_regclass('public.settings') AS settings,to_regclass('public.sessions') AS sessions").fetchone()
            if all(legacy[k] for k in ['records','settings','sessions']):
                fields={r['column_name'] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='settings'")}
                if fields=={'name','value'} and c.execute("SELECT 1 FROM public.settings WHERE name='signing_key'").fetchone():
                    for table in APP_TABLES:
                        if c.execute('SELECT to_regclass(?) AS t',('public.'+table,)).fetchone()['t']:
                            if c.execute('SELECT to_regclass(?) AS t',('shaadi_sync.'+table,)).fetchone()['t']:raise ValueError('Both public and private app tables exist; explicit migration is required.')
                            c.execute('ALTER TABLE public.'+table+' SET SCHEMA shaadi_sync')
        c.executescript(f'''
        CREATE TABLE IF NOT EXISTS records(id {pk},kind TEXT NOT NULL,data TEXT NOT NULL,event_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS audit(id {pk},actor TEXT,action TEXT,created DOUBLE PRECISION,event_id INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS users(phone TEXT PRIMARY KEY,name TEXT NOT NULL,created DOUBLE PRECISION NOT NULL);
        CREATE TABLE IF NOT EXISTS memberships(event_id INTEGER,phone TEXT,role TEXT NOT NULL,entity_id INTEGER,permissions TEXT NOT NULL DEFAULT '[]',revoked INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(event_id,phone));
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,phone TEXT,name TEXT,event_id INTEGER,csrf TEXT,expires DOUBLE PRECISION,demo_role TEXT,auth_mode TEXT NOT NULL DEFAULT 'legacy');
        CREATE TABLE IF NOT EXISTS challenges(phone TEXT PRIMARY KEY,code_hash TEXT,created DOUBLE PRECISION,attempts INTEGER NOT NULL DEFAULT 0,mode TEXT);
        CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY,count INTEGER,reset DOUBLE PRECISION);
        CREATE TABLE IF NOT EXISTS purchases(id TEXT PRIMARY KEY,event_id INTEGER,phone TEXT,plan TEXT,amount INTEGER,currency TEXT,status TEXT,payment_id TEXT UNIQUE,created DOUBLE PRECISION);
        CREATE TABLE IF NOT EXISTS outbox(id {pk},event_id INTEGER,guest_id INTEGER,phone TEXT,status TEXT,provider_id TEXT,error TEXT,created DOUBLE PRECISION);
        CREATE TABLE IF NOT EXISTS event_codes(code TEXT PRIMARY KEY,event_id INTEGER UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS webhook_events(id TEXT PRIMARY KEY,created DOUBLE PRECISION);
        CREATE TABLE IF NOT EXISTS feedback(id {pk},actor_hash TEXT UNIQUE NOT NULL,source TEXT NOT NULL,event_id INTEGER,rating INTEGER,usefulness INTEGER,willingness TEXT,persona TEXT,comments TEXT,created DOUBLE PRECISION,updated DOUBLE PRECISION);
        ''')
        if pg:
            c.execute('ALTER TABLE records ADD COLUMN IF NOT EXISTS event_id INTEGER NOT NULL DEFAULT 1')
            c.execute('ALTER TABLE audit ADD COLUMN IF NOT EXISTS event_id INTEGER NOT NULL DEFAULT 1')
        else:
            for table in ('records','audit'):
                if 'event_id' not in [r['name'] for r in c.execute(f'PRAGMA table_info({table})')]:
                    c.execute(f'ALTER TABLE {table} ADD COLUMN event_id INTEGER NOT NULL DEFAULT 1')
        if pg:
            c.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS auth_mode TEXT NOT NULL DEFAULT 'legacy'")
        elif 'auth_mode' not in [r['name'] for r in c.execute('PRAGMA table_info(sessions)')]:
            c.execute("ALTER TABLE sessions ADD COLUMN auth_mode TEXT NOT NULL DEFAULT 'legacy'")
        c.execute('CREATE INDEX IF NOT EXISTS records_scope ON records(event_id,kind)')
        c.execute('CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires)')
        if pg:
            for table in APP_TABLES:
                c.execute('ALTER TABLE shaadi_sync.'+table+' ENABLE ROW LEVEL SECURITY')
                c.execute('REVOKE ALL ON TABLE shaadi_sync.'+table+' FROM PUBLIC')
            for role in ['anon','authenticated']:
                if c.execute('SELECT 1 FROM pg_roles WHERE rolname=?',(role,)).fetchone():
                    c.execute('REVOKE ALL ON SCHEMA shaadi_sync FROM '+role)
                    c.execute('REVOKE ALL ON ALL TABLES IN SCHEMA shaadi_sync FROM '+role)
    if not pg:
        with connect(path) as c: c.execute('PRAGMA journal_mode=WAL')
