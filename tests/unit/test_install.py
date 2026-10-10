"""manage-restic installed from a wheel into a fresh virtual environment
finds its own manager.yaml. Needs no network, since the manager has no
dependencies, but takes a few seconds; runs when OSAT_INSTALL_TESTS=1."""

import os
import shutil
import subprocess
import tempfile
import unittest
import venv
from pathlib import Path

from support import REPO


def python_in(env: Path) -> Path:
    scripts = env / ("Scripts" if os.name == "nt" else "bin")
    return scripts / ("python.exe" if os.name == "nt" else "python")


@unittest.skipUnless(os.environ.get("OSAT_INSTALL_TESTS") == "1",
                     "set OSAT_INSTALL_TESTS=1 to build and install a wheel")
class Wheel(unittest.TestCase):

    def test_the_wheel_carries_manager_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "src"
            shutil.copytree(REPO, src, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "build", "dist", "*.egg-info"))
            env = tmp / "env"
            venv.EnvBuilder(with_pip=True).create(env)
            py = str(python_in(env))
            for args in (["-m", "pip", "install", "-q", "--upgrade", "pip"],
                         ["-m", "pip", "wheel", "-q", "--no-deps", "-w",
                          str(tmp / "w"), str(src)]):
                subprocess.run([py, *args], check=True, capture_output=True)
            wheel = next((tmp / "w").glob("*.whl"))
            subprocess.run([py, "-m", "pip", "install", "-q", str(wheel)],
                           check=True, capture_output=True)
            out = subprocess.run(
                [py, "-c", "from osat_manager_restic.manifest import "
                           "manifest_path; print(manifest_path())"],
                cwd=str(tmp), capture_output=True, text=True, check=True)
            found = Path(out.stdout.strip())
            self.assertTrue(str(found.resolve()).startswith(str(env.resolve())))
            self.assertEqual(found.read_bytes(),
                             (REPO / "manager.yaml").read_bytes())


if __name__ == "__main__":
    unittest.main()
