# 架构说明

## 一句话

一个 Windows 桌面端采集进程：每秒看一眼前台窗口，把「哪个程序、用了多久」写进本地 SQLite，
再异步批量上报给服务端。断网不丢数据。

## 模块划分

| 模块 | 职责 | 依赖 |
|---|---|---|
| `src/config.py` | 配置常量 + 命令行参数，产出不可变的 `Config` | 标准库 |
| `src/collector.py` | 调 Win32 API 取空闲秒数、前台进程名 | pywin32、psutil |
| `src/storage.py` | 本地 SQLite 缓存：建表、写入、取未同步、标记已同步 | sqlite3（标准库） |
| `src/sync.py` | 组装批量上报体、POST、按结果决定是否标记 | requests |
| `src/main.py` | 主循环：采集 → 判定活跃 → 累计时长 → 尝试同步 | 以上模块 |
| `src/__main__.py` | 让 `python -m src` 可用 | main |

依赖方向是单向的：

```
main ──► collector
  │
  ├────► storage ◄──── sync
  │
  └────► config
```

`storage` 不认识 `sync`，`sync` 只通过 `storage` 的函数读写数据；`collector` 完全不知道有数据库。
这样每一层都能单独测试：`tests/test_storage.py` 不需要 Windows API，`tests/test_sync.py` 用假 requests。

## 数据流

```
[每秒]
  GetLastInputInfo ──► idle 秒数
  GetForegroundWindow ──► 进程名（chrome.exe）

  活跃？（idle <= 300 且拿到进程名）
    ├─ 是：duration = now - last_tick
    │       └─ storage.save_record(...)  → usage_cache 表，synced=0
    └─ 否：last_tick = None（暂停计时，不补记空闲）

[每轮]
  sync.sync_unsynced()
    ├─ 取 synced=0 的记录
    ├─ POST /upload
    └─ 成功：mark_synced(ids)  失败：原样保留，下轮重试
```

## 数据模型（本地）

```sql
usage_cache(
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id   TEXT,      -- 设备标识
  app_name    TEXT,      -- 进程名，如 chrome.exe
  start_time  TEXT,      -- 'YYYY-MM-DD HH:MM:SS'
  end_time    TEXT,
  duration    INTEGER,   -- 秒
  record_key  TEXT,      -- 幂等键：device|start|app|duration
  synced      INTEGER    -- 0=未同步, 1=已同步
)
```

## 三个关键设计

### 1. 为什么用「幂等键」而不是自增 ID

断网重试时，同一条记录可能被上报多次。`record_key = 设备|开始时间|应用|时长`
由业务字段拼成，服务端对它建唯一索引：重复的请求不会产生重复行。
**幂等 = 同一操作执行多次，结果和执行一次相同。**

### 2. 为什么先写本地再上报（Write-ahead cache）

上报可能失败（断网、服务端重启）。如果「先上报、成功才存」，失败就丢数据。
现在的顺序是「先落盘、再尝试上报、成功才标记」，任何时刻断电，数据都还在本地。

### 3. 为什么空闲判定要在客户端做

服务端只看到「上报了什么」，看不到「用户有没有在动」。空闲 5 分钟以上还继续计时，
统计就失真了。`GetLastInputInfo` 是系统级的最后输入时间，比任何应用层猜测都准。

## 后续扩展点

- `collector` 增加窗口标题 → 可以区分「同一个 chrome.exe 在写代码还是刷视频」
- `storage` 增加按天清理 → 控制本地库体积
- `main` 增加单实例锁（命名互斥量）→ 防止重复计数
- 服务端的 `limits` 表已预留 → 达到每日限额后提醒或锁屏
