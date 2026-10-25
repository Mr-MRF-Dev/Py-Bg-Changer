from types import SimpleNamespace

import pytest

from py_bg_changer import wallpaper


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "XDG_SESSION_TYPE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def ran(monkeypatch):
    """Record the commands instead of running them."""
    commands = []
    monkeypatch.setattr(wallpaper, "_run", lambda cmd, **kwargs: commands.append(cmd))
    return commands


def installed(monkeypatch, *tools):
    monkeypatch.setattr(
        wallpaper.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in tools else None,
    )


def test_unknown_x11_desktop_uses_feh_when_it_is_installed(monkeypatch, tmp_path, ran):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    installed(monkeypatch, "feh")
    image = tmp_path / "a.png"
    wallpaper._linux(image)
    assert ran == [["feh", "--bg-fill", str(image)]]


def test_session_without_desktop_variables_still_uses_feh(monkeypatch, tmp_path, ran):
    # e.g. a window manager started with startx: all three variables are empty
    installed(monkeypatch, "feh")
    wallpaper._linux(tmp_path / "a.png")
    assert ran[0][0] == "feh"


def test_unknown_x11_desktop_without_tools_explains_what_to_do(
    monkeypatch, tmp_path, ran
):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    installed(monkeypatch)
    with pytest.raises(wallpaper.WallpaperError) as error:
        wallpaper._linux(tmp_path / "a.png")
    message = str(error.value)
    assert "XDG_SESSION_TYPE='x11'" in message
    assert "feh" in message
    assert ran == []


def test_wayland_never_tries_feh_and_asks_for_an_issue(monkeypatch, tmp_path, ran):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    installed(monkeypatch, "feh", "nitrogen")
    with pytest.raises(wallpaper.WallpaperError) as error:
        wallpaper._linux(tmp_path / "a.png")
    message = str(error.value)
    assert "Hyprland" in message
    assert "Wayland" in message
    assert ran == []


# --- XFCE --------------------------------------------------------------------


@pytest.fixture
def xfce(monkeypatch):
    """A fake XFCE: answers xfconf-query / xrandr and records every command."""
    state = SimpleNamespace(
        properties=[],
        workspaces="",
        monitors=" 0: +*eDP-1 1920/344x1080/194+0+0  eDP-1",
        ran=[],
    )

    def fake_run(cmd, check=True):
        state.ran.append(cmd)
        out = ""
        if cmd[:4] == ["xfconf-query", "-c", "xfce4-desktop", "-l"]:
            out = "\n".join(state.properties)
        elif cmd[:3] == ["xfconf-query", "-c", "xfwm4"]:
            out = state.workspaces
        elif cmd[:2] == ["xrandr", "--listmonitors"]:
            out = "Monitors: 1\n" + state.monitors + "\n"
        return SimpleNamespace(stdout=out, stderr="", returncode=0)

    monkeypatch.setattr(wallpaper, "_run", fake_run)
    installed(monkeypatch, "xrandr")
    return state


def sets(state):
    return [c for c in state.ran if c[0] == "xfconf-query" and "-s" in c]


def test_xfce_updates_every_existing_wallpaper_setting(tmp_path, xfce):
    xfce.properties = [
        "/backdrop/screen0/monitoreDP-1/workspace0/last-image",
        "/backdrop/screen0/monitoreDP-1/workspace1/last-image",
        "/desktop-icons/style",
    ]
    image = tmp_path / "a.png"
    wallpaper._xfce(image)
    assert [c[4] for c in sets(xfce)] == [
        "/backdrop/screen0/monitoreDP-1/workspace0/last-image",
        "/backdrop/screen0/monitoreDP-1/workspace1/last-image",
    ]
    assert all("--create" not in c for c in sets(xfce))
    assert all(c[-1] == str(image) for c in sets(xfce))


def test_fresh_xfce_gets_its_settings_created(tmp_path, xfce):
    xfce.properties = ["/desktop-icons/style", "/last-settings-migration-version"]
    xfce.workspaces = "2\n"
    xfce.monitors = (
        " 0: +*eDP-1 1920/344x1080/194+0+0  eDP-1\n"
        " 1: +HDMI-1 1920/527x1080/296+1920+0  HDMI-1"
    )
    image = tmp_path / "a.png"
    wallpaper._xfce(image)
    assert [c[4] for c in sets(xfce)] == [
        "/backdrop/screen0/monitoreDP-1/workspace0/last-image",
        "/backdrop/screen0/monitoreDP-1/workspace1/last-image",
        "/backdrop/screen0/monitorHDMI-1/workspace0/last-image",
        "/backdrop/screen0/monitorHDMI-1/workspace1/last-image",
    ]
    for command in sets(xfce):
        assert command[5:] == ["--create", "-t", "string", "-s", str(image)]


def test_fresh_xfce_assumes_four_workspaces_when_unknown(tmp_path, xfce):
    wallpaper._xfce(tmp_path / "a.png")
    assert len(sets(xfce)) == 4


def test_fresh_xfce_without_xrandr_explains_what_to_do(monkeypatch, tmp_path, xfce):
    installed(monkeypatch)  # nothing installed
    with pytest.raises(wallpaper.WallpaperError) as error:
        wallpaper._xfce(tmp_path / "a.png")
    assert "Settings > Desktop" in str(error.value)
    assert sets(xfce) == []


# --- picking the backend -----------------------------------------------------


@pytest.mark.parametrize(
    "desktop, backend",
    [
        ("gnome", "gnome"),
        ("ubuntu:gnome", "gnome"),
        ("budgie:gnome", "gnome"),
        ("pantheon", "gnome"),
        ("x-cinnamon", "cinnamon"),
        ("mate", "mate"),
        ("kde", "kde"),
        ("plasma", "kde"),
        ("xfce", "xfce"),
        ("sway", "sway"),
        ("i3", "fallback"),
        ("hyprland", "fallback"),
        ("", "fallback"),
    ],
)
def test_linux_backend_is_chosen_from_the_desktop_name(desktop, backend):
    assert wallpaper._linux_backend(desktop) == backend


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
def test_each_desktop_gets_its_own_command(
    monkeypatch, tmp_path, ran, desktop, expected
):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", desktop)
    image = tmp_path / "a.png"
    wallpaper._linux(image)
    assert ran == [
        [
            part.replace("URI", image.as_uri()).replace("PATH", str(image))
            for part in cmd
        ]
        for cmd in expected
    ]


def system(monkeypatch, name):
    monkeypatch.setattr(wallpaper.platform, "system", lambda: name)


def test_backend_info_for_windows_and_macos(monkeypatch):
    system(monkeypatch, "Windows")
    assert wallpaper.backend_info().tools == ()
    system(monkeypatch, "Darwin")
    assert wallpaper.backend_info().tools == ("osascript",)


def test_backend_info_for_a_known_linux_desktop(monkeypatch):
    system(monkeypatch, "Linux")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    info = wallpaper.backend_info()
    assert info.name == "kde"
    assert info.tools == ("plasma-apply-wallpaperimage",)


def test_backend_info_for_an_unknown_x11_desktop_needs_one_of_two_tools(monkeypatch):
    system(monkeypatch, "Linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    info = wallpaper.backend_info()
    assert info.tools == ("feh", "nitrogen")
    assert info.any_of


def test_backend_info_for_an_unknown_wayland_desktop_is_unsupported(monkeypatch):
    system(monkeypatch, "Linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    info = wallpaper.backend_info()
    assert not info.supported
    assert "Wayland" in info.note


def test_backend_info_for_another_operating_system(monkeypatch):
    system(monkeypatch, "FreeBSD")
    assert not wallpaper.backend_info().supported
