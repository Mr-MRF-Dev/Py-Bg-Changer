from py_bg_changer import cli, config


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
