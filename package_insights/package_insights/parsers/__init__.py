"""
Package format and client parsers for extracting package information from CI/CD logs.

This module provides a plugin-style architecture for parsing different package
manager logs to extract package information when 403 errors occur.
"""

from package_insights.parsers.base import BaseFormatClientParser
from package_insights.parsers.python_pip import PythonPipParser
from package_insights.parsers.npm import NpmParser
from package_insights.parsers.docker import DockerParser

# Registry of all available parsers
PARSERS = [
    PythonPipParser(),
    NpmParser(),
    DockerParser(),
]

__all__ = [
    "BaseFormatClientParser",
    "PythonPipParser", 
    "NpmParser",
    "DockerParser",
]