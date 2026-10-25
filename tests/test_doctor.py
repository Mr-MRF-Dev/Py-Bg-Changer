import pytest

from py_bg_changer import cli, config, doctor, wallpaper


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("PBC_CONFIG", str(tmp_path / "config.json"))


def backend(monkeypatch, info):
    monkeypatch.setattr(doctor, "backend_info", lambda: info)


def installed(monkeypatch, *tools):
    monkeypatch.setattr(
        doctor.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in tools else None,
    )


def test_everything_in_place(monkeypatch, capsys):
    backend(monkeypatch, wallpaper.Backend("gnome", ("gsettings",)))
    installed(monkeypatch, "gsettings")
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "[ok] gsettings" in out
    assert "Everything looks fine" in out
    assert str(config.config_path()) in out


def test_a_missing_tool_is_a_problem(monkeypatch, capsys):
    backend(monkeypatch, wallpaper.Backend("gnome", ("gsettings",)))
    installed(monkeypatch)
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "[missing] gsettings" in out
    assert "Found 1 problem" in out


def test_one_of_two_tools_is_enough(monkeypatch):
    info = wallpaper.Backend("fallback", ("feh", "nitrogen"), any_of=True)
    backend(monkeypatch, info)
    installed(monkeypatch, "nitrogen")
    assert cli.main(["doctor"]) == 0
    installed(monkeypatch)
    assert cli.main(["doctor"]) == 1


def test_optional_tools_are_never_a_problem(monkeypatch, capsys):
    info = wallpaper.Backend(
        "xfce", ("xfconf-query",), optional=("xrandr",), note="xrandr is optional"
    )
    backend(monkeypatch, info)
    installed(monkeypatch, "xfconf-query")
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "[missing] xrandr (optional)" in out
    assert "Note: xrandr is optional" in out


def test_an_unsupported_desktop_is_a_problem(monkeypatch, capsys):
    info = wallpaper.Backend(
        "none", supported=False, note="this Wayland desktop is not supported yet"
    )
    backend(monkeypatch, info)
    assert cli.main(["doctor"]) == 1
    assert "not supported yet" in capsys.readouterr().out


def test_a_corrupt_config_is_reported_and_doctor_keeps_going(
    tmp_path, monkeypatch, capsys
):
    backend(monkeypatch, wallpaper.Backend("windows"))
    config.config_path().write_text("{oops", encoding="utf-8")
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "cannot be read" in out
    assert "Backend:" in out


def test_saved_wallpapers_and_missing_files_are_listed(tmp_path, monkeypatch, capsys):
    backend(monkeypatch, wallpaper.Backend("windows"))
    config.save({"gone": str(tmp_path / "gone.png")})
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "1 wallpaper(s)" in out
    assert "gone" in out
