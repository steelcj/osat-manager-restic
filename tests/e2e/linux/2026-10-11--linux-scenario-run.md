# Linux end-to-end scenario run

Result: passed

Started 2026-10-11T22:35:17Z, finished 2026-10-11T22:35:36Z, in the Incus container mint223, restored to its clean snapshot 'clean' before and after the run.

```text
Image: mint223, restored to snapshot 'clean' (Linux Mint 22.3), Python 3.10.12, user tester (uid 1500), not root

== snapshot
PASS  recorded 3 entries in the clean account
== install-manager
[manage-restic] installed manage-restic 0.1.0 into /home/tester/.local/share/osat/restic/manager

PASS  the manager installs itself
  $ /home/tester/.local/bin/manage-restic --version
    manage-restic 0.1.0
PASS  manage-restic runs from its launcher
== install-two
  $ /home/tester/.local/bin/manage-restic --install 0.18.1
    [manage-restic] installed restic 0.18.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.18.1 is now active
  $ /home/tester/.local/bin/manage-restic --install
    [manage-restic] latest restic release: 0.19.1
    [manage-restic] installed restic 0.19.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.19.1 is now active
  $ /home/tester/.local/bin/manage-restic --status
    manage-restic 0.1.0
    install root  /home/tester/.local/share/osat/restic
    aliases in    /home/tester/.local/bin
    active        0.19.1
    installed     0.18.1, 0.19.1
    archived      0.18.1, 0.19.1
    alias         restic-0.18  (0.18)
    alias         restic-0.19  (0.19)
    alias         restic  (default)
    alias         manage-restic  (self)
PASS  0.18.1 and 0.19.1 are installed side by side
  $ /home/tester/.local/bin/restic version
    restic 0.19.1 compiled with go1.26.4 on linux/amd64
PASS  the generic alias runs the latest, 0.19.1
== switch
  $ /home/tester/.local/bin/manage-restic --switch 0.18.1
    [manage-restic] restic 0.18.1 is now active
  $ /home/tester/.local/bin/restic version
    restic 0.18.1 compiled with go1.25.1 on linux/amd64
PASS  switched to 0.18.1
  $ /home/tester/.local/bin/manage-restic --switch 0.19.1
    [manage-restic] restic 0.19.1 is now active
  $ /home/tester/.local/bin/restic version
    restic 0.19.1 compiled with go1.26.4 on linux/amd64
PASS  switched back to 0.19.1
== rename-alias
  $ /home/tester/.local/bin/manage-restic --alias restic-0.18=r18
    [manage-restic] alias restic-0.18 is now r18
  $ /home/tester/.local/bin/r18 version
    restic 0.18.1 compiled with go1.25.1 on linux/amd64
PASS  the renamed alias r18 runs 0.18.1
  $ /home/tester/.local/bin/restic version
    restic 0.19.1 compiled with go1.26.4 on linux/amd64
PASS  the generic alias still runs 0.19.1
PASS  the old alias name is gone
== protection
PASS  an installed binary cannot be modified
PASS  an installed binary cannot be deleted
  $ /home/tester/.local/bin/restic version
    restic 0.19.1 compiled with go1.26.4 on linux/amd64
PASS  restic still runs
== remove
  $ /home/tester/.local/bin/manage-restic --remove 0.18.1
    [manage-restic] removed restic 0.18.1; its verified archive is kept
  $ /home/tester/.local/bin/manage-restic --status
    manage-restic 0.1.0
    install root  /home/tester/.local/share/osat/restic
    aliases in    /home/tester/.local/bin
    active        0.19.1
    installed     0.19.1
    archived      0.18.1, 0.19.1
    alias         restic-0.19  (0.19)
    alias         restic  (default)
    alias         manage-restic  (self)
PASS  0.18.1 is removed
PASS  0.18.1 is still in the verified archive
== network disconnected: ip link set eth0 down
== restore-offline
PASS  the network is disconnected
  $ /home/tester/.local/bin/manage-restic --install 0.18.1
    [manage-restic] restoring restic_0.18.1_linux_amd64.bz2 from the verified archive, signature and checksum re-checked
    [manage-restic] installed restic 0.18.1, verified against the signed SHA256SUMS
    [manage-restic] restic 0.18.1 is now active
PASS  0.18.1 is restored from the archive
  $ /home/tester/.local/bin/manage-restic --switch 0.18.1
    [manage-restic] restic 0.18.1 is now active
  $ /home/tester/.local/bin/restic version
    restic 0.18.1 compiled with go1.25.1 on linux/amd64
PASS  the restored 0.18.1 runs
== network reconnected
== uninstall
  $ /home/tester/.local/bin/manage-restic --uninstall --yes
    [manage-restic] removed /home/tester/.local/share/osat/restic and every launcher manage-restic wrote; restic's own configuration and repositories are untouched
PASS  the install root is gone
PASS  no launcher is left
== compare
PASS  the account is exactly as it was before the manager
== mint223 restored to snapshot 'clean' and stopped
```
