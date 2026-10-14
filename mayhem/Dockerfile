# syntax=docker/dockerfile:1.7
#
# Commit-image Dockerfile (SMALL form) — builds ON TOP of the org base image
# (ghcr.io/mayhemheroes/base). The base provides debian + clang/llvm + libFuzzer + Python 3 + the
# identities + the build-contract ENV. autoflake is a PURE-PYTHON package whose only runtime dep is
# pyflakes, so this image installs the Atheris harness engine (atheris) plus the package and pytest
# into the base's system Python as root, then (as the non-root `mayhem` user) compiles the ELF
# launcher shims and runs the real pytest suite via build.sh / test.sh.
#
# Build (from the repo root):
#   DOCKER_BUILDKIT=1 docker build -f mayhem/Dockerfile \
#       --build-arg COMMIT=$(git rev-parse HEAD) \
#       [--build-arg SOURCE_DATE_EPOCH=$(date +%s)] \
#       -t autoflake-commit:test .

FROM ghcr.io/savantenvs/base:20260621

ARG COMMIT
ARG REPO_URL
# SOURCE_DATE_EPOCH stays an ARG (available to build.sh); never bake it as ENV — an empty value
# breaks clang. build.sh unsets it when empty.
ARG SOURCE_DATE_EPOCH
# Declared for parity with the build contract; autoflake has no native code to sanitize.
ARG SANITIZER_FLAGS

# Atheris (the libFuzzer harness engine — builds a native module against the base's clang/libFuzzer)
# plus pytest (used by the known-answer suite) go into the base's SYSTEM Python. PEP 668 marks that
# interpreter externally-managed, so --break-system-packages. This is the (networked) install step;
# build.sh deliberately does NOT pip-install, so its offline PATCH-tier re-run stays air-gapped.
# Atheris is pinned (3.1.0) for a reproducible engine.
USER root
# setuptools: this old commit imports distutils (removed from the stdlib in Python 3.12; setuptools
# supplies the shim) and builds from setup.py.
RUN pip install --no-cache-dir --break-system-packages atheris==3.1.0 pytest setuptools

# Source enters from the build CONTEXT (the CI checkout): the FULL repo (incl. .git history)
# is copied to /mayhem as `mayhem`; build.sh builds in place.
WORKDIR /mayhem
COPY --chown=2000:2000 . /mayhem

# Install autoflake itself (runtime dep: pyflakes) so the harness/oracle can `import autoflake`.
# Built from a scratch copy so the root-owned build/ and egg-info/ never land in the source tree.
RUN cp -r /mayhem /tmp/autoflake-src \
 && pip install --no-cache-dir --break-system-packages --no-build-isolation /tmp/autoflake-src \
 && rm -rf /tmp/autoflake-src \
 && cp -r mayhem/shims/lib2to3 "$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/"

USER mayhem

# Compile the ELF launcher shims (Mayhem needs an ELF target, not a .py).
RUN bash mayhem/build.sh

# Run autoflake's real pytest known-answer suite at build time; a failing suite fails the build.
RUN if [ -f mayhem/test.sh ]; then bash mayhem/test.sh; else echo "no mayhem/test.sh"; fi

LABEL org.opencontainers.image.source="${REPO_URL}" \
      org.opencontainers.image.revision="${COMMIT}" \
      rlenv.fix="adf7cff6fcf579462703d5540bdee68f7be9a9f0" \
      rlenv.tier="commit" \
      rlenv.source_date_epoch="${SOURCE_DATE_EPOCH}" \
      rlenv.user="mayhem"

USER mayhem
WORKDIR /mayhem
