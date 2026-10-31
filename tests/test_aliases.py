from helpers import stored
from py_bg_changer import cache, cli, config


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


def test_aliases_follow_a_replaced_image(image, applied):
    cli.main(["add", "night", str(image), "-a", "n"])
    image.write_bytes(b"different")
    cli.main(["add", "night", str(image)])
    assert cli.main(["n"]) == 0
    assert applied == [stored("night")]
