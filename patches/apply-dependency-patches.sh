#!/bin/sh
#
# Applies the patches in this directory to the vendored dependencies.
#
# served's upstream (meltwater/served) has been archived since 2021, so these
# fixes cannot be contributed back and cannot be picked up by moving the
# submodule forward. Carrying them here keeps a fresh clone buildable without
# depending on a fork that somebody has to keep hosting.
#
# Safe to run repeatedly; already applied patches are skipped.
set -e

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

apply_patch() {
    target="$1"
    patch="$2"
    name="$(basename "$patch")"

    if [ ! -d "$ROOT/$target" ]; then
        echo "patches: $target is missing, clone with --recursive" >&2
        exit 1
    fi

    if git -C "$ROOT/$target" apply --reverse --check "$patch" 2>/dev/null; then
        echo "patches: $name already applied"
        return 0
    fi

    if git -C "$ROOT/$target" apply --check "$patch" 2>/dev/null; then
        git -C "$ROOT/$target" apply "$patch"
        echo "patches: applied $name"
        return 0
    fi

    echo "patches: cannot apply $name to $target, it may be at an unexpected revision" >&2
    exit 1
}

apply_patch dependencies/served "$ROOT/patches/served-boost-asio.patch"
