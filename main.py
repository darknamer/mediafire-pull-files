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
        nargs="?",
        default=os.environ.get("MEDIAFIRE_FOLDER", ""),
        help=(
            "MediaFire folder: URL (e.g. https://www.mediafire.com/folder/KEY/Name), "
            "folder key (13 chars), or path (e.g. /Documents). "
            "Can also be set via MEDIAFIRE_FOLDER."
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

    folder_uri = parse_folder_identifier(args.folder)
    if not folder_uri:
        print("Error: No folder specified. Pass a MediaFire URL, folder key, or path.", file=sys.stderr)
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

    output = os.path.abspath(args.output)
    if not args.quiet:
        print("Folder URI: {}".format(folder_uri))
        print("Output dir: {}".format(output))

    try:
        download_folder(client, folder_uri, output, verbose=not args.quiet)
    except Exception as e:
        print("Download failed: {}".format(e), file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print("Done.")


if __name__ == "__main__":
    main()
