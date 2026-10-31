from helpers import stored
from py_bg_changer import cli, config


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


def test_wallpaper_named_default_still_works(image, applied):
    # configs from the original bg.py have a wallpaper literally named "default"
    config.save({"default": str(image)})
    assert cli.main([]) == 0
    assert applied == [image]
