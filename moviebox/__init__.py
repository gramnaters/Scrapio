from importlib import metadata

try:
    __version__ = metadata.version("provider-api")
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "Stremio Addon Developer"
__repo__ = ""
