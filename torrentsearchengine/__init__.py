"""
Torrent Search Engine Package

This package provides functionality for searching torrents across multiple providers.
"""

from .torrentprovider import TorrentProvider
from .exceptions import (
    RequestError, ValidationError, Timeout, ParseError, 
    FormatError, NotSupportedError
)
from .providermanager import TorrentProviderManager as ProviderManager
from .searchengine import TorrentSearchEngine as SearchEngine
from .result import TorrentResult as Result

__all__ = [
    'TorrentProvider',
    'RequestError',
    'ValidationError', 
    'Timeout',
    'ParseError',
    'FormatError',
    'NotSupportedError',
    'ProviderManager',
    'SearchEngine',
    'Result'
]