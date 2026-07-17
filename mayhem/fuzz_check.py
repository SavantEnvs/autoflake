#!/usr/bin/env python3
"""Atheris libFuzzer harness for autoflake (preserved target: check-fuzz).

Fuzzes autoflake's two core entry points over arbitrary unicode source text:
  - autoflake.check(source): pyflakes analysis of the source
  - autoflake.fix_code(source): the full unused-import/unused-variable rewrite pipeline

autoflake is pure Python; the interesting coverage lives in autoflake itself and its
pyflakes backend, both imported inside instrument_imports() so Atheris instruments them.
"""
import sys

import atheris

with atheris.instrument_imports():
    import autoflake


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    source = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    try:
        autoflake.check(source)
        autoflake.fix_code(source)
    except (SyntaxError, ValueError, RecursionError):
        # Expected "this input is not valid Python" signals: the tokenizer/ast raise
        # SyntaxError/ValueError on malformed source, and deeply nested expressions hit
        # the interpreter recursion limit. Not autoflake defects — swallow them so corpus
        # replay during Mayhem coverage collection doesn't abort on a malformed seed.
        return -1


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
