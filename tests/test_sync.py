"""sync 模块的单元测试：用假的 requests.post 模拟服务端，不真正联网。"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

import src.sync as sync_module
from src.storage import fetch_unsynced, init_db, save_record


@pytest.fixture()
def conn(tmp_path):
    connection = init_db(str(tmp_path / "sync_test.db"))
    yield connection
    connection.close()


def _add_record(conn):
    start = datetime.datetime(2026, 11, 3, 9, 0, 0)
    save_record(conn, "PC-001", "chrome.exe", start, start + datetime.timedelta(seconds=30), 30)


def test_build_payload_shape(conn):
    _add_record(conn)
    rows = fetch_unsynced(conn)
    payload = sync_module.build_payload("PC-001", rows)

    assert payload["device_id"] == "PC-001"
    assert len(payload["records"]) == 1
    assert set(payload["records"][0]) == {"app_name", "start_time", "end_time", "duration", "record_key"}


def test_successful_sync_marks_rows(conn):
    _add_record(conn)
    fake = MagicMock(status_code=200)
    fake.json.return_value = {"code": 0}

    with patch.object(sync_module.requests, "post", return_value=fake):
        count = sync_module.sync_unsynced(conn, "PC-001", "http://127.0.0.1:5000/upload")

    assert count == 1
    assert fetch_unsynced(conn) == []


def test_failed_sync_keeps_rows(conn):
    _add_record(conn)
    fake = MagicMock(status_code=500)
    fake.json.return_value = {"code": 1}

    with patch.object(sync_module.requests, "post", return_value=fake):
        count = sync_module.sync_unsynced(conn, "PC-001", "http://127.0.0.1:5000/upload")

    assert count == 0
    assert len(fetch_unsynced(conn)) == 1


def test_network_error_keeps_rows(conn):
    _add_record(conn)
    import requests

    with patch.object(sync_module.requests, "post", side_effect=requests.ConnectionError("offline")):
        count = sync_module.sync_unsynced(conn, "PC-001", "http://127.0.0.1:5000/upload")

    assert count == 0
    assert len(fetch_unsynced(conn)) == 1
