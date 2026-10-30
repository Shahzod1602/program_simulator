"""Exercise the privileged receiver's archive boundary without root access."""
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).resolve().parents[1] / 'deploy/receive_release.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name) / 'base'
        self.releases = Path(self.directory.name) / 'releases'
        self.files = {name: b'baseline' for name in ('requirements.lock', 'requirements.txt', 'sandbox/Dockerfile', 'sandbox/guest.py', 'server.py', 'sandbox_runner.py', 'public/index.html')}
        for name, data in self.files.items():
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.addCleanup(patch.stopall)
        patch.object(receiver, 'BASE', self.base).start()
        patch.object(receiver, 'RELEASES', self.releases).start()

    def archive(self, extra=None):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w') as bundle:
            for name, content in self.files.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                bundle.addfile(info, io.BytesIO(content))
            if extra:
                bundle.addfile(extra)
        return data.getvalue()

    def test_valid_release_and_repeated_delivery(self):
        first = receiver.unpack_release(self.archive())
        second = receiver.unpack_release(self.archive())
        self.assertNotEqual(first, second)
        self.assertEqual((first / 'server.py').read_bytes(), b'baseline')
        self.assertEqual((first / '.venv').readlink(), self.base / '.venv')

    def test_traversal_and_hidden_paths_rejected(self):
        for name in ('../escape', '/tmp/escape', '.env', 'public/../escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                receiver.unpack_release(self.archive(tarfile.TarInfo(name)))
        self.assertEqual(list(self.releases.iterdir()), [])

    def test_links_and_devices_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE):
            info = tarfile.TarInfo('public/unsafe')
            info.type = kind
            info.linkname = '/etc/passwd'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                receiver.unpack_release(self.archive(info))

    def test_runtime_changes_require_administrator(self):
        self.files['sandbox/guest.py'] = b'changed runtime'
        with self.assertRaisesRegex(ValueError, 'Administrator'):
            receiver.unpack_release(self.archive())
        self.assertEqual(list(self.releases.iterdir()), [])
