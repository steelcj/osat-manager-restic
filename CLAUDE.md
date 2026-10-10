# osat-manager-restic

`manage-restic` installs restic into a user's own account and manages its versions. It is the pilot OSAT manager.

## Working here

- Standard library only, `pathlib` throughout, no shell commands in the manager. Tests may use more.
- Platform differences live in `lib/osat_manager_restic/platforms.py` and nowhere else.
- Never weaken verification: a download is unpacked only after the signature and checksum both pass.
- Run `python3 -m unittest discover -s tests/unit` and `uc-automa check` before committing.
- A platform is verified only by running `tests/e2e_scenario.py` on it; never claim one that has not been run.
- Ask before pushing, tagging, or using the Windows virtual machine.

<!-- uc-portage:begin uc-automa-signpost -->
## uc-automa

This repository follows uc-automa at the version pinned in `.uc-automa.yaml`.

- The rules are uc-automa's directives, under `en-ca/docs/directives/` at that version. Each names the check that enforces it, if it has one.
- Run `uc-automa check` before committing, and `uc-automa offerings plan` to see whether shared files have drifted.
- Files the layout marks `from_offering` arrive from uc-automa; change them there, not here.
- If a rule is not written in a directive, ask. Never copy a convention from another repository.
<!-- uc-portage:end uc-automa-signpost -->
