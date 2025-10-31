import json
import logging
import os
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError
from os import path
from threading import current_thread
from typing import Any
from typing import List, Union, Optional

from .debrid.options import DebridOptions
from .providermanager import TorrentProviderManager
from .result import *
from .torrentprovider import TorrentProvider
from rd_api_py.rdapi import RD as RealDebrid
from .torrentbase import TorrentBase

logger = logging.getLogger(__name__)


class TorrentSearchEngine:

    def __init__(self):
        self.debrid_options = DebridOptions()
        self._debrid_enabled = True
        self.RD = RealDebrid()

        self._debrid_enabled = False
        self.provider_manager = TorrentProviderManager()

    def _search_debrid(self, query: str, category: str = None, limit: int = None):
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
        Search torrents.

        Parameters:
            query: str - The query to perform.
            category: str - The category to search.
            limit: int - The number of results to return.
            providers: List[Union[str, TorrentProvider]] - Providers to use.
            timeout: int - The max number of seconds to wait.
            n_threads: int - The max number of threads to use

        Returns:
            List[TorrentBase] - The torrents found.
                            Returns an empty list if the query is empty
                            or if no provider is used.
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
        Add a provider from dict/file/url.

        Raises:
            ValueError - There is an error in a property.
            ValidationError - The resource is incorrect.
            RequestError - The resource could not be retrieve from url.
            IOError - The file could not be read.
        """
        self.provider_manager.add(provider)

    def get_providers(self, enabled=None) -> List[TorrentProvider]:
        return self.provider_manager.get_all(enabled=enabled)

    def get_provider(self, name: str) -> Optional[TorrentProvider]:
        return self.provider_manager.get(name)

    def disable_providers(self, *providers: List[Union[str, TorrentProvider]]):
        logger.debug("Disabling providers: {}".format(providers))
        self.provider_manager.disable(*providers)

    def enable_providers(self, *providers: List[Union[str, TorrentProvider]]):
        logger.debug("Enabling providers: {}".format(providers))
        self.provider_manager.enable(*providers)

    def remove_providers(self, *providers: List[Union[str, TorrentProvider]]):
        logger.debug("Removing providers: {}".format(providers))
        self.provider_manager.remove(*providers)

    def _multithreaded_search(self, providers, category, query, limit,
                              timeout, n_threads):

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
        return sorted(items, key=lambda item: int("0" + item['seeds']), reverse=True)

    def enable_debrid(self):
        if self._debrid_enabled:
            return
        self._debrid_enabled = True
        self.RD = RealDebrid()
        pass

    def disable_debrid(self):
        self._debrid_enabled = False
        self.RD = None
        pass

    @staticmethod
    def brute_serialize(obj):
        return

    def rd_dl_magnet_refresh_states(self) -> dict[
        str | Any, TorrentBase]:

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
        ret_list = []
        for t in torrents:
            ret_list += [TorrentBase(**t)]
        return ret_list
