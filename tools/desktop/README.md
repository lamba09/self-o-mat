# Desktop launcher

Adds self-o-mat to the application menu (and optionally the GNOME dock).

```bash
./install.sh        # menu entry only
./install.sh --pin  # menu entry + sidebar / dock icon
```

The launcher always starts the binary from `build/`, which is required for the
web UI and assets. Rebuild the app before using the icon if `build/self_o_mat.app`
is missing.
