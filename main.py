"""
MediaFire folder downloader.

Downloads all files from a MediaFire folder (or account path), recreating
the same directory structure locally. Uses the official mediafire Python SDK.

Supports:
- Single or multiple folder URLs (comma/newline-separated in env or as CLI args)
- Multi-threaded downloads (thread count defaults to CPU count)
- Credentials and options via .env or CLI
"""

from __future__ import print_function

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import argparse
import hashlib
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

import requests
from dotenv import load_dotenv
from mediafire.client import MediaFireClient, File, Folder
from mediafire.client import DownloadError as MediaFireDownloadError

# Load .env from current directory (or parent) so MEDIAFIRE_* are available
load_dotenv()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Regex to extract folder_key from MediaFire folder URL
# Example: https://www.mediafire.com/folder/<folder_key>/<optional_name>
MEDIAFIRE_FOLDER_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?mediafire\.com/folder/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)

# Keys to look for in file/get_links response (API may return normal_download only)
DOWNLOAD_LINK_KEYS = ("direct_download", "normal_download", "download")

# Regex to find direct file URL in MediaFire normal_download HTML page
MEDIAFIRE_DIRECT_URL_IN_HTML = re.compile(
    r"https?://download\d*\.mediafire\.com/[^\s\"'<>]+",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Folder / path parsing
# ---------------------------------------------------------------------------
def parse_folder_identifier(identifier):
    """
    Parse user input into a MediaFire folder URI.

    Accepts:
    - MediaFire folder URL: https://www.mediafire.com/folder/ABC123/Name
    - Folder key only: ABC123 (13 chars)
    - Full URI: mf:ABC123 or mf:///Path/To/Folder

    Returns:
        str: MediaFire URI (e.g. mf:ABC123 or mf:///Path)
    """
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    # Already a MediaFire URI (e.g. mf:abc123 or mf:///Path)
    if identifier.startswith("mf:"):
        return identifier

    # Full URL: extract folder_key and return mf:<key>
    match = MEDIAFIRE_FOLDER_URL_PATTERN.search(identifier)
    if match:
        folder_key = match.group(1)
        return "mf:{}".format(folder_key)

    # Path-style for account root (e.g. /Documents)
    if identifier.startswith("/"):
        return "mf://" + identifier

    # 13-char alphanumeric is treated as folder_key; else as path
    if len(identifier) == 13 and identifier.isalnum():
        return "mf:{}".format(identifier)

    return "mf:///" + identifier.lstrip("/")


def _folder_display_name(identifier, uri, index):
    """
    Derive a safe subdir name for a folder (for multi-folder download).
    Prefers human-readable name from URL/path; falls back to folder_key or folder_N.
    """
    # From URL: .../folder/KEY/FolderName -> use FolderName if present
    match = MEDIAFIRE_FOLDER_URL_PATTERN.search(identifier)
    if match:
        parts = identifier.rstrip("/").split("/")
        # Last path segment is folder name if it differs from folder_key
        if len(parts) > 0 and parts[-1] and parts[-1] != match.group(1):
            name = parts[-1].strip()
            if name:
                return _sanitize_dirname(name)
        return _sanitize_dirname(match.group(1))  # use folder_key as name
    # URI is mf:key or mf:key/... -> use key or first segment
    if uri.startswith("mf:"):
        key = uri[3:].split("/")[0]
        return _sanitize_dirname(key) if key else "folder_{}".format(index)
    # URI is mf:///Path/To/Folder -> use last path segment
    path = uri.replace("mf://", "").strip("/")
    return _sanitize_dirname(path.split("/")[-1] or "folder_{}".format(index))


def _sanitize_dirname(name):
    """Make a string safe for use as a directory name (Windows/Unix)."""
    for c in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0'):
        name = name.replace(c, "_")
    return name.strip(". ") or "folder"


# ---------------------------------------------------------------------------
# Listing and downloading
# ---------------------------------------------------------------------------
def _default_worker_count():
    """Return default number of download threads (CPU logical cores, or 4 if unknown)."""
    n = os.cpu_count()
    return max(1, n) if n is not None else 4


def _get_download_url_from_links(result):
    """
    Extract download URL from file/get_links API response.
    Tries direct_download, then normal_download, then download. Returns None if not found.
    """
    raw = result.get("links")
    if not raw:
        return None
    first = raw[0] if isinstance(raw, list) and raw else (raw if isinstance(raw, dict) else None)
    if not isinstance(first, dict):
        return None
    for key in DOWNLOAD_LINK_KEYS:
        url = first.get(key)
        if url and isinstance(url, str) and url.startswith("http"):
            return url
    for v in first.values():
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def _extract_direct_url_from_html(html_text):
    """
    Extract MediaFire direct download URL from normal_download page HTML.
    Returns first match of https://download*.mediafire.com/... or None.
    """
    if not html_text:
        return None
    match = MEDIAFIRE_DIRECT_URL_IN_HTML.search(html_text)
    return match.group(0) if match else None


def _download_file_safe(client, file_uri, local_path):
    """
    Download file using API link; supports both direct_download and normal_download.
    Same behavior as client.download_file but does not assume 'direct_download' key.
    """
    resource = client.get_resource_by_uri(file_uri)
    if not isinstance(resource, File):
        raise MediaFireDownloadError("Only files can be downloaded")

    quick_key = resource["quickkey"]
    result = client.api.file_get_links(quick_key=quick_key, link_type="direct_download")
    download_url = _get_download_url_from_links(result)
    if not download_url:
        result = client.api.file_get_links(quick_key=quick_key)
        download_url = _get_download_url_from_links(result)
    if not download_url:
        raise MediaFireDownloadError(
            "No download link in API response for quick_key={}".format(quick_key)
        )
    download_url = download_url.replace("http:", "https:")

    name = resource["filename"]
    if (os.path.exists(local_path) and os.path.isdir(local_path)) or local_path.endswith("/"):
        local_path = os.path.join(local_path, name)
    parent = os.path.dirname(local_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    response = requests.get(download_url, stream=True)
    response.raise_for_status()

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "text/html" in content_type:
        # normal_download URL returned a page; try to extract direct file URL from HTML
        html_body = response.text
        direct_url = _extract_direct_url_from_html(html_body)
        if direct_url:
            direct_url = direct_url.replace("http:", "https:")
            response = requests.get(direct_url, stream=True)
            response.raise_for_status()
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" in content_type:
                direct_url = None
        if not direct_url:
            raise MediaFireDownloadError(
                "Download URL returned a web page (HTML) and no direct file link found. "
                "Check file permissions on MediaFire."
            )
    else:
        direct_url = None  # already have binary response

    checksum = hashlib.sha256()
    with open(local_path, "wb") as out_fd:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                out_fd.write(chunk)
                checksum.update(chunk)

    checksum_hex = checksum.hexdigest().lower()
    if checksum_hex != resource["hash"]:
        try:
            os.remove(local_path)
        except OSError:
            pass
        raise MediaFireDownloadError(
            "Hash mismatch ({} != {})".format(resource["hash"], checksum_hex)
        )


def list_all_files(client, folder_uri, local_base_path):
    """
    Recursively list all files under a MediaFire folder.
    Yields (file_uri, local_path) for each file (no download).
    """
    os.makedirs(local_base_path, exist_ok=True)
    for item in client.get_folder_contents_iter(folder_uri):
        if isinstance(item, File):
            file_uri = "mf:{}".format(item["quickkey"])
            filename = item["filename"]
            local_path = os.path.join(local_base_path, filename)
            yield (file_uri, local_path)
        elif isinstance(item, Folder):
            # Recurse into subfolder and yield all files inside
            folder_name = item["name"]
            sub_uri = "mf:{}".format(item["folderkey"])
            sub_path = os.path.join(local_base_path, folder_name)
            for file_uri, local_path in list_all_files(client, sub_uri, sub_path):
                yield (file_uri, local_path)


def _download_one_file(client_pool, file_uri, local_path, verbose):
    """
    Download a single file using a client from the pool (thread-safe).
    Borrows a client from the queue, downloads, then returns it.
    """
    client = client_pool.get()
    try:
        parent = os.path.dirname(local_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if verbose:
            print("Downloading: {}".format(local_path))
        _download_file_safe(client, file_uri, local_path)
    finally:
        client_pool.put(client)  # always return client to pool


def parse_folder_identifiers(raw):
    """
    Parse a string into a list of (folder_uri, display_name) for multi-folder download.
    Supports comma- and newline-separated values; strips whitespace and skips empty.
    """
    if not raw or not raw.strip():
        return []
    parts = [s.strip() for s in re.split(r"[\n,]+", raw) if s.strip()]
    result = []
    for i, identifier in enumerate(parts):
        uri = parse_folder_identifier(identifier)
        if uri:
            name = _folder_display_name(identifier, uri, i)
            result.append((uri, name))
    return result


def download_folder(
    client,
    folder_uri,
    local_base_path,
    verbose=True,
    client_pool=None,
    max_workers=None,
):
    """
    Recursively download all files from a MediaFire folder into local_base_path,
    creating subdirectories to match the remote structure.

    If client_pool and max_workers are set, files are downloaded in parallel using
    a thread pool (one client per worker). Otherwise downloads are sequential.
    """
    # First pass: list all files recursively (no download yet)
    file_list = list(list_all_files(client, folder_uri, local_base_path))

    if not file_list:
        return

    if client_pool is not None and max_workers is not None and max_workers >= 1:
        # Parallel: submit each file to thread pool; workers share client pool
        workers = min(max_workers, len(file_list))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _download_one_file, client_pool, file_uri, local_path, verbose
                ): (file_uri, local_path)
                for file_uri, local_path in file_list
            }
            for future in as_completed(futures):
                file_uri, local_path = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(
                        "Error downloading {}: {}".format(local_path, e),
                        file=sys.stderr,
                    )
                    raise
    else:
        # Sequential: single client, one file at a time
        for file_uri, local_path in file_list:
            parent = os.path.dirname(local_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            if verbose:
                print("Downloading: {}".format(local_path))
            try:
                _download_file_safe(client, file_uri, local_path)
            except Exception as e:
                print(
                    "Error downloading {}: {}".format(os.path.basename(local_path), e),
                    file=sys.stderr,
                )
                raise


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    """Parse arguments, create client(s), and download each requested folder."""
    parser = argparse.ArgumentParser(
        description="Download all files from a MediaFire folder, preserving directory structure."
    )
    parser.add_argument(
        "folder",
        nargs="*",
        default=None,
        help=(
            "One or more MediaFire folders: URL, folder key (13 chars), or path. "
            "Can also set MEDIAFIRE_FOLDER (comma- or newline-separated for multiple)."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=os.environ.get("MEDIAFIRE_OUTPUT", "./downloads"),
        help="Local directory to save files into (default: ./downloads). Can set MEDIAFIRE_OUTPUT.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Reduce output (only errors).",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("MEDIAFIRE_EMAIL"),
        help="MediaFire account email (or MEDIAFIRE_EMAIL).",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("MEDIAFIRE_PASSWORD"),
        help="MediaFire account password (or MEDIAFIRE_PASSWORD).",
    )
    parser.add_argument(
        "--app-id",
        default=os.environ.get("MEDIAFIRE_APP_ID", "42511"),
        help="MediaFire App ID (default: 42511). Can set MEDIAFIRE_APP_ID.",
    )
    # Default thread count from env (optional); None means use CPU count later
    try:
        default_threads = os.environ.get("MEDIAFIRE_THREADS")
        default_t = int(default_threads) if default_threads else None
    except (TypeError, ValueError):
        default_t = None
    parser.add_argument(
        "-j",
        "--threads",
        type=int,
        default=default_t,
        metavar="N",
        help=(
            "Number of download threads (default: CPU count). "
            "Set MEDIAFIRE_THREADS or use -j N."
        ),
    )
    args = parser.parse_args()

    # Resolve folder list: CLI args or MEDIAFIRE_FOLDER (comma/newline separated)
    if args.folder:
        raw = ",".join(args.folder) if len(args.folder) > 1 else args.folder[0]
    else:
        raw = os.environ.get("MEDIAFIRE_FOLDER", "")
    folders = parse_folder_identifiers(raw)

    if not folders:
        print(
            "Error: No folder specified. Pass one or more MediaFire URLs/keys, or set MEDIAFIRE_FOLDER "
            "(comma- or newline-separated for multiple).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.email or not args.password:
        print(
            "Error: MediaFire credentials required. Set MEDIAFIRE_EMAIL and MEDIAFIRE_PASSWORD "
            "or use --email and --password.",
            file=sys.stderr,
        )
        sys.exit(1)

    verbose = not args.quiet
    n_workers = args.threads if args.threads is not None else _default_worker_count()
    n_workers = max(1, n_workers)

    # When using multiple threads, create one logged-in client per worker (thread-safe)
    client_pool = None
    if n_workers > 1:
        client_pool = Queue()
        for _ in range(n_workers):
            c = MediaFireClient()
            try:
                c.login(
                    email=args.email,
                    password=args.password,
                    app_id=args.app_id,
                )
            except Exception as e:
                print("Login failed: {}".format(e), file=sys.stderr)
                sys.exit(1)
            client_pool.put(c)
        if verbose:
            print("Using {} download thread(s).".format(n_workers))

    # One client for folder listing and for sequential downloads when n_workers == 1
    client = MediaFireClient()
    try:
        client.login(
            email=args.email,
            password=args.password,
            app_id=args.app_id,
        )
    except Exception as e:
        print("Login failed: {}".format(e), file=sys.stderr)
        sys.exit(1)

    output_base = os.path.abspath(args.output)

    for folder_uri, display_name in folders:
        # One folder -> save directly to output_base; multiple -> output_base/display_name/
        if len(folders) == 1:
            local_path = output_base
            if verbose:
                print("Folder URI: {}".format(folder_uri))
                print("Output dir: {}".format(local_path))
        else:
            local_path = os.path.join(output_base, display_name)
            if verbose:
                print("Folder URI: {}".format(folder_uri))
                print("Output dir: {}".format(local_path))

        try:
            download_folder(
                client,
                folder_uri,
                local_path,
                verbose=verbose,
                client_pool=client_pool,
                max_workers=n_workers if client_pool else None,
            )
        except Exception as e:
            print("Download failed for {}: {}".format(folder_uri, e), file=sys.stderr)
            sys.exit(1)

    if verbose:
        print("Done.")


if __name__ == "__main__":
    main()
