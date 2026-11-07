from pathlib import Path

import pytest

from py_bg_changer import backends
from py_bg_changer.backends import (
    BACKENDS,
    Backend,
    BackendInfo,
    Environment,
    backend_info,
    pick,
)
from py_bg_changer.errors import WallpaperError


def linux(desktop="", session="x11", desktop_session=""):
    return Environment("Linux", desktop, desktop_session, session)


# --- the environment -----------------------------------------------------------------


def test_the_desktop_is_one_lowercase_string():
    env = Environment("Linux", "Ubuntu:GNOME", "ubuntu", "x11")
    assert env.desktop == "ubuntu:gnome:ubuntu"
    assert Environment("Linux", "", "MATE").desktop == "mate"
    assert Environment("Linux").desktop == ""


def test_the_session_is_lowercase():
    assert Environment("Linux", session_type="Wayland").session == "wayland"


def test_describe_shows_the_values_as_they_are():
    env = Environment("Linux", "Hyprland", "", "wayland")
    assert env.describe() == (
        "XDG_CURRENT_DESKTOP='Hyprland', DESKTOP_SESSION='', XDG_SESSION_TYPE='wayland'"
    )


def test_detect_reads_the_system_and_the_variables(monkeypatch):
    monkeypatch.setattr(backends.base.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("DESKTOP_SESSION", raising=False)
    assert Environment.detect() == Environment("Linux", "KDE", "", "wayland")


# --- the list of backends ----------------------------------------------------------------


def test_every_backend_has_its_own_name():
    names = [backend.name for backend in BACKENDS]
    assert len(names) == len(set(names))
    assert all(issubclass(backend, Backend) for backend in BACKENDS)


def test_the_catch_all_is_the_last_one():
    # it fits every X11 desktop, so anything after it would never be used
    assert BACKENDS[-1].name == "fallback (feh or nitrogen)"
    others = BACKENDS[:-1]
    for desktop in ("gnome", "kde", "xfce", "cinnamon", "mate", "sway", "i3"):
        fits = [b.name for b in others if b.matches(linux(desktop))]
        assert len(fits) <= 1, (desktop, fits)


@pytest.mark.parametrize(
    "env, name",
    [
        (Environment("Windows"), "windows (SystemParametersInfoW)"),
        (Environment("Darwin"), "macos (osascript)"),
        (linux("GNOME"), "gnome"),
        (linux("ubuntu:GNOME"), "gnome"),
        (linux("Budgie:GNOME"), "gnome"),
        (linux("Pantheon"), "gnome"),
        (linux("X-Cinnamon"), "cinnamon"),
        (linux("MATE"), "mate"),
        (linux("KDE"), "kde"),
        (linux("plasma"), "kde"),
        (linux("XFCE"), "xfce"),
        (linux("sway"), "sway"),
        (linux("i3"), "fallback (feh or nitrogen)"),
        (linux(""), "fallback (feh or nitrogen)"),
        (linux("Hyprland", session="x11"), "fallback (feh or nitrogen)"),
        (linux("", desktop_session="xfce"), "xfce"),
    ],
)
def test_the_backend_is_chosen_from_the_machine(env, name):
    backend = pick(env)
    assert backend is not None
    assert backend.name == name


def test_an_unknown_wayland_desktop_has_no_backend():
    assert pick(linux("Hyprland", session="wayland")) is None
    assert pick(Environment("FreeBSD")) is None


def test_a_known_wayland_desktop_still_has_one():
    assert pick(linux("sway", session="wayland")).name == "sway"
    assert pick(linux("GNOME", session="wayland")).name == "gnome"


# --- what doctor shows ---------------------------------------------------------------------


def test_info_for_windows_and_macos():
    assert backend_info(Environment("Windows")).tools == ()
    assert backend_info(Environment("Darwin")).tools == ("osascript",)


def test_info_for_a_known_linux_desktop():
    info = backend_info(linux("KDE"))
    assert info.name == "kde"
    assert info.tools == ("plasma-apply-wallpaperimage",)
    assert info.supported


def test_info_for_xfce_lists_the_optional_tool():
    info = backend_info(linux("XFCE"))
    assert info.tools == ("xfconf-query",)
    assert info.optional == ("xrandr",)
    assert "fresh XFCE" in info.note


def test_info_for_an_unknown_x11_desktop_needs_one_of_two_tools():
    info = backend_info(linux("i3"))
    assert info.tools == ("feh", "nitrogen")
    assert info.any_of


def test_info_for_an_unknown_wayland_desktop_is_unsupported():
    info = backend_info(linux("Hyprland", session="wayland"))
    assert not info.supported
    assert "Wayland" in info.note


def test_info_for_another_operating_system():
    info = backend_info(Environment("FreeBSD"))
    assert not info.supported
    assert "FreeBSD" in info.note


def test_info_is_what_a_backend_says_about_itself():
    assert BACKENDS[0].info() == BackendInfo(BACKENDS[0].name)


# --- setting the wallpaper ---------------------------------------------------------------------


@pytest.fixture
def ran(monkeypatch):
    """Record the commands instead of running them."""
    commands = []
    monkeypatch.setattr(
        Backend, "run", lambda self, cmd, **kwargs: commands.append(cmd)
    )
    return commands


def test_set_wallpaper_uses_the_backend_of_this_machine(monkeypatch, tmp_path, ran):
    monkeypatch.setattr(backends.base.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    image = tmp_path / "a.png"
    backends.set_wallpaper(image)
    assert ran == [["plasma-apply-wallpaperimage", str(image.resolve())]]


def test_set_wallpaper_resolves_the_path_first(monkeypatch, tmp_path, ran):
    monkeypatch.setattr(backends.base.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    monkeypatch.chdir(tmp_path)
    backends.set_wallpaper(Path("a.png"))
    assert ran[0][1] == str((tmp_path / "a.png").resolve())


def test_set_wallpaper_on_an_unknown_wayland_desktop_asks_for_an_issue(
    monkeypatch, tmp_path, ran
):
    monkeypatch.setattr(backends.base.platform, "system", lambda: "Linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "Hyprland")
    with pytest.raises(WallpaperError) as error:
        backends.set_wallpaper(tmp_path / "a.png")
    message = str(error.value)
    assert "XDG_CURRENT_DESKTOP='Hyprland'" in message
    assert "Wayland" in message
    assert "issues" in message
    assert ran == []


def test_set_wallpaper_on_another_operating_system_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(backends.base.platform, "system", lambda: "FreeBSD")
    with pytest.raises(WallpaperError, match="Unsupported operating system: FreeBSD"):
        backends.set_wallpaper(tmp_path / "a.png")
