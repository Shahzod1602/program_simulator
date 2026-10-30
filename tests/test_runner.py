import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from server import connect, create_app, digest, password_matches
from sandbox_runner import (SandboxUnavailable, communicate_bounded, create_runner,
                            docker_command, run_sandbox, validate_payload)
from reap_sandboxes import reap

ORIGIN = 'http://localhost:8000'
PASSWORD = 'test-password-only-12345'


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'test.sqlite3')
        self.app = create_app({'DATABASE': self.path, 'TESTING': True, 'PUBLIC_ORIGIN': ORIGIN, 'RUNNER_TOKEN': ''})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def send(self, path, data=None, client=None, csrf=None, method='POST', origin=ORIGIN):
        headers = {'Origin': origin}
        if csrf:
            headers['X-CSRF-Token'] = csrf
        return (client or self.client).open(path, method=method, json=data or {}, base_url=ORIGIN, headers=headers)

    def register(self, username='student_one', client=None):
        response = self.send('/api/register', {'username': username, 'password': PASSWORD}, client)
        self.assertEqual(response.status_code, 201, response.json)
        return response.json

    def get(self, path, client=None):
        return (client or self.client).get(path, base_url=ORIGIN)

    def test_guest_access_without_email_or_login(self):
        guest = self.send('/api/guest')
        self.assertEqual(guest.status_code, 200)
        self.assertEqual(guest.json['user']['role'], 'guest')
        self.assertNotIn('email', guest.json['user'])
        repeated = self.send('/api/guest')
        self.assertEqual(repeated.json['user']['id'], guest.json['user']['id'])
        self.assertEqual(self.get('/api/drafts').status_code, 200)

    def test_guest_conversion_keeps_saved_code(self):
        guest = self.send('/api/guest').json
        response = self.send('/api/drafts/python', {'code':'print(42)', 'stdin':''}, csrf=guest['csrf'], method='PUT')
        self.assertEqual(response.status_code, 200)
        account = self.register()
        self.assertEqual(account['user']['id'], guest['user']['id'])
        self.assertEqual(self.get('/api/drafts').json['drafts']['python']['code'], 'print(42)')

    def test_password_hash_and_cookie(self):
        result = self.register()
        with connect(self.path) as db:
            user = db.execute('SELECT * FROM users').fetchone()
            self.assertNotEqual(user['password'], PASSWORD)
            self.assertTrue(password_matches(PASSWORD, user['password']))
            session = db.execute('SELECT * FROM sessions').fetchone()
            self.assertEqual(len(session['hash']), 64)
        cookie = self.client.get_cookie('campus_session')
        self.assertNotEqual(cookie.value, session['hash'])
        self.assertTrue(cookie.http_only)
        self.assertEqual(cookie.same_site, 'Strict')

    def test_login_and_logout_revoke_session(self):
        registered = self.register()
        token = self.client.get_cookie('campus_session').value
        response = self.send('/api/logout', csrf=registered['csrf'])
        self.assertEqual(response.status_code, 200)
        self.client.set_cookie('campus_session', token)
        self.assertEqual(self.get('/api/drafts').status_code, 401)
        response = self.send('/api/login', {'username':'student_one', 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.get_cookie('campus_session').value, token)

    def test_invalid_login_does_not_disclose_account(self):
        self.register()
        responses = [self.send('/api/login', {'username': name, 'password':'wrong'}).json
                     for name in ('student_one', 'nonexistent')]
        self.assertEqual(responses[0], responses[1])

    def test_guests_cannot_log_in_with_internal_username(self):
        self.send('/api/guest')
        with connect(self.path) as db:
            username = db.execute('SELECT username FROM users').fetchone()[0]
        response = self.send('/api/login', {'username':username, 'password':'!'})
        self.assertEqual(response.status_code, 401)

    def test_csrf_origin_and_host(self):
        data = self.register()
        self.assertEqual(self.send('/api/run', {'language':'python','code':''}).status_code, 403)
        self.assertEqual(self.send('/api/run', {'language':'python','code':''}, csrf=data['csrf'], origin='https://evil.test').status_code, 403)
        self.assertEqual(self.client.get('/api/session', base_url='http://evil.test').status_code, 400)
        self.assertEqual(self.client.post('/api/login', json={}, base_url=ORIGIN).status_code, 403)

    def test_two_students_have_separate_drafts(self):
        first = self.register()
        second_client = self.app.test_client()
        second = self.register('student_two', second_client)
        for code, client, csrf in [('private first', self.client, first['csrf']), ('private second', second_client, second['csrf'])]:
            response = self.send('/api/drafts/python', {'code':code}, client, csrf, 'PUT')
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get('/api/drafts').json['drafts']['python']['code'], 'private first')
        self.assertEqual(self.get('/api/drafts', second_client).json['drafts']['python']['code'], 'private second')

    def test_unconfigured_runner_never_executes_host_code(self):
        data = self.register()
        with patch('subprocess.Popen') as host:
            response = self.send('/api/run', {'language':'python','code':'print(42)'}, csrf=data['csrf'])
            self.assertEqual(response.status_code, 503)
            self.assertIn('Host execution is disabled', response.json['error'])
            host.assert_not_called()
        with connect(self.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM leases').fetchone()[0], 0)

    def test_execution_only_forwards_to_private_worker(self):
        data = self.register()
        self.app.config['RUNNER_TOKEN'] = 'x' * 40
        payload = {'language':'python', 'code':'print(42)', 'stdin':''}
        result = dict(stdout='42\n', stderr='', exitCode=0, timedOut=False, truncated=False, phase='run', durationMs=12)
        with patch('server.urlopen', return_value=io.BytesIO(json.dumps(result).encode())) as worker, patch('subprocess.Popen') as host:
            response = self.send('/api/run', payload, csrf=data['csrf'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json, result)
            req = worker.call_args.args[0]
            self.assertEqual(req.full_url, 'http://127.0.0.1:8001/execute')
            self.assertEqual(json.loads(req.data), payload)
            self.assertEqual(req.get_header('Authorization'), 'Bearer ' + 'x' * 40)
            host.assert_not_called()

    def test_run_quotas_and_active_lease(self):
        data = self.register()
        with connect(self.path) as db:
            db.execute('INSERT INTO leases VALUES (?,?,?)', ('active', data['user']['id'], 99999999999))
        self.assertEqual(self.send('/api/run', {'language':'python','code':''}, csrf=data['csrf']).status_code, 429)
        with connect(self.path) as db:
            db.execute('DELETE FROM leases')
            db.execute('INSERT OR REPLACE INTO rates VALUES (?,?,?)', (f"run-minute:{data['user']['id']}", 20, 99999999999))
        self.assertEqual(self.send('/api/run', {'language':'python','code':''}, csrf=data['csrf']).status_code, 429)

    def test_request_size_validation(self):
        data = self.register()
        for payload in ({'language':'unknown','code':''}, {'language':[],'code':''}, {'language':'python','code':'x'*60001}, {'language':'python','code':'','stdin':'x'*16001}):
            self.assertEqual(self.send('/api/run', payload, csrf=data['csrf']).status_code, 400)
        self.assertEqual(self.send('/api/run', {'x':'a'*100001}, csrf=data['csrf']).status_code, 413)

    def test_weak_password_and_username_validation(self):
        for username, password in [('ab', PASSWORD), ('has space', PASSWORD), ('student', 'short')]:
            response = self.send('/api/register', {'username':username,'password':password})
            self.assertEqual(response.status_code, 400)

    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.send('/api/login', {'username':'unknown', 'password':'wrong'}).status_code, 401)
        self.assertEqual(self.send('/api/login', {'username':'unknown','password':'wrong'}).status_code, 429)

    def test_disabled_and_expired_sessions(self):
        self.register()
        with connect(self.path) as db:
            db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.get('/api/drafts').status_code, 401)
        logged_in = self.send('/api/login', {'username':'student_one','password':PASSWORD})
        self.assertEqual(logged_in.status_code, 200)
        with connect(self.path) as db:
            db.execute('UPDATE users SET active=0')
        self.assertEqual(self.get('/api/drafts').status_code, 401)

    def test_headers(self):
        response = self.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        response.close()

    def test_production_requires_https_and_token(self):
        with self.assertRaises(RuntimeError):
            create_app({'DATABASE': self.path, 'PRODUCTION':True, 'PUBLIC_ORIGIN':ORIGIN})
        with self.assertRaises(RuntimeError):
            create_app({'DATABASE': self.path, 'RUNNER_URL':'http://remote.test:8001'})
        secure = create_app({'DATABASE':self.path, 'PUBLIC_ORIGIN':'https://lab.example.edu', 'PRODUCTION':True, 'RUNNER_TOKEN':'x'*40})
        client = secure.test_client()
        response = client.post('/api/guest', base_url='https://lab.example.edu', headers={'Origin':'https://lab.example.edu'}, json={})
        self.assertTrue(client.get_cookie('campus_session', domain='lab.example.edu').secure)
        self.assertIn('max-age=', response.headers['Strict-Transport-Security'])


class SandboxContractTests(unittest.TestCase):
    def test_reaper_only_removes_expired_campus_containers(self):
        stale = {'Name':'/campus-fixture', 'Config':{'Labels':{'campus.sandbox':'1'}}, 'Created':'2000-01-01T00:00:00Z'}
        unrelated = {'Name':'/other-service', 'Config':{'Labels':{}}, 'Created':'2000-01-01T00:00:00Z'}
        responses = [subprocess.CompletedProcess([], 0, 'stale\nother\n'),
                     subprocess.CompletedProcess([], 0, json.dumps([stale])),
                     subprocess.CompletedProcess([], 0),
                     subprocess.CompletedProcess([], 0, json.dumps([unrelated]))]
        with patch('reap_sandboxes.subprocess.run', side_effect=responses) as docker:
            reap()
        removals = [call.args[0] for call in docker.call_args_list if call.args[0][1] == 'rm']
        self.assertEqual(removals, [['docker', 'rm', '-f', 'stale']])

    def test_isolation_flags_and_no_mounts(self):
        command = docker_command('test')
        for flag in ('--runtime=runsc', '--network=none', '--read-only', '--user=10001:10001',
                     '--cap-drop=ALL', '--security-opt=no-new-privileges:true', '--pids-limit=64',
                     '--memory=512m', '--cpus=1', '--pull=never', '--log-driver=none'):
            self.assertIn(flag, command)
        self.assertNotIn('--privileged', command)
        self.assertFalse(any(value.startswith(('-v', '--volume', '--mount')) for value in command))

    def test_missing_sandbox_fails_closed(self):
        with patch('sandbox_runner.sandbox_ready', return_value=False), patch('subprocess.Popen') as process:
            with self.assertRaises(SandboxUnavailable):
                run_sandbox({'language':'python', 'code':'print(42)', 'stdin':''})
            process.assert_not_called()

    def test_worker_requires_secret(self):
        with patch.dict(os.environ, {'RUNNER_TOKEN':''}):
            with self.assertRaises(RuntimeError):
                create_runner()
        with patch.dict(os.environ, {'RUNNER_TOKEN':'x'*40}):
            client = create_runner().test_client()
        self.assertEqual(client.post('/execute', json={}).status_code, 401)
        with patch('sandbox_runner.sandbox_ready', return_value=False):
            self.assertEqual(client.get('/health', headers={'Authorization':'Bearer '+'x'*40}).status_code, 503)

    def test_worker_validation(self):
        for data in (None, [], {'language':[]}, {'language':'python','code':4}):
            with self.assertRaises(ValueError):
                validate_payload(data)

    def test_host_output_collection_is_bounded(self):
        # Trusted fixed test fixture, not submitted student code.
        process = subprocess.Popen([sys.executable, '-c', 'print("x" * 2200000)'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with self.assertRaises(SandboxUnavailable):
                communicate_bounded(process, b'')
        finally:
            process.kill(); process.wait()
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()


@unittest.skipUnless(os.environ.get('RUN_SANDBOX_TESTS') == '1', 'Requires Linux Docker + gVisor + built sandbox image')
class RealSandboxTests(unittest.TestCase):
    def run_code(self, language, code, stdin=''):
        return run_sandbox(validate_payload(dict(language=language, code=code, stdin=stdin)))

    def test_all_languages(self):
        cases = [('python', 'print(int(input())*2)'),
                 ('javascript', 'console.log(Number(require("fs").readFileSync(0,"utf8"))*2)'),
                 ('ruby', 'puts gets.to_i*2'),
                 ('sql', 'SELECT 21*2 AS result;'),
                 ('c', '#include <stdio.h>\nint main(){int n;scanf("%d",&n);printf("%d",n*2);}'),
                 ('cpp', '#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<n*2;}'),
                 ('java', 'import java.util.Scanner; public class Main {public static void main(String[] a){System.out.println(new Scanner(System.in).nextInt()*2);}}'),
                 ('go', 'package main\nimport "fmt"\nfunc main(){var n int;fmt.Scan(&n);fmt.Println(n*2)}')]
        for language, code in cases:
            with self.subTest(language=language):
                result = self.run_code(language, code, '21')
                self.assertEqual(result['exitCode'], 0, result)
                self.assertIn('42', result['stdout'])

    def test_timeout(self):
        self.assertTrue(self.run_code('python', 'while True: pass')['timedOut'])

    def test_output_flood(self):
        self.assertTrue(self.run_code('python', 'while True: print("x"*10000)')['truncated'])

    def test_network_and_root_filesystem_blocked(self):
        program = '''import socket
try:
    socket.create_connection(("1.1.1.1",443), timeout=1)
    print("NETWORK_OPEN")
except OSError:
    print("NETWORK_BLOCKED")
try:
    open("/etc/campus-probe", "w").write("test")
    print("ROOT_WRITABLE")
except OSError:
    print("ROOT_BLOCKED")
'''
        result = self.run_code('python', program)
        self.assertIn('NETWORK_BLOCKED', result['stdout'])
        self.assertIn('ROOT_BLOCKED', result['stdout'])
        self.assertNotIn('NETWORK_OPEN', result['stdout'])

    def test_memory_limit(self):
        result = self.run_code('python', 'x = bytearray(1024*1024*1024); print("ALLOCATED")')
        self.assertNotEqual(result['exitCode'], 0)
        self.assertNotIn('ALLOCATED', result['stdout'])

    def test_temporary_files_disappear(self):
        self.run_code('python', 'open("marker", "w").write("private")')
        result = self.run_code('python', 'import os; print(os.path.exists("marker"))')
        self.assertEqual(result['stdout'].strip(), 'False')

    def test_host_file_is_not_mounted(self):
        with tempfile.NamedTemporaryFile() as marker:
            result = self.run_code('python', 'import os; print(os.path.exists(' + repr(marker.name) + '))')
            self.assertEqual(result['stdout'].strip(), 'False')
