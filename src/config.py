"""配置与命令行参数。

所有可调参数集中在这里，其他模块只接收值、不读全局变量，
这样测试时可以传入一份临时 Config，不需要改环境。
"""

import argparse
from dataclasses import dataclass

# ==================== 默认配置（按需修改） ====================
DEFAULT_DEVICE_ID = "PC-001"                 # 设备唯一标识，多台机器部署时每台改成不同值
DEFAULT_SERVER_URL = "http://127.0.0.1:5000"  # 后端服务地址
DEFAULT_DB_PATH = "usage_cache.db"           # 本地 SQLite 缓存文件
COLLECT_INTERVAL = 1                         # 采集间隔（秒）
IDLE_LIMIT = 300                             # 空闲阈值（秒）：超过则暂停计时
HTTP_TIMEOUT = 5                             # 上报请求超时（秒）
# ============================================================


@dataclass(frozen=True)
class Config:
    """一次运行所需的全部参数，不可变。"""

    device_id: str = DEFAULT_DEVICE_ID
    server_url: str = DEFAULT_SERVER_URL
    db_path: str = DEFAULT_DB_PATH
    interval: int = COLLECT_INTERVAL
    idle_limit: int = IDLE_LIMIT
    http_timeout: int = HTTP_TIMEOUT

    @property
    def sync_endpoint(self) -> str:
        """上报接口完整地址，例如 http://127.0.0.1:5000/upload。"""
        return self.server_url.rstrip("/") + "/upload"


def parse_args(argv=None) -> Config:
    """解析命令行参数，覆盖默认配置。

    用法：python -m src.main --device PC-002 --server http://127.0.0.1:5000
    """
    parser = argparse.ArgumentParser(description="应用使用时长采集客户端")
    parser.add_argument("--device", default=DEFAULT_DEVICE_ID, help="设备唯一标识，如 PC-002")
    parser.add_argument("--server", default=DEFAULT_SERVER_URL, help="后端地址，如 http://127.0.0.1:5000")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="本地 SQLite 缓存文件路径")
    args = parser.parse_args(argv)

    return Config(
        device_id=args.device,
        server_url=args.server,
        db_path=args.db,
    )
