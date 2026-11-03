import json

import pytest

from helpers import save_wallpapers
from py_bg_changer import cli, config
from py_bg_changer.errors import ConfigError
from py_bg_changer.library import Library
from py_bg_changer.state import State


def test_old_bg_py_config_format_still_loads(tmp_path, monkeypatch):
    old = tmp_path / "old.json"
    old.write_text('{"wallpapers": {"default": "C:/x.jpg"}}', encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(old))
    assert config.load_library().wallpapers == {"default": "C:/x.jpg"}


def test_other_config_keys_survive_a_save(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text('{"wallpapers": {}, "future": 1}', encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(f))
    save_wallpapers({"a": "b"})
    assert '"future": 1' in f.read_text(encoding="utf-8")


def test_corrupt_config_reports_error(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(bad))
    assert cli.main(["list"]) == 1
    assert "Could not read" in capsys.readouterr().err


# --- the library and the state in the file -----------------------------------------


def test_the_library_round_trips(tmp_path):
    library = Library(
        wallpapers={"night": "/img/n.png", "day": "/img/d.png"},
        aliases={"n": "night"},
        default="night",
    )
    config.save_library(library)
    assert config.load_library() == library


def test_an_empty_library_is_written_without_empty_keys():
    config.save_library(Library())
    data = json.loads(config.config_path().read_text(encoding="utf-8"))
    assert data == {"wallpapers": {}}


def test_nothing_saved_yet_loads_an_empty_library():
    assert config.load_library() == Library()
    assert config.load_state() == State()


def test_saving_the_library_keeps_the_state_and_unknown_keys(tmp_path):
    config.config_path().write_text(
        json.dumps(
            {
                "wallpapers": {},
                "current": "/img/a.png",
                "history": ["/img/b.png"],
                "future": 1,
            }
        ),
        encoding="utf-8",
    )
    config.save_library(Library(wallpapers={"a": "/img/a.png"}, default="a"))
    data = json.loads(config.config_path().read_text(encoding="utf-8"))
    assert data["current"] == "/img/a.png"
    assert data["history"] == ["/img/b.png"]
    assert data["future"] == 1
    assert data["default"] == "a"


def test_saving_the_state_keeps_the_library():
    config.save_library(Library(wallpapers={"a": "/img/a.png"}, default="a"))
    config.save_state(State(current="/img/a.png", history=["/img/b.png"]))
    assert config.load_library().wallpapers == {"a": "/img/a.png"}
    assert config.load_library().default == "a"
    assert config.load_state() == State(current="/img/a.png", history=["/img/b.png"])


def test_a_dangling_default_is_kept_as_it_is_written():
    config.config_path().write_text(
        json.dumps({"wallpapers": {}, "default": "gone"}), encoding="utf-8"
    )
    library = config.load_library()
    assert library.default == "gone"
    assert library.default_name() is None


@pytest.mark.parametrize("key", ["wallpapers", "aliases"])
def test_a_wrongly_shaped_config_is_reported(key):
    config.config_path().write_text(json.dumps({key: ["oops"]}), encoding="utf-8")
    with pytest.raises(ConfigError, match=f"'{key}' must be an object"):
        config.load_library()


def test_a_history_that_also_ended_with_the_current_image_is_cleaned_up():
    config.config_path().write_text(
        json.dumps({"current": "/img/b.png", "history": ["/img/a.png", "/img/b.png"]}),
        encoding="utf-8",
    )
    assert config.load_state() == State(current="/img/b.png", history=["/img/a.png"])


# --- every command writes the config once, never half of it ----------------------------


@pytest.fixture
def writes(monkeypatch):
    calls = []
    real = config._write

    def counting(data):
        calls.append(data)
        real(data)

    monkeypatch.setattr(config, "_write", counting)
    return calls


def test_adding_with_aliases_and_default_is_one_write(image, writes):
    cli.main(["add", "night", str(image), "-a", "n", "--default"])
    assert len(writes) == 1
    assert writes[0]["default"] == "night"
    assert writes[0]["aliases"] == {"n": "night"}


def test_renaming_the_default_is_one_write(image, writes):
    cli.main(["add", "night", str(image), "-a", "n", "-d"])
    writes.clear()
    cli.main(["rename", "night", "midnight"])
    assert len(writes) == 1
    assert writes[0]["default"] == "midnight"
    assert writes[0]["aliases"] == {"n": "midnight"}


def test_removing_the_default_is_one_write(image, writes):
    cli.main(["add", "night", str(image), "-d"])
    writes.clear()
    cli.main(["remove", "night"])
    assert len(writes) == 1
    assert "default" not in writes[0]


def test_a_command_that_changes_nothing_writes_nothing(image, writes):
    cli.main(["add", "night", str(image), "-a", "n"])
    writes.clear()
    cli.main(["alias", "night", "n"])
    cli.main(["rename", "night", "night"])
    cli.main(["list"])
    assert writes == []
