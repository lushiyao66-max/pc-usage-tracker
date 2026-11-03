"""HTTP 上报。

把本地未同步记录批量 POST 到服务端 /upload；
仅当 HTTP 200 且业务 code=0 时才标记为已同步，否则保留待下次重试。
"""

import requests

from .storage import fetch_unsynced, mark_synced


def build_payload(device_id: str, rows: list[dict]) -> dict:
    """组装服务端要求的批量上报格式。"""
    return {
        "device_id": device_id,
        "records": [
            {
                "app_name": r["app_name"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "duration": r["duration"],
                "record_key": r["record_key"],
            }
            for r in rows
        ],
    }


def sync_unsynced(conn, device_id: str, endpoint: str, timeout: int = 5) -> int:
    """批量上报 synced=0 的记录，返回成功上报的条数。

    - 请求成功且服务端返回 code=0，才把这些记录标记为 synced=1；
    - 网络异常 / 服务端异常时不修改标记，下一轮循环自动重试，避免重复上报。
    """
    rows = fetch_unsynced(conn)
    if not rows:
        return 0

    payload = build_payload(device_id, rows)

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        result = resp.json()
        # 仅当 HTTP 200 且业务 code=0 时才认定同步成功
        if resp.status_code == 200 and result.get("code") == 0:
            mark_synced(conn, [r["id"] for r in rows])
            print(f"[同步成功] 上报 {len(rows)} 条记录")
            return len(rows)
    except (requests.RequestException, ValueError):
        # 断网、服务端未启动、返回非 JSON 等情况：静默留待下次重试
        print("[同步失败] 网络不可用，记录已保留在本地，稍后自动重试")
    return 0
