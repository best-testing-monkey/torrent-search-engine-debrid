import json
import logging
import os
from urllib.parse import unquote
import rarfile
import requests
from pathlib import Path
from tqdm import tqdm
import tempfile
import shutil

logger = logging.getLogger(__name__)

class RarDownloader:
    def __init__(self, chunk_size=8192, timeout=30):
        self.chunk_size = chunk_size
        self.timeout = timeout

    def download_and_extract(self, url, extract_to=None, download_to=None,
                             keep_rar=False, headers=None, verify_ssl=True, unpack=True):
        """
        Download and extract a large RAR file with progress bar

        Args:
            url: URL to download from
            extract_to: Directory to extract files to
            download_to: Directory to download RAR file to (default: temp)
            keep_rar: Whether to keep the RAR file after extraction
            headers: Custom headers for the request
            verify_ssl: Whether to verify SSL certificates

        Returns:
            tuple: (success: bool, rar_path: str or None)
        """
        # Set up directories
        if extract_to is None:
            extract_to = Path.cwd() / "extracted"
        else:
            extract_to = Path(extract_to)

        extract_to.mkdir(parents=True, exist_ok=True)

        # Determine where to save the RAR file
        if download_to is None:
            # Use temporary directory
            temp_dir = tempfile.mkdtemp()
            filename = self._get_filename_from_url(url)
            rar_path = Path(temp_dir) / filename
            cleanup_rar = True
        else:
            download_to = Path(download_to)
            download_to.mkdir(parents=True, exist_ok=True)
            filename = self._get_filename_from_url(url)
            rar_path = download_to / filename
            cleanup_rar = not keep_rar

        session = requests.Session()
        if headers:
            session.headers.update(headers)

        try:
            # Download with progress bar
            logger.info("Downloading %s from %s", filename, url)
            success = self._download_with_progress(session, url, rar_path, verify_ssl)

            if not success:
                return False, None

            if not unpack:
                return False, None

            # Extract using rarfile
            logger.info("Extracting RAR file...")
            with rarfile.RarFile(rar_path) as rf:
                # if password:
                #     rf.setpassword(password)

                # List contents
                logger.debug("Contents:")
                for info in rf.infolist():
                    logger.debug("  %s", info.filename)

                # Extract all
                rf.extractall(path=str(extract_to))

            # Cleanup if needed
            if cleanup_rar and not keep_rar:
                rar_path.unlink()
                if download_to is None:  # Remove temp directory
                    shutil.rmtree(temp_dir)
                return True, None
            else:
                return True, str(rar_path)

        except requests.exceptions.RequestException as e:
            logger.error("✗ Download error: %s", e)
            return False, None
        except Exception as e:
            logger.error("✗ Extraction error: %s", e)
            return False, None
        finally:
            session.close()

    def _download_with_progress(self, session, url, file_path, verify_ssl):
        """Download file with progress bar, streaming to disk"""
        try:
            # Get file size for progress bar
            head_response = session.head(url, verify=verify_ssl, timeout=self.timeout)
            total_size = int(head_response.headers.get('content-length', 0))

            # Start the actual download
            response = session.get(url, stream=True, verify=verify_ssl, timeout=self.timeout)
            response.raise_for_status()

            # Update total size if not available from HEAD request
            if total_size == 0:
                total_size = int(response.headers.get('content-length', 0))

            # Create progress bar
            progress_bar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc=file_path.name,
                ncols=80
            )

            # Stream download to file
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        file.write(chunk)
                        progress_bar.update(len(chunk))

            progress_bar.close()

            # Verify file was downloaded completely
            downloaded_size = file_path.stat().st_size
            if total_size > 0 and downloaded_size != total_size:
                logger.warning("✗ Warning: Expected %d bytes, got %d", total_size, downloaded_size)

            return True

        except Exception as e:
            logger.error("✗ Download failed: %s", e)
            return False

    def _get_filename_from_url(self, url):
        """Extract filename from URL or generate one"""
        filename = url.split('/')[-1]
        if not filename or '.' not in filename:
            filename = "downloaded_file.rar"
        elif not filename.lower().endswith('.rar'):
            filename += '.rar'
        filename = unquote(filename)
        return filename

    def download_only(self, url, download_to, headers=None, verify_ssl=True):
        """Download RAR file only, without extracting"""
        download_to = Path(download_to)
        download_to.mkdir(parents=True, exist_ok=True)

        filename = self._get_filename_from_url(url)
        rar_path = download_to / filename

        session = requests.Session()
        if headers:
            session.headers.update(headers)

        try:
            success = self._download_with_progress(session, url, rar_path, verify_ssl)
            return success, str(rar_path) if success else None
        finally:
            session.close()

# Usage examples
if __name__ == "__main__":
    downloader = RarDownloader(chunk_size=1024 * 1024)  # 1MB chunks for large files

    # Example 1: Download and extract, remove RAR after
    url = "https://example.com/large_file.rar"
    success, rar_path = downloader.download_and_extract(
        url=url,
        extract_to="./extracted_files",
        keep_rar=False
    )

    if success:
        logger.info("✓ Download and extraction completed successfully!")
    else:
        logger.error("✗ Failed to download or extract")

    # Example 2: Download to specific location and keep RAR
    success, rar_path = downloader.download_and_extract(
        url=url,
        extract_to="./extracted_files",
        download_to="./downloads",
        keep_rar=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )

    if success:
        logger.info("✓ RAR file saved to: %s", rar_path)

    # Example 3: Download only (no extraction)
    success, rar_path = downloader.download_only(
        url=url,
        download_to="./downloads"
    )

    if success:
        logger.info("✓ RAR file downloaded to: %s", rar_path)
        # Extract later manually if needed
        # patoolib.extract_archive(rar_path, outdir="./extracted_files")
