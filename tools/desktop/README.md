# Desktop launcher

Adds self-o-mat to the application menu (and optionally the GNOME dock), and can
start it automatically when the desktop session opens.

```bash
./install.sh                     # menu entry only
./install.sh --pin                # menu entry + sidebar / dock icon
./install.sh --autostart          # + launch on login
./install.sh --pin --autostart    # all of the above
```

The launcher always starts the binary from `build/`, which is required for the
web UI and assets. Rebuild the app before using the icon if `build/self_o_mat.app`
is missing.

## Autostart on boot

`--autostart` drops the same `.desktop` entry into `~/.config/autostart/`, which
every XDG desktop (GNOME, Xfce, ...) runs once a user session starts. For a booth
that boots straight to a logged-in desktop (auto-login, no lock screen), that is
enough to have self-o-mat come up on power-on with no terminal involved.

This relies on the session already existing when the entry runs, so it needs no
extra delay or manual `DISPLAY`/`WAYLAND_DISPLAY` handling. Remove
`~/.config/autostart/self-o-mat.desktop` to disable it again.
