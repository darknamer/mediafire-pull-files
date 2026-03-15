"""
Unit tests for main.py (MediaFire folder downloader).

Tests pure functions and behavior with mocked MediaFire client, requests, and I/O.
No changes to main.py logic; coverage via pytest and pytest-cov.
"""

from __future__ import print_function

import hashlib
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import after potential env so tests don't depend on real .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main as main_module


# ---------------------------------------------------------------------------
# _default_log_filename
# ---------------------------------------------------------------------------
def test_default_log_filename_format():
    name = main_module._default_log_filename()
    assert name.startswith("log-")
    assert name.endswith(".log")
    assert len(name) == len("log-YYYYMMDD.log")  # log- + 8 digits + .log


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------
def test_setup_logging_creates_handlers(tmp_path):
    log_file = str(tmp_path / "test.log")
    main_module.setup_logging(verbose=True, log_file=log_file)
    assert len(main_module.logger.handlers) >= 2  # file + console
    main_module.logger.handlers.clear()


def test_setup_logging_quiet(tmp_path):
    log_file = str(tmp_path / "quiet.log")
    main_module.setup_logging(verbose=False, log_file=log_file)
    main_module.logger.handlers.clear()


# ---------------------------------------------------------------------------
# parse_folder_identifier
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "identifier,expected",
    [
        ("", None),
        (None, None),
        ("   \n  ", None),
        ("https://www.mediafire.com/folder/abc123xyz/MyFolder", "mf:abc123xyz"),
        ("https://mediafire.com/folder/ABC123/Name", "mf:ABC123"),
        ("http://www.mediafire.com/folder/xyz789/", "mf:xyz789"),
        ("mf:abc123", "mf:abc123"),
        ("mf:///Path/To/Folder", "mf:///Path/To/Folder"),
        ("/Documents", "mf:///Documents"),
        ("1z3vk56tf787k", "mf:1z3vk56tf787k"),  # 13-char alphanumeric
        ("some/path", "mf:///some/path"),
    ],
)
def test_parse_folder_identifier(identifier, expected):
    assert main_module.parse_folder_identifier(identifier) == expected


def test_parse_folder_identifier_13_char_not_key_if_not_alnum():
    # 12 chars -> path
    result = main_module.parse_folder_identifier("1z3vk56tf787")
    assert result == "mf:///1z3vk56tf787"
    # 13 chars with space -> path
    result = main_module.parse_folder_identifier("1z3vk56tf78 7")
    assert result is not None and "1z3vk56tf78" in result or "mf://" in result


# ---------------------------------------------------------------------------
# _folder_display_name
# ---------------------------------------------------------------------------
def test_folder_display_name_from_url():
    identifier = "https://www.mediafire.com/folder/abc123/MyFolderName"
    uri = "mf:abc123"
    name = main_module._folder_display_name(identifier, uri, 0)
    assert name == "MyFolderName"


def test_folder_display_name_from_key():
    identifier = "abc123xyz9876"
    uri = "mf:abc123xyz9876"
    name = main_module._folder_display_name(identifier, uri, 0)
    assert name == "abc123xyz9876"


def test_folder_display_name_path_uri():
    # mf:///Path: first segment after "mf:" is empty, so fallback to folder_{index}
    identifier = "/Documents/Backup"
    uri = "mf:///Documents/Backup"
    name = main_module._folder_display_name(identifier, uri, 1)
    assert name == "folder_1"


def test_folder_display_name_fallback():
    identifier = "https://www.mediafire.com/folder/abc123/"
    uri = "mf:abc123"
    name = main_module._folder_display_name(identifier, uri, 0)
    assert name == "abc123"


# ---------------------------------------------------------------------------
# _sanitize_path_component / _sanitize_dirname
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name,expected",
    [
        ("normal", "normal"),
        ("file.txt", "file.txt"),
        ("path/with/slash", "path_with_slash"),
        ("col:on", "col_on"),
        ("star*asterisk", "star_asterisk"),
        ("", "file"),
        ("  dot.  ", "dot"),
        ("a", "a"),
    ],
)
def test_sanitize_path_component(name, expected):
    assert main_module._sanitize_path_component(name) == expected


def test_sanitize_path_component_non_string():
    assert main_module._sanitize_path_component(None) == "file"


def test_sanitize_dirname():
    assert main_module._sanitize_dirname("Folder") == "Folder"
    assert main_module._sanitize_dirname("") == "folder"
    assert main_module._sanitize_dirname(None) == "folder"


# ---------------------------------------------------------------------------
# _default_worker_count
# ---------------------------------------------------------------------------
def test_default_worker_count():
    with patch("main.os.cpu_count", return_value=8):
        assert main_module._default_worker_count() == 8
    with patch("main.os.cpu_count", return_value=1):
        assert main_module._default_worker_count() == 1
    with patch("main.os.cpu_count", return_value=None):
        assert main_module._default_worker_count() == 4


# ---------------------------------------------------------------------------
# _get_download_url_from_links
# ---------------------------------------------------------------------------
def test_get_download_url_from_links_empty():
    assert main_module._get_download_url_from_links({}) is None
    assert main_module._get_download_url_from_links({"links": None}) is None
    assert main_module._get_download_url_from_links({"links": []}) is None


def test_get_download_url_from_links_direct():
    result = {
        "links": [{"direct_download": "https://download123.mediafire.com/abc/file.zip"}]
    }
    assert main_module._get_download_url_from_links(result) == (
        "https://download123.mediafire.com/abc/file.zip"
    )


def test_get_download_url_from_links_normal_download():
    result = {
        "links": [{"normal_download": "https://www.mediafire.com/file/xyz/download"}]
    }
    assert main_module._get_download_url_from_links(result) == (
        "https://www.mediafire.com/file/xyz/download"
    )


def test_get_download_url_from_links_list_order():
    result = {
        "links": [
            {"normal_download": "https://normal.com"},
            {"direct_download": "https://direct.com"},
        ]
    }
    assert main_module._get_download_url_from_links(result) == "https://normal.com"


def test_get_download_url_from_links_dict_form():
    result = {"links": {"direct_download": "https://example.com/f"}}
    assert main_module._get_download_url_from_links(result) == "https://example.com/f"


# ---------------------------------------------------------------------------
# _extract_direct_url_from_html
# ---------------------------------------------------------------------------
def test_extract_direct_url_from_html_empty():
    assert main_module._extract_direct_url_from_html("") is None
    assert main_module._extract_direct_url_from_html(None) is None


def test_extract_direct_url_from_html_found():
    html = 'Click <a href="https://download1234.mediafire.com/xyz/file.bin">here</a>'
    url = main_module._extract_direct_url_from_html(html)
    assert url == "https://download1234.mediafire.com/xyz/file.bin"


def test_extract_direct_url_from_html_no_match():
    html = "<html><body>No mediafire link here</body></html>"
    assert main_module._extract_direct_url_from_html(html) is None


# ---------------------------------------------------------------------------
# parse_folder_identifiers
# ---------------------------------------------------------------------------
def test_parse_folder_identifiers_empty():
    assert main_module.parse_folder_identifiers("") == []
    assert main_module.parse_folder_identifiers("   ") == []
    assert main_module.parse_folder_identifiers(None) == []


def test_parse_folder_identifiers_comma():
    raw = "https://www.mediafire.com/folder/k1/First,https://www.mediafire.com/folder/k2/Second"
    result = main_module.parse_folder_identifiers(raw)
    assert len(result) == 2
    assert result[0] == ("mf:k1", "First")
    assert result[1] == ("mf:k2", "Second")


def test_parse_folder_identifiers_newline():
    raw = "https://www.mediafire.com/folder/k1/One\nhttps://www.mediafire.com/folder/k2/Two"
    result = main_module.parse_folder_identifiers(raw)
    assert len(result) == 2
    assert result[0][0] == "mf:k1"
    assert result[1][0] == "mf:k2"


def test_parse_folder_identifiers_single():
    raw = "1z3vk56tf787k"
    result = main_module.parse_folder_identifiers(raw)
    assert len(result) == 1
    assert result[0][0] == "mf:1z3vk56tf787k"


# ---------------------------------------------------------------------------
# list_all_files (with mock client)
# ---------------------------------------------------------------------------
def test_list_all_files_empty_folder(tmp_path):
    client = MagicMock()
    client.get_folder_contents_iter.return_value = iter([])
    files = list(main_module.list_all_files(client, "mf:key", str(tmp_path)))
    assert files == []
    assert (tmp_path).exists()


def test_list_all_files_single_file(tmp_path):
    client = MagicMock()
    file_item = MagicMock()
    file_item.__class__ = main_module.File
    file_item.__iter__ = lambda self: iter([])
    file_item.__getitem__ = lambda self, k: {"quickkey": "qk1", "filename": "a.txt"}[k]
    client.get_folder_contents_iter.return_value = iter([file_item])
    files = list(main_module.list_all_files(client, "mf:key", str(tmp_path)))
    assert len(files) == 1
    assert files[0][0] == "mf:qk1"
    assert files[0][1].replace("\\", "/").endswith("a.txt")


def test_list_all_files_with_subfolder(tmp_path):
    client = MagicMock()
    file_item = MagicMock()
    file_item.__class__ = main_module.File
    file_item.__iter__ = lambda self: iter([])
    file_item.__getitem__ = lambda self, k: {"quickkey": "qk1", "filename": "root.txt"}[k]
    folder_item = MagicMock()
    folder_item.__class__ = main_module.Folder
    folder_item.__iter__ = lambda self: iter([])
    folder_item.__getitem__ = lambda self, k: {"folderkey": "fk1", "name": "SubDir"}[k]
    # First call: root contents; second: subfolder contents
    sub_file = MagicMock()
    sub_file.__class__ = main_module.File
    sub_file.__iter__ = lambda self: iter([])
    sub_file.__getitem__ = lambda self, k: {"quickkey": "qk2", "filename": "nested.txt"}[k]

    def contents_iter(folder_uri, *_a, **_kw):
        if "mf:key" in (folder_uri or ""):
            return iter([file_item, folder_item])
        return iter([sub_file])

    client.get_folder_contents_iter.side_effect = contents_iter
    files = list(main_module.list_all_files(client, "mf:key", str(tmp_path)))
    assert len(files) == 2
    paths = [f[1].replace("\\", "/") for f in files]
    assert any("root.txt" in p for p in paths)
    assert any("nested.txt" in p and "SubDir" in p for p in paths)


# ---------------------------------------------------------------------------
# _download_file_safe (heavy mock: client, requests)
# ---------------------------------------------------------------------------
@patch("main.requests.get")
def test_download_file_safe_success(mock_get, tmp_path):
    client = MagicMock()
    resource = MagicMock()
    resource.__class__ = main_module.File
    _data = {
        "quickkey": "qk1",
        "filename": "test.bin",
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    resource.__getitem__ = lambda self, k: _data[k]
    resource.get = lambda k, default=None: _data.get(k, default)
    client.get_resource_by_uri.return_value = resource
    client.api.file_get_links.return_value = {
        "links": [{"direct_download": "https://example.com/f"}]
    }
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.headers = {"Content-Type": "application/octet-stream"}
    resp.iter_content = lambda **kw: [b""]
    mock_get.return_value = resp
    local = str(tmp_path / "test.bin")
    main_module._download_file_safe(client, "mf:qk1", local)
    assert os.path.isfile(local)
    assert open(local, "rb").read() == b""


@patch("main.requests.get")
def test_download_file_safe_not_file_raises(mock_get):
    client = MagicMock()
    client.get_resource_by_uri.return_value = MagicMock()  # not File
    with pytest.raises(main_module.MediaFireDownloadError):
        main_module._download_file_safe(client, "mf:qk1", "/tmp/out.bin")


@patch("main.requests.get")
def test_download_file_safe_hash_mismatch_removes_file(mock_get, tmp_path):
    """When server hash does not match local SHA-256, file is removed and error raised."""
    client = MagicMock()
    resource = MagicMock()
    resource.__class__ = main_module.File
    # Empty content has SHA-256 e3b0c44...; use wrong hash to force mismatch
    _data = {
        "quickkey": "qk1",
        "filename": "test.bin",
        "hash": "0000000000000000000000000000000000000000000000000000000000000000",
    }
    resource.__getitem__ = lambda self, k: _data[k]
    resource.get = lambda k, default=None: _data.get(k, default)
    client.get_resource_by_uri.return_value = resource
    client.api.file_get_links.return_value = {
        "links": [{"direct_download": "https://example.com/f"}]
    }
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.headers = {"Content-Type": "application/octet-stream"}
    resp.iter_content = lambda **kw: [b""]
    mock_get.return_value = resp
    local = str(tmp_path / "test.bin")
    with pytest.raises(main_module.MediaFireDownloadError) as exc_info:
        main_module._download_file_safe(client, "mf:qk1", local)
    assert "Hash mismatch" in str(exc_info.value)
    assert not os.path.isfile(local)


@patch("main.requests.get")
def test_download_file_safe_no_server_hash_skips_verification(mock_get, tmp_path):
    """When server does not provide hash, download succeeds and integrity check is skipped."""
    client = MagicMock()
    resource = MagicMock()
    resource.__class__ = main_module.File
    _data = {"quickkey": "qk1", "filename": "test.bin"}  # no "hash" -> skip verification
    resource.__getitem__ = lambda self, k: _data[k]
    resource.get = lambda k, default=None: _data.get(k, default)
    client.get_resource_by_uri.return_value = resource
    client.api.file_get_links.return_value = {
        "links": [{"direct_download": "https://example.com/f"}]
    }
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.headers = {"Content-Type": "application/octet-stream"}
    resp.iter_content = lambda **kw: [b"content"]
    mock_get.return_value = resp
    local = str(tmp_path / "test.bin")
    main_module._download_file_safe(client, "mf:qk1", local)
    assert os.path.isfile(local)
    assert open(local, "rb").read() == b"content"


# ---------------------------------------------------------------------------
# download_folder
# ---------------------------------------------------------------------------
def test_download_folder_empty(tmp_path):
    client = MagicMock()
    client.get_folder_contents_iter.return_value = iter([])
    main_module.download_folder(client, "mf:key", str(tmp_path), verbose=False)
    client.get_folder_contents_iter.assert_called()


@patch("main._download_file_safe")
def test_download_folder_skips_existing(mock_download, tmp_path):
    """When file exists and its hash matches server, skip download."""
    existing = tmp_path / "existing.txt"
    existing.write_text("x")
    hash_of_x = hashlib.sha256(b"x").hexdigest().lower()
    client = MagicMock()
    file_item = MagicMock()
    file_item.__class__ = main_module.File
    file_item.__iter__ = lambda self: iter([])
    file_item.__getitem__ = lambda self, k: {"quickkey": "qk1", "filename": "existing.txt"}[k]
    client.get_folder_contents_iter.return_value = iter([file_item])
    # When checking existing file, get_resource_by_uri must return a File with matching hash
    resource = MagicMock()
    resource.__class__ = main_module.File
    resource.get = lambda k, default=None: hash_of_x if k == "hash" else {"quickkey": "qk1", "filename": "existing.txt"}.get(k, default)
    client.get_resource_by_uri.return_value = resource
    main_module.download_folder(client, "mf:key", str(tmp_path), verbose=False)
    mock_download.assert_not_called()


@patch("main._download_file_safe")
def test_download_folder_redownloads_when_existing_hash_mismatch(mock_download, tmp_path):
    """When file exists but hash does not match server, re-download (overwrite)."""
    existing = tmp_path / "existing.txt"
    existing.write_text("x")
    # Server hash is different (e.g. server has newer version)
    wrong_hash = "0" * 64
    client = MagicMock()
    file_item = MagicMock()
    file_item.__class__ = main_module.File
    file_item.__iter__ = lambda self: iter([])
    file_item.__getitem__ = lambda self, k: {"quickkey": "qk1", "filename": "existing.txt"}[k]
    client.get_folder_contents_iter.return_value = iter([file_item])
    resource = MagicMock()
    resource.__class__ = main_module.File
    resource.get = lambda k, default=None: wrong_hash if k == "hash" else {"quickkey": "qk1", "filename": "existing.txt"}.get(k, default)
    client.get_resource_by_uri.return_value = resource
    mock_download.return_value = None  # no exception
    main_module.download_folder(client, "mf:key", str(tmp_path), verbose=False)
    mock_download.assert_called_once()


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------
def test_main_exits_when_no_folder(capsys):
    with patch.object(sys, "argv", ["main.py"]):
        with patch.dict(os.environ, {"MEDIAFIRE_FOLDER": "", "MEDIAFIRE_EMAIL": "a@b.com", "MEDIAFIRE_PASSWORD": "p"}, clear=False):
            with pytest.raises(SystemExit) as exc:
                main_module.main()
            assert exc.value.code == 1


def test_main_exits_when_no_credentials(capsys):
    with patch.object(sys, "argv", ["main.py", "https://www.mediafire.com/folder/abc123/x"]):
        with patch.dict(os.environ, {"MEDIAFIRE_EMAIL": "", "MEDIAFIRE_PASSWORD": ""}, clear=False):
            with pytest.raises(SystemExit) as exc:
                main_module.main()
            assert exc.value.code == 1


@patch("main.download_folder")
@patch("main.MediaFireClient")
def test_main_success_with_mocked_client(mock_client_class, mock_download, tmp_path):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    # main() expects download_folder to return a DownloadSummary
    mock_download.return_value = main_module.DownloadSummary(
        total=1, success=1, downloaded=1, skipped=0, failed=0, failed_list=[]
    )
    out = str(tmp_path / "out")
    log_file = str(tmp_path / "log.txt")
    with patch.object(sys, "argv", [
        "main.py",
        "https://www.mediafire.com/folder/abc123/Folder",
        "-o", out,
        "-q",
        "-l", log_file,
        "-j", "1",  # single thread so client_pool is None
    ]):
        with patch.dict(os.environ, {"MEDIAFIRE_EMAIL": "u@test.com", "MEDIAFIRE_PASSWORD": "pw"}, clear=False):
            main_module.main()
    mock_client.login.assert_called()
    mock_download.assert_called_once()
    call_kw = mock_download.call_args[1]
    assert call_kw["verbose"] is False
    assert call_kw["client_pool"] is None


@patch("main.download_folder")
@patch("main.MediaFireClient")
def test_main_exits_1_when_downloads_fail(mock_client_class, mock_download, tmp_path):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_download.return_value = main_module.DownloadSummary(
        total=2, success=1, downloaded=1, skipped=0, failed=1,
        failed_list=[("/path/to/file.txt", "Connection error")],
    )
    with patch.object(sys, "argv", [
        "main.py", "https://www.mediafire.com/folder/abc123/x",
        "-o", str(tmp_path / "out"), "-q", "-l", str(tmp_path / "log.txt"), "-j", "1",
    ]):
        with patch.dict(os.environ, {"MEDIAFIRE_EMAIL": "u@test.com", "MEDIAFIRE_PASSWORD": "pw"}, clear=False):
            with pytest.raises(SystemExit) as exc:
                main_module.main()
            assert exc.value.code == 1
