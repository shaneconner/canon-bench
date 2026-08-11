#!/usr/bin/env python3
"""Check the working tree against the freeze manifest.

    python3 tests/verify_freeze.py

The manifest pins the suite by content as of the freeze commit (a1bf589,
aggregate hash 32820fccc3c96717 over the manifest itself). It verifies 115 of
115 files there.

At HEAD it verifies 113 of 115, and that is the expected result, not a
tampering signal. One post-freeze commit (ad6aa45) added a worker-model
passthrough to run_suite.py and run_session.py so the Sol robustness pass could
swap the worker; defaults were untouched and the judge stays pinned regardless.
That amendment is disclosed in Section 7 of the paper and is visible in the git
history. This script names those two files explicitly and fails on anything
else, so an unexpected difference is loud.

To see the frozen state verify completely:

    git stash && git checkout a1bf589 && python3 tests/verify_freeze.py
"""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AMENDED = {"run_suite.py", "run_session.py"}
FREEZE_COMMIT = "a1bf589"

verified = []
amended = []
unexpected = []
missing = []

for line in (ROOT / "FREEZE-manifest.txt").read_text().splitlines():
    if not line.strip():
        continue
    digest, rel = line.split("  ", 1)
    path = ROOT / rel
    if not path.exists():
        missing.append(rel)
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual == digest:
        verified.append(rel)
    elif rel in AMENDED:
        amended.append(rel)
    else:
        unexpected.append(rel)

total = len(verified) + len(amended) + len(unexpected) + len(missing)
print(f"{len(verified)} of {total} files match the freeze manifest.")

if amended:
    print(f"\n{len(amended)} differ by the disclosed post-freeze amendment:")
    for rel in sorted(amended):
        print(f"  {rel}")
    try:
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%h %s", "--", *sorted(amended)],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if subject:
            print(f"  last touched by: {subject}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    print(f"  the suite verifies completely at the freeze commit {FREEZE_COMMIT}")

if missing:
    print(f"\n{len(missing)} MISSING:")
    for rel in sorted(missing):
        print(f"  {rel}")

if unexpected:
    print(f"\n{len(unexpected)} UNEXPECTED difference(s), not covered by the amendment:")
    for rel in sorted(unexpected):
        print(f"  {rel}")

sys.exit(1 if (unexpected or missing) else 0)
