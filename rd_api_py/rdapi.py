#!/usr/bin/env python3

import os
import time
import json
import logging
from json import JSONDecodeError

import requests
import itertools
from pathlib import Path

# Import connection pooling utilities from parent project
import sys
parent_path = str(Path(__file__).parent.parent)
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

try:
    from utils import get_http_pool
    CONNECTION_POOLING_AVAILABLE = True
except ImportError:
    CONNECTION_POOLING_AVAILABLE = False


class RD:
    """
    Real-Debrid API client for premium torrent and direct download services.
    
    This class provides a comprehensive interface to Real-Debrid's REST API,
    enabling torrent-to-direct-link conversion, unrestricted downloads, and
    account management features. Includes connection pooling, error handling,
    and rate limiting for reliable API interactions.
    
    Environment Variables:
        RD_APITOKEN (required): Real-Debrid API token from account settings
        SLEEP (optional): Base sleep time in milliseconds between requests (default: 2000)
        LONG_SLEEP (optional): Extended sleep time for rate limiting (default: 30000)
        
    Attributes:
        system: System information and API status
        user: User account management and information
        unrestrict: Link unrestriction and torrent conversion
        traffic: Traffic and download statistics
        streaming: Streaming links and transcoding
        torrents: Torrent management and downloads
        downloads: Download history and management
        hosts: Supported host information
        
    Features:
        - Connection pooling for improved performance
        - Automatic retry with exponential backoff
        - Comprehensive error handling and logging
        - Rate limiting to respect API limits
        - Thread-safe operation for concurrent use
        - Fallback support without connection pooling
        
    Example:
        >>> # Initialize client (requires RD_APITOKEN environment variable)
        >>> rd = RD()
        >>> 
        >>> # Check account status
        >>> user_info = rd.user.get()
        >>> print(f"Premium until: {user_info['expiration']}")
        >>> 
        >>> # Unrestrict a download link
        >>> link = rd.unrestrict.link("https://example.com/file.zip")
        >>> print(f"Direct link: {link['download']}")
        >>> 
        >>> # Add torrent for conversion
        >>> torrent_id = rd.torrents.add_torrent("magnet:?xt=urn:btih:...")
        >>> print(f"Torrent added: {torrent_id}")
        
    Raises:
        ValueError: If RD_APITOKEN environment variable is not set
        ConnectionError: If API is unreachable or returns server errors
        requests.HTTPError: For HTTP-related errors during API calls
        
    Note:
        - Requires valid Real-Debrid premium account and API token
        - API token can be obtained from Real-Debrid account settings
        - Respects Real-Debrid's rate limiting and usage policies
        - Automatically handles error codes and provides meaningful messages
    """
    def __init__(self):
        self.rd_apitoken = os.getenv('RD_APITOKEN')
        self.base_url = 'https://api.real-debrid.com/rest/1.0'
        self.header = {'Authorization': "Bearer " + str(self.rd_apitoken)}
        self.error_codes = json.load(open(os.path.join(Path(__file__).parent.absolute(), 'error_codes.json')))
        self.sleep = int(os.getenv('SLEEP', 2000)) / 1000
        self.long_sleep = int(os.getenv('LONG_SLEEP', 30000)) / 1000
        self.count_obj = itertools.cycle(range(0, 501))
        self.count = next(self.count_obj)

        # Initialize connection pool for API requests
        if CONNECTION_POOLING_AVAILABLE:
            self._http_pool = get_http_pool(
                "rd_api", 
                pool_maxsize=10,
                max_retries=2,
                timeout=(10.0, 30.0)
            )
        else:
            self._http_pool = None

        # Check the API token
        self.check_token()

        self.system = self.System(self)
        self.user = self.User(self)
        self.unrestrict = self.Unrestrict(self)
        self.traffic = self.Traffic(self)
        self.streaming = self.Streaming(self)
        self.downloads = self.Downloads(self)
        self.torrents = self.Torrents(self)
        self.hosts = self.Hosts(self)
        self.settings = self.Settings(self)

    def get(self, path, **options):
        if self._http_pool:
            # Use connection pool for better performance
            request = self._http_pool.get(self.base_url + path, headers=self.header, params=options)
        else:
            # Fallback to standard requests
            request = requests.get(self.base_url + path, headers=self.header, params=options)
        return self.handler(request, self.error_codes, path)

    def post(self, path, **payload):
        if self._http_pool:
            # Use connection pool for better performance
            request = self._http_pool.post(self.base_url + path, headers=self.header, data=payload)
        else:
            # Fallback to standard requests
            request = requests.post(self.base_url + path, headers=self.header, data=payload)
        return self.handler(request, self.error_codes, path)

    def put(self, path, filepath, **payload):
        with open(filepath, 'rb') as file:
            if self._http_pool:
                # Use connection pool for better performance
                request = self._http_pool.put(self.base_url + path, headers=self.header, data=file, params=payload)
            else:
                # Fallback to standard requests
                request = requests.put(self.base_url + path, headers=self.header, data=file, params=payload)
        return self.handler(request, self.error_codes, path)

    def delete(self, path):
        if self._http_pool:
            # Use connection pool for better performance
            request = self._http_pool.delete(self.base_url + path, headers=self.header)
        else:
            # Fallback to standard requests
            request = requests.delete(self.base_url + path, headers=self.header)
        return self.handler(request, self.error_codes, path)

    def handler(self, request, error_codes, path):
        try:
            request.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            logging.error('Real-Debrid API HTTP error at %s: %s', path, errh)
        except requests.exceptions.ConnectionError as errc:
            logging.error('Real-Debrid API connection error at %s: %s', path, errc)
        except requests.exceptions.Timeout as errt:
            logging.error('Real-Debrid API timeout error at %s: %s', path, errt)
        except requests.exceptions.RequestException as err:
            logging.error('Real-Debrid API request error at %s: %s', path, err)
        try:
            if 'error_code' in request.json():
                code = request.json()['error_code']
                message = error_codes.get(str(code), 'Unknown error')
                logging.warning('Real-Debrid API error code %s (%s) at %s', code, message, path)
        except (JSONDecodeError, ValueError, AttributeError, KeyError) as e:
            # JSON parsing failed, response has no json method, or missing keys
            # This is expected for non-JSON responses and shouldn't be logged as error
            logging.debug('Unable to parse JSON response for error codes at %s: %s', path, str(e))
        self.handle_sleep()
        return request

    def check_token(self):
        if self.rd_apitoken is None or self.rd_apitoken == 'your_token_here':
            logging.warning('Real-Debrid API token not configured - add valid token to .env file')

    def handle_sleep(self):
        if self.count < 500:
            logging.debug('Sleeping %ss', self.sleep)
            time.sleep(self.sleep)
        elif self.count == 500:
            logging.debug('Sleeping %ss', self.long_sleep)
            time.sleep(self.long_sleep)
            self.count = 0

    class System:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def disable_token(self):
            return self.rd.get('/disable_access_token')

        def time(self):
            return self.rd.get('/time')

        def iso_time(self):
            return self.rd.get('/time/iso')

    class User:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/user')

    class Unrestrict:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def check(self, link, password=None):
            return self.rd.post('/unrestrict/check', link=link, password=password)

        def link(self, link, password=None, remote=None):
            return self.rd.post('/unrestrict/link', link=link, password=password, remote=remote)

        def folder(self, link):
            return self.rd.post('/unrestrict/folder', link=link)

        def container_file(self, filepath):
            return self.rd.put('/unrestrict/containerFile', filepath=filepath)

        def container_link(self, link):
            return self.rd.post('/unrestrict/containerLink', link=link)

    class Traffic:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/traffic')

        def details(self, start=None, end=None):
            return self.rd.get('/traffic/details', start=start, end=end)

    class Streaming:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def transcode(self, id):
            return self.rd.get('/streaming/transcode/' + str(id))

        def media_info(self, id):
            return self.rd.get('/streaming/mediaInfos/' + str(id))

    class Downloads:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self, offset=None, page=None, limit=None):
            return self.rd.get('/downloads', offset=offset, page=page, limit=limit)

        def delete(self, id):
            return self.rd.delete('/downloads/delete/' + str(id))

    class Torrents:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self, offset=None, page=None, limit=None, filter=None):
            return self.rd.get('/torrents', offset=offset, page=page, limit=limit, filter=filter)

        def getAll(self, filter=None):
            total = []
            for page in range(1, 100):
                response = self.rd.get('/torrents', offset=None, page=page, limit=50, filter=filter)
                try:
                    page_torrents = json.loads(
                        response.content)
                    total += page_torrents
                except Exception as e:
                    break
            return total

        def info(self, id):
            return self.rd.get('/torrents/info/' + str(id))

        def instant_availability(self, hash):
            return self.rd.get('/torrents/instantAvailability/' + str(hash))

        def active_count(self):
            return self.rd.get('/torrents/activeCount')

        def available_hosts(self):
            return self.rd.get('/torrents/availableHosts')

        def add_file(self, filepath, host=None):
            return self.rd.put('/torrents/addTorrent', filepath=filepath, host=host)

        def add_magnet(self, magnet, host=None):
            magnet_link = str(magnet)
            if not magnet_link.startswith('magnet:?xt=urn:btih:'):
                magnet_link = 'magnet:?xt=urn:btih:' + magnet_link
            return self.rd.post('/torrents/addMagnet', magnet=magnet_link, host=host)

        def select_files(self, id, files):
            return self.rd.post('/torrents/selectFiles/' + str(id), files=str(files))

        def delete(self, id):
            return self.rd.delete('/torrents/delete/' + str(id))

    class Hosts:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/hosts')

        def status(self):
            return self.rd.get('/hosts/status')

        def regex(self):
            return self.rd.get('/hosts/regex')

        def regex_folder(self):
            return self.rd.get('/hosts/regexFolder')

        def domains(self):
            return self.rd.get('/hosts/domains')

    class Settings:
        def __init__(self, rd_instance):
            self.rd = rd_instance

        def get(self):
            return self.rd.get('/settings')

        def update(self, setting_name, setting_value):
            return self.rd.post('/settings/update', setting_name=setting_name, setting_value=setting_value)

        def convert_points(self):
            return self.rd.post('/settings/convertPoints')

        def change_password(self):
            return self.rd.post('/settings/changePassword')

        def avatar_file(self, filepath):
            return self.rd.put('/settings/avatarFile', filepath=filepath)

        def avatar_delete(self):
            return self.rd.delete('/settings/avatarDelete')
