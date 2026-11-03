"""前台窗口与键鼠空闲状态采集（Windows 专用）。

只做两件事：
1. get_idle_seconds()   ／ 键鼠多久没动了
2. get_foreground_app() ／ 现在最前面的是哪个程序

依赖 pywin32（win32gui / win32process）与 psutil。
"""

import ctypes

import psutil
import win32gui
import win32process


def get_idle_seconds() -> float:
    """调用 Windows API GetLastInputInfo 获取键鼠空闲时长（秒）。

    GetLastInputInfo 返回“最后一次输入到现在”的毫秒数，
    再用 GetTickCount() 减去它即可得到空闲毫秒数。
    """

    class LASTINPUTINFO(ctypes.Structure):
        """Windows 原生结构体，cbSize 为结构体大小，dwTime 为最后输入时刻的 tick。"""

        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    # 读取最后一次键鼠输入的时间戳
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    # GetTickCount() 为系统启动至今的毫秒数
    idle_millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return idle_millis / 1000.0


def get_foreground_app() -> str | None:
    """获取当前前台窗口的进程名（如 chrome.exe）。

    步骤：拿到前台窗口句柄 -> 由句柄得到进程 PID -> 用 psutil 取进程名。
    取不到（如锁屏、无前台窗口）时返回 None。
    """
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None

    # GetWindowThreadProcessId 返回 (线程ID, 进程PID)，这里只取 PID
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if not pid:
        return None

    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        # 进程已退出或无权限访问时，放弃本次采集
        return None
