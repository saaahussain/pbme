"""Verify the SHA-256 checksums shipped with the offline artifact."""
from pathlib import Path
import hashlib
import sys

root = Path(__file__).resolve().parent
failures = []
entries = (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
for entry in entries:
    expected, filename = entry.split("  ", 1)
    path = root / filename
    if not path.is_file():
        failures.append(filename + " (missing)")
        continue
    with path.open("rb") as handle:
        actual = hashlib.file_digest(handle, "sha256").hexdigest()
    if actual != expected:
        failures.append(filename + " (checksum mismatch)")
if failures:
    print("Verification failed\n" + "\n".join(failures))
    sys.exit(1)
print(f"Verified {len(entries)} artifact files.")
