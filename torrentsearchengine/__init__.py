"""
Torrent Search Engine Package

This package provides functionality for searching torrents across multiple providers.
"""

from torrentsearchengine.models.torrentprovider import TorrentProvider
from torrentsearchengine.util.exceptions import (
    RequestError, ValidationError, Timeout, ParseError, 
    FormatError, NotSupportedError
)
from torrentsearchengine.util.providermanager import TorrentProviderManager as ProviderManager
from .searchengine import TorrentSearchEngine as SearchEngine
from torrentsearchengine.models.result import TorrentResult as Result

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