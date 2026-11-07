import pytest

from py_bg_changer import doctor, gui
from py_bg_changer.backends import BackendInfo


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

    monkeypatch.setattr(gui, "cli_run", boom)
    assert gui.main(["anything"]) == 1
    assert "kaboom" in popups[0]


def test_a_report_with_problems_is_shown_in_a_message(monkeypatch, popups):
    info = BackendInfo("none", supported=False, note="this desktop is not supported")
    monkeypatch.setattr(doctor, "backend_info", lambda: info)
    assert gui.main(["doctor"]) == 1
    assert len(popups) == 1
    assert "not supported" in popups[0]
    assert "Found 1 problem" in popups[0]


def test_help_is_silent_and_not_an_error(popups):
    assert gui.main(["--help"]) == 0
    assert popups == []
