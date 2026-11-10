import json
import os
import shutil
import threading
import time

import pytest

from helpers import add_images, stored
from py_bg_changer import cli, config, gui, jsonfile, migrations
from py_bg_changer.errors import ConfigError

# The config of py-bg-changer 1.x: it holds the image that was set last and the ones
# before it, and it does not say which version it is.
V1 = {
    "wallpapers": {"night": "/img/night.png", "day": "/img/day.png"},
    "aliases": {"n": "night"},
    "default": "night",
    "current": "/img/day.png",
    "history": ["/img/a.png", "/img/night.png"],
    "future": 1,
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def files_in_config_dir():
    return sorted(p.name for p in config.config_path().parent.iterdir())


@pytest.fixture
def v1():
    """Write a config of version 1. Returns its text, to compare with later."""
    config.config_path().write_text(json.dumps(V1, indent=2), encoding="utf-8")
    return config.config_path().read_text(encoding="utf-8")


class FailingWrite:
    """Make the n-th write of a file fail, like a full disk or a crash would."""

    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch
        self.real = jsonfile.write

    def __call__(self, number):
        calls = []

        def write(path, data):
            calls.append(path)
            if len(calls) == number:
                raise OSError("disk full")
            self.real(path, data)

        self.monkeypatch.setattr(jsonfile, "write", write)
        return calls

    def disarm(self):
        """Writes work again (the other patches of the test stay)."""
        self.monkeypatch.setattr(jsonfile, "write", self.real)


@pytest.fixture
def failing_write(monkeypatch):
    return FailingWrite(monkeypatch)


# --- what a migration does -----------------------------------------------------------


def test_nothing_saved_yet_means_nothing_to_migrate():
    assert migrations.migrate() is None
    assert not config.config_path().exists()
    assert not config.state_path().exists()


def test_a_config_of_version_1_is_migrated(v1):
    result = migrations.migrate()
    assert (result.from_version, result.to_version) == (1, 2)

    expected = {k: v for k, v in V1.items() if k not in ("current", "history")}
    assert read(config.config_path()) == {**expected, "version": 2}
    assert read(config.state_path()) == {
        "version": 2,
        "current": "/img/day.png",
        "history": ["/img/a.png", "/img/night.png"],
    }


def test_the_original_is_kept_as_a_backup(v1):
    result = migrations.migrate()
    assert result.backup.name == "config.json.v1.bak"
    assert result.backup.read_text(encoding="utf-8") == v1


def test_no_lock_or_temporary_file_is_left_behind(v1):
    migrations.migrate()
    names = files_in_config_dir()
    assert names == ["config.json", "config.json.v1.bak", "state.json"]


def test_the_notice_says_where_things_are(v1):
    result = migrations.migrate()
    assert str(config.state_path()) in result.notice
    assert str(result.backup) in result.notice
    assert "1 -> 2" in result.notice


def test_migrating_again_does_nothing(v1):
    migrations.migrate()
    before = {
        n: (config.config_path().parent / n).read_bytes() for n in files_in_config_dir()
    }
    assert migrations.migrate() is None
    after = {
        n: (config.config_path().parent / n).read_bytes() for n in files_in_config_dir()
    }
    assert after == before


def test_a_state_that_changed_after_the_migration_is_never_overwritten(v1):
    from py_bg_changer.state import State

    migrations.migrate()
    config.save_state(State(current="/img/newer.png", history=["/img/day.png"]))
    assert migrations.migrate() is None
    assert config.load_state().current == "/img/newer.png"


def test_an_old_history_that_ended_with_the_current_image_is_cleaned_up():
    # an earlier format kept the image that is set now at the end of the history
    data = {"current": "/img/b.png", "history": ["/img/a.png", "/img/b.png"]}
    config.config_path().write_text(json.dumps(data), encoding="utf-8")
    migrations.migrate()
    assert read(config.state_path())["history"] == ["/img/a.png"]
    assert read(config.state_path())["current"] == "/img/b.png"


def test_a_config_that_only_knows_the_current_image():
    config.config_path().write_text(
        json.dumps({"current": "/img/a.png"}), encoding="utf-8"
    )
    migrations.migrate()
    assert read(config.state_path()) == {
        "version": 2,
        "current": "/img/a.png",
        "history": [],
    }


def test_only_the_five_newest_previous_images_are_kept():
    history = [f"/img/{n}.png" for n in range(8)]
    config.config_path().write_text(
        json.dumps({"current": "/img/now.png", "history": history}), encoding="utf-8"
    )
    migrations.migrate()
    assert read(config.state_path())["history"] == history[-5:]


def test_values_of_the_wrong_type_are_dropped():
    data = {"current": 7, "history": ["/img/a.png", None, 3, "/img/b.png"]}
    config.config_path().write_text(json.dumps(data), encoding="utf-8")
    migrations.migrate()
    state = read(config.state_path())
    assert "current" not in state
    assert state["history"] == ["/img/a.png", "/img/b.png"]


def test_a_history_that_is_not_a_list_becomes_empty():
    config.config_path().write_text(
        json.dumps({"current": "/img/a.png", "history": "oops"}), encoding="utf-8"
    )
    migrations.migrate()
    assert read(config.state_path())["history"] == []


# --- files that need nothing are not written -----------------------------------------


def test_a_config_from_bg_py_needs_nothing(monkeypatch):
    text = json.dumps({"wallpapers": {"default": "C:/x.jpg"}})
    config.config_path().write_text(text, encoding="utf-8")
    monkeypatch.setattr(
        jsonfile,
        "write",
        lambda *a: pytest.fail("a file that needs nothing was written"),
    )
    assert migrations.migrate() is None
    assert config.config_path().read_text(encoding="utf-8") == text
    assert files_in_config_dir() == ["config.json"]  # no backup, no state, no lock


def test_a_config_that_is_already_version_2_is_left_alone(monkeypatch):
    text = json.dumps({"version": 2, "wallpapers": {}})
    config.config_path().write_text(text, encoding="utf-8")
    monkeypatch.setattr(
        jsonfile,
        "write",
        lambda *a: pytest.fail("a file that needs nothing was written"),
    )
    assert migrations.migrate() is None


def test_state_keys_left_in_a_version_2_config_are_ignored_not_migrated():
    # what an older py-bg-changer does if it is used again after the migration
    data = {"version": 2, "wallpapers": {}, "current": "/img/old.png", "history": []}
    config.config_path().write_text(json.dumps(data), encoding="utf-8")
    assert migrations.migrate() is None
    assert read(config.config_path()) == data
    assert config.load_state().current is None


# --- it stops safely and finishes the next time --------------------------------------


def test_a_crash_while_writing_the_state_changes_nothing(v1, failing_write):
    failing_write(1)
    with pytest.raises(ConfigError, match="Could not move your saved files"):
        migrations.migrate()
    assert config.config_path().read_text(encoding="utf-8") == v1
    assert not config.state_path().exists()
    assert "config.json.lock" not in files_in_config_dir()


def test_the_next_run_finishes_after_a_crash_in_the_state(
    v1, failing_write, monkeypatch
):
    failing_write(1)
    with pytest.raises(ConfigError):
        migrations.migrate()
    failing_write.disarm()
    assert migrations.migrate() is not None
    assert read(config.state_path())["current"] == "/img/day.png"
    assert "current" not in read(config.config_path())


def test_a_crash_between_the_two_writes_leaves_everything_readable(v1, failing_write):
    failing_write(2)  # the state is written, then the config fails
    with pytest.raises(ConfigError):
        migrations.migrate()
    assert config.config_path().read_text(encoding="utf-8") == v1  # still version 1
    assert (
        read(config.state_path())["current"] == "/img/day.png"
    )  # and the state is there
    assert "config.json.lock" not in files_in_config_dir()


def test_the_next_run_finishes_after_a_crash_between_the_writes(v1, failing_write):
    failing_write(2)
    with pytest.raises(ConfigError):
        migrations.migrate()
    state_before = config.state_path().read_bytes()
    failing_write.disarm()

    result = migrations.migrate()
    assert result is not None
    assert config.state_path().read_bytes() == state_before  # not written again
    assert "current" not in read(config.config_path())
    assert read(config.config_path())["version"] == 2


def test_the_first_backup_is_the_one_that_stays(v1, failing_write):
    failing_write(2)
    with pytest.raises(ConfigError):
        migrations.migrate()
    failing_write.disarm()
    # the config changes before the second attempt (it could have been edited)
    data = read(config.config_path())
    data["wallpapers"]["extra"] = "/img/extra.png"
    config.config_path().write_text(json.dumps(data), encoding="utf-8")

    result = migrations.migrate()
    assert result.backup.read_text(encoding="utf-8") == v1


def test_a_crash_while_making_the_backup_changes_nothing(v1, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("no space left")

    monkeypatch.setattr(shutil, "copy2", refuse)
    with pytest.raises(ConfigError, match="no space left"):
        migrations.migrate()
    assert files_in_config_dir() == ["config.json"]
    assert config.config_path().read_text(encoding="utf-8") == v1


def test_a_state_that_is_already_there_is_newer_and_stays(v1):
    newer = {"version": 2, "current": "/img/newer.png", "history": []}
    config.state_path().write_text(json.dumps(newer), encoding="utf-8")
    migrations.migrate()
    assert read(config.state_path()) == newer
    assert "current" not in read(config.config_path())


def test_an_unreadable_state_stops_the_migration_before_anything_is_lost(v1):
    config.state_path().write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError, match="Could not read"):
        migrations.migrate()
    assert config.config_path().read_text(encoding="utf-8") == v1


# --- files it must not touch ---------------------------------------------------------


def test_a_broken_config_is_reported_and_not_touched():
    config.config_path().write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError, match="Could not read"):
        migrations.migrate()
    assert files_in_config_dir() == ["config.json"]


def test_a_config_that_is_not_an_object_is_reported():
    config.config_path().write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ConfigError, match="unexpected format"):
        migrations.migrate()


def test_a_config_from_a_newer_program_is_refused_and_not_touched():
    text = json.dumps({"version": 3, "wallpapers": {}, "current": "/img/a.png"})
    config.config_path().write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="newer py-bg-changer"):
        migrations.migrate()
    assert config.config_path().read_text(encoding="utf-8") == text
    assert files_in_config_dir() == ["config.json"]


def test_a_state_from_a_newer_program_is_refused(v1):
    config.state_path().write_text(json.dumps({"version": 3}), encoding="utf-8")
    with pytest.raises(ConfigError, match="newer py-bg-changer"):
        migrations.migrate()
    assert config.config_path().read_text(encoding="utf-8") == v1
    with pytest.raises(ConfigError, match="newer py-bg-changer"):
        config.load_state()


@pytest.mark.parametrize("version", ["2", 0, -1, 1.5, True, []])
def test_a_version_that_is_not_a_whole_number_is_reported(version):
    config.config_path().write_text(
        json.dumps({"version": version, "wallpapers": {}}), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="'version' must be a whole number"):
        migrations.migrate()


# --- two programs at the same time ------------------------------------------------------


def test_a_lock_that_stays_makes_it_give_up_without_touching_anything(v1, monkeypatch):
    monkeypatch.setattr(migrations, "LOCK_TIMEOUT", 0.2)
    lock = config.config_path().with_name("config.json.lock")
    lock.write_text("123")
    with pytest.raises(ConfigError, match="Another py-bg-changer"):
        migrations.migrate()
    assert lock.exists()  # it is not ours to delete
    assert config.config_path().read_text(encoding="utf-8") == v1


def test_a_lock_left_by_a_crash_is_taken_over(v1, monkeypatch):
    monkeypatch.setattr(migrations, "LOCK_STALE", 1)
    lock = config.config_path().with_name("config.json.lock")
    lock.write_text("123")
    old = time.time() - 60
    os.utime(lock, (old, old))
    assert migrations.migrate() is not None
    assert not lock.exists()


def test_it_waits_for_a_lock_that_is_released(v1):
    lock = config.config_path().with_name("config.json.lock")
    lock.write_text("123")
    threading.Timer(0.15, lock.unlink).start()
    assert migrations.migrate() is not None


def test_the_lock_is_released_when_the_migration_fails(v1, failing_write):
    failing_write(1)
    with pytest.raises(ConfigError):
        migrations.migrate()
    assert not config.config_path().with_name("config.json.lock").exists()


def test_programs_starting_together_migrate_once(v1):
    results = []
    barrier = threading.Barrier(8)

    def start():
        barrier.wait()
        results.append(migrations.migrate())

    threads = [threading.Thread(target=start) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 8
    assert len([r for r in results if r is not None]) == 1
    assert read(config.state_path())["current"] == "/img/day.png"
    assert "current" not in read(config.config_path())
    assert files_in_config_dir() == ["config.json", "config.json.v1.bak", "state.json"]


# --- the command comes after the migration ---------------------------------------------------


@pytest.fixture
def old_install(tmp_path, applied):
    """What 1.x left behind: saved wallpapers with real images, and a history."""
    add_images(tmp_path, "a", "b", "c")
    data = read(config.config_path())
    data.pop("version")  # a file of version 1 does not say which version it is
    data["current"] = str(stored("c").resolve())
    data["history"] = [str(stored("a").resolve()), str(stored("b").resolve())]
    config.config_path().write_text(json.dumps(data), encoding="utf-8")
    applied.clear()
    return data


def test_the_migration_happens_before_the_command(old_install, applied, capsys):
    assert cli.main(["a"]) == 0
    assert applied == [stored("a")]  # the command ran
    out, err = capsys.readouterr()
    assert "Wallpaper set to 'a'" in out
    assert "moved to a new layout" in err  # and the user was told, in the terminal

    assert "current" not in read(config.config_path())
    state = read(config.state_path())
    assert state["current"] == str(stored("a").resolve())
    assert state["history"][-1] == str(
        stored("c").resolve()
    )  # the old current went on it


def test_the_user_is_told_only_once(old_install, applied, capsys):
    cli.main(["a"])
    capsys.readouterr()
    cli.main(["b"])
    assert "moved to a new layout" not in capsys.readouterr().err


def test_back_still_works_with_the_history_of_version_1(old_install, applied):
    assert cli.main(["back"]) == 0
    assert applied == [stored("b")]
    assert cli.main(["back"]) == 0
    assert applied[-1] == stored("a")
    assert cli.main(["back"]) == 1


def test_the_window_less_program_migrates_silently(old_install, applied, capsys):
    assert gui.main(["a"]) == 0
    assert capsys.readouterr().err == ""
    assert applied == [stored("a")]
    assert read(config.state_path())["current"] == str(stored("a").resolve())


def test_a_failed_migration_stops_the_command(
    old_install, applied, failing_write, capsys
):
    failing_write(1)
    assert cli.main(["a"]) == 1
    err = capsys.readouterr().err
    assert "Could not move your saved files" in err
    assert applied == []


@pytest.mark.parametrize("argv", [["--help"], ["--version"], ["add"], ["path"]])
def test_commands_that_do_not_need_the_files_leave_them_alone(
    old_install, argv, capsys
):
    before = config.config_path().read_text(encoding="utf-8")
    try:
        cli.main(argv)
    except SystemExit:
        pass
    assert config.config_path().read_text(encoding="utf-8") == before
    assert not config.state_path().exists()


def test_doctor_migrates_and_says_so(old_install, capsys):
    cli.main(["doctor"])
    out = capsys.readouterr().out
    assert "Moved:" in out
    assert "State:" in out
    assert config.state_path().exists()


def test_the_config_stays_readable_for_version_1(old_install, applied):
    cli.main(["a"])
    data = read(config.config_path())
    # what py-bg-changer 1.x looks at is all still there
    assert set(data["wallpapers"]) == {"a", "b", "c"}
    assert "aliases" not in data  # none were saved
    assert data["version"] == 2  # an extra key, which 1.x keeps and ignores


def test_a_config_that_is_a_link_stays_a_link(tmp_path, v1):
    real = tmp_path / "dotfiles" / "config.json"
    real.parent.mkdir()
    shutil.move(str(config.config_path()), real)
    try:
        config.config_path().symlink_to(real)
    except OSError:
        pytest.skip("links are not available here")
    migrations.migrate()
    assert config.config_path().is_symlink()
    assert read(real)["version"] == 2
    assert "current" not in read(real)
