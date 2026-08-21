from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("responsible-ai-banking-agent")
except PackageNotFoundError:  # pragma: no cover - source-tree fallback
    __version__ = "0.2.0.dev0"
