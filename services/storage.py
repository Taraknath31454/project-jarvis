"""SQLite persistence. Raw commands and personal payloads never enter history."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

class Storage:
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, created TEXT, text TEXT);
                CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, due TEXT, text TEXT, delivered INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, timestamp TEXT, command TEXT, action TEXT, success INTEGER);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def note(self, text):
        with self.connect() as db:
            db.execute('INSERT INTO notes(created,text) VALUES (?,?)', (datetime.now().isoformat(), text))

    def reminder(self, due, text):
        with self.connect() as db:
            db.execute('INSERT INTO reminders(due,text) VALUES (?,?)', (due.isoformat(), text))

    def pending(self):
        with self.connect() as db:
            return db.execute('SELECT id,due,text FROM reminders WHERE delivered=0 ORDER BY due').fetchall()

    def due(self):
        now = datetime.now().isoformat()
        with self.connect() as db:
            return db.execute('SELECT id,text FROM reminders WHERE delivered=0 AND due<=? ORDER BY due', (now,)).fetchall()

    def acknowledge(self, reminder_id):
        with self.connect() as db:
            db.execute('UPDATE reminders SET delivered=1 WHERE id=?', (reminder_id,))

    def history(self, action, success):
        # Canonical recognized command only. Never retain voice text, queries, notes,
        # filenames, clipboard contents, unknown input, or arbitrary exception text.
        with self.connect() as db:
            db.execute('INSERT INTO history(timestamp,command,action,success) VALUES (?,?,?,?)',
                       (datetime.now().isoformat(timespec='seconds'), action.replace('_', ' '), action, int(success)))
            db.execute('DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT 500)')

    def recent(self):
        with self.connect() as db:
            return db.execute('SELECT timestamp,command,success FROM history ORDER BY id DESC LIMIT 12').fetchall()

    def notes(self, limit=100):
        with self.connect() as db:
            return db.execute('SELECT id,created,text FROM notes ORDER BY id DESC LIMIT ?', (limit,)).fetchall()

    def clear_history(self):
        with self.connect() as db:
            db.execute('DELETE FROM history')
