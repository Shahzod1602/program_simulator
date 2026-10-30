"""Private runner service. Requires Docker + gVisor on a dedicated Linux worker."""
import hmac
import json
import os
import selectors
import shutil
import subprocess
import threading
import time
import uuid

from flask import Flask, jsonify, request

LANGUAGES = frozenset(('python', 'cpp', 'c', 'javascript', 'java', 'go', 'ruby', 'sql'))
IMAGE = os.environ.get('SANDBOX_IMAGE', 'campus-sandbox:1')
MAX_RESPONSE = 2 * 1024 * 1024
SLOTS = threading.BoundedSemaphore(max(1, int(os.environ.get('RUNNER_SLOTS', '4'))))


class SandboxUnavailable(Exception):
    pass


def validate_payload(data):
    if not isinstance(data, dict) or not isinstance(data.get('language'), str) or data['language'] not in LANGUAGES:
        raise ValueError('Unsupported language.')
    if not isinstance(data.get('code'), str) or not isinstance(data.get('stdin', ''), str):
        raise ValueError('Code and input must be text.')
    if len(data['code'].encode()) > 60000 or len(data.get('stdin', '').encode()) > 16000:
        raise ValueError('Code is limited to 60 KB and input to 16 KB.')
    return {key: data.get(key, '') for key in ('language', 'code', 'stdin')}


def docker_command(name):
    # No user-controlled commands, images, mounts, runtime, environment or network options.
    return ['docker', 'run', '--rm', '--pull=never', '--name', name, '--runtime=runsc',
            '--label=campus.sandbox=1', '--stop-timeout=1',
            '--network=none', '--read-only', '--user=10001:10001', '--cap-drop=ALL',
            '--security-opt=no-new-privileges:true', '--pids-limit=64', '--memory=512m',
            '--memory-swap=512m', '--cpus=1', '--ulimit=nofile=128:128',
            '--ulimit=fsize=33554432:33554432', '--ulimit=core=0:0',
            '--tmpfs=/work:rw,exec,nosuid,nodev,size=96m,uid=10001,gid=10001,mode=700',
            '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=96m,uid=10001,gid=10001,mode=700',
            '--log-driver=none', '--workdir=/work', '-i', IMAGE]


def sandbox_ready():
    if not shutil.which('docker'):
        return False
    try:
        result = subprocess.run(['docker', 'info', '--format', '{{json .Runtimes}}'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode or 'runsc' not in json.loads(result.stdout):
            return False
        image = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True, timeout=5)
        return image.returncode == 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False


def communicate_bounded(process, data, timeout=40):
    selector = selectors.DefaultSelector()
    for stream, name, event in [(process.stdin, 'stdin', selectors.EVENT_WRITE),
                                (process.stdout, 'stdout', selectors.EVENT_READ),
                                (process.stderr, 'stderr', selectors.EVENT_READ)]:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, event, name)
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired('sandbox', timeout)
            for key, _ in selector.select(.1):
                if key.data == 'stdin':
                    try:
                        data = data[os.write(key.fd, data[:4096]):]
                    except BrokenPipeError:
                        data = b''
                    if not data:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                else:
                    block = os.read(key.fd, 8192)
                    if not block:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        if len(output[key.data]) + len(block) > MAX_RESPONSE:
                            raise SandboxUnavailable('Sandbox output limit exceeded.')
                        output[key.data].extend(block)
        process.wait(timeout=max(.01, deadline-time.monotonic()))
        return bytes(output['stdout']), bytes(output['stderr'])
    finally:
        selector.close()


def run_sandbox(payload):
    payload = validate_payload(payload)
    if not sandbox_ready():
        raise SandboxUnavailable('Secure runner unavailable. Docker, gVisor (runsc), and the sandbox image are required. Host execution is disabled.')
    name = 'campus-' + uuid.uuid4().hex
    started = time.monotonic()
    process = None
    try:
        process = subprocess.Popen(docker_command(name), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = communicate_bounded(process, json.dumps(payload).encode())
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return dict(stdout='', stderr='Sandbox wall-clock limit reached.', exitCode=124,
                        timedOut=True, truncated=False, phase='run', durationMs=40000)
        if len(stdout) > MAX_RESPONSE:
            raise SandboxUnavailable('Runner returned an oversized response.')
        if process.returncode:
            # Do not leak worker internals to students.
            if process.returncode == 137:
                return dict(stdout='', stderr='Sandbox memory or process limit reached.', exitCode=137,
                            timedOut=False, truncated=False, phase='run', durationMs=round((time.monotonic()-started)*1000))
            raise SandboxUnavailable('Sandbox failed to start or was interrupted. Ask the administrator to check the runner.')
        try:
            result = json.loads(stdout)
            if not isinstance(result, dict) or not all(key in result for key in ('stdout', 'stderr', 'exitCode', 'timedOut', 'truncated', 'phase', 'durationMs')):
                raise ValueError()
            return result
        except (ValueError, TypeError):
            raise SandboxUnavailable('Sandbox returned an invalid result.') from None
    except OSError as error:
        raise SandboxUnavailable('Cannot contact the secure runner.') from error
    finally:
        if process and process.poll() is None:
            process.kill()
            process.wait()
        if process:
            for stream in (process.stdin, process.stdout, process.stderr):
                if not stream.closed:
                    stream.close()
        try:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def create_runner():
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 100000
    token = os.environ.get('RUNNER_TOKEN', '')
    if len(token) < 32 or 'REPLACE_' in token:
        raise RuntimeError('Set RUNNER_TOKEN to a random secret of at least 32 characters.')

    @app.before_request
    def authorize():
        if not hmac.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + token):
            return jsonify(error='Unauthorized'), 401

    @app.get('/health')
    def health():
        ready = sandbox_ready()
        return jsonify(ready=ready), 200 if ready else 503

    @app.post('/execute')
    def execute():
        try:
            payload = validate_payload(request.get_json(silent=True))
        except ValueError as error:
            return jsonify(error=str(error)), 400
        if not SLOTS.acquire(blocking=False):
            return jsonify(error='Runner is busy. Try again shortly.'), 429
        try:
            return jsonify(run_sandbox(payload))
        except SandboxUnavailable as error:
            return jsonify(error=str(error)), 503
        finally:
            SLOTS.release()

    return app
