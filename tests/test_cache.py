from helpers import stored
from py_bg_changer import cache, cli


def test_add_keeps_a_private_copy(image):
    cli.main(["add", "night", str(image)])
    copy = stored("night")
    assert copy != image.resolve()
    assert copy.parent == cache.cache_dir()
    assert copy.read_bytes() == image.read_bytes()


def test_still_works_after_the_original_is_deleted(image, applied):
    cli.main(["add", "night", str(image)])
    image.unlink()
    assert cli.main(["night"]) == 0
    assert applied == [stored("night")]


def test_remove_deletes_the_copy(image):
    cli.main(["add", "a", str(image)])
    copy = stored("a")
    assert cli.main(["remove", "a"]) == 0
    assert not copy.exists()


def test_shared_copy_lives_until_the_last_name_is_removed(image):
    cli.main(["add", "a", str(image)])
    cli.main(["add", "b", str(image)])
    copy = stored("a")
    assert copy == stored("b")
    cli.main(["remove", "a"])
    assert copy.exists()
    cli.main(["remove", "b"])
    assert not copy.exists()


def test_replacing_an_image_drops_the_old_copy(image):
    cli.main(["add", "a", str(image)])
    old = stored("a")
    image.write_bytes(b"different")
    cli.main(["add", "a", str(image)])
    assert stored("a") != old
    assert stored("a").exists()
    assert not old.exists()


def test_original_is_never_touched_by_remove(image):
    cli.main(["add", "a", str(image)])
    cli.main(["remove", "a"])
    assert image.exists()
