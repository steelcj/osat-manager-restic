# Roadmap

Forward plan only; completed items move to [CHANGELOG.md](CHANGELOG.md).

## Next release

- Verify end to end on Windows, once the Windows 11 virtual machine can be reached, and on Linux arm64.
- Verify end to end on macOS, on Apple hardware.

## Later

- Move shared manager behaviour into one installed package, if that open question is answered yes, retiring this manager's own copies of the manifest lookup and the YAML reader.
- Offer to add the launcher directory to `PATH` on Windows.
- A deliberate command to prune old archived versions, refusing the active version.
- Reach 1.0.0 when Linux, macOS and Windows are all verified.
