# Contributing

Changes arrive as commits on a branch and are reviewed by Christopher Steel before they reach `main`.

## Before committing

- `python3 -m unittest discover -s tests/unit` and `uc-automa check` pass.
- A change to behaviour comes with a test that fails without it.
- A change to the pinned signing key in `manager.yaml` names, in its commit message, where the new fingerprint was confirmed.
- After changing installation, verification or aliases, run the end-to-end scenario on Linux and update the platform status table with what was actually run.

## License

This document, *Contributing*, by **Christopher Steel**, with AI assistance from **Claude Opus 5.5 (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).
