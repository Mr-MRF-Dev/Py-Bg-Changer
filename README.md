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
pbc add night img.jpg -a n -a dark   # ...and give it extra names (aliases)
pbc alias night moon                 # add more aliases later
pbc rename night midnight            # rename a wallpaper or an alias
pbc night                            # set it by name (or any alias: pbc n)
pbc ~/Pictures/any.png               # or set any image directly
pbc list                             # see what you saved (* marks the default); `pbc ls` works too
pbc default night                    # choose what a plain "pbc" sets
pbc remove night                     # forget a name (or just an alias)
pbc                                  # set the default wallpaper
```

If a saved name clashes with a command (say, one called `list`, `ls` or `default`), use `pbc set list`.

### Win+R and launchers (no console window)

Running `pbc` from Win+R opens a terminal that closes right away. Use `pbcw` (or
`py-bg-changer-w`) instead: it takes the same arguments, opens no window, and shows a
small message box only if something goes wrong.

```bash
pbcw night                           # from Win+R: set it silently
```

It prints nothing on success, so use `pbc` in a terminal for `list`, `default` and
the like.

### Aliases

A wallpaper can have as many aliases as you like, and every alias works anywhere a name
does (`pbc n`, `pbc default n`, `pbc alias n moon`). Add them while saving with
`-a` (repeat it for more) or later with `pbc alias NAME ALIAS...`. `pbc list` shows
them in brackets after the name.

Removing an alias leaves the wallpaper alone; removing a wallpaper also removes its
aliases. If you replace the image saved under a name, its aliases follow the new image.

Rename either one with `pbc rename OLD NEW`. Renaming a wallpaper keeps its aliases, its
image and its place as the default.

### Default wallpaper

Run `pbc` with no arguments and it sets your default wallpaper. Pick the default with
`pbc default NAME`, or do it while saving an image with `pbc add NAME IMAGE --default`.
`pbc default` on its own shows the current choice.

### Your images are copied

When you save an image, `py-bg-changer` keeps its own copy next to the config file and
gives that copy to the system. If you later move or delete the original, the wallpaper
still works. The copy is removed when you remove the name (or replace its image), and
your original file is never touched.

## Supported desktops

| OS      | Notes                                                                                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Windows | Built in, nothing extra needed                                                                                                                               |
| macOS   | Built in (uses `osascript`)                                                                                                                                  |
| Linux   | GNOME, Budgie, Cinnamon, MATE, KDE Plasma, XFCE and Sway work out of the box. Anything else (i3, bspwm, ...) falls back to `feh` or `nitrogen` if installed. |

## Config

Saved names live in a small JSON file, and the copied images in a `wallpapers` folder
next to it. Run `pbc path` to see where. Set `PBC_CONFIG` to use a different file.

```json
{
  "wallpapers": {
    "night": "/home/me/.config/py-bg-changer/wallpapers/3e23e8160039594a.png"
  },
  "aliases": { "n": "night", "dark": "night" },
  "default": "night"
}
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
