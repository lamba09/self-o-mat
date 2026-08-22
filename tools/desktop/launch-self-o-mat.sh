#!/bin/sh
# Start self-o-mat from the build directory so the web UI and assets resolve.
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
BUILD="$ROOT/build"
BIN="$BUILD/self_o_mat.app"

if [ ! -x "$BIN" ]; then
    echo "self-o-mat is not built yet: missing $BIN" >&2
    echo "Build it with: cd $ROOT/build && cmake .. && make -j2" >&2
    exit 1
fi

cd "$BUILD"
exec ./self_o_mat.app "$@"
