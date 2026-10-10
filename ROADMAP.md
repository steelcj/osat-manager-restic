# Roadmap

Forward plan only; completed items move to [CHANGELOG.md](CHANGELOG.md).

## 0.1.1

Findings of the third independent review of the OpenPGP verifier, none a violation of its five properties:

- Detect a download shorter than its `Content-Length` and retry it, rather than reporting it as a checksum mismatch.
- Refuse a `now` that is not a finite number in `verify`, so a caller cannot switch off the time checks.
- Refuse a critical bit on subpackets in the unhashed area, which nothing signs.
- Test that the manager applies the 1 MiB cap to `SHA256SUMS` and its signature, not only that the constant is small.
- Put an overall time limit on each download, as well as the per-read timeout.

## Next release

- Verify end to end on Windows, once the Windows 11 virtual machine can be reached, and on Linux arm64.
- Verify end to end on macOS, on Apple hardware.

## Later

- Move shared manager behaviour into one installed package, if that open question is answered yes, retiring this manager's own copies of the manifest lookup and the YAML reader.
- Offer to add the launcher directory to `PATH` on Windows.
- A deliberate command to prune old archived versions, refusing the active version.
- Reach 1.0.0 when Linux, macOS and Windows are all verified.
