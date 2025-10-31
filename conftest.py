"""
Pytest configuration for torrent_search tests.
This file ensures the torrent_search directory is properly set up for testing.
"""

import sys
import os

# Add the torrent_search directory to Python path
torrent_search_dir = os.path.dirname(__file__)
if torrent_search_dir not in sys.path:
    sys.path.insert(0, torrent_search_dir)