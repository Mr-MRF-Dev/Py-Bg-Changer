import json
from pathlib import Path

import pytest

from helpers import save_wallpapers
from py_bg_changer import cli, config, jsonfile
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
    assert data == {"version": 2, "wallpapers": {}}


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
    config_data = json.loads(config.config_path().read_text(encoding="utf-8"))
    assert "current" not in config_data
    assert "history" not in config_data
    state_data = json.loads(config.state_path().read_text(encoding="utf-8"))
    assert state_data == {
        "version": 2,
        "current": "/img/a.png",
        "history": ["/img/b.png"],
    }


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


# --- every command writes the config once, never half of it ----------------------------


@pytest.fixture
def writes(monkeypatch):
    """The data written to the config file, one entry per write."""
    calls = []
    real = jsonfile.write

    def counting(path, data):
        if path == config.config_path():
            calls.append(data)
        real(path, data)

    monkeypatch.setattr(jsonfile, "write", counting)
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


def test_setting_a_wallpaper_never_writes_the_config(image, applied, writes):
    cli.main(["add", "night", str(image), "-d"])
    writes.clear()
    cli.main(["night"])
    cli.main([])
    cli.main(["random"])
    assert writes == []
    assert config.load_state().current is not None  # it went to state.json


# --- where the files are ---------------------------------------------------------------


@pytest.fixture
def default_places(monkeypatch, tmp_path):
    """No overrides: the places the program uses on a normal machine."""
    for name in (
        "PBC_CONFIG",
        "PBC_STATE",
        "XDG_CONFIG_HOME",
        "XDG_STATE_HOME",
        "APPDATA",
        "LOCALAPPDATA",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def system(monkeypatch, name):
    monkeypatch.setattr(config.platform, "system", lambda: name)


def test_state_is_in_the_state_folder_of_linux(monkeypatch, default_places):
    system(monkeypatch, "Linux")
    assert (
        config.state_path()
        == default_places / ".local" / "state" / "py-bg-changer" / "state.json"
    )
    assert (
        config.config_path()
        == default_places / ".config" / "py-bg-changer" / "config.json"
    )


def test_state_follows_xdg_state_home(monkeypatch, default_places):
    system(monkeypatch, "Linux")
    monkeypatch.setenv("XDG_STATE_HOME", str(default_places / "elsewhere"))
    assert (
        config.state_path()
        == default_places / "elsewhere" / "py-bg-changer" / "state.json"
    )


def test_state_is_in_the_local_folder_on_windows(monkeypatch, default_places):
    system(monkeypatch, "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(default_places / "Local"))
    monkeypatch.setenv("APPDATA", str(default_places / "Roaming"))
    assert (
        config.state_path() == default_places / "Local" / "py-bg-changer" / "state.json"
    )
    assert (
        config.config_path()
        == default_places / "Roaming" / "py-bg-changer" / "config.json"
    )


def test_state_and_config_share_the_folder_on_macos(monkeypatch, default_places):
    system(monkeypatch, "Darwin")
    assert config.state_path().parent == config.config_path().parent
    assert config.state_path().name == "state.json"


def test_a_custom_config_keeps_its_state_next_to_it(monkeypatch, default_places):
    system(monkeypatch, "Linux")
    monkeypatch.setenv("PBC_CONFIG", str(default_places / "mine" / "c.json"))
    assert config.state_path() == default_places / "mine" / "state.json"


def test_the_state_file_can_be_chosen(monkeypatch, default_places):
    monkeypatch.setenv("PBC_CONFIG", str(default_places / "mine" / "c.json"))
    monkeypatch.setenv("PBC_STATE", str(default_places / "elsewhere.json"))
    assert config.state_path() == default_places / "elsewhere.json"


def test_no_state_file_means_an_empty_state():
    assert not config.state_path().exists()
    assert config.load_state() == State()


def test_saving_the_state_keeps_unknown_keys():
    config.state_path().write_text(
        json.dumps({"version": 2, "future": 7}), encoding="utf-8"
    )
    config.save_state(State(current="/img/a.png"))
    data = json.loads(config.state_path().read_text(encoding="utf-8"))
    assert data == {"version": 2, "future": 7, "current": "/img/a.png", "history": []}


def test_a_library_saved_before_the_migration_is_not_stamped_as_migrated():
    # it still holds the state of version 1, so it must stay version 1 until migrated
    config.config_path().write_text(
        json.dumps({"wallpapers": {}, "current": "/img/a.png"}), encoding="utf-8"
    )
    config.save_library(Library(wallpapers={"a": "/img/a.png"}))
    assert "version" not in json.loads(config.config_path().read_text(encoding="utf-8"))
