"""The errors that py-bg-changer shows to the user instead of a traceback.

Code deep inside the program only raises them. Whoever runs a command (the terminal
entry point `cli.main`, the window-less one `gui.main`) decides how to show them, and
which exit code to return.
"""


class PbcError(Exception):
    """A problem the user can understand. Its message is shown as it is."""

    exit_code = 1


class UserError(PbcError):
    """The input does not make sense: an unknown name, a name that is taken, ..."""


class UsageError(UserError):
    """The command line itself is wrong (missing arguments, unknown options)."""

    exit_code = 2


class ConfigError(PbcError):
    """The config file exists but cannot be used."""


class WallpaperError(PbcError):
    """The wallpaper could not be applied."""
