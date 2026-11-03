"""pc-usage-tracker 采集客户端。

包内模块：
    config     配置与命令行参数
    collector  前台窗口 / 空闲时间采集（Windows API）
    storage    本地 SQLite 缓存
    sync       HTTP 批量上报
    main       采集主循环与入口

运行：python -m src.main
"""

__version__ = "0.1.0"
