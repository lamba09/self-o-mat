#!/bin/sh
# Install a GNOME/Ubuntu application menu entry and optionally pin it to the dock.
set -e

DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ROOT="$(CDPATH= cd -- "$DIR/../.." && pwd)"
BUILD="$ROOT/build"
LAUNCHER="$DIR/launch-self-o-mat.sh"

APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
DESKTOP_ID=self-o-mat.desktop

PIN=0
for arg in "$@"; do
    case "$arg" in
        --pin) PIN=1 ;;
        -h|--help)
            echo "Usage: $0 [--pin]"
            echo "  Installs self-o-mat.desktop into $APPS"
            echo "  --pin  also add it to the GNOME dock / sidebar"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

chmod +x "$LAUNCHER"

mkdir -p "$APPS"
sed -e "s|@LAUNCHER@|$LAUNCHER|g" -e "s|@BUILD@|$BUILD|g" \
    "$DIR/self-o-mat.desktop.in" > "$APPS/$DESKTOP_ID"
chmod +x "$APPS/$DESKTOP_ID"

for size in 48 64 128 256; do
    mkdir -p "$ICONS/${size}x${size}/apps"
    cp "$DIR/self-o-mat-${size}.png" "$ICONS/${size}x${size}/apps/self-o-mat.png"
done
mkdir -p "$ICONS/scalable/apps"
cp "$DIR/self-o-mat.svg" "$ICONS/scalable/apps/self-o-mat.svg"

# Refresh desktop and icon caches when the tools are present.
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$ICONS" 2>/dev/null || true

echo "Installed menu entry: $APPS/$DESKTOP_ID"

if [ "$PIN" -eq 1 ]; then
    if ! command -v gsettings >/dev/null; then
        echo "gsettings not found; skip pinning" >&2
        exit 0
    fi
    # Append to GNOME favorites if it is not already there.
    current="$(gsettings get org.gnome.shell favorite-apps)"
    case "$current" in
        *"'$DESKTOP_ID'"*|*"\"$DESKTOP_ID\""*)
            echo "Already pinned to the dock"
            ;;
        "@as []"|"[]")
            gsettings set org.gnome.shell favorite-apps "['$DESKTOP_ID']"
            echo "Pinned to the dock"
            ;;
        *)
            # current looks like ['a.desktop', 'b.desktop']
            trimmed="${current%]}"
            gsettings set org.gnome.shell favorite-apps "${trimmed}, '$DESKTOP_ID']"
            echo "Pinned to the dock"
            ;;
    esac
fi
