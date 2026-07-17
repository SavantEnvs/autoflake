#!/usr/bin/python3
"""run_tests.py — RUN autoflake's own test suite and print a parseable summary.

Invoked via the `/mayhem/autoflake-tests` ELF launcher (NOT directly), so the verify-repo
sabotage oracle can neuter the launcher and prove the test oracle is behavioral.

It runs the FULL upstream suite, exactly what upstream CI runs:
  1. `pytest` at the repo root (test_autoflake.py — the entire unit + functional suite:
     known-answer cases asserting fix_code()/check() rewrites, CLI behavior via subprocess,
     config-file handling, exact diff outputs, ...), writes a JUnit XML and parses the counts.
  2. `python test_fuzz.py ./*.py` (upstream's "fuzz" CI job) — a functional known-answer check
     that autoflake, run over the repo's own Python files, never introduces a syntax error and
     never increases the pyflakes warning count. Counted as one additional test.

Prints one line:

    RUNTESTS tests=<n> passed=<p> failed=<f> skipped=<s>

Exit 0 iff failed == 0. mayhem/test.sh parses that line into a CTRF report.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

SRC = os.environ.get("SRC", "/mayhem")
XML = "/tmp/autoflake-junit.xml"


def main() -> int:
    os.chdir(SRC)
    pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml", XML])

    try:
        root = ET.parse(XML).getroot()
    except Exception:
        print("RUNTESTS tests=0 passed=0 failed=1 skipped=0")
        return 1
    suites = root.findall("testsuite") or ([root] if root.tag == "testsuite" else [])
    if not suites:
        print("RUNTESTS tests=0 passed=0 failed=1 skipped=0")
        return 1

    tests = failed = skipped = 0
    for s in suites:
        tests += int(s.get("tests", 0))
        failed += int(s.get("failures", 0)) + int(s.get("errors", 0))
        skipped += int(s.get("skipped", 0))

    # Upstream's fuzz CI job: test_fuzz.py over the repo's own sources (known-answer: output
    # must stay syntactically valid and never add pyflakes warnings).
    rc = subprocess.run(
        [sys.executable, "test_fuzz.py", *sorted(glob.glob("./*.py"))],
        cwd=SRC,
    ).returncode
    tests += 1
    if rc != 0:
        failed += 1

    passed = tests - failed - skipped
    print(f"RUNTESTS tests={tests} passed={passed} failed={failed} skipped={skipped}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
