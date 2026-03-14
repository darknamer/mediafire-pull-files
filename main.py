"""
MediaFire folder downloader.

Downloads all files from a MediaFire folder (or account path), recreating
the same directory structure locally. Uses the official mediafire Python SDK.
"""

from __future__ import print_function

import argparse
import os
import re
import sys

from dotenv import load_dotenv
from mediafire.client import MediaFireClient, File, Folder

# Load .env from current directory (or parent) so MEDIAFIRE_* are available
load_dotenv()


# MediaFire folder URL pattern: https://www.mediafire.com/folder/<folder_key>/<optional_name>
MEDIAFIRE_FOLDER_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?mediafire\.com/folder/([a-zA-Z0-9]+)",
    re.IGNORECASE,
)


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

    # Already a mediafire URI
    if identifier.startswith("mf:"):
        return identifier

    # URL: extract folder_key
    match = MEDIAFIRE_FOLDER_URL_PATTERN.search(identifier)
    if match:
        folder_key = match.group(1)
        return "mf:{}".format(folder_key)

    # Path-style (root folder by path)
    if identifier.startswith("/"):
        return "mf://" + identifier

    # Assume folder key (13 chars) or path without leading slash
    if len(identifier) == 13 and identifier.isalnum():
        return "mf:{}".format(identifier)

    return "mf:///" + identifier.lstrip("/")


def _folder_display_name(identifier, uri, index):
    """Derive a safe subdir name for a folder (for multi-folder download)."""
    # From URL path: .../folder/KEY/FolderName -> use FolderName
    match = MEDIAFIRE_FOLDER_URL_PATTERN.search(identifier)
    if match:
        # URL like https://www.mediafire.com/folder/1z3vk56tf787k/ImageBasedAttendance
        parts = identifier.rstrip("/").split("/")
        if len(parts) > 0 and parts[-1] and parts[-1] != match.group(1):
            name = parts[-1].strip()
            if name:
                return _sanitize_dirname(name)
        return _sanitize_dirname(match.group(1))  # folder key
    # mf:folderkey or mf:///Path -> use key or last path segment
    if uri.startswith("mf:"):
        key = uri[3:].split("/")[0]
        return _sanitize_dirname(key) if key else "folder_{}".format(index)
    # mf:///Path/To/Folder
    path = uri.replace("mf://", "").strip("/")
    return _sanitize_dirname(path.split("/")[-1] or "folder_{}".format(index))


def _sanitize_dirname(name):
    """Make a string safe for use as a directory name."""
    # Remove or replace chars that are invalid in dir names
    for c in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0'):
        name = name.replace(c, "_")
    return name.strip(". ") or "folder"


def parse_folder_identifiers(raw):
    """
    Parse a string into a list of (folder_uri, display_name) for multi-folder download.

    Supports comma- and newline-separated values. Strips whitespace and skips empty entries.
    """
    if not raw or not raw.strip():
        return []
    # Split by comma and newline, strip, drop empty
    parts = []
    for s in re.split(r"[\n,]+", raw):
        s = s.strip()
        if s:
            parts.append(s)
    result = []
    for i, identifier in enumerate(parts):
        uri = parse_folder_identifier(identifier)
        if uri:
            name = _folder_display_name(identifier, uri, i)
            result.append((uri, name))
    return result


def download_folder(client, folder_uri, local_base_path, verbose=True):
    """
    Recursively download all files from a MediaFire folder into local_base_path,
    creating subdirectories to match the remote structure.

    Args:
        client: MediaFireClient instance (logged in).
        folder_uri: MediaFire folder URI (e.g. mf:folderkey or mf:///Path).
        local_base_path: Local directory path to write files into.
        verbose: If True, print each file/folder action.
    """
    os.makedirs(local_base_path, exist_ok=True)

    for item in client.get_folder_contents_iter(folder_uri):
        if isinstance(item, File):
            file_uri = "mf:{}".format(item["quickkey"])
            filename = item["filename"]
            local_path = os.path.join(local_base_path, filename)
            if verbose:
                print("Downloading: {}".format(local_path))
            try:
                client.download_file(file_uri, local_path)
            except Exception as e:
                print("Error downloading {}: {}".format(filename, e), file=sys.stderr)
        elif isinstance(item, Folder):
            folder_name = item["name"]
            sub_uri = "mf:{}".format(item["folderkey"])
            sub_path = os.path.join(local_base_path, folder_name)
            if verbose:
                print("Entering folder: {}".format(sub_path))
            download_folder(client, sub_uri, sub_path, verbose=verbose)
        else:
            if verbose:
                print("Skipping unknown item: {}".format(type(item)), file=sys.stderr)


def main():
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
    args = parser.parse_args()

    # Build list of (folder_uri, display_name): from CLI list or MEDIAFIRE_FOLDER (comma/newline separated)
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
    verbose = not args.quiet

    for folder_uri, display_name in folders:
        # Single folder: download into output_base; multiple: output_base/display_name/
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
            download_folder(client, folder_uri, local_path, verbose=verbose)
        except Exception as e:
            print("Download failed for {}: {}".format(folder_uri, e), file=sys.stderr)
            sys.exit(1)

    if verbose:
        print("Done.")


if __name__ == "__main__":
    main()
