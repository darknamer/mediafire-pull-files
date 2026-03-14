# MediaFire Pull File

Download all files from a MediaFire folder (or path) to your machine, preserving the same directory structure as on MediaFire.

## Tech stack

- **Backend:** Python 3
- **Library:** [mediafire](https://pypi.org/project/mediafire/) (MediaFire Python Open SDK) for API auth, folder listing, and file download
- **HTTP:** `requests` (dependency of mediafire)

## Features

- Recursively download every file under a MediaFire folder
- Create local subdirectories to mirror MediaFire folder structure
- Support for folder URL, folder key, or account path
- Optional credentials via environment variables or CLI

## Requirements

- Python 3.6+
- MediaFire account (folder listing and download use the Core API and require login)

## Installation

```bash
pip install -r requirements.txt
```

Or:

```bash
pip install mediafire
```

## Configuration

Credentials are required for folder listing. Use either environment variables or CLI arguments.

| Variable / Option   | Description                    | Default   |
|---------------------|--------------------------------|-----------|
| `MEDIAFIRE_EMAIL`   | Account email                  | —         |
| `MEDIAFIRE_PASSWORD`| Account password              | —         |
| `MEDIAFIRE_APP_ID`  | MediaFire App ID               | `42511`   |
| `MEDIAFIRE_FOLDER`  | Default folder (URL/key/path)   | —         |
| `MEDIAFIRE_OUTPUT`  | Default output directory       | `./downloads` |

Example `.env` (copy from `.env.example` and fill in):

```env
MEDIAFIRE_EMAIL=your.email@example.com
MEDIAFIRE_PASSWORD=your_password
MEDIAFIRE_FOLDER=https://www.mediafire.com/folder/XXXXX/MyFolder
MEDIAFIRE_OUTPUT=./downloads
```

To load `.env` in a shell before running (optional):

```bash
# Bash
export $(grep -v '^#' .env | xargs)
python main.py
```

Or pass credentials on the command line (see Usage).

## Usage

```bash
python main.py [FOLDER] [-o OUTPUT] [--email EMAIL] [--password PASSWORD] [--app-id APP_ID] [-q]
```

**FOLDER** can be:

1. **MediaFire folder URL**  
   `https://www.mediafire.com/folder/1z3vk56tf787k/ImageBasedAttendance`  
   The script uses the folder key from the URL.

2. **Folder key** (13 characters)  
   `1z3vk56tf787k`

3. **Account path** (for your own files)  
   `mf:///Documents` or `/Documents`  
   Path is relative to your MediaFire root.

If `FOLDER` is omitted, the script uses `MEDIAFIRE_FOLDER` (if set).

**Examples:**

```bash
# Download folder from URL into ./downloads (credentials from env)
python main.py "https://www.mediafire.com/folder/1z3vk56tf787k/ImageBasedAttendance"

# Download into a specific directory
python main.py "https://www.mediafire.com/folder/KEY/Name" -o ./my_backup

# Credentials on the command line
python main.py 1z3vk56tf787k -o ./out --email you@example.com --password secret

# Use env for folder and output; quiet mode
set MEDIAFIRE_FOLDER=https://www.mediafire.com/folder/KEY/Name
set MEDIAFIRE_OUTPUT=./downloads
python main.py -q
```

## How it works (technical)

1. **Folder identifier**  
   `parse_folder_identifier()` normalizes input to a MediaFire URI:
   - URL → extract folder key → `mf:<folder_key>`
   - 13-char alphanumeric → `mf:<folder_key>`
   - Path (e.g. `/Documents`) → `mf:///Documents`

2. **Authentication**  
   `MediaFireClient.login()` uses `MediaFireApi.user_get_session_token()` with email, password, and app_id. The session token is stored on the API client and used for all later requests.

3. **Folder listing**  
   `client.get_folder_contents_iter(folder_uri)`:
   - Resolves `folder_uri` via `get_resource_by_uri()` (path or key).
   - Calls `folder_get_content` (Core API) for `content_type` `folders` and `files`, with chunking.
   - Yields `File` or `Folder` objects (dict-like with `quickkey`/`filename` or `folderkey`/`name`).

4. **Recursive download**  
   `download_folder(client, folder_uri, local_base_path)`:
   - Ensures `local_base_path` exists.
   - For each `File`: build URI `mf:<quickkey>`, call `client.download_file(uri, local_path)` (uses `file_get_links` and streams to disk; verifies SHA256 when provided).
   - For each `Folder`: build URI `mf:<folderkey>`, create `local_base_path/<name>`, call `download_folder()` recursively.

5. **Directory structure**  
   Local directories are created to match MediaFire: each remote folder becomes a subdirectory under the output path; files are written with their MediaFire filenames.

## Project layout

```
mediafire_pull_file/
├── main.py           # Entry point: CLI, parse folder ID, login, recursive download
├── requirements.txt  # mediafire, requests
├── .env.example      # Example env vars for credentials and defaults
└── README.md         # This file
```

## License

Use and adapt as needed. MediaFire SDK: see [mediafire on PyPI](https://pypi.org/project/mediafire/) and its license (BSD).
