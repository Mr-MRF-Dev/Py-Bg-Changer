# 🖼️ Py Bg Changer

[![PyPI](https://img.shields.io/pypi/v/py-bg-changer)](https://pypi.org/project/py-bg-changer/)
[![Python Versions](https://img.shields.io/pypi/pyversions/py-bg-changer)](https://pypi.org/project/py-bg-changer/)
![GitHub repo size](https://img.shields.io/github/repo-size/Mr-MRF-Dev/Py-Bg-Changer)
[![Tests](https://github.com/Mr-MRF-Dev/Py-Bg-Changer/actions/workflows/test.yml/badge.svg)](https://github.com/Mr-MRF-Dev/Py-Bg-Changer/actions/workflows/test.yml)
[![GitHub License](https://img.shields.io/github/license/Mr-MRF-Dev/Py-Bg-Changer)](/LICENSE)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

<!-- ![Screenshot](/images/screenshot.gif) -->

Simple cross-platform wallpaper changer made with Python. Change your desktop wallpaper from the terminal, Win+R or any launcher. Works on Windows, macOS and Linux, with no dependencies.

The command is `py-bg-changer`, and `pbc` is the short alias for it.

## 📥 Installation

you can install the latest version from [PyPI](https://pypi.org/project/py-bg-changer/) with [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv tool install py-bg-changer
```

or try it without installing:

```bash
uvx --from py-bg-changer pbc --help
```

prefer pip? `pipx install py-bg-changer` or `pip install py-bg-changer` work too. Needs Python 3.10+.

## 📖 Usage

```bash
pbc add night ~/Pictures/night.jpg   # save an image under a name
pbc add night img.jpg -a n -a dark   # ...and give it extra names (aliases)
pbc add night img.jpg --default      # ...or make it the default right away
pbc alias night moon                 # add more aliases later
pbc rename night midnight            # rename a wallpaper or an alias
pbc night                            # set it by name (or any alias: pbc n)
pbc ~/Pictures/any.png               # or set any image directly
pbc random                           # set a random saved wallpaper
pbc list                             # see what you saved (* marks the default); `pbc ls` works too
pbc default night                    # choose what a plain "pbc" sets
pbc remove night                     # forget a name (or just an alias)
pbc                                  # set the default wallpaper
```

> If a saved name clashes with a command (say, one called `list`, `ls`, `default` or `random`), use `pbc set list`.

## 🛠 Getting Started

follow the instruction to install Py Bg Changer from source (to try the latest code or to work on it):

1. Clone Code

   use [Git](https://git-scm.com/) on your system

   ```bash
   git clone https://github.com/Mr-MRF-Dev/Py-Bg-Changer.git
   ```

   or use [GitHub CLI](https://cli.github.com/)

   ```bash
   gh repo clone Mr-MRF-Dev/Py-Bg-Changer
   ```

2. Change your directory.

   ```bash
   cd Py-Bg-Changer
   ```

3. Install it with [uv](https://docs.astral.sh/uv/)

   ```bash
   uv tool install --editable .
   ```

   `--editable` means any change you make to the code is used right away. Leave it out for a normal install, or use `pip install .` if you prefer pip.

4. Check that it works

   ```bash
   pbc --version
   ```

Done :)

> to remove it later: `uv tool uninstall py-bg-changer` (your saved wallpapers and config stay where they are).

## 💡 Tips

- Running `pbc` from Win+R opens a terminal that closes right away. Use `pbcw` (or `py-bg-changer-w`) instead: it takes the same arguments, opens no window, and shows a small message box only if something goes wrong.

  ```bash
  pbcw night
  ```

  it prints nothing on success, so use `pbc` in a terminal for `list`, `default` and the like.

- `pbc random` sets one of your saved wallpapers at random. It skips images whose file is missing, and (when you have more than one) it never picks the image that is set right now, so you always get a change. To know that, the last image set is remembered in the config file under `current`. It works from Win+R too: `pbcw random`.

- A wallpaper can have as many aliases as you like, and every alias works anywhere a name does (`pbc n`, `pbc default n`, `pbc alias n moon`). Removing an alias leaves the wallpaper alone; removing a wallpaper also removes its aliases. Renaming a wallpaper keeps its aliases, its image and its place as the default.

- When you save an image, `py-bg-changer` keeps its own copy next to the config file and gives that copy to the system. If you later move or delete the original, the wallpaper still works. The copy is removed when you remove the name (or replace its image), and your original file is never touched.

- Saved names live in a small JSON file, and the copied images in a `wallpapers` folder next to it. Run `pbc path` to see where, or set `PBC_CONFIG` to use a different file.

  ```json
  {
    "wallpapers": {
      "night": "/home/me/.config/py-bg-changer/wallpapers/3e23e8160039594a.png"
    },
    "aliases": { "n": "night", "dark": "night" },
    "default": "night"
  }
  ```

## 🖥️ Supported Desktops

| OS      | Notes                                                                                                                                                        |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Windows | Built in, nothing extra needed                                                                                                                               |
| macOS   | Built in (uses `osascript`)                                                                                                                                  |
| Linux   | GNOME, Budgie, Cinnamon, MATE, KDE Plasma, XFCE and Sway work out of the box. Anything else (i3, bspwm, ...) falls back to `feh` or `nitrogen` if installed. |

## 👨‍💻 Development

the project is managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync              # create the virtualenv and install everything
uv run pytest        # run the tests
uv run pbc --help    # run the CLI from source
```

## 🤝 Contributing

we welcome any contributions you may have. If you're interested in helping out, fork the repository and create an [Issue](https://github.com/Mr-MRF-Dev/Py-Bg-Changer/issues) and [PR](https://github.com/Mr-MRF-Dev/Py-Bg-Changer/pulls).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](/LICENSE) file for details.
