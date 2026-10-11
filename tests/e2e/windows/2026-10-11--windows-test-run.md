# Windows test run

- Unit tests: passed
- Network cut self-test: passed
- End-to-end scenario: passed
- Offline install from wheels: passed

Started 2026-10-11T22:26:51Z, finished 2026-10-11T22:35:17Z, in the Incus virtual machine windows, reached over SSH and restored to its clean snapshot 'osat-ready-tools' before each part and afterwards. The account name, the computer name and the network addresses are replaced by placeholders.

## Unit tests

```text
Sources: uc-portage at 876468a, uc-automa at 1e5be19, osat-manager-restic at 37bcb06
Platform: Windows-11-10.0.26200-SP0, Python 3.15.0 at C:\Users\<user>\AppData\Local\python-manager\3.15.0\python\python.exe, git version 2.56.0.windows.2, user <user>, not an administrator
PyYAML: built without its C extension (PYYAML_FORCE_LIBYAML=0), because PyYAML 6.0.3 has no Windows wheel for Python 3.15
== create a virtual environment (exit 0)

== install uc-portage and uc-automa, editable (exit 0)

== uc-portage unit tests, with install tests (exit 0)
..........................................................
----------------------------------------------------------------------
Ran 58 tests in 45.511s

OK
== uc-automa unit tests, with install tests (exit 0)
....................................
----------------------------------------------------------------------
Ran 36 tests in 70.460s

OK
== uc-automa check on itself (exit 0)
[uc-automa] conforms: 12 directive(s) checked, layout 'uc-automa'
== osat-manager-restic unit tests, with install tests (exit 0)
..s...................ss..................s.......
----------------------------------------------------------------------
Ran 50 tests in 29.967s

OK (skipped=4)
== windows restored to snapshot 'osat-ready-tools' and stopped
```

## Network cut self-test

```text
== the network cut's self-test, probes over SSH
PASS  no proxy is configured in the instance
PASS  before: the host's SSH answers
PASS  before the step: the dead-man's switch fires after the step's limit: 600 s left, limit 300 s
PASS  at the end of the step: the cut is still in place and every negative probe still fails
IPV6  the IPv6 internet path: not testable on this network: no IPv6 route on the host
PASS  direct HTTPS over IPv4 to restic's release URL, no proxy: works before the cut: OK 0.2
PASS  direct HTTPS over IPv4 to restic's release URL, no proxy: fails during the cut: FAILED 4.1 URLError <urlopen error timed out>
PASS  direct HTTPS over IPv4 to restic's release URL, no proxy: works again after the cut: OK 0.2
N/A   direct HTTPS over IPv6 to a public address, no proxy: fails before the cut too, so it proves nothing here: FAILED 4.0 URLError <urlopen error timed out>
PASS  IPv4: TCP to the host <host-ipv4>:443: works before the cut: OK 0.0
PASS  IPv4: TCP to the host <host-ipv4>:443: fails during the cut: FAILED 4.0 TimeoutError
PASS  IPv4: TCP to the host <host-ipv4>:443: works again after the cut: OK 0.0
PASS  IPv4: relay attempts through the host <host-ipv4>:80: works before the cut: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv4: relay attempts through the host <host-ipv4>:80: fails during the cut: FAILED no answer: TimeoutError | no answer: TimeoutError
PASS  IPv4: relay attempts through the host <host-ipv4>:80: works again after the cut: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv4: relay attempts through the host <host-ipv4>:80: never relays to GitHub: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv4: relay attempts through the host <host-ipv4>:443: works before the cut: OK (closed) | (closed)
PASS  IPv4: relay attempts through the host <host-ipv4>:443: fails during the cut: FAILED no answer: TimeoutError | no answer: TimeoutError
PASS  IPv4: relay attempts through the host <host-ipv4>:443: works again after the cut: OK (closed) | (closed)
PASS  IPv4: relay attempts through the host <host-ipv4>:443: never relays to GitHub: OK (closed) | (closed)
PASS  IPv6: TCP to the host <host-ipv6>:443: works before the cut: OK 0.0
PASS  IPv6: TCP to the host <host-ipv6>:443: fails during the cut: FAILED 4.0 TimeoutError
PASS  IPv6: TCP to the host <host-ipv6>:443: works again after the cut: OK 0.0
PASS  IPv6: relay attempts through the host <host-ipv6>:80: works before the cut: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv6: relay attempts through the host <host-ipv6>:80: fails during the cut: FAILED no answer: TimeoutError | no answer: TimeoutError
PASS  IPv6: relay attempts through the host <host-ipv6>:80: works again after the cut: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv6: relay attempts through the host <host-ipv6>:80: never relays to GitHub: OK HTTP/1.1 308 Permanent Redirect | HTTP/1.1 308 Permanent Redirect
PASS  IPv6: relay attempts through the host <host-ipv6>:443: works before the cut: OK (closed) | (closed)
PASS  IPv6: relay attempts through the host <host-ipv6>:443: fails during the cut: FAILED no answer: TimeoutError | no answer: TimeoutError
PASS  IPv6: relay attempts through the host <host-ipv6>:443: works again after the cut: OK (closed) | (closed)
PASS  IPv6: relay attempts through the host <host-ipv6>:443: never relays to GitHub: OK (closed) | (closed)
PASS  during the cut: nothing on the host <host-ipv4> is reachable but its DNS: open: [53]
PASS  during the cut: nothing on the host <host-ipv6> is reachable but its DNS: open: [53]
PASS  throughout the cut: the host's SSH kept answering: 66 checks, 0 failed
PASS  afterwards: the instance's configuration is as before
PASS  afterwards: no NIC override
PASS  afterwards: no ACL with the prefix is left
PASS  afterwards: no dead-man's switch is left: []
NOTE  during the cut, DNS on the host <host-ipv4>: OK 1 answer(s)
NOTE  during the cut, DNS on the host <host-ipv6>: OK 1 answer(s)
NOTE  the IPv6 internet path: not testable on this network: no IPv6 route on the host
NOTE  not provable on this host: direct HTTPS over IPv6 to a public address, no proxy
windows restored to snapshot 'osat-ready-tools' and stopped
== windows restored to snapshot 'osat-ready-tools' and stopped
```

## End-to-end scenario

```text
Sources: uc-portage at 876468a, uc-automa at 1e5be19, osat-manager-restic at 37bcb06
Platform: Windows-11-10.0.26200-SP0, Python 3.15.0 at C:\Users\<user>\AppData\Local\python-manager\3.15.0\python\python.exe, git version 2.56.0.windows.2, user <user>, not an administrator
== snapshot (exit 0)
== snapshot
PASS  recorded 6890 entries in the clean account
== install-manager (exit 0)
== install-manager
[manage-restic] installed manage-restic 0.1.0 into C:\Users\<user>\AppData\Local\osat\restic\manager

PASS  the manager installs itself
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --version
    manage-restic 0.1.0
PASS  manage-restic runs from its launcher
== install-two (exit 0)
== install-two
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --install 0.18.1
    [manage-restic] installed restic 0.18.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.18.1 is now active
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --install
    [manage-restic] latest restic release: 0.19.1
    [manage-restic] installed restic 0.19.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.19.1 is now active
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --status
    manage-restic 0.1.0
    install root  C:\Users\<user>\AppData\Local\osat\restic
    aliases in    C:\Users\<user>\AppData\Local\osat\bin
    active        0.19.1
    installed     0.18.1, 0.19.1
    archived      0.18.1, 0.19.1
    alias         restic-0.18  (0.18)
    alias         restic-0.19  (0.19)
    alias         restic  (default)
    alias         manage-restic  (self)
PASS  0.18.1 and 0.19.1 are installed side by side
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.19.1 compiled with go1.26.4 on windows/amd64
PASS  the generic alias runs the latest, 0.19.1
== switch (exit 0)
== switch
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --switch 0.18.1
    [manage-restic] restic 0.18.1 is now active
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.18.1 compiled with go1.25.1 on windows/amd64
PASS  switched to 0.18.1
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --switch 0.19.1
    [manage-restic] restic 0.19.1 is now active
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.19.1 compiled with go1.26.4 on windows/amd64
PASS  switched back to 0.19.1
== rename-alias (exit 0)
== rename-alias
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --alias restic-0.18=r18
    [manage-restic] alias restic-0.18 is now r18
  $ C:\Users\<user>\AppData\Local\osat\bin\r18.cmd version
    restic 0.18.1 compiled with go1.25.1 on windows/amd64
PASS  the renamed alias r18 runs 0.18.1
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.19.1 compiled with go1.26.4 on windows/amd64
PASS  the generic alias still runs 0.19.1
PASS  the old alias name is gone
== protection (exit 0)
== protection
PASS  an installed binary cannot be modified
PASS  an installed binary cannot be deleted
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.19.1 compiled with go1.26.4 on windows/amd64
PASS  restic still runs
== remove (exit 0)
== remove
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --remove 0.18.1
    [manage-restic] removed restic 0.18.1; its verified archive is kept
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --status
    manage-restic 0.1.0
    install root  C:\Users\<user>\AppData\Local\osat\restic
    aliases in    C:\Users\<user>\AppData\Local\osat\bin
    active        0.19.1
    installed     0.19.1
    archived      0.18.1, 0.19.1
    alias         restic-0.19  (0.19)
    alias         restic  (default)
    alias         manage-restic  (self)
PASS  0.18.1 is removed
PASS  0.18.1 is still in the verified archive
== network cut: osat-offline-08c23a6ae7e0, the host's SSH only; 7 probes worked before it and are re-proven at the end of the step
== restore-offline (exit 0)
== restore-offline
PASS  the network is disconnected
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --install 0.18.1
    [manage-restic] restoring restic_0.18.1_windows_amd64.zip from the verified archive, signature and checksum re-checked
    [manage-restic] installed restic 0.18.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.18.1 is now active
PASS  0.18.1 is restored from the archive
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --switch 0.18.1
    [manage-restic] restic 0.18.1 is now active
  $ C:\Users\<user>\AppData\Local\osat\bin\restic.cmd version
    restic 0.18.1 compiled with go1.25.1 on windows/amd64
PASS  the restored 0.18.1 runs
== at the end of the step the cut was intact and every probe still failed; the network is reconnected
== uninstall (exit 0)
== uninstall
  $ C:\Users\<user>\AppData\Local\osat\bin\manage-restic.cmd --uninstall --yes
    [manage-restic] removed C:\Users\<user>\AppData\Local\osat\restic and every launcher manage-restic wrote; restic's own configuration and repositories are untouched
PASS  the install root is gone
PASS  no launcher is left
== compare (exit 0)
== compare
PASS  the account is exactly as it was before the manager
== windows restored to snapshot 'osat-ready-tools' and stopped
```

## Offline install from wheels

```text
Sources: uc-portage at 876468a, uc-automa at 1e5be19, osat-manager-restic at 37bcb06
Platform: Windows-11-10.0.26200-SP0, Python 3.15.0 at C:\Users\<user>\AppData\Local\python-manager\3.15.0\python\python.exe, git version 2.56.0.windows.2, user <user>, not an administrator
Built from uc-portage's tag v0.1.0
Built from uc-automa's tag v0.1.0
Wheel pyyaml-6.0.3-py3-none-any.whl sha256 e6cd29fbc0edbc79ddfac6abaad3fbf8bd1ba1d96eac5415311a0005b59275ea
Wheel uc_automa-0.1.0-py3-none-any.whl sha256 1bffa096af4c2fe914ab10d956c2123bc28051ddd7ed99b43b37428e5ddfcaa7
Wheel uc_portage-0.1.0-py3-none-any.whl sha256 f7a1fe86a5d1ce7f9461da041d7ad1c86aa52eed57cfde7779cb484e940ad002
== unpack the wheels (exit 0)

== network cut: osat-offline-20df70759d8f, the host's SSH only; 7 probes worked before it and are re-proven at the end of the step
== create a virtual environment (exit 0)

== install uc-automa and its dependencies from the wheels, no index (exit 0)
Looking in links: c:\Users\<user>\src\wheels
Processing .\src\wheels\uc_automa-0.1.0-py3-none-any.whl
Processing .\src\wheels\pyyaml-6.0.3-py3-none-any.whl (from uc-automa)
Processing .\src\wheels\uc_portage-0.1.0-py3-none-any.whl (from uc-automa)
Installing collected packages: PyYAML, uc-portage, uc-automa

Successfully installed PyYAML-6.0.3 uc-automa-0.1.0 uc-portage-0.1.0
== PyYAML is the pure build, without libyaml (exit 0)
PyYAML 6.0.3 libyaml False
== the installed commands run (exit 0)
uc-portage 0.1.0
uc-automa 0.1.0
== the installed uc-automa checks uc-automa at v0.1.0 (exit 0)
[uc-automa] conforms: 12 directive(s) checked, layout 'uc-automa'
== at the end of the step the cut was intact and every probe still failed; the network is reconnected
== windows restored to snapshot 'osat-ready-tools' and stopped
```
