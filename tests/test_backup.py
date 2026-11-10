import contextlib, io, os, sqlite3, tempfile, unittest
from unittest.mock import patch
import server, manage
class BackupTests(unittest.TestCase):
 def test_consistent_backup_and_no_overwrite(self):
  old=server.DB
  with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'DATABASE_URL':'','APP_MODE':'test','DEMO_MODE':'1'}):
   try:
    server.DB=d+'/source.sqlite3';server.initialize()
    with contextlib.redirect_stdout(io.StringIO()):manage.backup(d+'/backup.sqlite3')
    with sqlite3.connect(d+'/backup.sqlite3') as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertGreater(c.execute('SELECT count(*) FROM records').fetchone()[0],0)
    self.assertEqual(os.stat(d+'/backup.sqlite3').st_mode&0o777,0o600)
    with self.assertRaises(FileExistsError):manage.backup(d+'/backup.sqlite3')
    with self.assertRaises(ValueError):manage.backup(server.DB)
   finally:server.DB=old
