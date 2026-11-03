"""storage 模块的单元测试：不依赖 Windows API、不依赖网络。"""

import datetime
import os

import pytest

from src.storage import (
    build_record_key,
    fetch_unsynced,
    init_db,
    mark_synced,
    save_record,
)


@pytest.fixture()
def conn(tmp_path):
    """每个用例一个独立的临时数据库，互不干扰。"""
    db_path = os.path.join(str(tmp_path), "test_cache.db")
    connection = init_db(db_path)
    yield connection
    connection.close()


def _make_record(conn, app_name="chrome.exe", duration=30, device_id="PC-001"):
    start = datetime.datetime(2026, 11, 3, 9, 0, 0)
    end = start + datetime.timedelta(seconds=duration)
    return save_record(conn, device_id, app_name, start, end, duration)


def test_init_db_is_idempotent(tmp_path):
    """重复初始化同一个文件不应报错（CREATE TABLE IF NOT EXISTS）。"""
    db_path = os.path.join(str(tmp_path), "a.db")
    init_db(db_path).close()
    init_db(db_path).close()


def test_save_record_returns_expected_key(conn):
    key = _make_record(conn)
    assert key == "PC-001|2026-11-03 09:00:00|chrome.exe|30"


def test_saved_record_is_unsynced(conn):
    _make_record(conn)
    rows = fetch_unsynced(conn)
    assert len(rows) == 1
    assert rows[0]["app_name"] == "chrome.exe"
    assert rows[0]["duration"] == 30


def test_mark_synced_moves_records_out_of_queue(conn):
    _make_record(conn)
    _make_record(conn, app_name="Code.exe")

    rows = fetch_unsynced(conn)
    assert len(rows) == 2

    mark_synced(conn, [rows[0]["id"]])

    remaining = fetch_unsynced(conn)
    assert len(remaining) == 1
    assert remaining[0]["app_name"] == "Code.exe"


def test_build_record_key_format(conn):
    assert build_record_key("PC-002", "2026-11-03 09:00:00", "msedge.exe", 12) == (
        "PC-002|2026-11-03 09:00:00|msedge.exe|12"
    )
