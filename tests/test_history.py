import json
from pathlib import Path

from helpers import add_images, stored
from py_bg_changer import cli, config


def test_current_when_nothing_was_set(capsys):
    assert cli.main(["current"]) == 0
    assert "Nothing has been set" in capsys.readouterr().out


def test_current_shows_the_name_and_aliases(image, applied, capsys):
    cli.main(["add", "night", str(image), "-a", "n"])
    cli.main(["night"])
    capsys.readouterr()
    assert cli.main(["current"]) == 0
    out = capsys.readouterr().out
    assert "night (n)" in out
    assert str(stored("night").resolve()) in out


def test_current_shows_only_the_path_after_the_wallpaper_was_removed(
    image, applied, capsys
):
    cli.main(["add", "night", str(image)])
    cli.main(["night"])
    copy = stored("night").resolve()
    cli.main(["remove", "night"])
    capsys.readouterr()
    assert cli.main(["current"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(str(copy))
    assert "(missing)" in out


def test_current_marks_a_missing_file(image, applied, capsys):
    cli.main(["add", "night", str(image)])
    cli.main(["night"])
    stored("night").unlink()
    capsys.readouterr()
    cli.main(["current"])
    out = capsys.readouterr().out
    assert out.startswith("night")
    assert "(missing)" in out


def test_back_without_any_history_fails(applied, capsys):
    assert cli.main(["back"]) == 1
    assert applied == []
    assert "no previous wallpaper" in capsys.readouterr().err


def test_back_after_a_single_wallpaper_fails(tmp_path, applied):
    add_images(tmp_path, "a")
    cli.main(["a"])
    assert cli.main(["back"]) == 1


def test_back_walks_through_the_previous_wallpapers(tmp_path, applied):
    add_images(tmp_path, "a", "b", "c")
    for name in ("a", "b", "c"):
        cli.main([name])
    assert cli.main(["back"]) == 0
    assert applied[-1] == stored("b")
    assert cli.main(["back"]) == 0
    assert applied[-1] == stored("a")
    assert cli.main(["back"]) == 1


def test_back_does_not_add_itself_to_the_history(tmp_path, applied):
    add_images(tmp_path, "a", "b")
    cli.main(["a"])
    cli.main(["b"])
    assert cli.main(["back"]) == 0
    assert cli.main(["back"]) == 1  # a toggle between a and b would succeed here


def test_back_skips_images_that_are_missing(tmp_path, applied):
    add_images(tmp_path, "a", "b", "c")
    for name in ("a", "b", "c"):
        cli.main([name])
    stored("b").unlink()
    assert cli.main(["back"]) == 0
    assert applied[-1] == stored("a")


def test_back_updates_the_current_image(tmp_path, applied):
    add_images(tmp_path, "a", "b")
    cli.main(["a"])
    cli.main(["b"])
    cli.main(["back"])
    current = config.get_current()
    assert current is not None
    assert Path(current) == stored("a").resolve()


def test_back_prints_the_name(tmp_path, applied, capsys):
    add_images(tmp_path, "a", "b")
    cli.main(["a"])
    cli.main(["b"])
    capsys.readouterr()
    cli.main(["back"])
    assert "set back to a" in capsys.readouterr().out


def test_history_keeps_only_the_five_previous_images(tmp_path, applied):
    names = "abcdefgh"
    add_images(tmp_path, *names)
    for name in names:
        cli.main([name])
    assert config.HISTORY_LIMIT == 5
    assert [Path(p) for p in config.get_history()] == [
        stored(name).resolve() for name in "cdefg"
    ]


def test_history_does_not_contain_the_image_that_is_set_now(tmp_path, applied):
    add_images(tmp_path, "a", "b")
    cli.main(["a"])
    assert config.get_history() == []
    cli.main(["b"])
    assert [Path(p) for p in config.get_history()] == [stored("a").resolve()]
    current = config.get_current()
    assert current is not None
    assert Path(current) == stored("b").resolve()


def test_history_is_empty_again_after_going_all_the_way_back(tmp_path, applied):
    add_images(tmp_path, "a", "b", "c")
    for name in ("a", "b", "c"):
        cli.main([name])
    cli.main(["back"])
    cli.main(["back"])
    assert config.get_history() == []
    current = config.get_current()
    assert current is not None
    assert Path(current) == stored("a").resolve()


def test_setting_the_same_image_again_does_not_grow_the_history(tmp_path, applied):
    add_images(tmp_path, "a")
    for _ in range(3):
        cli.main(["a"])
    assert config.get_history() == []


def test_history_starts_from_the_current_image_of_an_older_version(tmp_path, applied):
    add_images(tmp_path, "a", "b")
    path = config.config_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    data["current"] = str(stored("a").resolve())  # no "history" key yet
    path.write_text(json.dumps(data), encoding="utf-8")
    cli.main(["b"])
    assert cli.main(["back"]) == 0
    assert applied[-1] == stored("a")


def test_an_older_history_that_ended_with_the_current_image_still_works(
    tmp_path, applied
):
    add_images(tmp_path, "a", "b")
    path = config.config_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    a, b = str(stored("a").resolve()), str(stored("b").resolve())
    data["history"], data["current"] = [a, b], b
    path.write_text(json.dumps(data), encoding="utf-8")
    assert cli.main(["back"]) == 0
    assert applied == [stored("a")]
    assert config.get_history() == []
