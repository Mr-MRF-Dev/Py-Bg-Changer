from pathlib import Path

import pytest

from helpers import add_images, stored
from py_bg_changer import cli, config


@pytest.fixture
def first_choice(monkeypatch):
    """Make `pbc random` deterministic: always take the first candidate."""
    offered = []

    def choose(seq):
        offered.append(list(seq))
        return seq[0]

    monkeypatch.setattr(cli.random, "choice", choose)
    return offered


def test_random_sets_one_of_the_saved_wallpapers(tmp_path, applied):
    add_images(tmp_path, "a", "b", "c")
    assert cli.main(["random"]) == 0
    assert len(applied) == 1
    assert applied[0] in {stored("a"), stored("b"), stored("c")}


def test_random_avoids_the_wallpaper_that_is_set_right_now(
    tmp_path, applied, first_choice
):
    add_images(tmp_path, "a", "b")
    for _ in range(3):
        assert cli.main(["random"]) == 0
    assert applied == [stored("a"), stored("b"), stored("a")]


def test_random_never_repeats_back_to_back(tmp_path, applied):
    add_images(tmp_path, "a", "b", "c")
    for _ in range(30):
        cli.main(["random"])
    assert len(applied) == 30
    assert all(x != y for x, y in zip(applied, applied[1:], strict=False))


def test_random_avoids_an_image_that_was_set_by_alias(tmp_path, applied, first_choice):
    add_images(tmp_path, "a", "b")
    cli.main(["alias", "a", "x"])
    assert cli.main(["x"]) == 0
    assert cli.main(["random"]) == 0
    assert applied == [stored("a"), stored("b")]


def test_random_with_a_single_wallpaper_still_works(tmp_path, applied, first_choice):
    add_images(tmp_path, "a")
    assert cli.main(["random"]) == 0
    assert cli.main(["random"]) == 0
    assert applied == [stored("a"), stored("a")]


def test_random_offers_each_image_once_even_with_two_names(
    tmp_path, image, applied, first_choice
):
    cli.main(["add", "a", str(image)])
    cli.main(["add", "b", str(image)])  # same image under a second name
    add_images(tmp_path, "c")
    assert stored("a") == stored("b")
    assert cli.main(["random"]) == 0
    assert len(first_choice[0]) == 2


def test_random_skips_images_that_are_missing(tmp_path, applied, first_choice):
    add_images(tmp_path, "a", "b")
    stored("a").unlink()
    assert cli.main(["random"]) == 0
    assert cli.main(["random"]) == 0
    assert applied == [stored("b"), stored("b")]


def test_random_with_nothing_saved_fails(applied, capsys):
    assert cli.main(["random"]) == 1
    assert applied == []
    assert "Nothing is saved yet" in capsys.readouterr().err


def test_random_when_every_file_is_missing_fails(tmp_path, applied, capsys):
    config.save({"gone": str(tmp_path / "gone.png")})
    assert cli.main(["random"]) == 1
    assert applied == []
    assert "exist any more" in capsys.readouterr().err


def test_setting_a_wallpaper_remembers_the_current_image(image, applied):
    cli.main(["add", "night", str(image)])
    assert config.get_current() is None
    cli.main(["night"])
    current = config.get_current()
    assert current is not None
    assert Path(current) == stored("night").resolve()
