import pytest

from py_bg_changer import cli, errors
from py_bg_changer.commands import apply


def test_every_error_is_a_pbc_error():
    for error in (
        errors.UserError,
        errors.UsageError,
        errors.ConfigError,
        errors.WallpaperError,
    ):
        assert issubclass(error, errors.PbcError)


def test_an_unknown_name_raises_a_user_error(applied):
    with pytest.raises(errors.UserError, match="Unknown wallpaper") as caught:
        cli.run(["nope"])
    assert caught.value.exit_code == 1
    assert applied == []


def test_bad_arguments_raise_a_usage_error_with_exit_code_2():
    with pytest.raises(errors.UsageError) as caught:
        cli.run(["add"])
    assert caught.value.exit_code == 2
    assert str(caught.value).startswith("usage:")
    assert "error:" in str(caught.value)


def test_a_corrupt_config_raises_a_config_error(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    monkeypatch.setenv("PBC_CONFIG", str(bad))
    with pytest.raises(errors.ConfigError, match="Could not read"):
        cli.run(["list"])


def test_a_wallpaper_error_is_raised_as_it_is(image, monkeypatch):
    def refuse(path):
        raise errors.WallpaperError("the desktop said no")

    monkeypatch.setattr(apply, "set_wallpaper", refuse)
    cli.main(["add", "night", str(image)])
    with pytest.raises(errors.WallpaperError, match="the desktop said no"):
        cli.run(["night"])


def test_main_shows_the_message_and_returns_the_exit_code(capsys):
    assert cli.main(["nope"]) == 1
    assert "Unknown wallpaper" in capsys.readouterr().err
    assert cli.main(["add"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage:")
    assert "error:" in err


def test_a_successful_command_returns_zero(image, applied):
    cli.main(["add", "night", str(image)])
    assert cli.run(["night"]) == 0


def test_help_and_version_still_exit_normally(capsys):
    for flag in ("--help", "--version"):
        with pytest.raises(SystemExit) as caught:
            cli.main([flag])
        assert caught.value.code == 0
