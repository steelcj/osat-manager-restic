"""The OSAT manager end-to-end scenario, one step per invocation.

Run inside the platform being verified, as an ordinary user, with real
downloads from restic's release pages. A platform driver, such as
tests/e2e/linux/run_in_incus.py, calls the steps in order and handles
what the user cannot, such as disconnecting the network.

    python3 e2e_scenario.py STEP

Steps: snapshot, install-manager, install-two, switch, rename-alias,
protection, remove, restore-offline, uninstall, compare.
Each prints PASS or FAIL lines and exits 1 on the first failure.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OLDER, NEWER = "0.18.1", "0.19.1"
HOME = Path.home()
SRC = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(os.environ.get("E2E_SNAPSHOT",
                             str(Path(tempfile.gettempdir()) / "e2e-snapshot.json")))
WINDOWS = os.name == "nt"


def bin_dir() -> Path:
    if WINDOWS:
        return Path(os.environ["LOCALAPPDATA"]) / "osat" / "bin"
    return HOME / ".local" / "bin"


def root() -> Path:
    if WINDOWS:
        return Path(os.environ["LOCALAPPDATA"]) / "osat" / "restic"
    if sys.platform == "darwin":
        return HOME / "Library" / "Application Support" / "osat" / "restic"
    return HOME / ".local" / "share" / "osat" / "restic"


def command(name: str) -> str:
    path = bin_dir() / (name + ".cmd" if WINDOWS else name)
    return str(path)


def run(*argv, check=True):
    result = subprocess.run(list(argv), capture_output=True, text=True)
    print(f"  $ {' '.join(argv)}")
    for line in (result.stdout + result.stderr).strip().splitlines():
        print(f"    {line}")
    if check and result.returncode != 0:
        fail(f"{argv[0]} exited with {result.returncode}")
    return result


def passed(message):
    print(f"PASS  {message}")


def fail(message):
    print(f"FAIL  {message}")
    sys.exit(1)


def expect(condition, message):
    passed(message) if condition else fail(message)


def home_listing():
    entries = []
    for path in sorted(HOME.rglob("*")):
        rel = path.relative_to(HOME).as_posix()
        if rel.split("/")[0] in ("src", ".bash_history", ".cache"):
            continue
        entries.append(rel + ("/" if path.is_dir() else ""))
    return entries


def restic_version(name="restic"):
    return run(command(name), "version").stdout


def step_snapshot():
    SNAPSHOT.write_text(json.dumps(home_listing()))
    passed(f"recorded {len(home_listing())} entries in the clean account")


def step_install_manager():
    env = dict(os.environ, PYTHONPATH=str(SRC / "lib"))
    result = subprocess.run([sys.executable, "-m", "osat_manager_restic",
                             "--self-install"], env=env, capture_output=True,
                            text=True, cwd=str(HOME))
    print(result.stdout + result.stderr)
    expect(result.returncode == 0, "the manager installs itself")
    out = run(command("manage-restic"), "--version").stdout
    expect("manage-restic" in out, "manage-restic runs from its launcher")


def step_install_two():
    run(command("manage-restic"), "--install", OLDER)
    run(command("manage-restic"), "--install")
    status = run(command("manage-restic"), "--status").stdout
    expect(OLDER in status and NEWER in status,
           f"{OLDER} and {NEWER} are installed side by side")
    expect(f"restic {NEWER}" in restic_version(),
           f"the generic alias runs the latest, {NEWER}")


def step_switch():
    run(command("manage-restic"), "--switch", OLDER)
    expect(f"restic {OLDER}" in restic_version(), f"switched to {OLDER}")
    run(command("manage-restic"), "--switch", NEWER)
    expect(f"restic {NEWER}" in restic_version(), f"switched back to {NEWER}")


def step_rename_alias():
    run(command("manage-restic"), "--alias", "restic-0.18=r18")
    expect(f"restic {OLDER}" in restic_version("r18"),
           "the renamed alias r18 runs 0.18.1")
    expect(f"restic {NEWER}" in restic_version("restic"),
           "the generic alias still runs 0.19.1")
    expect(not Path(command("restic-0.18")).exists(),
           "the old alias name is gone")


def step_protection():
    binary = root() / "versions" / NEWER / ("restic.exe" if WINDOWS else "restic")
    try:
        with binary.open("ab") as f:
            f.write(b"x")
        fail("an installed binary could be modified")
    except PermissionError:
        passed("an installed binary cannot be modified")
    try:
        binary.unlink()
        fail("an installed binary could be deleted")
    except PermissionError:
        passed("an installed binary cannot be deleted")
    expect(f"restic {NEWER}" in restic_version(), "restic still runs")


def step_remove():
    run(command("manage-restic"), "--remove", OLDER)
    status = run(command("manage-restic"), "--status").stdout
    installed = [l for l in status.splitlines() if l.startswith("installed")][0]
    archived = [l for l in status.splitlines() if l.startswith("archived")][0]
    expect(OLDER not in installed, f"{OLDER} is removed")
    expect(OLDER in archived, f"{OLDER} is still in the verified archive")


def step_restore_offline():
    # -B: the probe fails with a traceback, and Python caches the modules
    # that prints with inside its own installation, which on Windows is in
    # the account being compared.
    probe = subprocess.run([sys.executable, "-B", "-c",
                            "import urllib.request;urllib.request.urlopen("
                            "'https://github.com', timeout=10)"],
                           capture_output=True)
    expect(probe.returncode != 0, "the network is disconnected")
    out = run(command("manage-restic"), "--install", OLDER).stdout
    expect("verified archive" in out, f"{OLDER} is restored from the archive")
    run(command("manage-restic"), "--switch", OLDER)
    expect(f"restic {OLDER}" in restic_version(),
           f"the restored {OLDER} runs")


def step_uninstall():
    run(command("manage-restic"), "--uninstall", "--yes")
    expect(not root().exists(), "the install root is gone")
    leftovers = [p.name for p in bin_dir().glob("*")] if bin_dir().exists() else []
    expect(not leftovers, "no launcher is left")


def step_compare():
    before = json.loads(SNAPSHOT.read_text())
    after = home_listing()
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    for entry in added:
        print(f"    left behind: {entry}")
    for entry in removed:
        print(f"    missing: {entry}")
    expect(not added and not removed,
           "the account is exactly as it was before the manager")


STEPS = {name[len("step_"):].replace("_", "-"): func
         for name, func in globals().items() if name.startswith("step_")}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in STEPS:
        print(f"usage: e2e_scenario.py {{{','.join(STEPS)}}}")
        sys.exit(2)
    print(f"== {sys.argv[1]}")
    STEPS[sys.argv[1]]()
