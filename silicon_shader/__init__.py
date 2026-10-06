"""Silicon Shader: local, bounded shader optimization."""

from importlib.metadata import PackageNotFoundError, version

try:
    # One source of truth: the version in pyproject.toml.
    __version__ = version("silicon-shader")
except PackageNotFoundError:
    __version__ = "0+unknown"
