"""University web application. Student code is sent only to the isolated worker."""
import hashlib
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from sandbox_runner import LANGUAGES, validate_payload

ROOT = Path(__file__).resolve().parent
LESSON_IDS = frozenset(item['id'] for item in json.loads((ROOT / 'public' / 'learning-data.json').read_text())['lessons'])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the private worker credential through a redirect.
        return None


def urlopen(req, timeout):
    return build_opener(NoRedirect).open(req, timeout=timeout)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return salt + ':' + value


def password_matches(password, encoded):
    salt = encoded.split(':')[0]
    return hmac.compare_digest(password_hash(password, salt), encoded)


@contextmanager
def connect(path):
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with connect(path) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          password TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('guest','student','admin')),
          active INTEGER NOT NULL DEFAULT 1, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
          csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires);
        CREATE TABLE IF NOT EXISTS drafts (
          user_id INTEGER NOT NULL REFERENCES users(id), language TEXT NOT NULL,
          code TEXT NOT NULL, stdin TEXT NOT NULL, updated REAL NOT NULL,
          PRIMARY KEY(user_id, language));
        CREATE TABLE IF NOT EXISTS progress (
          user_id INTEGER NOT NULL REFERENCES users(id), lesson_id TEXT NOT NULL,
          completed INTEGER NOT NULL CHECK(completed IN (0,1)), updated REAL NOT NULL,
          PRIMARY KEY(user_id, lesson_id));
        CREATE TABLE IF NOT EXISTS rates (
          key TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS leases (
          id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id INTEGER PRIMARY KEY, user_id INTEGER, event TEXT NOT NULL, language TEXT, created REAL NOT NULL);
        ''')
    path.chmod(0o600)


def create_app(overrides=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATABASE=os.environ.get('DATABASE', str(ROOT / '.data' / 'campus.sqlite3')),
        PUBLIC_ORIGIN=os.environ.get('PUBLIC_ORIGIN', 'http://localhost:8000').rstrip('/'),
        PRODUCTION=os.environ.get('APP_ENV') == 'production',
        RUNNER_URL=os.environ.get('RUNNER_URL', 'http://127.0.0.1:8001').rstrip('/'),
        RUNNER_TOKEN=os.environ.get('RUNNER_TOKEN', ''),
        GUESTS_PER_HOUR=int(os.environ.get('GUESTS_PER_HOUR', '240')),
        REGISTRATIONS_PER_15_MIN=int(os.environ.get('REGISTRATIONS_PER_15_MIN', '120')),
        MAX_ACTIVE_RUNS=max(1, int(os.environ.get('MAX_ACTIVE_RUNS', '4'))),
        MAX_CONTENT_LENGTH=100000,
    )
    if overrides:
        app.config.update(overrides)
    origin = urlsplit(app.config['PUBLIC_ORIGIN'])
    worker = urlsplit(app.config['RUNNER_URL'])
    if origin.scheme not in ('http', 'https') or not origin.netloc or origin.path:
        raise RuntimeError('PUBLIC_ORIGIN must be an origin without a path.')
    if app.config['PRODUCTION'] and (origin.scheme != 'https' or len(app.config['RUNNER_TOKEN']) < 32 or 'REPLACE_' in app.config['RUNNER_TOKEN']):
        raise RuntimeError('Production requires an HTTPS PUBLIC_ORIGIN and a strong RUNNER_TOKEN.')
    if worker.scheme not in ('http', 'https') or not worker.netloc:
        raise RuntimeError('Invalid RUNNER_URL.')
    if worker.scheme == 'http' and worker.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise RuntimeError('Remote workers require HTTPS. Use a localhost SSH tunnel for private HTTP workers.')
    if app.config['PRODUCTION']:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    initialize(app.config['DATABASE'])
    dummy_hash = password_hash(secrets.token_urlsafe(20))

    def database():
        return connect(app.config['DATABASE'])

    def audit(user_id, event, language=None):
        with database() as db:
            db.execute('INSERT INTO audit(user_id,event,language,created) VALUES (?,?,?,?)',
                       (user_id, event, language, time.time()))

    def rate_limit(key, maximum, seconds):
        now = time.time()
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM rates WHERE expires < ?', (now,))
            row = db.execute('SELECT count FROM rates WHERE key=?', (key,)).fetchone()
            if row and row['count'] >= maximum:
                return False
            db.execute('INSERT INTO rates VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now + seconds))
        return True

    def session():
        value = request.cookies.get('campus_session', '')
        if not value or len(value) > 128:
            return None
        with database() as db:
            return db.execute('''SELECT users.id, users.username, users.name, users.role, sessions.csrf
                FROM sessions JOIN users ON users.id=sessions.user_id
                WHERE sessions.hash=? AND sessions.expires>? AND users.active=1''',
                (digest(value), time.time())).fetchone()

    def issue_session(user):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with database() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            old = request.cookies.get('campus_session')
            if old:
                db.execute('DELETE FROM sessions WHERE hash=?', (digest(old),))
            db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(token), user['id'], csrf, time.time() + 12 * 3600))
        response = jsonify(user={key: user[key] for key in ('id', 'username', 'name', 'role')}, csrf=csrf)
        response.set_cookie('campus_session', token, max_age=43200, httponly=True,
                            secure=origin.scheme == 'https', samesite='Strict', path='/')
        return response

    @app.before_request
    def security():
        if request.host != origin.netloc:
            return jsonify(error='Invalid host.'), 400
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            if request.headers.get('Origin') != app.config['PUBLIC_ORIGIN']:
                return jsonify(error='Request origin rejected.'), 403
            if not request.is_json:
                return jsonify(error='JSON content type required.'), 415
        if request.path.startswith('/api/') and request.path not in ('/api/login', '/api/register', '/api/guest', '/api/session', '/api/health'):
            user = session()
            if user is None:
                return jsonify(error='Sign in to continue.'), 401
            request.campus_user = user
            if request.method != 'GET' and not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), user['csrf']):
                return jsonify(error='Session check failed. Reload and try again.'), 403

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['Cache-Control'] = 'no-store'
        if origin.scheme == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Request too large. Limit: 100 KB.'), 413

    @app.errorhandler(500)
    def server_error(error):
        return jsonify(error='Server error. Please try again or contact your administrator.'), 500

    def body():
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    @app.post('/api/guest')
    def guest():
        existing = session()
        if existing:
            return jsonify(user={key: existing[key] for key in ('id', 'username', 'name', 'role')}, csrf=existing['csrf'])
        if not rate_limit('guest:' + request.remote_addr, app.config['GUESTS_PER_HOUR'], 3600):
            return jsonify(error='Too many new workspaces. Please try again later.'), 429
        with database() as db:
            cursor = db.execute('INSERT INTO users(username,name,password,role,created) VALUES (?,?,?,?,?)',
                                ('guest-' + secrets.token_hex(16), 'Guest student', '!', 'guest', time.time()))
            uid = cursor.lastrowid
        return issue_session(dict(id=uid, username='', name='Guest student', role='guest'))

    @app.post('/api/register')
    def register():
        if not rate_limit('register:' + request.remote_addr, app.config['REGISTRATIONS_PER_15_MIN'], 900):
            return jsonify(error='Too many attempts. Try again in 15 minutes.'), 429
        data = body()
        username, password = (data.get(key, '') for key in ('username', 'password'))
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify(error='Invalid registration details.'), 400
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,30}', username) or not 12 <= len(password) <= 256:
            return jsonify(error='Use a username of 3–30 letters, numbers or underscores, and a password of 12–256 characters.'), 400
        encoded = password_hash(password)
        existing = session()
        if existing and existing['role'] != 'guest':
            return jsonify(error='Sign out before creating another account.'), 409
        try:
            with database() as db:
                db.execute('BEGIN IMMEDIATE')
                if existing and existing['role'] == 'guest':
                    uid = existing['id']
                    db.execute("UPDATE users SET username=?,name=?,password=?,role='student' WHERE id=?", (username, username, encoded, uid))
                else:
                    cursor = db.execute('INSERT INTO users(username,name,password,role,created) VALUES (?,?,?,?,?)',
                                        (username, username, encoded, 'student', time.time()))
                    uid = cursor.lastrowid
                user = dict(id=uid, username=username, name=username, role='student')
        except sqlite3.IntegrityError:
            return jsonify(error='Username is unavailable. Choose another one.'), 400
        audit(user['id'], 'register')
        return issue_session(user), 201

    @app.post('/api/login')
    def login():
        data = body()
        username, password = data.get('username', ''), data.get('password', '')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 254 or len(password) > 256:
            return jsonify(error='Invalid username or password.'), 400
        username = username.strip().lower()
        if not rate_limit('login-ip:' + request.remote_addr, 30, 900) or not rate_limit('login-username:' + digest(username), 10, 900):
            return jsonify(error='Too many sign-in attempts. Try again in 15 minutes.'), 429
        with database() as db:
            user = db.execute("SELECT * FROM users WHERE username=? AND role != 'guest'", (username,)).fetchone()
        valid = password_matches(password, user['password'] if user else dummy_hash)
        if not user or not valid or not user['active']:
            return jsonify(error='Invalid username or password.'), 401
        audit(user['id'], 'login')
        return issue_session(user)

    @app.get('/api/session')
    def get_session():
        user = session()
        if user is None:
            return jsonify(user=None), 200
        return jsonify(user={key: user[key] for key in ('id', 'username', 'name', 'role')}, csrf=user['csrf'])

    @app.post('/api/logout')
    def logout():
        with database() as db:
            db.execute('DELETE FROM sessions WHERE hash=?', (digest(request.cookies.get('campus_session', '')),))
        response = jsonify(ok=True)
        response.delete_cookie('campus_session', path='/', secure=origin.scheme == 'https', httponly=True, samesite='Strict')
        return response

    @app.get('/api/progress')
    def get_progress():
        with database() as db:
            rows = db.execute('SELECT lesson_id,completed FROM progress WHERE user_id=?', (request.campus_user['id'],)).fetchall()
        return jsonify(progress={row['lesson_id']: bool(row['completed']) for row in rows})

    @app.put('/api/progress/<lesson_id>')
    def save_progress(lesson_id):
        data = body()
        if lesson_id not in LESSON_IDS or type(data.get('completed')) is not bool:
            return jsonify(error='Unknown lesson or invalid completion flag.'), 400
        uid = request.campus_user['id']
        if not rate_limit(f'progress:{uid}', 60, 60):
            return jsonify(error='Too many updates. Please try again shortly.'), 429
        with database() as db:
            db.execute('''INSERT INTO progress VALUES (?,?,?,?) ON CONFLICT(user_id,lesson_id)
                DO UPDATE SET completed=excluded.completed,updated=excluded.updated''',
                (uid, lesson_id, int(data['completed']), time.time()))
        return jsonify(ok=True)

    @app.get('/api/drafts')
    def get_drafts():
        with database() as db:
            rows = db.execute('SELECT language,code,stdin,updated FROM drafts WHERE user_id=?', (request.campus_user['id'],)).fetchall()
        return jsonify(drafts={row['language']: dict(code=row['code'], stdin=row['stdin'], updated=row['updated']) for row in rows})

    @app.put('/api/drafts/<language>')
    def save_draft(language):
        try:
            data = validate_payload({**body(), 'language': language})
        except ValueError as error:
            return jsonify(error=str(error)), 400
        user_id = request.campus_user['id']
        if not rate_limit(f'save:{user_id}', 120, 60):
            return jsonify(error='Saving too frequently. Try again shortly.'), 429
        with database() as db:
            db.execute('''INSERT INTO drafts VALUES (?,?,?,?,?) ON CONFLICT(user_id,language)
                DO UPDATE SET code=excluded.code,stdin=excluded.stdin,updated=excluded.updated''',
                (user_id, language, data['code'], data['stdin'], time.time()))
        return jsonify(ok=True)

    def worker_request(endpoint, payload=None):
        token = app.config['RUNNER_TOKEN']
        if len(token) < 32:
            return {'error': 'Secure runner is not configured. Host execution is disabled.'}, 503
        req = Request(app.config['RUNNER_URL'] + endpoint,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        try:
            with urlopen(req, timeout=50 if payload is not None else 6) as response:
                result = response.read(2 * 1024 * 1024 + 1)
                if len(result) > 2 * 1024 * 1024:
                    return {'error': 'Invalid worker response.'}, 503
                return json.loads(result), 200
        except HTTPError as error:
            status = 429 if error.code == 429 else 503
            error.close()
            return {'error': 'Secure runner is busy or unavailable. Host execution is disabled.'}, status
        except (URLError, TimeoutError, OSError, ValueError):
            return {'error': 'Secure runner unavailable. Ask your administrator to check the worker. Host execution is disabled.'}, 503

    @app.get('/api/health')
    def health():
        return jsonify(ok=True)

    @app.get('/api/runner-status')
    def runner_status():
        result, status = worker_request('/health')
        return jsonify(ready=status == 200 and result.get('ready') is True)

    @app.post('/api/run')
    def run():
        try:
            payload = validate_payload(body())
        except ValueError as error:
            return jsonify(error=str(error)), 400
        uid = request.campus_user['id']
        if not rate_limit('run-ip:' + request.remote_addr, 60, 60):
            return jsonify(error='Too many runs from this network. Try again shortly.'), 429
        if not rate_limit(f'run-minute:{uid}', 20, 60) or not rate_limit(f'run-day:{uid}', 500, 86400):
            return jsonify(error='Execution quota reached. Please try again later.'), 429
        lease = secrets.token_hex(16)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM leases WHERE expires < ?', (time.time(),))
            if db.execute('SELECT 1 FROM leases WHERE user_id=?', (uid,)).fetchone() or db.execute('SELECT COUNT(*) FROM leases').fetchone()[0] >= app.config['MAX_ACTIVE_RUNS']:
                return jsonify(error='Runner is busy or your program is already running. Try again shortly.'), 429
            db.execute('INSERT INTO leases VALUES (?,?,?)', (lease, uid, time.time() + 90))
        try:
            result, status = worker_request('/execute', payload)
            audit(uid, 'run' if status == 200 else 'run_unavailable', payload['language'])
            return jsonify(result), status
        finally:
            with database() as db:
                db.execute('DELETE FROM leases WHERE id=?', (lease,))

    @app.get('/')
    def home():
        return send_from_directory(ROOT / 'public', 'index.html')

    @app.get('/<path:filename>')
    def static_file(filename):
        if filename.startswith('api/'):
            return jsonify(error='Not found.'), 404
        return send_from_directory(ROOT / 'public', filename)

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=int(os.environ.get('PORT', '8000')), threaded=True)
