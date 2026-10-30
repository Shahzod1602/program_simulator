"""Remove only stale Campus Code containers after a runner crash. Worker host only."""
from datetime import datetime, timezone
import json
import subprocess
import time


def reap():
    listing = subprocess.run(['docker', 'ps', '-aq', '--filter', 'label=campus.sandbox=1'],
                             capture_output=True, text=True, check=True, timeout=10)
    removed = 0
    for container_id in listing.stdout.split():
        inspected = subprocess.run(['docker', 'inspect', container_id], capture_output=True,
                                   text=True, timeout=5)
        if inspected.returncode:
            continue
        record = json.loads(inspected.stdout)[0]
        if record.get('Config', {}).get('Labels', {}).get('campus.sandbox') != '1' or not record.get('Name', '').startswith('/campus-'):
            continue
        created = datetime.fromisoformat(record['Created'].replace('Z', '+00:00')).timestamp()
        if time.time() - created > 90:
            subprocess.run(['docker', 'rm', '-f', container_id], check=True, timeout=10)
            removed += 1
    print(f'Removed {removed} expired Campus Code containers.')


if __name__ == '__main__':
    reap()
