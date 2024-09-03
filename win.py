import os
import tkinter as tk
import winreg
from tkinter import messagebox

import win32gui
import wrapt
from clicknium import clicknium as cc, ui
from tenacity import retry, stop_after_delay, wait_fixed
from win32comext.shell import shell, shellcon

from pyext.commons import ContextLogger


def open_file_dialog(title="请选择文件"):
    """
    打开文件选择框,选择单个文件

    Args:
        title: 窗口标题

    Returns:
        str: 选择的文件路径
    """
    desktop_pidl = shell.SHGetFolderLocation(0, shellcon.CSIDL_DESKTOP, 0, 0)
    pidl, display_name, image_list = shell.SHBrowseForFolder(
        win32gui.GetDesktopWindow(),
        desktop_pidl,
        title,
        shellcon.BIF_BROWSEINCLUDEFILES,
        None,
        None
    )

    if pidl:
        path = shell.SHGetPathFromIDList(pidl)
        # 检查是否是MP3文件
        if isinstance(path, bytes):
            path = path.decode('utf-8')  # 将字节字符串转换为Unicode字符串
        if os.path.isfile(path) :
            return path.lower()
        else:
            return None
    return None

def show_message_box(msg,callback=None,type="info"):
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    if type == "info":
        res =messagebox.showinfo("提示", msg)
    elif type == "warning":
        res =messagebox.showwarning("警告", msg)
    elif type == "error":
        res =messagebox.showerror("错误", msg)
    elif type == "question":
        res = messagebox.askquestion("问题", msg)
    else:
        res =messagebox.showinfo("提示", msg)
    # 或者使用其他类型的消息框:
    # messagebox.showwarning("警告", "这是一个警告框！")
    # messagebox.showerror("错误", "这是一个错误框！")
    if callback:
        callback(res)
    root.destroy()

def get_windows_theme():
    """
    获取当前系统使用的主题

    仅限win11

    Returns:
        str: 主题类型,Dark Theme或Light Theme

    Raises:
        WindowsError: 如果无法确定主题类型,则引发此异常
    """
    # 打开注册表键
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")

    # 读取 AppsUseLightTheme 值
    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")

    # 关闭注册表键
    winreg.CloseKey(key)

    # 根据值返回主题类型
    if value == 0:
        return "Dark Theme"
    else:
        return "Light Theme"


def is_window_active(window_title):
    """
    检查窗口是否处于活动状态

    Args:
        window_title: 窗口标题

    Returns:
        bool: 如果窗口处于活动状态,则返回True,否则返回False
    """
    # 获取当前激活窗口的句柄
    active_window = win32gui.GetForegroundWindow()

    # 获取窗口标题
    active_title = win32gui.GetWindowText(active_window)

    # 比较窗口标题
    return active_title == window_title


def wait_win(locator, timeout=0, interval=1):
    """
    这个装饰器会等待定位符(locator)指向的窗口出现并处于活动状态
    Args:
        locator: clicknium定位符
        timeout: 超时时间,默认不会超时,一直等待
        interval: 等待间隔,默认1秒
    """
    window_name = str(locator).split(".")[-1]
    ContextLogger.set_name("win")

    @retry(stop=stop_after_delay(timeout if timeout > 0 else 86400), wait=wait_fixed(interval))
    def wait_window_exists():
        """
        等待窗口出现
        """
        ContextLogger.info(f"正在等待窗口[{window_name}]出现...")
        if not cc.is_existing(locator):
            raise Exception(f"窗口[{window_name}]未打开")
        return True

    @retry(stop=stop_after_delay(timeout if timeout > 0 else 86400), wait=wait_fixed(interval))
    def wait_window_active():
        """
        等待窗口处于活动状态
        """
        ContextLogger.info(f"正在等待窗口[{window_name}]处于活动状态...")
        window = ui(locator)
        window_title = window.get_property("Name")
        if not is_window_active(window_title):
            window.set_focus()
            raise Exception(f"窗口[{window_title}]未处于活动状态")
        return True

    @wrapt.decorator
    def decorator(wrapped, instance, args, kwargs):
        window_exists = wait_window_exists()
        ContextLogger.info(f"窗口[{window_name}]已出现")
        window_active = wait_window_active()
        ContextLogger.info(f"窗口[{window_name}]已处于活动状态")
        if window_exists and window_active:
            return wrapped(*args, **kwargs)

    return decorator
