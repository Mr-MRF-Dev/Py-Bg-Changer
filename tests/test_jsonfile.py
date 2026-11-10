import json
import os
import stat
import sys

import pytest

from py_bg_changer import jsonfile
from py_bg_changer.errors import ConfigError


def test_write_then_read(tmp_path):
    path = tmp_path / "a" / "b.json"
    jsonfile.write(path, {"name": "ñ", "n": [1]})  # the folder is created
    assert jsonfile.read(path) == {"name": "ñ", "n": [1]}
    assert path.read_text(encoding="utf-8").endswith("}\n")
    assert "ñ" in path.read_text(encoding="utf-8")  # not escaped


@pytest.mark.parametrize(
    "content, message",
    [
        (b"{oops", "Could not read"),
        (b"\xff\xfe\x00bad", "Could not read"),  # not even text
        (b"[1, 2]", "unexpected format"),
        (b'"text"', "unexpected format"),
    ],
)
def test_a_file_that_cannot_be_used_is_reported(tmp_path, content, message):
    path = tmp_path / "bad.json"
    path.write_bytes(content)
    with pytest.raises(ConfigError, match=message):
        jsonfile.read(path)


def test_a_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="Could not read"):
        jsonfile.read(tmp_path / "missing.json")


def test_a_failed_write_leaves_the_old_file_and_no_temporary_one(tmp_path, monkeypatch):
    path = tmp_path / "a.json"
    jsonfile.write(path, {"v": 1})

    def fail(fd):
        raise OSError("disk full")

    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError, match="disk full"):
        jsonfile.write(path, {"v": 2})
    assert jsonfile.read(path) == {"v": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


def test_data_that_cannot_be_written_leaves_the_old_file(tmp_path):
    path = tmp_path / "a.json"
    jsonfile.write(path, {"v": 1})
    with pytest.raises(TypeError):
        jsonfile.write(path, {"v": object()})
    assert jsonfile.read(path) == {"v": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


def test_a_link_is_followed_not_replaced(tmp_path):
    real = tmp_path / "real.json"
    jsonfile.write(real, {"v": 1})
    link = tmp_path / "link.json"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("links are not available here")
    jsonfile.write(link, {"v": 2})
    assert link.is_symlink()
    assert jsonfile.read(real) == {"v": 2}


@pytest.mark.skipif(sys.platform == "win32", reason="no file modes on Windows")
def test_the_mode_of_an_existing_file_is_kept(tmp_path):
    path = tmp_path / "a.json"
    path.write_text("{}", encoding="utf-8")
    path.chmod(0o644)
    jsonfile.write(path, {"v": 1})
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_two_writers_never_share_a_temporary_file(tmp_path, monkeypatch):
    names = []
    real = jsonfile.tempfile.mkstemp

    def recording(*args, **kwargs):
        fd, name = real(*args, **kwargs)
        names.append(name)
        return fd, name

    monkeypatch.setattr(jsonfile.tempfile, "mkstemp", recording)
    for _ in range(3):
        jsonfile.write(tmp_path / "a.json", {})
    assert len(set(names)) == 3
    assert json.loads((tmp_path / "a.json").read_text(encoding="utf-8")) == {}
