"""本地 SQLite 缓存。

断网时先把每条使用记录写进本地库，联网后再批量上报；
上报成功后把 synced 置 1，失败则保持 0，等下一轮重试。
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT,
    app_name    TEXT,
    start_time  TEXT,
    end_time    TEXT,
    duration    INTEGER,
    record_key  TEXT,
    synced      INTEGER DEFAULT 0
)
"""


def init_db(db_path: str) -> sqlite3.Connection:
    """打开（不存在则创建）本地缓存库，并确保表结构存在。"""
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def build_record_key(device_id: str, start_str: str, app_name: str, duration: int) -> str:
    """生成幂等键：同一设备、同一开始时刻、同一应用、同一时长视为同一条记录。

    服务端以 record_key 建唯一索引，重复上报不会产生重复数据。
    """
    return f"{device_id}|{start_str}|{app_name}|{duration}"


def save_record(conn, device_id, app_name, start_time, end_time, duration) -> str:
    """把一条未同步记录写入本地 SQLite，synced 默认 0。返回 record_key。"""
    fmt = "%Y-%m-%d %H:%M:%S"
    start_str = start_time.strftime(fmt)
    end_str = end_time.strftime(fmt)
    record_key = build_record_key(device_id, start_str, app_name, duration)

    conn.execute(
        """
        INSERT INTO usage_cache
            (device_id, app_name, start_time, end_time, duration, record_key, synced)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (device_id, app_name, start_str, end_str, duration, record_key),
    )
    conn.commit()
    return record_key


def fetch_unsynced(conn) -> list[dict]:
    """取出所有 synced=0 的记录，按字典返回，供上报模块组包。"""
    rows = conn.execute(
        """
        SELECT id, device_id, app_name, start_time, end_time, duration, record_key
        FROM usage_cache WHERE synced = 0
        ORDER BY id
        """
    ).fetchall()

    keys = ("id", "device_id", "app_name", "start_time", "end_time", "duration", "record_key")
    return [dict(zip(keys, row)) for row in rows]


def mark_synced(conn, ids) -> None:
    """把一批记录标记为已同步。"""
    conn.executemany("UPDATE usage_cache SET synced = 1 WHERE id = ?", [(i,) for i in ids])
    conn.commit()
