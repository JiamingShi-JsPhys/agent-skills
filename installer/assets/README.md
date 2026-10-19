# Icon assets

Place the platform-native installer icons here before building the
packaged executables:

- `icon.ico`  -- Windows (`.exe`)
- `icon.icns` -- macOS (`.app`)

These are **not** required for the Python / CLI installer to run; they are
only consumed by PyInstaller when you build the double-click target.
