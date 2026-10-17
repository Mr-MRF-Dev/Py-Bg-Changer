import pytest

from py_bg_changer import cli, gui


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("PBC_CONFIG", str(tmp_path / "config.json"))


@pytest.fixture
def image(tmp_path):
    f = tmp_path / "pic.png"
    f.write_bytes(b"x")
    return f


@pytest.fixture
def applied(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "set_wallpaper", calls.append)
    return calls


@pytest.fixture
def popups(monkeypatch):
    messages = []
    monkeypatch.setattr(gui, "_show_error", messages.append)
    return messages


def test_success_is_silent(image, applied, popups, capsys):
    assert gui.main(["add", "night", str(image)]) == 0
    assert gui.main(["night"]) == 0
    assert len(applied) == 1
    assert popups == []
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_errors_show_a_message(applied, popups):
    assert gui.main(["nope"]) == 1
    assert applied == []
    assert len(popups) == 1
    assert "Unknown wallpaper" in popups[0]


def test_bad_arguments_show_a_message(popups):
    assert gui.main(["add"]) == 2
    assert len(popups) == 1
    assert popups[0]


def test_unexpected_errors_show_a_message(monkeypatch, popups):
    def boom(argv):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(gui, "cli_main", boom)
    assert gui.main(["anything"]) == 1
    assert "kaboom" in popups[0]
