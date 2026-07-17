#!/usr/bin/env bash
#
# autoflake/mayhem/test.sh — RUN autoflake's own pytest suite and emit a CTRF
# summary. exit 0 iff no test failed.
#
# PATCH-grade behavioral oracle: the full upstream suite — test_autoflake.py (known-answer cases
# asserting fix_code()/check() rewrites, exact diff outputs, CLI behavior) plus upstream's
# test_fuzz.py functional check (autoflake over the repo's own sources must keep them
# syntactically valid and never increase pyflakes warnings). A no-op / "exit(0)" /
# behavior-altering patch to autoflake cannot pass it.
#
# The suite is run through the `/mayhem/autoflake-tests` ELF launcher (which exec()s
# `python3 mayhem/run_tests.py`), NOT python directly. That matters for the verify-repo
# anti-reward-hack check: it LD_PRELOADs a constructor that _exit(0)s every NON-system
# executable. The system `python3` under /usr/bin is SPARED, but `/mayhem/autoflake-tests` is
# not — so under sabotage the launcher exits before pytest runs, no RUNTESTS line is produced, and
# this script reports a failure. The normal run is unaffected.
#
# This script only RUNS the suite (build.sh compiled the launcher); it never compiles.
set -uo pipefail
[ -n "${SOURCE_DATE_EPOCH:-}" ] || unset SOURCE_DATE_EPOCH

SRC="${SRC:-/mayhem}"
cd "$SRC"

# emit_ctrf <tool> <passed> <failed> [skipped] [pending] [other]
emit_ctrf() {
  local tool="$1" passed="$2" failed="$3" skipped="${4:-0}" pending="${5:-0}" other="${6:-0}"
  local tests=$(( passed + failed + skipped + pending + other ))
  cat > "${CTRF_REPORT:-$SRC/ctrf-report.json}" <<JSON
{
  "results": {
    "tool": { "name": "$tool" },
    "summary": {
      "tests": $tests,
      "passed": $passed,
      "failed": $failed,
      "pending": $pending,
      "skipped": $skipped,
      "other": $other
    }
  }
}
JSON
  printf 'CTRF {"results":{"tool":{"name":"%s"},"summary":{"tests":%d,"passed":%d,"failed":%d,"pending":%d,"skipped":%d,"other":%d}}}\n' \
    "$tool" "$tests" "$passed" "$failed" "$pending" "$skipped" "$other"
  [ "$failed" -eq 0 ]
}

if [ ! -x /mayhem/autoflake-tests ]; then
  echo "FATAL: /mayhem/autoflake-tests launcher missing — run mayhem/build.sh first" >&2
  emit_ctrf "pytest" 0 1 0
  exit 2
fi

echo "=== running pytest (autoflake known-answer suite) via /mayhem/autoflake-tests ==="
out="$(/mayhem/autoflake-tests 2>&1)"; rc=$?
echo "$out"

line="$(printf '%s\n' "$out" | sed -n 's/^RUNTESTS //p' | head -1)"
if [ -z "$line" ]; then
  # No summary line: the suite did not run (e.g. neutered launcher under the sabotage oracle,
  # an import error, or a crash). That is a FAILURE — do not pass vacuously.
  echo "no RUNTESTS summary line from the test runner (rc=$rc)" >&2
  emit_ctrf "pytest" 0 1 0
  exit 1
fi

# line looks like: tests=N passed=P failed=F skipped=S
TESTS=$(echo "$line"   | sed -n 's/.*tests=\([0-9][0-9]*\).*/\1/p')
PASSED=$(echo "$line"  | sed -n 's/.*passed=\([0-9][0-9]*\).*/\1/p')
FAILED=$(echo "$line"  | sed -n 's/.*failed=\([0-9][0-9]*\).*/\1/p')
SKIPPED=$(echo "$line" | sed -n 's/.*skipped=\([0-9][0-9]*\).*/\1/p')
: "${TESTS:=0}" "${PASSED:=0}" "${FAILED:=0}" "${SKIPPED:=0}"

# Guard against a parsed-but-empty suite.
if [ "$TESTS" -eq 0 ]; then
  echo "test runner reported 0 tests collected" >&2
  emit_ctrf "pytest" 0 1 0
  exit 1
fi

emit_ctrf "pytest" "$PASSED" "$FAILED" "$SKIPPED"
