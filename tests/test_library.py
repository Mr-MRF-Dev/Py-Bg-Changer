from pathlib import Path

import pytest

from py_bg_changer.errors import UserError
from py_bg_changer.library import Library


@pytest.fixture
def library():
    return Library(
        wallpapers={"night": "/img/night.png", "day": "/img/day.png"},
        aliases={"n": "night", "dark": "night"},
        default="night",
    )


# --- looking things up ---------------------------------------------------------


def test_resolve_finds_names_and_aliases(library):
    assert library.resolve("night") == "night"
    assert library.resolve("dark") == "night"
    assert library.resolve("nope") is None


def test_an_alias_of_a_missing_wallpaper_resolves_to_nothing(library):
    library.aliases["ghost"] = "gone"
    assert library.resolve("ghost") is None


def test_kind_of(library):
    assert library.kind_of("night") == "wallpaper"
    assert library.kind_of("n") == "alias"
    assert library.kind_of("nope") is None


def test_labels_show_the_aliases(library):
    assert library.label("night") == "night (n, dark)"
    assert library.label("day") == "day"
    assert library.labels() == "night (n, dark), day"


def test_default_name_follows_the_chosen_default(library):
    library.default = "dark"  # an alias works too
    assert library.default_name() == "night"
    assert library.chosen_default() == "night"


def test_default_name_ignores_a_default_that_no_longer_exists(library):
    library.default = "gone"
    assert library.chosen_default() is None
    assert library.default_name() is None


def test_a_wallpaper_named_default_is_used_when_nothing_is_chosen():
    # configs from the original bg.py
    library = Library(wallpapers={"default": "/img/a.png"})
    assert library.chosen_default() is None
    assert library.default_name() == "default"


def test_names_using_an_image(tmp_path):
    image = tmp_path / "a.png"
    library = Library(
        wallpapers={"a": str(image), "b": str(image), "c": str(tmp_path / "c.png")},
        aliases={"x": "a"},
    )
    assert library.names_using(image.resolve()) == ["a (x)", "b"]


def test_unknown_suggests_a_close_name_and_lists_what_exists(library):
    error = library.unknown("nigth")
    assert isinstance(error, UserError)
    assert "Unknown wallpaper: 'nigth'" in str(error)
    assert "Did you mean 'night'?" in str(error)
    assert "Available: night (n, dark), day" in str(error)


def test_unknown_in_an_empty_library_says_how_to_add_one():
    assert "pbc add NAME IMAGE" in str(Library().unknown("x"))


# --- adding ----------------------------------------------------------------------


def test_add_saves_the_wallpaper_and_its_aliases(library):
    aliases = library.check_new("dusk", ["d", "evening", "d"])
    assert aliases == ["d", "evening"]  # no repeats
    assert library.add("dusk", "/img/dusk.png", aliases) is None
    assert library.wallpapers["dusk"] == "/img/dusk.png"
    assert library.aliases["d"] == library.aliases["evening"] == "dusk"


def test_add_returns_the_image_it_replaced(library):
    assert library.add("night", "/img/new.png", []) == "/img/night.png"
    assert library.aliases["n"] == "night"  # the aliases follow the new image


@pytest.mark.parametrize(
    "name, aliases, message",
    [
        ("n", [], "already an alias of 'night'"),
        ("dusk", ["dusk"], "already the name of this wallpaper"),
        ("dusk", ["day"], "already a saved wallpaper name"),
        ("dusk", ["n"], "already an alias of 'night'"),
    ],
)
def test_check_new_refuses_names_that_are_taken(library, name, aliases, message):
    with pytest.raises(UserError, match=message):
        library.check_new(name, aliases)


def test_a_wallpaper_may_repeat_its_own_alias(library):
    assert library.check_new("night", ["n"]) == ["n"]


def test_add_aliases_through_another_alias(library):
    assert library.add_aliases("n", ["moon"]) == ("night", ["moon"])
    assert library.aliases["moon"] == "night"


def test_add_aliases_returns_only_the_new_ones(library):
    assert library.add_aliases("night", ["n", "moon"]) == ("night", ["moon"])
    assert library.add_aliases("night", ["n"]) == ("night", [])


def test_add_aliases_to_an_unknown_name_fails(library):
    with pytest.raises(UserError, match="Unknown wallpaper"):
        library.add_aliases("nope", ["x"])


def test_an_alias_cannot_take_the_name_of_another_wallpaper(library):
    with pytest.raises(UserError, match="already a saved wallpaper name"):
        library.add_aliases("night", ["day"])
    assert library.aliases == {"n": "night", "dark": "night"}


# --- renaming --------------------------------------------------------------------


def test_renaming_a_wallpaper_keeps_its_place_its_aliases_and_the_default(library):
    library.rename("night", "midnight")
    assert list(library.wallpapers) == ["midnight", "day"]
    assert library.wallpapers["midnight"] == "/img/night.png"
    assert library.aliases == {"n": "midnight", "dark": "midnight"}
    assert library.default == "midnight"


def test_renaming_an_alias_changes_only_the_alias(library):
    library.rename("n", "moon")
    assert library.aliases == {"moon": "night", "dark": "night"}
    assert list(library.wallpapers) == ["night", "day"]


@pytest.mark.parametrize(
    "old, new, message",
    [
        ("night", "day", "already a saved wallpaper name"),
        ("day", "n", "already an alias of 'night'"),
        ("nope", "x", "Unknown wallpaper"),
    ],
)
def test_rename_refuses_names_that_are_taken_or_unknown(library, old, new, message):
    with pytest.raises(UserError, match=message):
        library.rename(old, new)
    assert list(library.wallpapers) == ["night", "day"]  # nothing changed


# --- removing --------------------------------------------------------------------


def test_removing_a_wallpaper_takes_its_aliases_and_the_default(library):
    assert library.remove_wallpaper("night") == ("/img/night.png", ["n", "dark"])
    assert list(library.wallpapers) == ["day"]
    assert library.aliases == {}
    assert library.default is None


def test_removing_another_wallpaper_keeps_the_default(library):
    library.remove_wallpaper("day")
    assert library.default == "night"


def test_removing_an_alias_keeps_the_wallpaper(library):
    assert library.remove_alias("n") == "night"
    assert library.aliases == {"dark": "night"}
    assert "night" in library.wallpapers


# --- the default -------------------------------------------------------------------


def test_choose_default_stores_the_real_name(library):
    assert library.choose_default("dark") == "night"
    assert library.default == "night"
    assert library.choose_default("day") == "day"


def test_choose_default_must_be_a_saved_name(library):
    with pytest.raises(UserError, match="Unknown wallpaper"):
        library.choose_default("nope")
    assert library.default == "night"


def test_resolved_path_expands_the_home_folder():
    from py_bg_changer.library import resolved_path

    assert resolved_path("~") == Path.home().resolve()
