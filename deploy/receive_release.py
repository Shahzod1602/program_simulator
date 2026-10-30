#!/usr/bin/python3
"""Root-owned forced SSH deployment receiver. Never run source or pip as root."""
import fcntl
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request

BASE = Path('/opt/campus-code')
CURRENT = Path('/opt/campus-current')
RELEASES = Path('/opt/campus-releases')

def switch(target):
    temporary = Path('/opt/.campus-current-next')
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    temporary.replace(CURRENT)

def restart():
    subprocess.run(['systemctl', 'restart', 'campus-runner', 'campus-web'], check=True)

def healthy():
    for _ in range(30):
        try:
            request = urllib.request.Request('http://127.0.0.1:8010/api/health', headers={'Host': 'autplatform.uz'})
            with urllib.request.urlopen(request, timeout=2) as response:
                if response.status == 200 and b'"ok":true' in response.read().replace(b' ', b''):
                    return True
        except (OSError, ValueError):
            pass
        time.sleep(1)
    return False

def unpack_release(archive):
    release = RELEASES / (hashlib.sha256(archive).hexdigest()[:16] + '-' + str(time.time_ns()))
    RELEASES.mkdir(mode=0o755, exist_ok=True)
    # A fresh directory, regular files only, no symbolic links or traversal.
    release.mkdir(mode=0o755)
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
            for member in bundle:
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or any(p.startswith('.') for p in name.parts):
                    raise ValueError('Hidden or unsafe release path')
                target = release.joinpath(*name.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    total += member.size
                    if total > 20 * 1024 * 1024:
                        raise ValueError('Extracted release too large')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as output:
                        shutil.copyfileobj(bundle.extractfile(member), output)
                    target.chmod(0o644)
                else:
                    raise ValueError('Only directories and regular files are permitted')
        # Dependency/runtime upgrades require a separate administrator review.
        # Do not execute repository Dockerfiles, install hooks or pip as root.
        for name in ('requirements.lock', 'requirements.txt', 'sandbox/Dockerfile', 'sandbox/guest.py'):
            if (release / name).read_bytes() != (BASE / name).read_bytes():
                raise ValueError(f'Administrator must update runtime baseline first: {name}')
        for name in ('server.py', 'sandbox_runner.py', 'public/index.html'):
            if not (release / name).is_file():
                raise ValueError(f'Missing {name}')
        (release / '.venv').symlink_to(BASE / '.venv')
    except Exception:
        shutil.rmtree(release)
        raise
    return release

def main():
    lock = open('/run/lock/campus-deploy.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    archive = sys.stdin.buffer.read(20 * 1024 * 1024 + 1)
    if len(archive) > 20 * 1024 * 1024:
        raise ValueError('Release exceeds 20 MiB')
    release = unpack_release(archive)
    # Back up the live database consistently; no source-supplied commands.
    backup_dir = Path('/var/backups/campus-code')
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    backup = backup_dir / (release.name + '.sqlite3')
    with sqlite3.connect('/var/lib/campus-code/campus.sqlite3') as source:
        with sqlite3.connect(backup) as destination:
            source.backup(destination)
    backup.chmod(0o600)
    previous = CURRENT.resolve()
    switch(release)
    try:
        restart()
        if not healthy():
            raise RuntimeError('New release health check failed')
    except Exception:
        switch(previous)
        restart()
        raise
    print('Deployed release:', release.name)
    # Retain current and previous releases plus the latest five backups.
    for path in RELEASES.iterdir():
        if path.is_dir() and path.resolve() not in (release, previous):
            shutil.rmtree(path)
    for old in sorted(backup_dir.glob('*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)[5:]:
        old.unlink()

if __name__ == '__main__':
    main()
