import inspect

import pytest

from py_bg_changer import cli
from py_bg_changer.commands import COMMANDS, all_names
from py_bg_changer.commands.registry import arg, command


@pytest.fixture
def scratch_commands():
    """Let a test register commands, and forget them afterwards."""
    before = list(COMMANDS)
    yield
    COMMANDS[:] = before


# --- the list of commands -----------------------------------------------------------


def test_the_commands_are_registered_in_the_order_of_the_help():
    assert [cmd.name for cmd in COMMANDS] == [
        "add",
        "alias",
        "rename",
        "remove",
        "default",
        "set",
        "random",
        "back",
        "current",
        "list",
        "doctor",
        "path",
    ]


def test_every_command_name_and_alias_is_used_once():
    used = [name for cmd in COMMANDS for name in (cmd.name, *cmd.aliases)]
    assert len(used) == len(set(used))
    assert all_names() == set(used)
    assert {"ls", "rm"} <= all_names()


def test_every_command_has_a_help_text():
    for cmd in COMMANDS:
        assert cmd.help.strip(), cmd.name


def test_every_handler_takes_exactly_the_arguments_of_its_command():
    # a handler is called with one keyword argument per argument of its command
    sub_parsers = {}
    for action in cli.build_parser()._actions:
        if isinstance(getattr(action, "choices", None), dict):
            sub_parsers = action.choices
    for cmd in COMMANDS:
        dests = sub_parsers[cmd.name].get_default("_dests")
        parameters = list(inspect.signature(cmd.handler).parameters)
        assert sorted(parameters) == sorted(dests), cmd.name


def test_every_command_shows_up_in_the_help(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    for cmd in COMMANDS:
        assert cmd.name in out
        for text, what in cmd.examples:
            assert text in out
            assert what in out


def test_the_examples_are_lined_up():
    epilog = cli.build_parser().epilog.splitlines()
    shown = [(text, what) for cmd in COMMANDS for text, what in cmd.examples]
    lines = [line for line in epilog if line.startswith("  pbc")]
    assert len(lines) == len(shown)
    columns = {line.rindex(what) for line, (_, what) in zip(lines, shown, strict=True)}
    assert len(columns) == 1


# --- adding a command ------------------------------------------------------------------


def test_a_new_command_needs_nothing_but_its_registration(scratch_commands, capsys):
    @command(
        "hello",
        help="say hello",
        aliases=("hi",),
        args=(arg("who"), arg("-l", "--loud", action="store_true", dest="loud")),
        examples=(("pbc hello you", "greet someone"),),
    )
    def cmd_hello(who, loud):
        print(who.upper() if loud else who)

    assert cli.main(["hello", "you"]) == 0
    assert capsys.readouterr().out == "you\n"
    assert cli.main(["hi", "you", "--loud"]) == 0  # the alias works too
    assert capsys.readouterr().out == "YOU\n"
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert "say hello" in out
    assert "pbc hello you" in out


def test_a_command_can_return_an_exit_code(scratch_commands):
    @command("grumpy", help="always fails")
    def cmd_grumpy():
        return 3

    assert cli.main(["grumpy"]) == 3


def test_a_command_name_cannot_be_used_twice(scratch_commands):
    with pytest.raises(ValueError, match="already in use: add"):
        command("add", help="again")(lambda: None)
    with pytest.raises(ValueError, match="already in use: ls"):
        command("another", help="clash", aliases=("ls",))(lambda: None)
    assert "another" not in all_names()
