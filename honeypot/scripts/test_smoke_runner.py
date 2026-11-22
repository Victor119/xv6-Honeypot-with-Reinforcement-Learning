"""Host tests: the runner must never mistake a failed boot for a pass."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from smoke import Guest


class RunnerTests(unittest.TestCase):
    def guest(self, program):
        real_popen = subprocess.Popen
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        def child(*args, **kwargs):
            return real_popen([sys.executable, "-c", program], **kwargs)

        with patch("smoke.subprocess.Popen", side_effect=child):
            guest = Guest("fake-qemu", Path(directory.name) / "serial.log", 1)
        self.addCleanup(guest.close)
        return guest

    def test_expected_output(self):
        self.guest("print('registered')").expect(b"registered", timeout=5)

    def test_premature_exit(self):
        with self.assertRaisesRegex(AssertionError, "exited"):
            self.guest("print('boot failed')").expect(b"registered", timeout=5)

    def test_kernel_panic(self):
        with self.assertRaisesRegex(AssertionError, "panic:"):
            self.guest("print('cpu0: panic: broken')").expect(b"registered", timeout=5)

    def test_guest_assertion(self):
        with self.assertRaisesRegex(AssertionError, "FAIL"):
            self.guest("print('hptest: FAIL isolation')").expect(b"PASS", timeout=5)

    def test_hung_guest(self):
        with self.assertRaisesRegex(AssertionError, "Timed out"):
            self.guest("import time; time.sleep(30)").expect(b"registered", timeout=.1)


if __name__ == "__main__":
    unittest.main()
