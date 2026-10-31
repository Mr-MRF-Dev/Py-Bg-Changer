import pytest

from py_bg_changer import cli


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Every test gets its own config file (and image folder) in a temp dir."""
    monkeypatch.setenv("PBC_CONFIG", str(tmp_path / "config.json"))


@pytest.fixture
def image(tmp_path):
    f = tmp_path / "pic.png"
    f.write_bytes(b"x")
    return f


@pytest.fixture
def applied(monkeypatch):
    """Record the images that would be set, instead of touching the desktop."""
    calls = []
    monkeypatch.setattr(cli, "set_wallpaper", calls.append)
    return calls
