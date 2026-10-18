from pathlib import Path

import pytest

from py_bg_changer import cache, cli, config


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


def stored(name):
    return Path(config.load()[name])


# --- setting wallpapers ------------------------------------------------------


def test_add_then_set_by_name(image, applied):
    assert cli.main(["add", "night", str(image)]) == 0
    assert cli.main(["night"]) == 0
    assert applied == [stored("night")]


def test_set_by_direct_path(image, applied):
    assert cli.main([str(image)]) == 0
    assert applied == [image]


def test_unknown_name_fails_with_suggestion(image, applied, capsys):
    cli.main(["add", "night", str(image)])
    assert cli.main(["nigth"]) == 1
    assert applied == []
    err = capsys.readouterr().err
    assert "Unknown wallpaper" in err
    assert "Did you mean 'night'" in err


def test_missing_file_fails(tmp_path, applied, capsys):
    config.save({"gone": str(tmp_path / "gone.png")})
    assert cli.main(["gone"]) == 1
    assert applied == []
    assert "File not found" in capsys.readouterr().err


def test_remove(image):
    cli.main(["add", "a", str(image)])
    assert cli.main(["remove", "a"]) == 0
    assert config.load() == {}


def test_list_marks_missing_files(tmp_path, capsys):
    config.save({"gone": str(tmp_path / "gone.png")})
    assert cli.main(["list"]) == 0
    assert "(missing)" in capsys.readouterr().out


# --- default wallpaper -------------------------------------------------------


def test_default_command_sets_and_shows(image, capsys):
    cli.main(["add", "night", str(image)])
    assert cli.main(["default"]) == 0
    assert "No default" in capsys.readouterr().out
    assert cli.main(["default", "night"]) == 0
    capsys.readouterr()
    assert cli.main(["default"]) == 0
    assert capsys.readouterr().out.strip() == "night"


def test_no_arguments_sets_the_chosen_default(tmp_path, image, applied):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "day", str(image)])
    cli.main(["add", "night", str(other)])
    cli.main(["default", "night"])
    assert cli.main([]) == 0
    assert applied == [stored("night")]


def test_add_with_default_flag(image):
    cli.main(["add", "night", str(image), "--default"])
    assert config.get_default() == "night"


def test_no_default_gives_a_hint(image, applied, capsys):
    cli.main(["add", "night", str(image)])
    assert cli.main([]) == 1
    assert applied == []
    assert "pbc default" in capsys.readouterr().err


def test_default_must_be_a_saved_name(capsys):
    assert cli.main(["default", "nope"]) == 1
    assert "Unknown wallpaper" in capsys.readouterr().err


def test_removing_the_default_clears_it(image):
    cli.main(["add", "night", str(image), "-d"])
    cli.main(["remove", "night"])
    assert config.get_default() is None


def test_list_marks_the_default(image, capsys):
    cli.main(["add", "night", str(image), "-d"])
    capsys.readouterr()
    cli.main(["list"])
    assert capsys.readouterr().out.startswith("*")


def test_wallpaper_named_default_still_works(image, applied):
    # configs from the original bg.py have a wallpaper literally named "default"
    config.save({"default": str(image)})
    assert cli.main([]) == 0
    assert applied == [image]


# --- our own copy of each image ----------------------------------------------


def test_add_keeps_a_private_copy(image):
    cli.main(["add", "night", str(image)])
    copy = stored("night")
    assert copy != image.resolve()
    assert copy.parent == cache.cache_dir()
    assert copy.read_bytes() == image.read_bytes()


def test_still_works_after_the_original_is_deleted(image, applied):
    cli.main(["add", "night", str(image)])
    image.unlink()
    assert cli.main(["night"]) == 0
    assert applied == [stored("night")]


def test_remove_deletes_the_copy(image):
    cli.main(["add", "a", str(image)])
    copy = stored("a")
    assert cli.main(["remove", "a"]) == 0
    assert not copy.exists()


def test_shared_copy_lives_until_the_last_name_is_removed(image):
    cli.main(["add", "a", str(image)])
    cli.main(["add", "b", str(image)])
    copy = stored("a")
    assert copy == stored("b")
    cli.main(["remove", "a"])
    assert copy.exists()
    cli.main(["remove", "b"])
    assert not copy.exists()


def test_replacing_an_image_drops_the_old_copy(image):
    cli.main(["add", "a", str(image)])
    old = stored("a")
    image.write_bytes(b"different")
    cli.main(["add", "a", str(image)])
    assert stored("a") != old
    assert stored("a").exists()
    assert not old.exists()


def test_original_is_never_touched_by_remove(image):
    cli.main(["add", "a", str(image)])
    cli.main(["remove", "a"])
    assert image.exists()


# --- aliases -----------------------------------------------------------------


def test_add_with_aliases_then_set_by_alias(image, applied):
    assert cli.main(["add", "night", str(image), "-a", "n", "--alias", "dark"]) == 0
    assert cli.main(["dark"]) == 0
    assert cli.main(["n"]) == 0
    assert applied == [stored("night")] * 2


def test_alias_command_adds_aliases_later(image, applied):
    cli.main(["add", "night", str(image)])
    assert cli.main(["alias", "night", "n", "dark"]) == 0
    assert config.load_aliases() == {"n": "night", "dark": "night"}
    assert cli.main(["n"]) == 0
    assert applied == [stored("night")]


def test_alias_can_be_added_through_another_alias(image):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["alias", "n", "dark"]) == 0
    assert config.load_aliases()["dark"] == "night"


def test_alias_cannot_reuse_a_wallpaper_name(tmp_path, image, capsys):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "night", str(image)])
    cli.main(["add", "day", str(other)])
    assert cli.main(["alias", "night", "day"]) == 1
    assert "already a saved wallpaper" in capsys.readouterr().err
    assert config.load_aliases() == {}


def test_alias_cannot_point_to_two_wallpapers(tmp_path, image, capsys):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "night", str(image), "-a", "n"])
    cli.main(["add", "day", str(other)])
    assert cli.main(["alias", "day", "n"]) == 1
    assert "already an alias of 'night'" in capsys.readouterr().err
    assert config.load_aliases() == {"n": "night"}


def test_name_cannot_be_an_existing_alias(image, capsys):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["add", "n", str(image)]) == 1
    assert "alias of 'night'" in capsys.readouterr().err


def test_failed_add_changes_nothing(tmp_path, image):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "night", str(image)])
    assert cli.main(["add", "day", str(other), "-a", "night"]) == 1
    assert list(config.load()) == ["night"]
    assert len(list(cache.cache_dir().iterdir())) == 1


def test_adding_the_same_alias_again_is_fine(image):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["alias", "night", "n"]) == 0
    assert config.load_aliases() == {"n": "night"}


def test_default_can_be_chosen_by_alias(image, applied):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["default", "n"]) == 0
    assert config.get_default() == "night"
    assert cli.main([]) == 0
    assert applied == [stored("night")]


def test_removing_an_alias_keeps_the_wallpaper(image):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["remove", "n"]) == 0
    assert config.load_aliases() == {}
    assert "night" in config.load()


def test_removing_a_wallpaper_removes_its_aliases(image, applied):
    cli.main(["add", "night", str(image), "-a", "n", "-a", "dark"])
    assert cli.main(["remove", "night"]) == 0
    assert config.load_aliases() == {}
    assert cli.main(["n"]) == 1
    assert applied == []


def test_list_shows_aliases(image, capsys):
    cli.main(["add", "night", str(image), "-a", "n", "-a", "dark"])
    capsys.readouterr()
    cli.main(["list"])
    assert "night (n, dark)" in capsys.readouterr().out


def test_aliases_follow_a_replaced_image(image, applied):
    cli.main(["add", "night", str(image), "-a", "n"])
    image.write_bytes(b"different")
    cli.main(["add", "night", str(image)])
    assert cli.main(["n"]) == 0
    assert applied == [stored("night")]


# --- config file -------------------------------------------------------------


def test_old_bg_py_config_format_still_loads(tmp_path, monkeypatch):
    old = tmp_path / "old.json"
    old.write_text('{"wallpapers": {"default": "C:/x.jpg"}}', encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(old))
    assert config.load() == {"default": "C:/x.jpg"}


def test_other_config_keys_survive_a_save(tmp_path, monkeypatch):
    f = tmp_path / "c.json"
    f.write_text('{"wallpapers": {}, "future": 1}', encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(f))
    config.save({"a": "b"})
    assert '"future": 1' in f.read_text(encoding="utf-8")


def test_corrupt_config_reports_error(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(bad))
    assert cli.main(["list"]) == 1
    assert "Could not read" in capsys.readouterr().err
