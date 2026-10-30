"""Account recovery and retention. Run only as the application administrator."""
import argparse
import getpass
import os
import time

from server import connect, initialize, password_hash

parser = argparse.ArgumentParser()
parser.add_argument('--database', default=os.environ.get('DATABASE', '.data/campus.sqlite3'))
commands = parser.add_subparsers(dest='command', required=True)
reset = commands.add_parser('reset-password')
reset.add_argument('username')
disable = commands.add_parser('disable-user')
disable.add_argument('username')
commands.add_parser('cleanup')
args = parser.parse_args()
initialize(args.database)
if args.command == 'cleanup':
    with connect(args.database) as db:
        now = time.time()
        for table in ('sessions', 'rates', 'leases'):
            db.execute(f'DELETE FROM {table} WHERE expires < ?', (now,))
        # Guest drafts and guest accounts expire after one day. Named accounts stay.
        for table in ('drafts', 'progress', 'sessions', 'leases'):
            db.execute(f"DELETE FROM {table} WHERE user_id IN (SELECT id FROM users WHERE role='guest' AND created < ?)", (now - 86400,))
        db.execute("DELETE FROM users WHERE role='guest' AND created < ?", (now - 86400,))
        db.execute('DELETE FROM audit WHERE created < ?', (now - 90 * 86400,))
    print('Expired sessions, day-old guest workspaces, and audit records older than 90 days removed.')
else:
    with connect(args.database) as db:
        user = db.execute("SELECT id FROM users WHERE username=? AND role != 'guest'", (args.username.strip().lower(),)).fetchone()
        if not user:
            parser.error('Account not found.')
        if args.command == 'reset-password':
            password = getpass.getpass('New password (at least 12 characters): ')
            if not 12 <= len(password) <= 256 or password != getpass.getpass('Repeat password: '):
                parser.error('Password is too short, too long, or does not match.')
            db.execute('UPDATE users SET password=? WHERE id=?', (password_hash(password), user['id']))
        else:
            db.execute('UPDATE users SET active=0 WHERE id=?', (user['id'],))
        db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
    print('Account updated; existing sessions revoked.')
