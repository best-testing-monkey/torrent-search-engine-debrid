# torrent-search-engine-debrid

Python library to search torrents from multiple websites with Real-Debrid premium integration.

# About
This Python library allows you to search torrents by scraping torrent websites and integrate with Real-Debrid for premium torrent downloading. Features include:

- **Multi-provider torrent searching** - Search across multiple torrent sites simultaneously
- **Real-Debrid integration** - Premium torrent-to-direct-link conversion
- **Automatic downloads** - Background task processing with progress tracking
- **Local storage** - Download files locally with automatic RAR extraction
- **High-level API** - Simple methods for music, movies, and TV shows

You can add websites to scrape by providing a configuration file (see Provider File section below).

# Usage

## Requirements
- Python 3.5 or higher
- Real-Debrid premium account (for Real-Debrid features)
- Dependencies: `requests`, `beautifulsoup4`, `jsonschema`, `rd_api_py`, `json5`, `rarfile`, `tqdm`

## Installation
You can install this library from Github using this command:

```bash
$ pip install git+https://github.com/best-testing-monkey/torrent-search-engine-debrid
```

## Environment Variables

### `RD_APITOKEN` (Required for Real-Debrid features)
Your Real-Debrid API token for authentication.

**How to obtain your API token:**
1. Log in to your Real-Debrid account at https://real-debrid.com
2. Go to: Account Settings → API
3. Copy your API token

**How to set the environment variable:**

**Linux/macOS:**
```bash
export RD_APITOKEN="your_api_token_here"
```

**Windows (Command Prompt):**
```cmd
set RD_APITOKEN=your_api_token_here
```

**Windows (PowerShell):**
```powershell
$env:RD_APITOKEN="your_api_token_here"
```

**Python .env file:**
```
RD_APITOKEN=your_api_token_here
```

## Examples

### Basic Torrent Search

```python
from torrentsearchengine import TorrentSearchEngine

search_engine = TorrentSearchEngine()
# add torrent provider from a file or url
search_engine.add_provider('sites/1337x.json5')
search_engine.add_provider('sites/piratebay.json5')

# perform the query and find max 50 results
results = search_engine.search('ubuntu', limit=50)

# retrieve the details of the first result
details = results[0].fetch_details()

# get the magnet from the details
magnet = details.link
print(f"Magnet: {magnet}")
```

### Real-Debrid Integration

```python
from torrentsearchengine import TorrentSearchEngine
import time

# Initialize engine (RD_APITOKEN env variable must be set)
engine = TorrentSearchEngine()
engine.add_provider('sites/1337x.json5')

# Search for torrents
results = engine.search('metallica master of puppets', limit=10)

# Start Real-Debrid download
torrent = results[0]
torrent.startDebridDownload()

# Monitor download progress
while torrent['info']['progress'] < 100:
    time.sleep(20)
    torrent.updateInfo()
    print(f"Status: {torrent['info']['status']}")
    print(f"Progress: {torrent['info']['progress']}%")
    print(f"Seeders: {torrent['info']['seeders']}")

# Download to local storage with automatic extraction
if torrent['info']['status'] == 'downloaded':
    torrent.downloadToLocal(path="./downloads/music", unpack=True)
```

### High-Level API for Music

```python
from search import Search

# Search and download music album
# Automatically tries: FLAC → MP3 → general → discography
results = Search.MusicAlbum(
    artist="Pink Floyd",
    album="Dark Side of the Moon",
    download_wait_for_completion=True,
    save_path="./downloads/music"
)

# Wait for background downloads to complete
Search.wait_for_background_tasks()
```

### High-Level API for Movies

```python
from search import Search

# Search and download movie
results = Search.Movie(
    movie="Inception",
    year="2010",
    download_wait_for_completion=True
)
```

## Features

### Real-Debrid Integration
- **Instant downloads** - Convert torrents to direct download links
- **Premium speeds** - Download at maximum speed without seeding
- **Cached torrents** - Instantly access popular torrents already cached by Real-Debrid
- **Progress tracking** - Monitor download status and progress in real-time
- **Automatic extraction** - RAR files are automatically extracted during download

### Multi-Provider Search
- Search across multiple torrent sites simultaneously
- Multi-threaded execution for fast results
- Built-in providers: 1337x, KickassTorrents, EZTV, ETTV, MagnetDL, The Pirate Bay
- Easy to add custom providers via JSON5 configuration

### High-Level Search API
- `Search.MusicAlbum()` - Progressive quality search (FLAC → MP3 → general)
- `Search.MusicArtist()` - Full discography search
- `Search.Movie()` - Multi-language and quality preferences
- Background task processing for non-blocking downloads

### Torrent Management
- Category-based searching
- Detailed metadata (seeds, leeches, size, files, etc.)
- Enable/disable providers dynamically
- Result sorting by seeders

## Provider File
You can add torrent providers from JSON or JSON5 files (or URLs to these files).

**Note**: JSON5 format is now supported, allowing comments and more flexible syntax.

You can find an explained example of provider file in [sites/PROVIDER_EXAMPLE.md](sites/PROVIDER_EXAMPLE.md)

### Structure

The torrent provider json file has the following structure:

- **name** _(required)_ - The name (and identifier) of the torrent provider.

- **fullname** _(optional)_ - The full name of the torrent provider, this is the diplayed name. Defaults to the **name**.
    
- **url** _(required)_ - The base url of the torrent provider.

- **headers** _(optional)_ - HTTP headers to use in the requests to this website.

- **search** _(required)_ - The search path relative to the base url.

- **whitespace** _(optional)_ - The whitespaces in the query are replaced with this character (by default they are replace with %20).
    
    The path needs to include the search query as a variable using the keyword: `{query}`.

- **list** _(required)_ - This property defines how to scrape the data from the torrent provider.

    It includes the following properties:

    - **items** _(required)_ - The CSS selector that selects all the torrent html elements (e.g the rows of a table).

    - **next** _(optional)_ - The CSS selector that selects the link to the next page.
    
    - **item** _(required)_ - This property defines the selectors to scrape the data from a the torrent html element.

        The attributes currently supported are:

        - **name** _(required)_ - Name of the torrent.
        - **url** _(optional)_ - Link to the page of the torrent.
        - **size** _(optional)_ - Size of the torrent.
        - **seeds** _(optional)_ - Number of seeders of this torrent (the selected value must be an **integer**).
        - **leechers** _(optional)_ - Number of leechers of this torrent (the selected value must be an **integer**).

- **item** _(optional)_ - This property defines how to scrape the data from the torrent page (the page linked by the **url** torrent attribute).


### Torrent's properties

The torrent's properties currently supported are:
- **name** _(required)_ - Name of the torrent. This selector has to be defined in `list.item`.
- **url** _(optional)_ - Link to the page of the torrent. This selector has to be defined in `list.item`.
- **link** _(required)_ - Link to magnet or .torrent file. This need to be defined either in `list.item` or in `item`.
- **size** _(optional)_ - Size of the torrent.
- **seeds** _(optional)_ - Number of seeders of this torrent (the selected value must be an **integer**).
- **leechers** _(optional)_ - Number of leechers of this torrent (the selected value must be an **integer**).
- **time** _(optional)_ - Time of the torrent.
- **infohash** _(optional)_ - INFOHASH of te torrent.
- **files** _(optional)_ - List of files in the torrent.
- **trackers** _(optional)_ - List of trackers in the torrent.
- **description** _(optional)_ - Description of the torrent.
- **uploader** _(optional)_ - The name of the user that uploaded the torrent.
- **uploader_url** _(optional)_ - The link to the page of the user that uploaded the torrent.


### Selector

The selector used to select the torrent data has the following structure:

```
<CSS selector> @ <html attribute> | re: <regex matcher> | fmt: <regex formatter>
```
The default html attribute is `text` (the inner text of the html element selected).

The options `re` and `fmt` are optional, their job is to select only part of the text or format the text, you can use regex capturing groups in `re` and `fmt`.



