from py_bg_changer import cli, config


def test_list_marks_missing_files(tmp_path, capsys):
    config.save({"gone": str(tmp_path / "gone.png")})
    assert cli.main(["list"]) == 0
    assert "(missing)" in capsys.readouterr().out


def test_list_marks_the_default(image, capsys):
    cli.main(["add", "night", str(image), "-d"])
    capsys.readouterr()
    cli.main(["list"])
    assert capsys.readouterr().out.startswith("*")


def test_list_shows_aliases(image, capsys):
    cli.main(["add", "night", str(image), "-a", "n", "-a", "dark"])
    capsys.readouterr()
    cli.main(["list"])
    assert "night (n, dark)" in capsys.readouterr().out


def test_rename_keeps_the_order_of_the_list(tmp_path):
    for name in ("a", "b", "c"):
        f = tmp_path / f"{name}.png"
        f.write_bytes(name.encode())
        cli.main(["add", name, str(f)])
    cli.main(["rename", "b", "x"])
    assert list(config.load()) == ["a", "x", "c"]


def test_ls_is_short_for_list(image, capsys):
    cli.main(["add", "night", str(image)])
    capsys.readouterr()
    assert cli.main(["ls"]) == 0
    assert "night" in capsys.readouterr().out
