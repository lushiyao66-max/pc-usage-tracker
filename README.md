# pc-usage-tracker

一个本地 PC 使用情况追踪器：记录并分析每天在各程序上花费的时间，用来生成自己的「时间账本」。

当前阶段只包含 **Windows 采集客户端**：每秒识别前台程序，把使用时长写进本地 SQLite，
再批量上报到服务端。断网不丢数据。服务端（Flask + MySQL）与网页看板暂不在本仓库。

## 目录结构

```
pc-usage-tracker/
├── src/                     # 源码（全部逻辑都在这里）
│   ├── __init__.py
│   ├── __main__.py          # 支持 python -m src
│   ├── config.py            # 配置常量 + 命令行参数
│   ├── collector.py         # Win32 采集：空闲秒数 / 前台进程
│   ├── storage.py           # 本地 SQLite 缓存
│   ├── sync.py              # HTTP 批量上报
│   └── main.py              # 主循环与入口
├── tests/                   # 单元测试（pytest）
│   ├── conftest.py
│   ├── test_storage.py
│   └── test_sync.py
├── docs/
│   └── architecture.md      # 模块职责、数据流、设计取舍
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## 功能规划

- [x] 采集：识别前台进程，空闲超时暂停计时
- [x] 缓存：断网时写入本地 SQLite，联网后自动补报
- [x] 上报：按 `record_key` 幂等批量上报
- [ ] 采集窗口标题（区分同一程序的不同用途）
- [ ] 聚合：按应用、按小时汇总使用时长
- [ ] 展示：生成每日 / 每周时间账本
- [ ] 导出：CSV / JSON

## 技术栈

| 组件 | 用途 | 说明 |
|---|---|---|
| Python 3.10+ | 语言运行时 | 采集、缓存、上报全部用 Python |
| pywin32 | 调用 Win32 API | 提供 `win32gui` / `win32process`，用来取前台窗口和进程 PID |
| psutil | 进程信息 | 由 PID 取进程名（如 `chrome.exe`） |
| requests | HTTP 上报 | POST `/upload`，5 秒超时 |
| sqlite3 | 本地缓存 | **Python 标准库**，无需安装 |
| pytest | 单元测试 | 仅开发时需要，不参与运行 |

> 关于「C 扩展」的更正：这里调用的 Win32 API 是通过 **pywin32** 这个现成的 Python 扩展模块完成的，
> 不是自己写的 C 扩展。原 README 写的「C 扩展」不准确。

## 运行方式

### 1. 环境要求

- Windows 10 / 11
- Python 3.10 及以上

### 2. 安装依赖

在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. 启动采集

```powershell
python -m src.main
```

默认参数：设备号 `PC-001`、上报地址 `http://127.0.0.1:5000`、缓存文件 `usage_cache.db`。
可以用命令行覆盖：

```powershell
python -m src.main --device PC-002 --server http://192.168.1.10:5000 --db pc002.db
```

按 `Ctrl + C` 退出。退出前未上报的记录仍留在本地库里，下次启动会继续重试。

### 4. 运行测试

```powershell
python -m pytest -q
```

## 已知问题

1. **仅支持 Windows**：`collector.py` 依赖 `GetLastInputInfo` 和 `GetForegroundWindow`，macOS / Linux 无法运行。
2. **空闲判定有盲区**：`GetLastInputInfo` 只统计键鼠输入。看视频、用手柄、远程桌面挂机时可能被判定为“空闲”。
3. **休眠 / 锁屏会断档**：休眠期间不采集，唤醒后第一个间隔的时长可能偏大或直接丢弃。
4. **系统时间回拨**：`duration = now - last_tick` 可能为负，当前实现会跳过该段，但会导致一次统计缺失。
5. **没有单实例保护**：同一 `db` 路径启动两个进程会重复计时，建议每台机器只跑一个。
6. **本地库无限增长**：目前没有按天清理策略，长期运行后 `usage_cache.db` 会变大。
7. **`pywin32` 装不上**：多见于 Python 版本过新或权限不足；先升级 pip，再用管理员 PowerShell 重装。

## 开发进度

- **第 1 天**：仓库初始化，README / `.gitignore` / MIT LICENSE，首次 push。
- **第 2 天**：代码归档为标准结构（`src/`、`tests/`、`docs/`），拆分为五个模块；
  补充 `requirements.txt`、单元测试与本 README 的「技术栈 / 运行方式 / 已知问题」三节。

## 许可证

MIT，详见 [LICENSE](LICENSE)      888   。
