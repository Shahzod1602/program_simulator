"""Runs ONLY inside the disposable sandbox image. Never import on the web host."""
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import time

LIMIT = 128 * 1024
LANGUAGES = {
    'python': ('main.py', None, ['python3', '-I', '-u', 'main.py']),
    'javascript': ('main.js', None, ['node', '--max-old-space-size=128', 'main.js']),
    'ruby': ('main.rb', None, ['ruby', 'main.rb']),
    'sql': ('main.sql', None, ['sqlite3', '-batch', '-header', '-column', ':memory:', '.read main.sql']),
    'c': ('main.c', ['gcc', '-std=c17', '-Wall', '-Wextra', 'main.c', '-o', 'program'], ['./program']),
    'cpp': ('main.cpp', ['g++', '-std=c++17', '-Wall', '-Wextra', 'main.cpp', '-o', 'program'], ['./program']),
    'java': ('Main.java', ['javac', '-J-Xmx192m', 'Main.java'], ['java', '-Xmx128m', '-XX:ActiveProcessorCount=1', '-XX:ReservedCodeCacheSize=32m', '-cp', '.', 'Main']),
    'go': ('main.go', ['go', 'build', '-o', 'program', 'main.go'], ['./program']),
}


def execute(command, stdin, timeout):
    # Both streams are drained incrementally. Stop the program at the output limit.
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    selector = selectors.DefaultSelector()
    for stream, label in [(process.stdout, 'stdout'), (process.stderr, 'stderr')]:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, label)
    data = stdin.encode()
    if data:
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
    else:
        process.stdin.close()
    result = dict(stdout=bytearray(), stderr=bytearray(), timedOut=False, truncated=False)
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                result['timedOut'] = True
                break
            for key, _ in selector.select(min(.1, max(0, deadline - time.monotonic()))):
                if key.data == 'stdin':
                    try:
                        sent = os.write(key.fd, data[:4096])
                        data = data[sent:]
                    except BrokenPipeError:
                        data = b''
                    if not data:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    continue
                block = os.read(key.fd, 8192)
                if not block:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                target = result[key.data]
                available = LIMIT - len(target)
                target.extend(block[:available])
                if len(block) > available:
                    result['truncated'] = True
                    break
            if result['truncated']:
                break
        if process.poll() is None and not result['timedOut'] and not result['truncated']:
            try:
                process.wait(timeout=max(.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                result['timedOut'] = True
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        selector.close()
        for stream in (process.stdin, process.stdout, process.stderr):
            if not stream.closed:
                stream.close()
    result['exitCode'] = process.returncode
    for stream in ('stdout', 'stderr'):
        result[stream] = result[stream].decode('utf-8', 'replace')
    return result


def main():
    request = json.loads(sys.stdin.buffer.read(100001))
    filename, compiler, command = LANGUAGES[request['language']]
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    Path(filename).write_text(request['code'], encoding='utf-8')
    start = time.monotonic()
    phase = 'run'
    if compiler:
        result = execute(compiler, '', 30)
        phase = 'compile'
        if not result['exitCode'] and not result['timedOut'] and not result['truncated']:
            warnings = result['stderr']
            result = execute(command, request.get('stdin', ''), 5)
            result['stderr'] = (warnings + result['stderr'])[:LIMIT]
            phase = 'run'
    else:
        result = execute(command, request.get('stdin', ''), 5)
    result.update(phase=phase, durationMs=round((time.monotonic() - start) * 1000))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
