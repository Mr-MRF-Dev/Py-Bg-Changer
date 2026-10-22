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
