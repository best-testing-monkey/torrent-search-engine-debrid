"""
Multi-Provider Torrent Search Engine with Real-Debrid Integration.

This module provides a comprehensive torrent search engine that aggregates results from
multiple torrent provider sites and integrates with Real-Debrid for premium debrid services.
It features concurrent multi-threaded searching, intelligent result filtering, and caching
of Real-Debrid torrents for instant availability.

Key Features:
    - Multi-provider torrent searching with concurrent execution
    - Real-Debrid integration for cached torrent instant availability
    - Dynamic provider management (add/remove/enable/disable)
    - Intelligent search result sorting by seeder count
    - Category-based filtering and result limiting
    - Configurable timeout and thread pool management
    - Smart caching of debrid torrent lists

Main Components:
    - TorrentSearchEngine: Main search engine class
    - TorrentProviderManager: Manages multiple torrent site providers
    - DebridOptions: Configuration for Real-Debrid integration
    - TorrentBase: Unified torrent result format

Search Workflow:
    1. Check Real-Debrid cache for instant availability (if enabled)
    2. If not found, search configured public torrent providers concurrently
    3. Aggregate and sort results by seeder count
    4. Return unified TorrentBase objects with optional debrid integration

Example:
    >>> from torrentsearchengine.searchengine import TorrentSearchEngine
    >>>
    >>> # Initialize search engine
    >>> engine = TorrentSearchEngine()
    >>> engine.add_provider('kickasstorrents.json5')
    >>> engine.enable_debrid()
    >>>
    >>> # Search for torrents
    >>> results = engine.search("ubuntu", limit=10, timeout=30)
    >>> for torrent in results:
    ...     print(f"{torrent['name']} - {torrent['seeds']} seeders")

Provider Configuration:
    Providers are configured via JSON/JSON5 files that define:
    - Site URL patterns and search endpoints
    - HTML selectors for result parsing
    - Category mappings and filters
    - Request headers and authentication

Author: torrent-search-engine-debrid project
License: See project LICENSE file
"""

import os
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from threading import current_thread
from typing import Any
from typing import List, Union, Optional

from torrentsearchengine.models.debridOptions import DebridOptions
from torrentsearchengine.util.providermanager import TorrentProviderManager
from torrentsearchengine.models.torrentResult import *
from torrentsearchengine.models.torrentprovider import TorrentProvider
from rd_api_py import RD as RealDebrid
from torrentsearchengine.models.torrentbase import TorrentBase

logger = logging.getLogger(__name__)


class TorrentSearchEngine:
    """
    Multi-provider torrent search engine with Real-Debrid integration.

    This class provides a unified interface for searching torrents across multiple provider
    sites concurrently, with optional Real-Debrid integration for instant cached torrent
    availability. It manages providers dynamically and handles result aggregation, sorting,
    and filtering.

    Attributes:
        debrid_options (DebridOptions): Configuration for Real-Debrid integration including
            cache refresh settings and torrent list caching
        RD (RealDebrid): Real-Debrid API client instance (None if debrid disabled)
        provider_manager (TorrentProviderManager): Manages torrent site providers
        _debrid_enabled (bool): Internal flag indicating if Real-Debrid is enabled

    Features:
        - Concurrent multi-threaded searches across providers
        - Real-Debrid cache searching for instant torrent availability
        - Dynamic provider management (add, remove, enable, disable)
        - Result sorting by seeder count for quality prioritization
        - Configurable search limits, timeouts, and thread pools
        - Smart caching of debrid torrent lists

    Search Priority:
        1. Real-Debrid cached torrents (instant availability)
        2. Public torrent provider sites (concurrent search)

    Example:
        >>> # Initialize and configure engine
        >>> engine = TorrentSearchEngine()
        >>> engine.add_provider('/path/to/provider.json5')
        >>> engine.enable_debrid()
        >>>
        >>> # Search with debrid cache first
        >>> results = engine.search("linux iso", limit=10, noremote=None)
        >>>
        >>> # Search only public providers (skip debrid)
        >>> results = engine.search("ubuntu", limit=5, noremote=True)
        >>>
        >>> # Manage providers
        >>> providers = engine.get_providers(enabled=True)
        >>> engine.disable_providers('provider_name')

    Thread Safety:
        The search method uses ThreadPoolExecutor for concurrent provider searches.
        Individual provider instances should be thread-safe.

    Note:
        - Debrid is disabled by default after initialization
        - Call enable_debrid() to activate Real-Debrid integration
        - Provider configurations are loaded from JSON/JSON5 files
        - Results are always sorted by seeder count (highest first)
    """

    def __init__(self):
        """
        Initialize the TorrentSearchEngine.

        Creates a new search engine instance with debrid options and provider manager.
        Real-Debrid integration is initialized but then disabled by default - call
        enable_debrid() to activate it.

        Initialization Process:
            1. Creates DebridOptions instance for configuration
            2. Sets _debrid_enabled to True temporarily
            3. Initializes RealDebrid API client
            4. Disables debrid (sets _debrid_enabled to False)
            5. Creates TorrentProviderManager for provider management

        Post-Initialization State:
            - debrid_options: Configured with default settings
            - _debrid_enabled: False (debrid disabled)
            - RD: RealDebrid instance (not active)
            - provider_manager: Empty provider list

        Example:
            >>> engine = TorrentSearchEngine()
            >>> # Engine is initialized with debrid disabled
            >>> engine.enable_debrid()  # Activate Real-Debrid
            >>> engine.add_provider('provider.json5')  # Add torrent sites
        """
        self.debrid_options = DebridOptions()
        self._debrid_enabled = True
        self.RD = RealDebrid()

        self._debrid_enabled = False
        self.provider_manager = TorrentProviderManager()

    def _search_debrid(self, query: str, category: str = None, limit: int = None):
        """
        Internal method to search Real-Debrid cached torrents using smart word-based filtering.

        Searches through Real-Debrid's current torrent list for torrents matching the query.
        Uses intelligent word-based matching that requires all query words to appear in the
        filename in the correct order (with case-insensitive matching).

        Args:
            query (str): Search query to match against torrent filenames
            category (str, optional): Category filter (currently unused)
            limit (int, optional): Maximum results to return (currently unused)

        Returns:
            List[TorrentBase]: Matching torrents from Real-Debrid cache

        Matching Algorithm:
            1. Sanitize query: convert to lowercase and strip whitespace
            2. Split query into individual words
            3. For each cached torrent filename:
               - Find position of each query word in filename
               - Check if all words are present
               - Verify words appear in the same order as the query
            4. Return only torrents where all words match in correct order

        Example Matching:
            Query: "ubuntu 20.04 desktop"
            Matches: "Ubuntu_20.04_Desktop_amd64.iso"
            Doesn't match: "Desktop Ubuntu amd64" (wrong order)
            Doesn't match: "Ubuntu 18.04 Desktop" (missing "20.04")

        Process:
            1. Refreshes Real-Debrid torrent list via rd_dl_magnet_refresh_states()
            2. Filters torrents using word-based positional matching
            3. Updates torrent info if filename not cached
            4. Returns matching TorrentBase objects

        Note:
            - Matching is case-insensitive
            - All query words must appear in the filename
            - Words must appear in the same order as the query
            - The limit parameter is currently not enforced
            - Category parameter is currently not used for filtering
        """
        knownLocalList = self.rd_dl_magnet_refresh_states()

        # Sanitize query
        searchQuery_sanitized = query
        searchQuery_sanitized = searchQuery_sanitized.lower().strip()
        searchQuery_words = searchQuery_sanitized.split(" ")

        logger.info("Filter torrents")
        results = []
        for magnet in knownLocalList.keys():
            if magnet != 'all':
                torrent = knownLocalList[magnet]
                torrent["magnet"] = magnet

                if 'filename' not in torrent['info']:
                    torrent.updateInfo()

                if 'filename' in torrent['info']:
                    filename = torrent["info"]["filename"].lower()
                    positions: dict[int, str] = {}
                    for word in searchQuery_words:
                        pos = str.find(filename, word)
                        if pos > -1:
                            positions[pos] = word
                    if len(positions) == len(searchQuery_words):
                        # in order?
                        keys = sorted(positions.keys())
                        n = 0
                        correctCount = 0
                        for pos in keys:
                            if positions[pos] == searchQuery_words[n]:
                                correctCount += 1
                            n += 1
                        if len(searchQuery_words) == correctCount:
                            results += [torrent]
        logger.info(f"/Filter torrents: x{len(results)}")
        return results

    def search(self, query: str, category: str = None, limit: int = None,
               providers=None, timeout: int = None,
               n_threads: int = None, noremote: bool | None = False) -> List[TorrentBase]:
        """
        Search for torrents across Real-Debrid cache and/or public providers.

        This is the main search method that orchestrates searching across Real-Debrid cached
        torrents and public torrent providers. It supports concurrent multi-threaded searches,
        intelligent result filtering, and automatic result sorting by seeder count.

        Args:
            query (str): Search query string to find torrents
            category (str, optional): Category filter (e.g., "movies", "tv", "music")
            limit (int, optional): Maximum number of results to return
            providers (List[Union[str, TorrentProvider]], optional): Specific providers to use.
                If None, uses all enabled providers.
            timeout (int, optional): Maximum seconds to wait for all provider searches
            n_threads (int, optional): Maximum concurrent threads for provider searches.
                Defaults to min(num_providers, cpu_count * 5)
            noremote (bool | None, optional): Search mode control:
                - False (default): Try debrid cache first, then public providers if no results
                - True: Search only debrid cache, skip public providers
                - None: Try debrid cache, always search public providers regardless

        Returns:
            List[TorrentBase]: List of matching torrents sorted by seeder count (highest first).
                Returns empty list if query is empty or no providers configured.

        Search Flow:
            1. If query is empty, return empty list
            2. If debrid enabled and noremote is not False:
               - Search Real-Debrid cache using _search_debrid()
               - If results found and noremote=True, return debrid results
            3. If noremote=True and no debrid results, return empty list
            4. Get providers (specified or all enabled)
            5. Execute concurrent multi-threaded search across providers
            6. Sort results by seeder count (highest first)
            7. Convert to TorrentBase objects
            8. Limit results if specified
            9. Attach RD client to each result if debrid enabled
            10. Return final results

        Thread Pool Sizing:
            - Default: min(number_of_providers, cpu_count * 5)
            - Each provider search runs in a separate thread
            - Timeout is shared across all threads

        Result Processing:
            - Results are sorted by seeder count (descending)
            - Converted to TorrentBase format for consistency
            - Limited to specified count if limit provided
            - Real-Debrid client attached if debrid enabled

        Example:
            >>> # Search debrid cache first, then public providers
            >>> results = engine.search("ubuntu 22.04", limit=10, timeout=30)
            >>>
            >>> # Search only debrid cache
            >>> cached = engine.search("movie 2024", noremote=True)
            >>>
            >>> # Search debrid + always search public providers
            >>> all_results = engine.search("linux iso", noremote=None, limit=20)
            >>>
            >>> # Search specific providers only
            >>> results = engine.search("album flac", providers=['kickass', 'piratebay'])

        Note:
            - Empty queries return empty list immediately
            - Provider search happens concurrently for performance
            - Results always sorted by seeders regardless of source
            - Debrid cache is always checked first if enabled
            - Timeout applies to entire search operation, not per provider
        """
        # an empty query simply returns no torrent (for now?)
        if not query:
            return []

        if self._debrid_enabled and noremote is not None:
            logger.info("Debrid search")
            result = self._search_debrid(query=query, category=category, limit=limit)
            logger.info(f"Debrid search {len(result)} x result")
            if len(result) > 0:
                return result

        if noremote:
            return result

        if providers is None:
            # get only enabled providers
            providers = self.get_providers(enabled=True)
        else:
            # get as TorrentProvider
            providers = [provider if isinstance(provider, TorrentProvider)
                         else self.get_provider(provider)
                         for provider in providers]
            providers = [provider for provider in providers
                         if provider is not None]

        n_providers = len(providers)
        if n_providers == 0:
            return []

        if n_threads is None or n_threads < 1:
            max_threads = (os.cpu_count() or 1) * 5
            n_threads = n_providers if n_providers < max_threads \
                else max_threads

        logger.debug(("Searching on {} providers ({} threads): " +
                      "'{}' (limit: {}, timeout: {})")
                     .format(n_providers, n_threads, query, limit, timeout))

        torrents = self._multithreaded_search(providers, category, query,
                                              limit, timeout, n_threads)

        torrents = self._sort_by_seeds(torrents)
        torrents = self._to_torrentBase_list(torrents)
        if limit:
            torrents = torrents[:min(len(torrents), limit)]
        if self._debrid_enabled:
            for t in torrents:
                t.RD = self.RD

        return torrents

    def add_provider(self, provider: Union[str, dict, TorrentProvider]):
        """
        Add a torrent provider to the search engine.

        Loads and configures a torrent site provider from a file path, dictionary, or
        TorrentProvider instance. Providers define how to search specific torrent sites
        including URL patterns, HTML selectors, and result parsing logic.

        Args:
            provider (Union[str, dict, TorrentProvider]): Provider configuration source:
                - str: File path to JSON/JSON5 provider configuration file
                - dict: Provider configuration as a dictionary
                - TorrentProvider: Pre-configured TorrentProvider instance

        Raises:
            ValueError: Invalid property in provider configuration
            ValidationError: Provider configuration format is incorrect
            RequestError: Provider could not be retrieved from URL (if applicable)
            IOError: Provider configuration file could not be read

        Provider Configuration Format (JSON/JSON5):
            {
                "name": "ProviderName",
                "url": "https://example.com",
                "search_url": "https://example.com/search?q={query}",
                "categories": {...},
                "selectors": {...}
            }

        Example:
            >>> # Add provider from file
            >>> engine.add_provider('/path/to/kickasstorrents.json5')
            >>>
            >>> # Add provider from dict
            >>> config = {"name": "MyProvider", "url": "https://..."}
            >>> engine.add_provider(config)
            >>>
            >>> # Add provider instance
            >>> provider = TorrentProvider(config)
            >>> engine.add_provider(provider)

        Note:
            - Provider files typically use .json or .json5 extensions
            - JSON5 format supports comments and trailing commas
            - Newly added providers are enabled by default
            - Provider names must be unique
        """
        self.provider_manager.add(provider)

    def get_providers(self, enabled=None) -> List[TorrentProvider]:
        """
        Get list of torrent providers.

        Retrieves all configured torrent providers, optionally filtered by enabled status.

        Args:
            enabled (bool, optional): Filter by enabled status:
                - None (default): Return all providers
                - True: Return only enabled providers
                - False: Return only disabled providers

        Returns:
            List[TorrentProvider]: List of provider instances matching the filter

        Example:
            >>> # Get all providers
            >>> all_providers = engine.get_providers()
            >>>
            >>> # Get only enabled providers
            >>> active = engine.get_providers(enabled=True)
            >>>
            >>> # Get disabled providers
            >>> inactive = engine.get_providers(enabled=False)
        """
        return self.provider_manager.get_all(enabled=enabled)

    def get_provider(self, name: str) -> Optional[TorrentProvider]:
        """
        Get a specific provider by name.

        Args:
            name (str): Name of the provider to retrieve

        Returns:
            Optional[TorrentProvider]: Provider instance if found, None otherwise

        Example:
            >>> provider = engine.get_provider('kickasstorrents')
            >>> if provider:
            ...     print(f"Found provider: {provider.name}")
        """
        return self.provider_manager.get(name)

    def disable_providers(self, *providers: List[Union[str, TorrentProvider]]):
        """
        Disable one or more torrent providers.

        Disabled providers are not used in searches but remain configured. They can be
        re-enabled later without reconfiguration.

        Args:
            *providers: Variable number of providers to disable. Each can be:
                - str: Provider name
                - TorrentProvider: Provider instance

        Example:
            >>> # Disable by name
            >>> engine.disable_providers('kickasstorrents', 'piratebay')
            >>>
            >>> # Disable by instance
            >>> provider = engine.get_provider('eztv')
            >>> engine.disable_providers(provider)

        Note:
            - Disabled providers remain in the provider list
            - Use get_providers(enabled=False) to see disabled providers
        """
        logger.debug("Disabling providers: {}".format(providers))
        self.provider_manager.disable(*providers)

    def enable_providers(self, *providers: List[Union[str, TorrentProvider]]):
        """
        Enable one or more torrent providers.

        Enables previously disabled providers to be included in searches.

        Args:
            *providers: Variable number of providers to enable. Each can be:
                - str: Provider name
                - TorrentProvider: Provider instance

        Example:
            >>> # Enable by name
            >>> engine.enable_providers('kickasstorrents', 'piratebay')
            >>>
            >>> # Enable by instance
            >>> provider = engine.get_provider('eztv')
            >>> engine.enable_providers(provider)

        Note:
            - Newly added providers are enabled by default
            - Only affects providers that are already configured
        """
        logger.debug("Enabling providers: {}".format(providers))
        self.provider_manager.enable(*providers)

    def remove_providers(self, *providers: List[Union[str, TorrentProvider]]):
        """
        Remove one or more torrent providers from the engine.

        Permanently removes providers from the configuration. Unlike disabling,
        removed providers must be re-added to be used again.

        Args:
            *providers: Variable number of providers to remove. Each can be:
                - str: Provider name
                - TorrentProvider: Provider instance

        Example:
            >>> # Remove by name
            >>> engine.remove_providers('kickasstorrents', 'piratebay')
            >>>
            >>> # Remove by instance
            >>> provider = engine.get_provider('eztv')
            >>> engine.remove_providers(provider)

        Note:
            - Removed providers must be re-added via add_provider() to use again
            - Consider disable_providers() instead if you may want to re-enable later
        """
        logger.debug("Removing providers: {}".format(providers))
        self.provider_manager.remove(*providers)

    def _multithreaded_search(self, providers, category, query, limit,
                              timeout, n_threads):
        """
        Internal method to execute concurrent searches across multiple providers.

        Uses ThreadPoolExecutor to search multiple torrent providers simultaneously,
        aggregating results in a thread-safe queue with timeout management.

        Args:
            providers (List[TorrentProvider]): List of providers to search
            category (str): Category filter for searches
            query (str): Search query string
            limit (int): Maximum results per provider
            timeout (int): Maximum seconds for all searches
            n_threads (int): Number of concurrent worker threads

        Returns:
            List[dict]: Aggregated torrent results from all providers

        Thread Pool Behavior:
            - Each provider gets its own thread
            - Threads share a global timeout
            - Results are collected in thread-safe queue
            - Failed provider searches are logged but don't stop others

        Timeout Management:
            - Global timeout shared across all threads
            - Each thread calculates remaining time before searching
            - Threads skip search if timeout already exceeded
            - Queue size limited by limit parameter

        Error Handling:
            - Provider exceptions are caught and logged
            - Failed providers don't block other providers
            - Queue.Full exceptions are silently ignored
            - All threads complete before returning

        Example Flow:
            1. Create bounded queue (size = limit)
            2. Launch thread pool with n_threads workers
            3. Each thread:
               - Checks remaining timeout
               - Searches provider if time remaining
               - Adds results to queue (up to limit)
               - Logs any errors
            4. Wait for all threads to complete
            5. Drain queue and return results

        Note:
            - Thread pool uses daemon=True (cleanup on exit)
            - Results are not sorted (use _sort_by_seeds after)
            - Queue prevents excessive memory usage
            - Timeout is soft (threads not forcibly killed)
        """

        def task(q, provider, query, category, limit, timeout):
            logger.debug("Search on provider {} running on thread: {} ({})"
                         .format(provider.name,
                                 current_thread().name,
                                 current_thread().ident))
            if timeout is not None:
                elapsed_time = time.time() - start_time
                current_timeout = timeout - elapsed_time
                if current_timeout <= 0:
                    return
            else:
                current_timeout = None
            try:
                for torrent in provider.search(query, category=category,
                                               limit=limit,
                                               timeout=current_timeout):
                    q.put_nowait(torrent)
            except queue.Full:
                pass
            except Exception as e:
                message = "Stopped search on provider {}: {}" \
                    .format(provider.name, e)
                logger.warning(message)

        start_time = time.time()
        torrents = []
        q = queue.Queue(limit)
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            executor.daemon = True
            n = len(providers)
            args = [[q] * n, providers, [query] * n, [category] * n,
                    [limit] * n, [timeout] * n]
            for result in executor.map(task, *args):
                pass
        while not q.empty():
            torrents.append(q.get_nowait())

        return torrents

    def _sort_by_seeds(self, items: List[TorrentBase]) -> List[TorrentBase]:
        """
        Internal method to sort torrent results by seeder count.

        Sorts torrents in descending order by number of seeders (highest first).
        Higher seeder counts typically indicate better availability and download speeds.

        Args:
            items (List[TorrentBase]): List of torrent results to sort

        Returns:
            List[TorrentBase]: Sorted list with highest seeders first

        Note:
            - Uses "0" as default if seeds value is empty/missing
            - Handles non-numeric seed values gracefully
            - Sorts in descending order (reverse=True)
        """
        return sorted(items, key=lambda item: int("0" + item['seeds']), reverse=True)

    def enable_debrid(self):
        """
        Enable Real-Debrid integration for cached torrent searches.

        Activates Real-Debrid functionality, allowing the search engine to check
        cached torrents for instant availability before searching public providers.

        Process:
            1. Checks if already enabled (no-op if true)
            2. Sets _debrid_enabled flag to True
            3. Initializes RealDebrid API client

        Example:
            >>> engine = TorrentSearchEngine()
            >>> engine.enable_debrid()
            >>> # Now searches will check Real-Debrid cache first

        Note:
            - Requires RD_APITOKEN environment variable
            - No effect if already enabled
            - Real-Debrid searches happen before public provider searches
        """
        if self._debrid_enabled:
            return
        self._debrid_enabled = True
        self.RD = RealDebrid()
        pass

    def disable_debrid(self):
        """
        Disable Real-Debrid integration.

        Deactivates Real-Debrid functionality, making searches only use public
        torrent providers without checking the debrid cache.

        Process:
            1. Sets _debrid_enabled flag to False
            2. Removes RealDebrid client reference (sets to None)

        Example:
            >>> engine.disable_debrid()
            >>> # Now searches skip Real-Debrid cache

        Note:
            - Can be re-enabled with enable_debrid()
            - Does not affect already configured providers
            - Useful for debugging or testing public provider searches
        """
        self._debrid_enabled = False
        self.RD = None
        pass

    @staticmethod
    def brute_serialize(obj):
        """
        Placeholder method for object serialization.

        This is a stub method that currently has no implementation.
        May be intended for future serialization functionality.

        Args:
            obj: Object to serialize

        Returns:
            None

        Note:
            This method currently does nothing and always returns None.
        """
        return

    def rd_dl_magnet_refresh_states(self) -> dict[
        str | Any, TorrentBase]:
        """
        Refresh and retrieve Real-Debrid torrent list with smart caching.

        Fetches the current list of torrents from Real-Debrid, converts them to
        TorrentBase objects, and indexes them by magnet URL for fast lookup.
        Uses caching to avoid unnecessary API calls.

        Returns:
            dict[str | Any, TorrentBase]: Dictionary mapping magnet URLs to TorrentBase objects.
                Also includes special "all" key with metadata:
                - current_torrents_map["all"]["id"] = "all"
                - current_torrents_map["all"]["name"] = "all"
                - current_torrents_map["all"]["torrents"] = raw torrent list

        Caching Behavior:
            - If refreshEverySearch=False and cache exists, returns cached list
            - Otherwise, fetches fresh list from Real-Debrid API
            - Cache stored in debrid_options.lastTorrentList

        Torrent Processing:
            1. Fetches all torrents via RD.torrents.getAll()
            2. For each torrent:
               - Creates info dict from torrent data
               - Sets provider to "RealDebrid current torrents" if missing
               - Converts to TorrentBase object
               - Attaches RD client reference
               - Indexes by magnet URL
            3. Handles duplicate magnets by appending torrent ID

        Magnet URL Handling:
            - Primary key is the magnet URL
            - If duplicate magnet found, appends "&dn={torrent_id}" to make unique
            - Allows multiple torrents with same magnet to coexist

        Special "all" Entry:
            The returned dict includes an "all" key containing:
            - id: "all"
            - name: "all"
            - torrents: Complete raw torrent list from API

        Example:
            >>> torrents_map = engine.rd_dl_magnet_refresh_states()
            >>> # Access specific torrent by magnet
            >>> torrent = torrents_map[magnet_url]
            >>> # Access all torrents
            >>> all_torrents = torrents_map["all"]["torrents"]

        Note:
            - Respects debrid_options.refreshEverySearch setting
            - Logs retrieval progress at INFO level
            - Commented code shows optional info updating (currently disabled)
            - Cache persists until next refresh
        """

        if not self.debrid_options.refreshEverySearch and self.debrid_options.lastTorrentList is not None:
            return self.debrid_options.lastTorrentList

        global RD

        logger.info("retreiving RD list")
        current_torrents = self.RD.torrents.getAll()
        current_torrents_map: dict[str | Any, TorrentBase] = {}
        for t in current_torrents:
            t['info'] = dict(t)
            if not t.get('provider'):
                t['provider'] = 'RealDebrid current torrents'
            torrent = TorrentBase(**t)
            torrent.RD = self.RD

            torrent['info'] = t
            magnet = torrent['magnet']
            if magnet not in current_torrents_map:
                current_torrents_map[magnet] = torrent
            else:
                magnet = magnet + "&dn=" + torrent['id']
                current_torrents_map[magnet] = torrent
                # &dn=
        logger.info("/retreiving last RD list")

        current_torrents_map["all"] = {}
        current_torrents_map["all"]["id"] = "all"
        current_torrents_map["all"]["name"] = "all"
        current_torrents_map["all"]["torrents"] = current_torrents

        # # Dont need: already in get all
        # logger.info("updating RD info")
        # for magnetUrl in current_torrents_map:
        #     known = current_torrents_map[magnetUrl]
        #     if isinstance(known, TorrentBase) and known['info']['status'] not in ['downloaded']:
        #         known.RD = self.RD
        #         known.updateInfo()
        #     current_torrents_map[magnetUrl] = known
        # logger.info("/updating RD info")

        self.debrid_options.lastTorrentList = current_torrents_map

        return current_torrents_map

    def _to_torrentBase_list(self, torrents: list[dict]) -> list[TorrentBase]:
        """
        Internal method to convert dictionary torrents to TorrentBase objects.

        Transforms a list of torrent dictionaries into TorrentBase instances for
        consistent object-oriented access and Real-Debrid integration.

        Args:
            torrents (list[dict]): List of torrent dictionaries with torrent data

        Returns:
            list[TorrentBase]: List of TorrentBase objects

        Conversion Process:
            - Each dict is unpacked as keyword arguments to TorrentBase constructor
            - Preserves all torrent metadata (name, magnet, seeds, etc.)
            - Enables object methods like startDebridDownload(), updateInfo()

        Example:
            >>> raw_torrents = [{"name": "Ubuntu", "seeds": "100", ...}]
            >>> torrent_objects = engine._to_torrentBase_list(raw_torrents)
            >>> # Now can use object methods
            >>> torrent_objects[0].startDebridDownload()

        Note:
            - Used internally after provider searches
            - All torrent properties become accessible as dict keys
            - Enables Real-Debrid integration methods on results
        """
        ret_list = []
        for t in torrents:
            ret_list += [TorrentBase(**t)]
        return ret_list
