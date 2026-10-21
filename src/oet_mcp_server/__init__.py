"""
Open English Translation (OET) MCP Server package.
"""

from .database import OETDatabase

__version__ = "0.2.0"
__all__ = ["server", "OETDatabase"]


def __getattr__(name):
    # Corpus builders and identifier utilities must import without opening a database.
    if name == "server":
        from .server import server
        return server
    raise AttributeError(name)
