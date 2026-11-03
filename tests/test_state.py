from py_bg_changer.state import HISTORY_LIMIT, State


def always(path):
    return True


def test_the_first_image_has_nothing_before_it():
    state = State()
    state.record("a")
    assert state.current == "a"
    assert state.history == []


def test_the_replaced_image_goes_on_the_history():
    state = State()
    for image in "abc":
        state.record(image)
    assert state.current == "c"
    assert state.history == ["a", "b"]


def test_recording_the_current_image_again_changes_nothing():
    state = State()
    state.record("a")
    state.record("a")
    assert state.history == []


def test_only_the_newest_previous_images_are_kept():
    state = State()
    for image in "abcdefgh":
        state.record(image)
    assert HISTORY_LIMIT == 5
    assert state.history == list("cdefg")
    assert state.current == "h"


def test_go_back_takes_the_newest_previous_image():
    state = State()
    for image in "abc":
        state.record(image)
    assert state.go_back(always) == "b"
    assert (state.current, state.history) == ("b", ["a"])
    assert state.go_back(always) == "a"
    assert (state.current, state.history) == ("a", [])
    assert state.go_back(always) is None
    assert state.current == "a"  # nothing changed when there is nowhere to go


def test_go_back_skips_and_forgets_images_that_are_gone():
    state = State()
    for image in "abc":
        state.record(image)
    assert state.go_back(lambda path: path != "b") == "a"
    assert state.history == []


def test_go_back_with_no_image_left_returns_none():
    state = State(current="c", history=["a", "b"])
    assert state.go_back(lambda path: False) is None
    assert state.history == []
