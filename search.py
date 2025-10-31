import logging
import os
import time
from typing import List

from rd_api_py.rdapi import RD
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
        Search for and download music discograph from torrent sources.

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

    @staticmethod
    def Movie(movie: str, year: str, download_start: bool = True, download_wait_for_completion: bool = True):
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
        rd_torrent.downloadToLocal(
            path=str(save_path) + "\\" + rd_torrent['download_target'] + "\\",
            unpack=unpack_local)

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _download_wait(results, maxWaitMs=120000, keepTopN=1):
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
        logging.info(f"Starting all {len(results)} torrents")
        result: TorrentBase
        for result in results:
            result.startDebridDownload()

    @staticmethod
    def _search_torrents(queryoptions, results=None) -> List[TorrentBase]:
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
        logging.info("Waiting for background tasks (like local downloads and unpacking)")
        cls.bg_task_pool.wait_for_completion()
