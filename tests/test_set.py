from helpers import stored
from py_bg_changer import cli, config


def test_add_then_set_by_name(image, applied):
    assert cli.main(["add", "night", str(image)]) == 0
    assert cli.main(["night"]) == 0
    assert applied == [stored("night")]


def test_setting_an_image_by_path_is_not_supported(image, applied, capsys):
    assert cli.main([str(image)]) == 1
    assert applied == []
    err = capsys.readouterr().err
    assert "not a saved name" in err
    assert "pbc add NAME" in err


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
