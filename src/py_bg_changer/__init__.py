from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("py-bg-changer")
except PackageNotFoundError:
    __version__ = "unknown"
