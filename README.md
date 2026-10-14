# 🖼️ Py Bg Changer

Change your desktop wallpaper from the terminal, Win+R or any launcher.
Works on Windows, macOS and Linux. No dependencies.

The command is `py-bg-changer`, and `pbc` is the short alias for it.

## Install

With [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install py-bg-changer
```

Or try it without installing:

```bash
uvx --from py-bg-changer pbc --help
```

Prefer pip? `pipx install py-bg-changer` or `pip install py-bg-changer` work too. Needs Python 3.9+.

## Use

```bash
pbc add night ~/Pictures/night.jpg   # save an image under a name
pbc night                            # set it by name
pbc ~/Pictures/any.png               # or set any image directly
pbc list                             # see what you saved
pbc remove night                     # forget a name
pbc                                  # set the one named "default"
```

If a saved name clashes with a command (say, one called `list`), use `pbc set list`.

## Supported desktops

| OS | Notes |
|----|-------|
| Windows | Built in, nothing extra needed |
| macOS | Built in (uses `osascript`) |
| Linux | GNOME, Budgie, Cinnamon, MATE, KDE Plasma, XFCE and Sway work out of the box. Anything else (i3, bspwm, ...) falls back to `feh` or `nitrogen` if installed. |

## Config

Saved names live in a small JSON file. Run `pbc path` to see where. Set `PBC_CONFIG`
to use a different file.

```json
{ "wallpapers": { "default": "/home/me/Pictures/a.jpg" } }
```

## Development

The project is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync              # create the virtualenv and install everything
uv run pytest        # run the tests
uv run pbc --help    # run the CLI from source
```

### Releasing

```bash
uv build             # builds the sdist and wheel into dist/
uv publish           # uploads them to PyPI
```

Bump `version` in `pyproject.toml` before each release.

## License

MIT
