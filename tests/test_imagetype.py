import pytest

from helpers import PNG_SIGNATURE, png, stored
from py_bg_changer import cache, cli, config, imagetype
from py_bg_changer.errors import UserError

# The start of a real file of each format (just enough for the signature).
SAMPLES = {
    "png": PNG_SIGNATURE + bytes(24),
    "jpeg": b"\xff\xd8\xff\xe0" + bytes(28),
    "gif": b"GIF89a" + bytes(26),
    "bmp": b"BM" + bytes(12) + (40).to_bytes(4, "little") + bytes(14),
    "webp": b"RIFF" + bytes(4) + b"WEBP" + b"VP8 " + bytes(16),
    "tiff": b"II*\x00" + bytes(28),  # little-endian
    "tiff-big-endian": b"MM\x00*" + bytes(28),
    "heif": bytes(4) + b"ftypheic" + bytes(20),
}

NOT_IMAGES = {
    "empty": b"",
    "text": b"just some text\n",
    "svg": b'<svg xmlns="http://www.w3.org/2000/svg"/>',
    "pdf": b"%PDF-1.7\n",
    "zip": b"PK\x03\x04" + bytes(28),
    "bm-text": b"BM is two letters that a text file can start with",
    "bmp-with-a-wrong-header": b"BM" + bytes(12) + (7).to_bytes(4, "little"),
    "wav": b"RIFF" + bytes(4) + b"WAVEfmt " + bytes(16),
    "mp4": bytes(4) + b"ftypmp42" + bytes(20),
}


# --- telling the formats apart ----------------------------------------------------------


@pytest.mark.parametrize("name, data", SAMPLES.items())
def test_every_format_is_recognised(name, data):
    assert imagetype.detect(data) == name.split("-")[0]


@pytest.mark.parametrize("data", NOT_IMAGES.values(), ids=NOT_IMAGES.keys())
def test_other_content_is_not_an_image(data):
    assert imagetype.detect(data) is None


def test_every_format_has_a_sample():
    assert set(imagetype.FORMATS) == {name.split("-")[0] for name in SAMPLES}


# --- checking a file ----------------------------------------------------------------------


@pytest.mark.parametrize("extension", imagetype.EXTENSIONS)
def test_every_supported_extension_is_accepted(tmp_path, extension):
    f = tmp_path / f"a{extension}"
    f.write_bytes(png())
    imagetype.check(f)


def test_the_extension_may_be_in_capitals(tmp_path):
    f = tmp_path / "A.PNG"
    f.write_bytes(png())
    imagetype.check(f)


def test_the_extension_is_not_compared_with_the_content(tmp_path):
    f = tmp_path / "really-a-png.jpg"
    f.write_bytes(png())
    imagetype.check(f)


def test_a_file_of_another_type_is_refused_even_with_image_content(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_bytes(png())
    with pytest.raises(UserError, match=r"not a supported image type \(\.txt\)") as e:
        imagetype.check(f)
    assert "Supported: png, jpg, jpeg" in str(e.value)


def test_a_file_without_an_extension_is_refused(tmp_path):
    f = tmp_path / "picture"
    f.write_bytes(png())
    with pytest.raises(UserError, match=r"\(no extension\)"):
        imagetype.check(f)


def test_a_text_file_renamed_to_png_is_refused(tmp_path):
    f = tmp_path / "notes.png"
    f.write_text("this is not an image", encoding="utf-8")
    with pytest.raises(UserError, match="not a real image") as e:
        imagetype.check(f)
    assert "renamed" in str(e.value)


def test_an_empty_image_file_is_refused(tmp_path):
    f = tmp_path / "empty.png"
    f.write_bytes(b"")
    with pytest.raises(UserError, match="not a real image"):
        imagetype.check(f)


def test_a_file_that_cannot_be_read_is_reported(tmp_path):
    with pytest.raises(UserError, match="Could not read"):
        imagetype.check(tmp_path / "missing.png")


# --- pbc add -----------------------------------------------------------------------------------


def nothing_was_saved():
    return not config.config_path().exists() and not cache.cache_dir().exists()


def test_add_refuses_a_text_file(tmp_path, capsys):
    f = tmp_path / "notes.txt"
    f.write_text("hello", encoding="utf-8")
    assert cli.main(["add", "notes", str(f)]) == 1
    assert "not a supported image type" in capsys.readouterr().err
    assert nothing_was_saved()


def test_add_refuses_a_renamed_text_file(tmp_path, capsys):
    f = tmp_path / "notes.png"
    f.write_text("hello", encoding="utf-8")
    assert cli.main(["add", "notes", str(f), "-a", "n", "--default"]) == 1
    assert "not a real image" in capsys.readouterr().err
    assert nothing_was_saved()


def test_a_refused_file_does_not_replace_a_saved_image(tmp_path, image, capsys):
    cli.main(["add", "night", str(image)])
    copy = stored("night")
    bad = tmp_path / "bad.png"
    bad.write_text("hello", encoding="utf-8")
    assert cli.main(["add", "night", str(bad)]) == 1
    assert stored("night") == copy
    assert copy.exists()
    assert len(list(cache.cache_dir().iterdir())) == 1


def test_add_accepts_an_image_with_capital_letters(tmp_path, capsys):
    f = tmp_path / "Photo.JPG"
    f.write_bytes(SAMPLES["jpeg"])
    assert cli.main(["add", "photo", str(f)]) == 0
    assert stored("photo").suffix == ".jpg"
    assert stored("photo").read_bytes() == SAMPLES["jpeg"]


def test_a_missing_file_is_still_reported_as_missing(tmp_path, capsys):
    assert cli.main(["add", "a", str(tmp_path / "gone.png")]) == 1
    assert "File not found" in capsys.readouterr().err


def test_the_help_of_add_lists_the_image_types(capsys):
    with pytest.raises(SystemExit):
        cli.main(["add", "--help"])
    out = " ".join(capsys.readouterr().out.split())  # the help wraps long lines
    assert imagetype.supported() in out
