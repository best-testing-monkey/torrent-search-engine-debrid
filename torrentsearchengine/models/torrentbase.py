import json
import logging
import os
import json5

from torrentsearchengine import ValidationError
from torrentsearchengine.models.compressedDownloader import RarDownloader

logger = logging.getLogger(__name__)

class TorrentBase(dict[str, object]):
    """
    Represents a torrent with metadata and download capabilities.

    This class extends dict to store torrent metadata while providing
    convenient property access and methods for torrent operations.
    It integrates with Real-Debrid API for premium downloading capabilities.

    Attributes:
        name (str): Name/title of the torrent
        data (dict): Raw torrent metadata
        id (str): Unique identifier for the torrent
        RD: Real-Debrid API client instance

    Required Initialization Arguments:
        provider (TorrentProvider): The torrent provider/source
        name (str): Torrent name (or info.filename, filename, title)

    Optional Arguments:
        url (str): Info page URL for this torrent
        size (str): Human-readable size (e.g., "1.2 GB")
        seeds (int): Number of seeders
        leeches (int): Number of leechers
        magnet (str): Magnet link
        hash (str): Torrent hash
        info (dict): Additional torrent information

    Example:
        >>> torrent = TorrentBase(
        ...     provider=my_provider,
        ...     name="Ubuntu 22.04 LTS",
        ...     size="3.4 GB",
        ...     seeds=150,
        ...     magnet="magnet:?xt=urn:btih:..."
        ... )
        >>> torrent.fetch_details()  # Get additional metadata
        >>> torrent.startDebridDownload()  # Start download via Real-Debrid
    """

    def __init__(self, **kwargs: dict):
        """
        Initialize a torrent object with metadata.

        Processes and validates torrent metadata, handling various formats
        and automatically extracting information from different sources.

        Args:
            **kwargs: Torrent metadata with the following supported keys:

                Required:
                    provider (TorrentProvider): Source provider for this torrent
                    name (str): Torrent name (fallbacks: info.filename, filename, title)

                Optional:
                    url (str): Info page URL for detailed torrent information
                    size (str): Human-readable size string (e.g., "1.5 GB")
                    seeds (int): Number of seeders (active uploaders)
                    leeches (int): Number of leechers (downloaders)
                    magnet (str): Magnet link for direct torrent access
                    hash (str): Torrent hash (extracted from magnet if not provided)
                    info (dict): Additional torrent metadata
                    id (str): Unique torrent identifier

        Raises:
            ValueError: If required parameters (provider, name) are missing

        Note:
            - Automatically generates magnet links from hash values
            - Extracts hash from magnet links if hash not provided
            - Handles multiple naming conventions for torrent titles
            - Sanitizes magnet links for compatibility

        Example:
            >>> # Minimal torrent
            >>> torrent = TorrentBase(
            ...     provider=provider_instance,
            ...     name="My Torrent"
            ... )
            >>>
            >>> # Full metadata
            >>> torrent = TorrentBase(
            ...     provider=provider_instance,
            ...     name="Ubuntu 22.04 Desktop",
            ...     size="3.4 GB",
            ...     seeds=250,
            ...     leeches=15,
            ...     magnet="magnet:?xt=urn:btih:abcd1234...",
            ...     info={"quality": "720p", "format": "x264"}
            ... )
        """
        # provider and name are required
        super().__init__()
        self.RD = None
        self.name = None
        self.data = None
        self.id = None

        self._init(**kwargs)
        return

    def _init(self, **kwargs: dict):
        super().__init__()
        if not kwargs.get("provider"):
            raise ValueError("Provider is required")

        if kwargs.get('id') == 'all':
            kwargs["name"] = "all"

        if not kwargs.get("name") and kwargs.get('info') and kwargs.get('info').get('filename'):
            kwargs["name"] = kwargs['info']['filename']

        if not kwargs.get("name") and kwargs.get('filename'):
            kwargs["name"] = kwargs['filename']

        if not kwargs.get("name") and kwargs.get('title'):
            kwargs["name"] = kwargs['title']

        if 'hash' not in kwargs and 'magnet' in kwargs:
            magnetLink = str(kwargs['magnet'])
            magnetHash = magnetLink.split(":")[-1]
            kwargs['hash'] = magnetHash
            # kwargs['magnet'] = "magnet:?xt=urn:btih:" + magnetHash

        self.name = kwargs.get("name")
        self.data = kwargs

    @property

    @property
    def name(self):
        return self.data.get("name")

    @property
    def info_url(self):
        return self.data.get("info_url", "")

    @property
    def size(self):
        return self.data.get("size", "")

    @property
    def seeds(self):
        seeds = self.data.get("seeds", -1)
        try:
            return int(seeds)
        except Exception:
            return -1

    @property
    def leeches(self):
        leeches = self.data.get("leeches", -1)
        try:
            return int(leeches)
        except Exception:
            return -1

    def asdict(self) -> dict:
        base_dict = {"id": self.id, "provider": self.provider.name,
                     "name": self.name, "info_url": self.info_url,
                     "size": self.size, "seeds": self.seeds,
                     "leeches": self.leeches}
        for key in self.keys():
            self[key] = base_dict[key]
        return base_dict

    def toDict(self):
        base_dict = {}
        for key in self.keys():
            self[key] = base_dict[key]
        return base_dict

    def __str__(self):
        return self.name

    def fetch_details(self, timeout: int = 30):
        """
        Fetch detailed information about this torrent from the provider.

        Retrieves additional metadata such as file lists, descriptions,
        direct download links, and other detailed information that may
        not be available in initial search results.

        Args:
            timeout: Request timeout in seconds (default: 30)

        Returns:
            TorrentBase: Returns self with updated metadata

        Raises:
            ValueError: If required properties are missing
            requests.RequestException: If network request fails
            requests.Timeout: If request exceeds timeout duration

        Note:
            - Updates the current object with fetched details
            - May include file lists, descriptions, trackers, etc.
            - Information available depends on the torrent provider
            - Some providers may require additional authentication

        Example:
            >>> torrent = TorrentBase(provider=provider, name="Movie")
            >>> detailed = torrent.fetch_details(timeout=60)
            >>> print(f"Files: {detailed.files}")
            >>> print(f"Description: {detailed.description}")
            >>> print(f"Uploader: {detailed.uploader}")
        """
        details_data = self.provider.fetch_details_data(self, timeout)
        # the torrent details are a combination of the data
        # we already have and the new data found in the info page
        self._init(**{**self.data, **details_data})
        return self

    @name.setter
    def name(self, value: str) -> str:
        self._name = value

    @property
    def time(self):
        return self.data.get("time", "")

    @property
    def link(self):
        return self.data.get("magnet", "")

    @property
    def files(self):
        return self.data.get("files", [])

    @property
    def infohash(self):
        return self.data.get("infohash", "")

    @property
    def description(self):
        return self.data.get("description", "")

    @property
    def uploader(self):
        return self.data.get("uploader", "")

    @property
    def uploader_url(self):
        return self.data.get("uploader_url", "")

    @property
    def trackers(self):
        return self.data.get("trackers", [])

    def asdict(self) -> dict:
        """
        Convert torrent to a dictionary with all available metadata.

        Returns:
            dict: Complete torrent metadata including all properties

        Example:
            >>> torrent_dict = torrent.asdict()
            >>> print(json.dumps(torrent_dict, indent=2))
        """
        return {"id": self.id, "provider": self.provider.name,
                "name": self.name, "info_url": self.info_url,
                "size": self.size, "seeds": self.seeds,
                "leeches": self.leeches, "time": self.time,
                "magnet": self.link, "files": self.files,
                "infohash": self.infohash, "description": self.description,
                "uploader": self.uploader, "uploader_url": self.uploader_url,
                "trackers": self.trackers}

    def updateInfo(self):
        """
        Update torrent information from Real-Debrid API.

        Fetches the latest status, progress, and metadata for this torrent
        from Real-Debrid. This includes download status, file information,
        seeder counts, and other dynamic data.

        Note:
            - Requires a Real-Debrid API client and torrent ID
            - Updates self['info'] with current torrent status
            - Ensures required info fields exist with default values
            - Handles API errors gracefully by setting info to None
            - Should be called periodically to track download progress

        Info Fields Updated:
            - seeders: Number of available seeders
            - filename: Primary file name
            - status: Download status (waiting, downloading, downloaded, error)
            - progress: Download progress percentage (0-100)
            - id: Real-Debrid torrent identifier

        Example:
            >>> torrent.startDebridDownload()
            >>> # Wait some time...
            >>> torrent.updateInfo()
            >>> status = torrent['info']['status']
            >>> progress = torrent['info']['progress']
            >>> print(f"Status: {status}, Progress: {progress}%")
        """
        if 'info' not in self:
            self['info'] = {}
        for requiredInfoField in ['seeders', 'filename', 'status', 'progress', 'id']:
            if requiredInfoField not in self['info']:
                self['info'][requiredInfoField] = None

        if self.RD == None:
            return

        if 'info' not in self:
            self['info'] = {}
        for requiredInfoField in ['seeders', 'filename', 'status', 'progress', 'id']:
            if requiredInfoField not in self['info']:
                self['info'][requiredInfoField] = None

        if 'info' in self and 'status' in self['info'] and self['info']['status'] == 'error':
            return

        if 'info' not in self:
            self['info'] = {}
        for requiredInfoField in ['seeders', 'filename', 'status', 'progress']:
            if requiredInfoField not in self['info']:
                self['info'][requiredInfoField] = None

        if 'id' not in self and ('info' in self and 'id' in self['info']):
            self['id'] = self['info']['id']

        try:
            self["info"] = self.RD.torrents.info(self["id"]).json()
        except Exception as e:
            self["info"] = None
            logging.info(f"Info for torrent {self['id']} not retreivable")

        if 'info' not in self:
            self['info'] = {}
        for requiredInfoField in ['seeders', 'filename', 'status', 'progress', 'id']:
            if requiredInfoField not in self['info']:
                self['info'][requiredInfoField] = None
        pass

    def startDebridDownload(self):
        """
        Start a premium download using Real-Debrid service.

        Initiates a download through Real-Debrid's premium torrent service,
        which provides fast, cached downloads without needing to seed.
        This method adds the torrent to Real-Debrid and selects all files
        for download.

        Note:
            - Requires a configured Real-Debrid API client
            - Automatically selects all files in the torrent
            - Updates the torrent's info with download status
            - Handles errors gracefully by marking torrent status
            - Skips if download already started or completed

        Side Effects:
            - Updates self['info'] with Real-Debrid response
            - Sets self['id'] with Real-Debrid torrent ID
            - Calls updateInfo() to refresh status

        Example:
            >>> torrent = TorrentBase(provider=provider, name="Linux ISO",
            ...                      magnet="magnet:?xt=urn:btih:...")
            >>> torrent.startDebridDownload()
            >>> # Check status
            >>> if torrent['info']['status'] == 'downloaded':
            ...     print("Ready for local download!")
        """
        if 'info' in self and 'status' in self['info'] and self['info']['status'] not in ['deleted', 'error']:
            logger.info(f"Download already started/completed: {self['info']['filename']}")
            return
        title = ''
        if 'title' in self:
            title = self['title']
        elif 'name' in self:
            title = self['name']
        elif 'filename' in self:
            title = self['filename']
        logging.info(f"{title}> Start DL")

        magnetLink = str(self['magnet'])
        magnetLink = magnetLink.split("&")[0]

        result_call = self.RD.torrents.add_magnet(magnetLink)
        result = result_call.json()
        self['info'] = result
        if 'error' in result:
            result['id'] = ':ERROR:'
            result['status'] = 'error'
            result['filename'] = title
            result['progress'] = -1
            result['seeders'] = -1
        else:
            self.RD.torrents.select_files(id=result["id"], files="all")
        self['id'] = result["id"]
        self.updateInfo()
        logging.info(f"/{title}> Start DL")

    def removeTorrentDownload(self):
        """
        Remove this torrent from Real-Debrid downloads.

        Deletes the torrent from your Real-Debrid account, freeing up
        space and removing it from your active downloads list.

        Note:
            - Requires the torrent to have been added to Real-Debrid first
            - Permanently removes the torrent from your account
            - Cannot be undone - torrent must be re-added if needed again

        Example:
            >>> torrent.removeTorrentDownload()
            >>> # Torrent removed from Real-Debrid account
        """
        self.RD.torrents.delete(self['id'])
        logging.info(f"Removed RD download {self['info']['filename']}")

    def downloadToLocal(self, path: str, unpack: bool = True):
        """
        Download the torrent content to local storage.

        Downloads files from Real-Debrid to the specified local path.
        If the content is a RAR archive, it can optionally be extracted
        during the download process.

        Args:
            path: Local directory path where files should be downloaded
            unpack: Whether to extract RAR archives (default: True)

        Note:
            - Requires the torrent to be fully downloaded on Real-Debrid
            - Skips download if files already exist locally
            - Uses unrestricted download links for high-speed transfers
            - Supports automatic RAR extraction with progress tracking
            - Only downloads the first available file/link

        Raises:
            ValidationError: If Real-Debrid response is invalid
            OSError: If local file operations fail

        Example:
            >>> # Download and extract
            >>> torrent.downloadToLocal("./downloads/movie", unpack=True)
            >>>
            >>> # Download RAR only (don't extract)
            >>> torrent.downloadToLocal("./archives", unpack=False)
        """
        if 'info' in self and 'links' in self['info']:
            self['links'] = self['info']['links']

        if os.path.exists(path):
            logger.info(f"Skipping download: path exists ('{path}')")
            return
        if 'info' in self and 'status' in self['info'] and self['info']['status'] != 'downloaded':
            logger.info(f"Skipping local download: Not done yet")
            return
        if 'links' not in self:
            logger.info(f"Skipping local download: No download links exist")
            return

        response = self.RD.unrestrict.link(self['links'][0])
        link = None
        try:
            dict = json5.loads(response.text)
            link = dict['download']
        except json.JSONDecodeError as e:
            raise ValidationError(e) from e

        # Basic usage - download and extract large file
        downloader = RarDownloader(chunk_size=1024 * 1024)  # 1MB chunks

        dl_result = downloader.download_and_extract(
            url=link,
            extract_to=path,
            download_to=path,
            keep_rar=False,
            unpack=unpack
        )
