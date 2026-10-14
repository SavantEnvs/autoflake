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


# Tests that cannot pass on the base image's interpreter, skipped by name: since Python 3.10
# ast.literal_eval strips leading whitespace, so ' 1' is a literal for this old commit's
# is_literal_or_name (a behavior change in CPython, not in the code under test).
SKIP_BY_NAME = ["test_is_literal_or_name"]


def main() -> int:
    os.chdir(SRC)
    deselect = ["-k", " and ".join(f"not {n}" for n in SKIP_BY_NAME)]
    pytest.main(["-q", "-p", "no:cacheprovider", "--junitxml", XML, *deselect])

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
    tests += len(SKIP_BY_NAME)
    skipped += len(SKIP_BY_NAME)

    # Upstream's fuzz CI job: test_fuzz.py over the repo's own sources (known-answer: output
    # must stay syntactically valid and never add pyflakes warnings).
    # Older commits ship upstream's equivalent check as test_acid.py.
    acid = "test_fuzz.py" if os.path.exists("test_fuzz.py") else "test_acid.py"
    rc = subprocess.run(
        [sys.executable, acid, *sorted(glob.glob("./*.py"))],
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
