from helpers import stored
from py_bg_changer import cli, config


def test_rename_a_wallpaper_keeps_its_image_and_aliases(image, applied):
    cli.main(["add", "night", str(image), "-a", "n"])
    copy = stored("night")
    assert cli.main(["rename", "night", "midnight"]) == 0
    assert list(config.load()) == ["midnight"]
    assert stored("midnight") == copy
    assert config.load_aliases() == {"n": "midnight"}
    assert cli.main(["n"]) == 0
    assert applied == [copy]


def test_rename_updates_the_default(image, applied):
    cli.main(["add", "night", str(image), "-d"])
    assert cli.main(["rename", "night", "midnight"]) == 0
    assert config.get_default() == "midnight"
    assert cli.main([]) == 0
    assert len(applied) == 1


def test_rename_an_alias(image, applied):
    cli.main(["add", "night", str(image), "-a", "n"])
    assert cli.main(["rename", "n", "moon"]) == 0
    assert config.load_aliases() == {"moon": "night"}
    assert cli.main(["moon"]) == 0
    assert applied == [stored("night")]


def test_rename_cannot_take_an_existing_wallpaper_name(tmp_path, image, capsys):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "night", str(image)])
    cli.main(["add", "day", str(other)])
    assert cli.main(["rename", "night", "day"]) == 1
    assert "already a saved wallpaper" in capsys.readouterr().err
    assert list(config.load()) == ["night", "day"]


def test_rename_cannot_take_an_existing_alias(tmp_path, image, capsys):
    other = tmp_path / "other.png"
    other.write_bytes(b"y")
    cli.main(["add", "night", str(image)])
    cli.main(["add", "day", str(other), "-a", "d"])
    assert cli.main(["rename", "night", "d"]) == 1
    assert "already an alias of 'day'" in capsys.readouterr().err
    assert "night" in config.load()


def test_rename_unknown_name_fails(capsys):
    assert cli.main(["rename", "nope", "x"]) == 1
    assert "Unknown wallpaper" in capsys.readouterr().err


def test_rename_to_the_same_name_does_nothing(image):
    cli.main(["add", "night", str(image)])
    assert cli.main(["rename", "night", "night"]) == 0
    assert list(config.load()) == ["night"]
