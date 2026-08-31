"""
Open English Translation (OET) MCP Server package.
"""

from .server import server
from .database import OETDatabase

__version__ = "0.1.0"
__all__ = ["server", "OETDatabase"]
