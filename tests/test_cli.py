import pytest

from py_bg_changer import cli, config


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


def test_add_then_set_by_name(image, applied):
    assert cli.main(["add", "night", str(image)]) == 0
    assert cli.main(["night"]) == 0
    assert applied == [image.resolve()]


def test_set_by_direct_path(image, applied):
    assert cli.main([str(image)]) == 0
    assert applied == [image]


def test_no_arguments_uses_default(image, applied):
    cli.main(["add", "default", str(image)])
    assert cli.main([]) == 0
    assert len(applied) == 1


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
