# Changelog - Real-Debrid Integration

## Recent Updates (v2.0.0) - Real-Debrid Integration

### Major Features Added

#### 1. Real-Debrid Premium Download Integration
- **NEW**: Full integration with Real-Debrid API for premium torrent downloading
- **NEW**: Automatic torrent-to-direct-link conversion
- **NEW**: Local download with automatic RAR extraction
- **NEW**: Progress tracking and status monitoring

#### 2. High-Level Search Interface
- **NEW**: `Search` class providing simplified media search methods:
  - `Search.MusicAlbum(artist, album)` - Smart music album search with quality fallback (FLAC → MP3 → general)
  - `Search.MusicArtist(artist)` - Artist discography search
  - `Search.Movie(movie, year)` - Movie search with quality/language preferences
- **NEW**: Progressive search strategies with automatic fallback
- **NEW**: Background task processing for non-blocking downloads

#### 3. Enhanced Torrent Metadata
- **NEW**: `TorrentBase` class - Rich torrent object with download capabilities
- **NEW**: Methods: `fetch_details()`, `startDebridDownload()`, `downloadToLocal()`, `updateInfo()`
- **NEW**: Automatic magnet link generation from hash
- **NEW**: Support for multiple naming conventions (name, filename, title)

#### 4. Background Task Management
- **NEW**: `WorkerGovernor` class for managing concurrent downloads
- **NEW**: Configurable worker pool (default: 2 workers)
- **NEW**: Thread-safe job queue with status tracking
- **NEW**: Graceful shutdown and completion waiting

#### 5. Provider Enhancements
- **NEW**: JSON5 configuration file support (more flexible than JSON)
- **NEW**: Six pre-configured providers:
  - 1337x.am
  - KickassTorrents
  - EZTV
  - ETTV
  - MagnetDL
  - The Pirate Bay
- **NEW**: Category-based search support

### Files Added

```
torrentsearchengine/
├── debrid/
│   ├── __init__.py
│   └── options.py              # Debrid configuration options
├── torrentbase.py              # 700+ lines - Core torrent class with RD integration
└── result.py                   # TorrentResult wrapper class

util/
├── __init__.py
└── background.py               # WorkerGovernor for background tasks

search.py                       # High-level search interface (388 lines)

sites/                          # Provider configurations
├── 1337x.json5
├── kickasstorrents.json5
├── eztv.json5
├── ettv.json
├── magnetdl.json5
├── piratebay.json5
└── PROVIDER_EXAMPLE.md
```

### Files Modified

- `torrentsearchengine/searchengine.py` - Added debrid search, RD integration
- `torrentsearchengine/__init__.py` - Updated exports and documentation
- `torrentsearchengine/providermanager.py` - Enhanced provider management
- `torrentsearchengine/torrentprovider.py` - Provider improvements
- `example.py` - Updated with Real-Debrid usage examples
- `README.md` - Updated installation instructions

### Environment Variables Required

#### `RD_APITOKEN` (Required for Real-Debrid features)
**Description**: Your Real-Debrid API token for authentication

**How to obtain**:
1. Log in to your Real-Debrid account at https://real-debrid.com
2. Navigate to: Account Settings → API
3. Copy your API token

**How to set**:

**Linux/macOS**:
```bash
export RD_APITOKEN="your_api_token_here"
```

**Windows (Command Prompt)**:
```cmd
set RD_APITOKEN=your_api_token_here
```

**Windows (PowerShell)**:
```powershell
$env:RD_APITOKEN="your_api_token_here"
```

**Python .env file** (using python-dotenv):
```
RD_APITOKEN=your_api_token_here
```

**Note**: The `rd_api_py` library automatically reads this environment variable.

### New Dependencies

- `rd_api_py` - Real-Debrid API Python wrapper
- `json5` - JSON5 configuration file parser
- `rarfile` - RAR archive extraction
- `tqdm` - Progress bar for downloads

### Installation

```bash
# Install from GitHub
pip install git+https://github.com/best-testing-monkey/torrent-search-engine-debrid

# Or clone and install locally
git clone https://github.com/best-testing-monkey/torrent-search-engine-debrid.git
cd torrent-search-engine-debrid
pip install -r requirements.txt
```

### Usage Examples

#### Basic Search with Real-Debrid
```python
from torrentsearchengine import TorrentSearchEngine

engine = TorrentSearchEngine()
engine.add_provider('sites/1337x.json5')

# Search torrents
results = engine.search('ubuntu', limit=10)

# Start Real-Debrid download
for torrent in results[:1]:
    torrent.startDebridDownload()
    torrent.updateInfo()
    print(f"Status: {torrent['info']['status']}")
    print(f"Progress: {torrent['info']['progress']}%")
```

#### High-Level Music Album Search
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
```

#### High-Level Movie Search
```python
from search import Search

# Search and download movie
results = Search.Movie(
    movie="Inception",
    year="2010",
    download_wait_for_completion=False
)
```

#### Manual Download Control
```python
from torrentsearchengine.searchengine import TorrentSearchEngine
import time

engine = TorrentSearchEngine()
engine.add_provider('sites/1337x.json5')

results = engine.search('metallica master of puppets', limit=10)

# Start download on Real-Debrid
torrent = results[0]
torrent.startDebridDownload()

# Monitor progress
while torrent['info']['progress'] < 100:
    time.sleep(20)
    torrent.updateInfo()
    status = torrent['info']['status']
    progress = torrent['info']['progress']
    seeders = torrent['info']['seeders']
    print(f"Status: {status} | Progress: {progress}% | Seeders: {seeders}")

# Download to local storage
if torrent['info']['status'] == 'downloaded':
    torrent.downloadToLocal(path="./downloads/music", unpack=True)
```

#### Enable/Disable Debrid
```python
engine = TorrentSearchEngine()

# Debrid is enabled by default
engine.disable_debrid()  # Search only torrent sites

# Re-enable debrid
engine.enable_debrid()   # Search debrid + torrent sites
```

### API Changes

#### TorrentSearchEngine.search()
**New Parameters**:
- `n_threads: int` - Maximum number of threads for searching
- `noremote: bool` - If True, only search Real-Debrid (no remote torrent sites)

**Return Type Changed**:
- Now returns `List[TorrentBase]` instead of `List[Torrent]`

#### New Methods

**TorrentSearchEngine**:
- `enable_debrid()` - Enable Real-Debrid integration
- `disable_debrid()` - Disable Real-Debrid integration
- `_search_debrid(query, category, limit)` - Search only Real-Debrid cache
- `_to_torrentBase_list(torrents)` - Convert to TorrentBase objects

**TorrentBase**:
- `fetch_details(timeout=30)` - Fetch detailed torrent info from provider
- `startDebridDownload()` - Start download via Real-Debrid
- `updateInfo()` - Refresh torrent status from Real-Debrid
- `downloadToLocal(path, unpack=True)` - Download files to local storage
- `removeTorrentDownload()` - Remove torrent from Real-Debrid
- `asdict()` - Convert to dictionary representation

### Configuration

#### Debrid Options
```python
engine = TorrentSearchEngine()

# Configure refresh behavior
engine.debrid_options.refreshEverySearch = True   # Refresh RD cache each search
engine.debrid_options.refreshEverySearch = False  # Cache RD torrent list
```

### Breaking Changes

1. **Return Type**: `TorrentSearchEngine.search()` now returns `List[TorrentBase]` instead of `List[Torrent]`
2. **Dependencies**: Requires `rd_api_py`, `json5`, `rarfile`, `tqdm`
3. **Environment**: Requires `RD_APITOKEN` environment variable for Real-Debrid features

### Bug Fixes

- Fixed seed sorting when seeds are non-numeric
- Improved error handling in provider searches
- Better handling of torrent naming conventions

### Statistics

- **26 files changed**
- **2,158 insertions**, 79 deletions
- **New lines of code**: ~2,100
- **New classes**: 3 (TorrentBase, Search, WorkerGovernor)
- **New provider configs**: 6

### Credits

Original torrent search engine by Alex Covizzi
Real-Debrid integration and enhancements by best-testing-monkey

### License

Apache Software License (unchanged)
