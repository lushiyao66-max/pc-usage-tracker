"""采集主循环与程序入口。

运行：python -m src.main
退出：Ctrl+C
"""

import datetime
import time

from .collector import get_foreground_app, get_idle_seconds
from .config import Config, parse_args
from .storage import init_db, save_record
from .sync import sync_unsynced


def run(config: Config) -> None:
    """持续采集前台应用使用时长，并定期上报。

    1. 每轮读取空闲秒数与前台应用；
    2. 空闲未超时且能取到应用时，把“上一采集时刻 -> 当前时刻”计为一段使用时长；
    3. 一旦进入空闲状态，重置计时起点，避免把空闲时间补记进去；
    4. 每轮尝试同步本地未上报记录。
    """
    conn = init_db(config.db_path)
    last_tick = None  # 上一次“处于活跃状态”的采集时刻

    print(f"采集客户端已启动，设备ID={config.device_id}，服务端={config.server_url}")
    print(f"采集间隔 {config.interval}s，空闲阈值 {config.idle_limit}s，按 Ctrl+C 退出")

    try:
        while True:
            now = datetime.datetime.now()
            idle = get_idle_seconds()
            app = get_foreground_app()

            if app and idle <= config.idle_limit:
                # 用户正在操作且能识别到前台应用：累计上一个间隔的时长
                if last_tick is not None:
                    duration = int((now - last_tick).total_seconds())
                    if duration > 0:
                        save_record(conn, config.device_id, app, last_tick, now, duration)
                last_tick = now
            else:
                # 空闲超时或取不到应用：暂停计时，重置起点
                last_tick = None

            # 每轮都尝试把本地缓存批量上报
            sync_unsynced(conn, config.device_id, config.sync_endpoint, config.http_timeout)
            time.sleep(config.interval)

    except KeyboardInterrupt:
        print("\n收到退出指令，客户端已停止。")
    finally:
        conn.close()


def main(argv=None) -> None:
    """命令行入口：解析参数后启动主循环。"""
    run(parse_args(argv))


if __name__ == "__main__":
    main()
