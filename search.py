"""
Torrent Search Engine with Real-Debrid Integration.

This module provides a high-level interface for searching and downloading various media
types (music, movies, TV shows) from torrent sources with seamless Real-Debrid integration.
It combines multi-provider torrent searching with premium debrid services for instant
torrent-to-direct-link conversion and downloading.

The module uses progressive search strategies to find the best quality content, with
intelligent fallback mechanisms. All downloads are processed through Real-Debrid for
premium speeds and reliability.

Main Components:
    - Search: Main class providing high-level search and download methods
    - TorrentSearchEngine: Multi-provider torrent search functionality
    - Real-Debrid Integration: Premium torrent downloading and streaming
    - Background Task Pool: Asynchronous download processing

Environment Variables:
    RD_APITOKEN: Real-Debrid API token (required)

Example:
    >>> from search import Search
    >>>
    >>> # Search and download a music album
    >>> Search.MusicAlbum("Pink Floyd", "Dark Side of the Moon", save_path="/downloads")
    >>>
    >>> # Download a movie
    >>> Search.Movie("Inception", "2010")
    >>>
    >>> # Wait for all background tasks to complete
    >>> Search.wait_for_background_tasks()

Dependencies:
    - rd_api_py: Real-Debrid API client
    - torrent_search: Multi-provider torrent search engine
    - Valid Real-Debrid premium account

Author: torrent-search-engine-debrid project
License: See project LICENSE file
"""

import logging
import os
import time
from typing import List

from torrent_search.rd_api_py import RD
from torrent_search.torrentsearchengine.searchengine import TorrentSearchEngine
from torrent_search.torrentsearchengine.torrentbase import TorrentBase
from torrent_search.util.background import WorkerGovernor


class Search:
    """
    Unified search interface for torrent-based media downloads with Real-Debrid integration.
    
    This class provides high-level methods for searching and downloading various types of media
    content (music albums, movies, TV shows) from torrent sources. Features intelligent search
    strategies, quality preferences, and seamless Real-Debrid integration for premium downloading.
    
    Class Attributes:
        RD: Real-Debrid API client instance for premium torrent services
        engine: TorrentSearchEngine instance for multi-provider torrent searching  
        bg_task_pool: WorkerGovernor for managing background download tasks (2 workers)
        
    Features:
        - Multi-provider torrent searching across popular sites
        - Real-Debrid integration for instant torrent-to-direct-link conversion
        - Progressive search strategies with quality fallback
        - Background task processing for non-blocking downloads
        - Automatic file unpacking and organization
        - Comprehensive error handling and retry logic
        - Configurable download paths and completion waiting
        
    Supported Media Types:
        - Music Albums: Progressive quality search (FLAC -> MP3 -> general -> discography)
        - Movies: Multi-language and quality preference support  
        - TV Shows: Season and episode-specific searching
        - General content: Flexible query-based searching
        
    Dependencies:
        - Real-Debrid account with valid API token (RD_APITOKEN environment variable)
        - TorrentSearchEngine with configured provider sites
        - WorkerGovernor for background task management
        
    Example:
        >>> # Search and download music album
        >>> Search.MusicAlbum("Pink Floyd", "Dark Side of the Moon")
        >>> 
        >>> # Download movie with specific preferences
        >>> Search.Movie("Inception", "2010", download_wait_for_completion=False)
        >>> 
        >>> # Custom search with specific path
        >>> Search.search_and_download("artist album flac", save_path="/downloads/music")
        
    Note:
        - Requires valid Real-Debrid premium subscription for torrent downloading
        - Search providers are configured via JSON5 files in torrent_search/sites/
        - Background downloads continue even if main process exits (within session)
        - All downloads are logged and can be monitored via Real-Debrid dashboard
    """
    RD = RD()
    engine: TorrentSearchEngine = None
    bg_task_pool: WorkerGovernor = WorkerGovernor.started(num_workers=2)

    # noinspection PyUnresolvedReferences
    @classmethod
    def MusicAlbum(cls, artist: str, album: str, download_start: bool = True, download_wait_for_completion: bool = True,
                   save_path=None):
        """
        Search for and download music albums from torrent sources.
        
        Performs progressive search for albums with different quality preferences
        (FLAC -> MP3 -> general search -> discography) and integrates with 
        Real-Debrid for premium torrent downloading.
        
        Args:
            artist (str): Name of the artist/band
            album (str): Name of the album to search for
            download_start (bool): Whether to start download immediately (default: True)
            download_wait_for_completion (bool): Whether to wait for download completion (default: True)  
            save_path (optional): Local directory to save downloaded files (default: None)
            
        Returns:
            Search results and download information
            
        Search Strategy:
            1. "{artist} {album} flac" - High quality FLAC preference
            2. "{artist} {album} mp3" - Standard MP3 quality
            3. "{artist} {album}" - General album search
            4. "{artist} discography flac" - Full discography FLAC
            5. "{artist} discography mp3" - Full discography MP3
            6. "{artist} discography" - General discography search
            
        Features:
            - Progressive quality fallback (FLAC -> MP3 -> general)
            - Real-Debrid integration for premium downloading
            - Automatic unpacking of downloaded archives
            - Background task processing
            - Comprehensive error handling
            
        Example:
            >>> # Download specific album
            >>> results = Search.MusicAlbum("Pink Floyd", "The Dark Side of the Moon")
            >>> 
            >>> # Download without waiting for completion
            >>> results = Search.MusicAlbum("Beatles", "Abbey Road", download_wait_for_completion=False)
            >>> 
            >>> # Download to specific path
            >>> results = Search.MusicAlbum("Led Zeppelin", "IV", save_path="/music/downloads")
        """
        subjectTypeName = "album"
        subjectName = f"'{album}' by '{artist}'"
        queryoptions = {
            f"{artist} {album} flac": f"{artist} {album}",
            f"{artist} {album} mp3": f"{artist} {album}",
            f"{artist} {album}": f"{artist} {album}",
            f"{artist} discography flac": f"{artist}",
            f"{artist} discography mp3": f"{artist}",
            f"{artist} discography": f"{artist}",
        }

        results = cls._search_and_download(subjectTypeName=subjectTypeName,
                                              subjectName=subjectName,
                                              queryoptions=queryoptions,
                                              download_start=download_start,
                                              download_wait_for_completion=download_wait_for_completion,
                                              download_local=True,
                                              save_path=save_path,
                                              unpack_local=True)

        return results

    # noinspection PyUnresolvedReferences
    @classmethod
    def MusicArtist(cls, artist: str, download_start: bool = True, download_wait_for_completion: bool = True,
                   save_path=None):
        """
        Search for and download artist discography from torrent sources.

        Performs progressive search for full artist discography with different quality
        preferences (FLAC -> MP3 -> general) and integrates with Real-Debrid for
        premium torrent downloading.

        Args:
            artist (str): Name of the artist/band whose discography to download
            download_start (bool): Whether to start download immediately (default: True)
            download_wait_for_completion (bool): Whether to wait for download completion (default: True)
            save_path (optional): Local directory to save downloaded files (default: None)

        Returns:
            List[TorrentBase]: Search results and download information

        Search Strategy:
            1. "{artist} discography flac" - Full discography FLAC quality
            2. "{artist} discography mp3" - Full discography MP3 quality
            3. "{artist} discography" - General discography search

        Features:
            - Progressive quality fallback (FLAC -> MP3 -> general)
            - Real-Debrid integration for premium downloading
            - Automatic unpacking of downloaded archives
            - Background task processing
            - Comprehensive error handling

        Example:
            >>> # Download artist discography
            >>> results = Search.MusicArtist("Pink Floyd", save_path="/music/downloads")
            >>>
            >>> # Download without waiting for completion
            >>> results = Search.MusicArtist("Beatles", download_wait_for_completion=False)
            >>>
            >>> # Download to specific path
            >>> results = Search.MusicArtist("Led Zeppelin", save_path="/music/downloads")

        Note:
            This method searches specifically for artist discographies, not individual albums.
            Use MusicAlbum() for specific album downloads.
        """
        subjectTypeName = "discography"
        subjectName = f"'{artist}'"
        queryoptions = {
            f"{artist} discography flac": f"{artist}",
            f"{artist} discography mp3": f"{artist}",
            f"{artist} discography": f"{artist}",
        }

        results = cls._search_and_download(subjectTypeName=subjectTypeName,
                                              subjectName=subjectName,
                                              queryoptions=queryoptions,
                                              download_start=download_start,
                                              download_wait_for_completion=download_wait_for_completion,
                                              download_local=True,
                                              save_path=save_path,
                                              unpack_local=True)

        return results

    @staticmethod
    def Movie(movie: str, year: str, download_start: bool = True, download_wait_for_completion: bool = True):
        """
        Search for and download movies from torrent sources.

        Performs progressive search for movies with different quality and language preferences
        (1080p -> 720p with English/Dutch/Multi-language support) and integrates with
        Real-Debrid for premium torrent downloading.

        Args:
            movie (str): Name of the movie to search for
            year (str): Release year of the movie
            download_start (bool): Whether to start download immediately (default: True)
            download_wait_for_completion (bool): Whether to wait for download completion (default: True)

        Returns:
            List[TorrentBase]: Search results and download information

        Search Strategy:
            The method tries these queries in order until results are found:
            1. "{movie} {year} 1080p english" - High quality English audio
            2. "{movie} {year} 1080p eng" - High quality English audio (short form)
            3. "{movie} {year} 1080p dutch" - High quality Dutch audio
            4. "{movie} {year} 1080p nl" - High quality Dutch audio (short form)
            5. "{movie} {year} 1080p multi" - High quality multi-language
            6. "{movie} {year} 720p english" - Standard quality English audio
            7. "{movie} {year} 720p eng" - Standard quality English audio (short form)
            8. "{movie} {year} 720p dutch" - Standard quality Dutch audio
            9. "{movie} {year} 720p nl" - Standard quality Dutch audio (short form)
            10. "{movie} {year} 720p multi" - Standard quality multi-language

        Features:
            - Progressive quality fallback (1080p -> 720p)
            - Multi-language support (English, Dutch, Multi-language)
            - Real-Debrid integration for premium downloading
            - Automatic torrent quality selection
            - Comprehensive error handling

        Example:
            >>> # Download a movie
            >>> results = Search.Movie("Inception", "2010")
            >>>
            >>> # Download without waiting for completion
            >>> results = Search.Movie("The Matrix", "1999", download_wait_for_completion=False)
            >>>
            >>> # Start search without downloading
            >>> results = Search.Movie("Interstellar", "2014", download_start=False)

        Note:
            - Movies are downloaded to Real-Debrid cloud storage
            - Use save_path parameter in _search_and_download for local downloads
            - Quality preference: 1080p is tried first, then falls back to 720p
            - Language preference: English is tried first, then Dutch, then multi-language
        """
        subjectTypeName = "movie"
        subjectName = f"'{movie} ({year})"
        queryoptions = {
            f"{movie} {year} 1080p english": f"{movie} ({year})",
            f"{movie} {year} 1080p eng": f"{movie} ({year})",
            f"{movie} {year} 1080p dutch": f"{movie} ({year})",
            f"{movie} {year} 1080p nl": f"{movie} ({year})",
            f"{movie} {year} 1080p multi": f"{movie} ({year})",
            f"{movie} {year} 720p english": f"{movie} ({year})",
            f"{movie} {year} 720p eng": f"{movie} ({year})",
            f"{movie} {year} 720p dutch": f"{movie} ({year})",
            f"{movie} {year} 720p nl": f"{movie} ({year})",
            f"{movie} {year} 720p multi": f"{movie} ({year})",
        }

        results = Search._search_and_download(subjectTypeName=subjectTypeName,
                                              subjectName=subjectName,
                                              queryoptions=queryoptions,
                                              download_start=download_start,
                                              download_wait_for_completion=download_wait_for_completion)
        return results

    @staticmethod
    def _search(subjectTypeName, subjectName, queryoptions, additional_torrent_search=False) -> List[TorrentBase]:
        """
        Internal method to perform torrent searches using progressive query strategy.

        Searches for torrents using Real-Debrid first (for instant cached results), then
        optionally searches public torrent sites if needed. Uses the TorrentSearchEngine
        with debrid integration to find the best matches.

        Args:
            subjectTypeName (str): Type of media being searched (e.g., "movie", "album", "discography")
            subjectName (str): Friendly name of the subject for logging (e.g., "'Inception (2010)'")
            queryoptions (dict): Dictionary of query strings to try in order. Keys are search
                queries, values are download target names for organizing results.
            additional_torrent_search (bool): If True, always search public torrent sites even
                if Real-Debrid has cached results (default: False)

        Returns:
            List[TorrentBase]: List of matching torrents sorted by seeders, with each torrent
                containing download information and Real-Debrid integration

        Search Process:
            1. Searches Real-Debrid cache first for instant results
            2. If no cached results (or additional_torrent_search=True), searches public sites
            3. Results are sorted by seeder count for best quality/availability
            4. Each result includes download_target metadata for file organization

        Note:
            - Temporarily disables refreshEverySearch during the search for performance
            - Restores original refreshEverySearch setting after search completes
            - Logs search progress and result counts at INFO level
        """
        engine: TorrentSearchEngine = Search._getEngine()
        prev_refreshEverySearch = engine.debrid_options.refreshEverySearch

        logging.info(f"Starting search for {subjectTypeName} {subjectName}")

        engine.debrid_options.refreshEverySearch = False
        results: list[TorrentBase] = Search._search_rd(queryoptions)
        if len(results) == 0 or additional_torrent_search:
            results = Search._search_torrents(queryoptions, results)

        engine.debrid_options.refreshEverySearch = prev_refreshEverySearch
        return results

    @classmethod
    def _search_and_download(cls,
                             subjectTypeName,
                             subjectName,
                             queryoptions,
                             additional_torrent_search=False,
                             download_start=True,
                             download_wait_for_completion=True,
                             download_local=True,
                             save_path=None,
                             unpack_local=True):
        """
        Internal method to search for torrents and orchestrate the complete download workflow.

        This is the core method that coordinates searching, downloading, waiting, and local
        file management. It calls _search() to find torrents, then manages the download
        lifecycle through Real-Debrid and optional local file downloads.

        Args:
            subjectTypeName (str): Type of media (e.g., "movie", "album", "discography")
            subjectName (str): Friendly name for logging (e.g., "'Inception (2010)'")
            queryoptions (dict): Search query dictionary (keys=queries, values=download targets)
            additional_torrent_search (bool): Force public torrent search even if cached (default: False)
            download_start (bool): Start Real-Debrid downloads immediately (default: True)
            download_wait_for_completion (bool): Block until at least one download completes (default: True)
            download_local (bool): Download files to local filesystem (default: True)
            save_path (str, optional): Local directory path for downloads (required if download_local=True)
            unpack_local (bool): Automatically unpack archives after download (default: True)

        Returns:
            List[TorrentBase]: List of torrent results (limited to top 10), with download information

        Raises:
            Exception: If download_local=True but save_path is None

        Workflow:
            1. Search for torrents using _search()
            2. Limit results to top 10 by seeders
            3. If download_start=True, start Real-Debrid downloads
            4. If download_wait_for_completion=True, wait for at least one to complete
            5. If download_local=True, queue background jobs to download files locally
            6. Return the processed results

        Note:
            - Local downloads happen in background workers (non-blocking)
            - Torrents are sorted by seeder count before limiting to 10
            - Failed downloads are automatically cleaned up during wait phase
            - Each torrent gets tagged with download_target for file organization
        """
        if download_local and save_path is None:
            raise Exception("if download_local == True then save_path should be supplied")



        results = cls._search(subjectTypeName=subjectTypeName,
                                 subjectName=subjectName,
                                 queryoptions=queryoptions,
                                 additional_torrent_search=additional_torrent_search)
        results = results[:min(len(results), 10)]

        if download_start:
            cls._download_start(results)
        if download_wait_for_completion and len(results) > 0:
            results = cls._download_wait(results)
        if download_local:
            for rd_torrent in results:
                cls.bg_task_pool.add_job(cls._download_local,rd_torrent, save_path, unpack_local)

        return results

    @staticmethod
    def _download_local(rd_torrent, save_path, unpack_local):
        """
        Internal method to download a Real-Debrid torrent to the local filesystem.

        Downloads files from Real-Debrid's cloud storage to a local directory, with
        optional automatic unpacking of archives. Files are organized into subdirectories
        based on the download_target metadata.

        Args:
            rd_torrent (TorrentBase): Torrent object with Real-Debrid integration
            save_path (str): Base local directory path for downloads
            unpack_local (bool): If True, automatically unpack archives (.zip, .rar, etc.)

        File Organization:
            Files are saved to: {save_path}\\{download_target}\\
            where download_target is set during search (e.g., "Inception (2010)")

        Note:
            - This method is typically called in background workers for non-blocking downloads
            - Uses TorrentBase.downloadToLocal() method for the actual download
            - Archives are unpacked in-place if unpack_local=True
            - Supports all Real-Debrid supported archive formats
        """
        rd_torrent.downloadToLocal(
            path=str(save_path) + "\\" + rd_torrent['download_target'] + "\\",
            unpack=unpack_local)

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _download_wait(results, maxWaitMs=120000, keepTopN=1):
        """
        Internal method to wait for Real-Debrid torrent downloads to complete.

        Monitors a list of downloading torrents, waiting until at least one completes
        successfully. Automatically removes failed downloads and cleans up incomplete
        torrents once a download finishes. Only keeps the top N fastest completions.

        Args:
            results (List[TorrentBase]): List of torrent downloads to monitor
            maxWaitMs (int): Maximum time to wait in milliseconds (default: 120000 = 2 minutes)
            keepTopN (int): Number of completed torrents to keep (default: 1)

        Returns:
            List[TorrentBase]: List of completed torrents (up to keepTopN items), or
                all results if timeout occurs

        Monitoring Process:
            1. Poll each torrent's status every 20 seconds
            2. Log progress, status, and seeder count for each torrent
            3. Remove torrents with "error" status immediately
            4. Once any torrent reaches 100% progress:
               - Remove all incomplete downloads from Real-Debrid
               - Keep only top N fastest completions
               - Remove excess completed downloads from Real-Debrid
            5. If timeout occurs, keep all downloads without cleanup

        Status Updates:
            Logs for each torrent: "{filename}: [{status}] {progress}% {seeders}S"

        Cleanup Behavior:
            - On Success (before timeout):
                * Deletes incomplete torrents from Real-Debrid
                * Keeps top N completed torrents (by completion order)
                * Deletes extra completed torrents from Real-Debrid
            - On Timeout:
                * Keeps all torrents (no cleanup)
                * Returns all results for manual handling

        Note:
            - Polls Real-Debrid API every 20 seconds to check status
            - Failed downloads are removed immediately to free up slots
            - The keepTopN parameter prevents keeping multiple copies
            - Timeout does not cancel downloads, just stops waiting
        """
        logging.info(f"Waiting for one of them to complete")
        completed = []

        start_ms = int(time.time() * 1000)
        while len(completed) == 0 and len(results) > 0 and int(time.time() * 1000) - start_ms < maxWaitMs:
            downloadingResult: TorrentBase
            for downloadingResult in results:
                if not downloadingResult['info']["status"] in ["error"]:
                    downloadingResult.updateInfo()
                    logging.info(
                        f"{downloadingResult['info']['filename']}: [{downloadingResult['info']['status']}]\t{downloadingResult['info']['progress']}% {downloadingResult['info']['seeders']}S")
                if (downloadingResult['info']["progress"] is not None and downloadingResult['info']["progress"] >= 100):
                    completed.append(downloadingResult)
            results_copy = [] + results
            for downloadingResult in results_copy:
                if downloadingResult in completed:
                    results.remove(downloadingResult)
                if downloadingResult['info']["status"] in ["error"]:
                    results.remove(downloadingResult)
                    try:
                        downloadingResult.removeTorrentDownload()
                    except Exception:
                        logging.debug("deleted errored")
            if len(completed) == 0:
                time.sleep(20)
        timedout = int(time.time() * 1000) - start_ms >= maxWaitMs
        if not timedout:
            logging.info(f"Remove the other incomplete downloads")
            for result in results:
                result.removeTorrentDownload()
            kept = completed[:min(keepTopN, len(completed))]
            dumped = completed[len(kept):]
            logging.info(f"Remove the other completed downloads except top {len(kept)}/{len(completed)}")
            for torrent in dumped:
                if torrent in results:
                    results.remove(torrent)
                try:
                    torrent.removeTorrentDownload()
                except Exception:
                    logging.debug("deleting errored")
            return kept
        else:
            logging.info(f"Timed out: Won't remove incomplete downloads")
            return results

    @staticmethod
    def _download_start(results):
        """
        Internal method to start Real-Debrid downloads for all torrents in the results list.

        Initiates debrid downloads for each torrent, adding them to the Real-Debrid cloud
        for processing. The torrents will begin downloading on Real-Debrid's servers.

        Args:
            results (List[TorrentBase]): List of torrent objects to start downloading

        Process:
            1. Logs the number of torrents being started
            2. Calls startDebridDownload() on each torrent
            3. Torrents are queued in Real-Debrid for download

        Note:
            - This method does not wait for downloads to complete
            - Use _download_wait() to monitor progress and completion
            - Each torrent must have debrid integration enabled (via TorrentSearchEngine)
            - Downloads happen on Real-Debrid's servers, not locally
        """
        logging.info(f"Starting all {len(results)} torrents")
        result: TorrentBase
        for result in results:
            result.startDebridDownload()

    @staticmethod
    def _search_torrents(queryoptions, results=None) -> List[TorrentBase]:
        """
        Internal method to search public torrent sites for torrents.

        Searches multiple public torrent sites using the TorrentSearchEngine with progressive
        query strategies. Tries each query option in order and stops when results are found.
        Results are sorted by seeder count for best quality.

        Args:
            queryoptions (dict): Dictionary of search queries to try. Keys are query strings,
                values are download target names for organizing results.
            results (List[TorrentBase], optional): Existing results list to append to (default: None)

        Returns:
            List[TorrentBase]: Combined list of torrent results, sorted by seeder count (highest first)

        Search Process:
            1. For each query in queryoptions (in order):
               - Search public torrent sites with 10 result limit and 5 second timeout
               - Log the query and number of results found
               - Tag each result with download_target from queryoptions
               - Add results to the list and continue to next query
            2. Sort all results by seeder count
            3. Return sorted results

        Configured Torrent Sites:
            - KickAssTorrents
            - EZTV
            - ETTV
            - 1337x
            - MagnetDL
            - ThePirateBay

        Note:
            - Uses noremote=None to search public sites (not cached results)
            - Each query has 5 second timeout per site
            - Results from all queries are combined before sorting
            - Higher seeders = better availability and speed
        """
        engine: TorrentSearchEngine = Search._getEngine()

        if results is None:
            results = []
        logging.info(f"\t- (Torrent) sites")
        for query in queryoptions:
            logging.info(f"\t- Search: {query}")
            results_torrent = engine.search(query, limit=10, timeout=5, noremote=None)
            logging.info(f"\t\tFound  {len(results_torrent)}")
            if len(results_torrent) > 0:
                for result in results_torrent:
                    result['download_target'] = queryoptions[query]
                results += results_torrent
        results = engine._sort_by_seeds(results)
        return results

    @staticmethod
    def _search_rd(queryoptions, results=None) -> List[TorrentBase]:
        """
        Internal method to search Real-Debrid cache for instantly available torrents.

        Searches only Real-Debrid's cached torrents for instant availability, without querying
        public torrent sites. This provides the fastest results as cached torrents can be
        instantly downloaded. Uses progressive query strategy and stops at first success.

        Args:
            queryoptions (dict): Dictionary of search queries to try. Keys are query strings,
                values are download target names for organizing results.
            results (List[TorrentBase], optional): Existing results list to append to (default: None)

        Returns:
            List[TorrentBase]: List of cached torrent results ready for instant download

        Search Process:
            1. For each query in queryoptions (in order):
               - Search Real-Debrid cache with 20 result limit and 15 second timeout
               - Log the query and number of cached results found
               - If results found:
                 * Tag each result with download_target from queryoptions
                 * Add to results list and BREAK (stop trying other queries)
               - If no results, try next query
            2. Return results (empty if no cached torrents found)

        Advantages of Cached Search:
            - Instant availability (no waiting for torrent download)
            - No seeder requirements (already downloaded by Real-Debrid)
            - Premium download speeds immediately
            - Lower API usage and faster response times

        Note:
            - Uses noremote=True to search only cached/local results
            - Stops at first successful query (unlike _search_torrents)
            - Longer timeout (15s) allows thorough cache checking
            - Higher limit (20) provides more instant download options
        """
        engine: TorrentSearchEngine = Search._getEngine()

        if results is None:
            results = []

        logging.info(f"\t- Only local/debrid")
        for query in queryoptions:
            logging.info(f"\t- Search: {query}")
            results_rd: list[TorrentBase] = engine.search(query, limit=20, timeout=15, noremote=True)
            logging.info(f"\t\tFound  {len(results_rd)}")
            if len(results_rd) > 0:
                for result in results_rd:
                    result['download_target'] = queryoptions[query]
                results = results + results_rd
                break
        return results

    @classmethod
    def _getEngine(cls) -> TorrentSearchEngine:
        """
        Internal method to get or initialize the TorrentSearchEngine singleton.

        Lazily initializes and configures the search engine on first call, then returns
        the cached instance on subsequent calls. The engine is configured with multiple
        torrent site providers and Real-Debrid integration.

        Returns:
            TorrentSearchEngine: Configured search engine with debrid integration enabled

        Initialization Process (first call only):
            1. Creates new TorrentSearchEngine instance
            2. Loads configuration files for each torrent provider:
               - KickAssTorrents (kickasstorrents.json5)
               - EZTV (eztv.json5)
               - ETTV (ettv.json)
               - 1337x (1337x.json5)
               - MagnetDL (magnetdl.json5)
               - ThePirateBay (piratebay.json5)
            3. Enables Real-Debrid integration
            4. Caches instance in Search.engine class variable

        Provider Configuration:
            - All provider configs are loaded from the /sites/ subdirectory
            - JSON5 format allows comments and flexible configuration
            - Each provider defines search patterns, selectors, and site-specific rules

        Singleton Pattern:
            - Only one engine instance exists per Search class
            - Reused across all search operations for efficiency
            - Maintains debrid connection and provider state

        Note:
            - Provider configs must exist in the sites/ directory
            - Real-Debrid integration is enabled by default
            - Engine instance is shared across all Search class methods
        """
        if Search.engine is None:
            Search.engine = TorrentSearchEngine()
            engine = Search.engine
            script_dir = os.path.dirname(os.path.abspath(__file__))

            engine.add_provider(script_dir + '\\sites\\kickasstorrents.json5')
            engine.add_provider(script_dir + '\\sites\\eztv.json5')
            engine.add_provider(script_dir + '\\sites\\ettv.json')
            engine.add_provider(script_dir + '\\sites\\1337x.json5')
            engine.add_provider(script_dir + '\\sites\\magnetdl.json5')
            engine.add_provider(script_dir + '\\sites\\piratebay.json5')
            engine.enable_debrid()  # = Default
        return Search.engine
        pass

    @classmethod
    def wait_for_background_tasks(cls):
        """
        Wait for all background tasks to complete before continuing.

        Blocks execution until all queued background jobs (local file downloads and unpacking)
        finish processing. Use this method to ensure all downloads are complete before the
        application exits or before performing operations that depend on downloaded files.

        Background Tasks Include:
            - Local file downloads from Real-Debrid to filesystem
            - Archive unpacking (.zip, .rar, etc.)
            - File organization and metadata processing

        Returns:
            None (blocks until completion)

        Example:
            >>> # Start multiple downloads
            >>> Search.MusicAlbum("Artist1", "Album1", save_path="/music")
            >>> Search.MusicAlbum("Artist2", "Album2", save_path="/music")
            >>>
            >>> # Wait for all background downloads to finish
            >>> Search.wait_for_background_tasks()
            >>> print("All downloads complete!")

        Worker Pool Configuration:
            - 2 concurrent workers process tasks in parallel
            - Tasks are processed in FIFO (first-in-first-out) order
            - Each task downloads and unpacks one torrent

        Note:
            - Always call this before exiting if download_local=True was used
            - Necessary to ensure file integrity and complete unpacking
            - Does not wait for Real-Debrid downloads (only local operations)
            - Logs progress message when called
        """
        logging.info("Waiting for background tasks (like local downloads and unpacking)")
        cls.bg_task_pool.wait_for_completion()
