from types import SimpleNamespace

import pytest

from py_bg_changer import backends
from py_bg_changer.backends import (
    Backend,
    Environment,
    pick,
)
from py_bg_changer.backends.base import LinuxDesktop
from py_bg_changer.errors import WallpaperError


@pytest.fixture
def ran(monkeypatch):
    """Record the commands instead of running them."""
    commands = []
    monkeypatch.setattr(
        Backend, "run", lambda self, cmd, **kwargs: commands.append(cmd)
    )
    return commands


def installed(monkeypatch, *tools):
    monkeypatch.setattr(
        backends.x11.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in tools else None,
    )


def linux(desktop="", session="x11"):
    return Environment("Linux", desktop, "", session)


# --- one command (or two) for each desktop ---------------------------------------------


@pytest.mark.parametrize(
    "desktop, expected",
    [
        (
            "GNOME",
            [
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.background",
                    "picture-uri",
                    "URI",
                ],
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.background",
                    "picture-uri-dark",
                    "URI",
                ],
            ],
        ),
        (
            "X-Cinnamon",
            [
                [
                    "gsettings",
                    "set",
                    "org.cinnamon.desktop.background",
                    "picture-uri",
                    "URI",
                ]
            ],
        ),
        (
            "MATE",
            [["gsettings", "set", "org.mate.background", "picture-filename", "PATH"]],
        ),
        ("KDE", [["plasma-apply-wallpaperimage", "PATH"]]),
        ("sway", [["swaymsg", "output", "*", "bg", "PATH", "fill"]]),
    ],
)
def test_each_desktop_gets_its_own_command(tmp_path, ran, desktop, expected):
    image = tmp_path / "a.png"
    pick(linux(desktop)).set(image)
    assert ran == [
        [
            part.replace("URI", image.as_uri()).replace("PATH", str(image))
            for part in cmd
        ]
        for cmd in expected
    ]


def test_the_dark_mode_key_of_gnome_is_allowed_to_fail(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(
        Backend, "run", lambda self, cmd, check=True: seen.append((cmd[-2], check))
    )
    pick(linux("GNOME")).set(tmp_path / "a.png")
    assert seen == [("picture-uri", True), ("picture-uri-dark", False)]


# --- macOS and Windows --------------------------------------------------------------------


def test_macos_runs_osascript_with_the_path_escaped(tmp_path, ran):
    image = tmp_path / 'my "best" \\ photo.png'
    pick(Environment("Darwin")).set(image)
    command, flag, script = ran[0]
    assert (command, flag) == ("osascript", "-e")
    assert 'to set picture to "' in script
    escaped = str(image).replace("\\", "\\\\").replace('"', '\\"')
    assert script.endswith(f'"{escaped}"')


def test_windows_asks_the_system_to_change_the_wallpaper(monkeypatch, tmp_path):
    import ctypes

    calls = []

    def system_parameters_info(action, param, path, flags):
        calls.append((action, param, path, flags))
        return 1

    user32 = SimpleNamespace(SystemParametersInfoW=system_parameters_info)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=user32), raising=False)
    image = tmp_path / "a.png"
    pick(Environment("Windows")).set(image)
    assert calls == [(0x14, 0, str(image), 0x03)]


def test_windows_can_refuse(monkeypatch, tmp_path):
    import ctypes

    user32 = SimpleNamespace(SystemParametersInfoW=lambda *args: 0)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=user32), raising=False)
    with pytest.raises(WallpaperError, match="Windows refused"):
        pick(Environment("Windows")).set(tmp_path / "a.png")


# --- any other desktop on X11 -----------------------------------------------------------------


def test_an_unknown_x11_desktop_uses_feh_when_it_is_installed(
    monkeypatch, tmp_path, ran
):
    installed(monkeypatch, "feh")
    image = tmp_path / "a.png"
    pick(linux("i3")).set(image)
    assert ran == [["feh", "--bg-fill", str(image)]]


def test_nitrogen_is_used_when_feh_is_not_installed(monkeypatch, tmp_path, ran):
    installed(monkeypatch, "nitrogen")
    image = tmp_path / "a.png"
    pick(linux("i3")).set(image)
    assert ran == [["nitrogen", "--set-zoom-fill", "--save", str(image)]]


def test_a_session_without_desktop_variables_still_uses_feh(monkeypatch, tmp_path, ran):
    # e.g. a window manager started with startx: all three variables are empty
    installed(monkeypatch, "feh")
    pick(Environment("Linux")).set(tmp_path / "a.png")
    assert ran[0][0] == "feh"


def test_an_unknown_x11_desktop_without_tools_explains_what_to_do(
    monkeypatch, tmp_path, ran
):
    installed(monkeypatch)
    with pytest.raises(WallpaperError) as error:
        pick(linux("i3")).set(tmp_path / "a.png")
    message = str(error.value)
    assert "XDG_SESSION_TYPE='x11'" in message
    assert "XDG_CURRENT_DESKTOP='i3'" in message
    assert "feh" in message
    assert ran == []


# --- supporting a new desktop ---------------------------------------------------------------------


def test_a_new_desktop_needs_only_a_class_and_a_place_in_the_list(
    monkeypatch, tmp_path, ran
):
    class Hyprland(LinuxDesktop):
        name = "hyprland"
        tools = ("hyprctl",)
        keywords = ("hyprland",)

        def set(self, path):
            self.run(["hyprctl", "hyprpaper", "wallpaper", f",{path}"])

    monkeypatch.setattr(backends, "BACKENDS", [Hyprland, *backends.BACKENDS])
    env = linux("Hyprland", session="wayland")  # no backend fitted this before
    assert pick(env).name == "hyprland"
    assert backends.backend_info(env).tools == ("hyprctl",)
    pick(env).set(tmp_path / "a.png")
    assert ran == [["hyprctl", "hyprpaper", "wallpaper", f",{tmp_path / 'a.png'}"]]
