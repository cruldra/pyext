import logging
import os
import re
import socket
import sys
import time
import uuid
from datetime import datetime
from typing import Tuple, Any
import subprocess
from dataclasses import dataclass
import ctypes
from functools import wraps
from loguru import logger
import coloredlogs
import psutil
from PIL import ImageFont
from coloredlogs import ColoredFormatter, parse_encoded_styles

# region 批处理任务的执行结果
from datetime import datetime
from typing import List, Any, Dict


class BatchProcessingResult:
    """
    批处理任务的执行结果

    References:
        - [poe](https://poe.com/s/EjySosRoZFDGKroOIaqr)


    Example:
        ```python
        from datetime import datetime

# 创建一个新的批处理结果实例
result = BatchProcessingResult("TASK_001", datetime.now())

# 设置总项目数
result.set_total_items(100)

# 模拟处理过程
for i in range(100):
    success = i % 10 != 0  # 假设每10个项目中有1个失败
    result.add_processed_item(success)
    if not success:
        result.add_error("ProcessingError", f"Failed to process item {i}")

# 添加额外信息
result.add_additional_info("processor_version", "1.0.3")

# 完成任务
result.complete(datetime.now())

# 获取摘要
summary = result.get_summary()
print(summary)
        ```
    """

    def __init__(self, task_id: str, start_time: datetime = None):
        self.task_id = task_id
        """任务ID"""
        self.start_time = start_time if start_time else datetime.now()
        """开始时间"""
        self.end_time: datetime = None
        """结束时间"""
        self.status: str = "Running"
        """状态"""
        self.total_items: int = 0
        """总数"""
        self.processed_items: int = 0
        """处理数量"""
        self.successful_items: int = 0
        """成功数量"""
        self.failed_items: int = 0
        """失败数量"""
        self.errors: List[Dict[str, Any]] = []
        """错误列表"""
        self.additional_info: Dict[str, Any] = {}
        """额外信息"""

    def complete(self, end_time: datetime =None ,fail_threshold: int = None):
        """
        完成任务

        Args:
            end_time: 结束时间
            fail_threshold: 失败阈值,如果失败数量超过阈值,则任务失败,默认为任务总数的50%
        """
        self.end_time = end_time if end_time else datetime.now()
        self.status = "Completed"

        if fail_threshold is None:
            fail_threshold = self.total_items // 2
        if self.failed_items > fail_threshold:
            self.fail(self.end_time, f"Failed items exceed the threshold of {fail_threshold}")

    def fail(self, end_time: datetime, reason: str):
        """
        任务失败

        Args:
            end_time: 结束时间
            reason: 失败原因
        """
        self.end_time = end_time
        self.status = "Failed"
        self.add_error("Task Failure", reason)

    def add_successful_item(self):
        """
        添加成功项目
        """
        self.processed_items += 1
        self.successful_items += 1

    def add_failed_item(self, error_message: str):
        """
        添加失败项目
        """
        self.processed_items += 1
        self.failed_items += 1
        self.add_error("ProcessingError", error_message)

    def add_error(self, error_type: str, error_message: str):
        """
        添加错误
        """
        self.errors.append({
            "type": error_type,
            "message": error_message,
            "time": datetime.now()
        })

    def set_total_items(self, total: int):
        """
        设置总项目数

        Args:
            total: 总数
        """
        self.total_items = total

    def add_additional_info(self, key: str, value: Any):
        """
        添加额外信息

        Args:
            key: 键
            value: 值
        """
        self.additional_info[key] = value

    def get_duration(self) -> float:
        """
        获取批处理任务的耗时

        Returns:
            float: 耗时（秒）
        """
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    def get_summary(self) -> Dict[str, Any]:
        """
        获取任务摘要

        Returns:
            Dict[str, Any]: 摘要
        """
        return {
            "task_id": self.task_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.get_duration(),
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "error_count": len(self.errors),
            "additional_info": self.additional_info
        }


# endregion

# region 数字范围
class IntRange(object):
    """
    数字范围
    """

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def __contains__(self, item):
        return self.start <= item <= self.end

    def __iter__(self):
        return iter(range(self.start, self.end + 1))


# endregion

# region 文本处理
class Text(object):
    CHINESE_LINE_BREAKER = '[。！？]'
    """中文断句符"""
    ENGLISH_LINE_BREAKER = '[.!?]'
    """英文断句符"""

    def __init__(self, value: str):
        self.value = value

    def break_lines(self, pattern: str):
        """
        对文本进行断行

        Args:
            pattern: 分隔符

        Returns:
            list[Text]: 断行后的文本列表
        """
        return [Text(line) for line in re.split(pattern, self.value) if line]

    def calculate_text_width(self, font_path: str, font_size: int):
        """
        计算文本的宽度

        Args:
            font_path: 字体文件路径
            font_size: 字体大小

        Returns:
            tuple[int, int]: 宽度, 高度
        """
        font = ImageFont.truetype(font_path, font_size)
        width, height = font.getbbox(self.value)[2:]
        return width, height


# endregion

# region 对象工具
class Objects(object):
    """
    对象工具
    """

    @classmethod
    def pick_fields_values(cls, obj: Any, fields_regex: str) -> list[Any]:
        """
        从对象中选取所有名称符合正则表达式的属性，获取它们的值然后返回一个列表

        :param obj: 对象
        :param fields_regex: 字段正则表达式
        :return:
        """
        # 正则表达式匹配 'title' 后跟一个或多个数字
        fields_pattern = re.compile(fields_regex)
        # 使用列表推导式获取所有匹配的属性值
        fields_values = [getattr(obj, attr) for attr in dir(obj)
                         if fields_pattern.match(attr) and hasattr(obj, attr)]

        # 按照数字顺序排序
        return fields_values


# endregion


# region uuid
class UUID(object):
    @classmethod
    def random(cls, upper=False, formats: list[Tuple[int, str]] = None):
        """
        生成一个随机的UUID

        :param upper: 是否大写
        :param formats: 格式化方式,例如:[(8, '-'), (12, '-'), (16, '-'), (20, '-')]
        :return: UUID字符串
        """
        random_uuid = uuid.uuid4()
        if upper:
            random_uuid = random_uuid.hex.upper()

        if formats:
            formatted_uuid = ""
            start = 0
            for end, sep in formats:
                formatted_uuid += random_uuid[start:end] + sep
                start = end
            formatted_uuid += random_uuid[start:]
            return formatted_uuid
        else:
            return random_uuid


# endregion


# region 命令行工具
@dataclass
class CommandLineOutput(object):
    """
    命令行输出
    """
    output: str
    """标准输出"""
    error: str
    """错误输出"""
    status: int
    """状态码"""


class CommandLine(object):
    @classmethod
    def run(cls, command: str, cwd: str = None, encoding=None) -> subprocess.Popen:
        """
        运行命令,返回进程对象
        """
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                                encoding=encoding)

    @classmethod
    def run_and_get(cls, command: str, cwd: str = None, encoding=None) -> CommandLineOutput:
        """
        阻塞方式运行命令,返回命令行输出

        :param command: 命令行命令
        :param cwd: 工作目录
        :param encoding: 编码
        :return: 命令行输出
        """
        process = cls.run(command, cwd, encoding)
        stdout, stderr = process.communicate()
        return CommandLineOutput(stdout, stderr, process.returncode)

    # @classmethod
    # def run_async(cls, command: str, line_callback: callable = lambda line: print(line.strip()),
    #               cwd: str = None, encoding=None
    #               ):
    #     """
    #     异步方式运行命令
    #
    #     :param command: 命令行命令
    #     :param line_callback: 每一行输出的回调函数
    #     :param cwd: 工作目录
    #     :param encoding: 编码
    #     """
    #     process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
    #                                encoding=encoding)
    #     for line in iter(process.stdout.readline, ''):
    #         line_callback(line)
    #     for line in iter(process.stderr.readline, ''):
    #         line_callback(line)


# endregion


# region 显示器
class Display(object):
    @classmethod
    def get_screen_resolution(cls) -> tuple[int, int]:
        """
        获取屏幕分辨率

        Returns:
            tuple[int, int]: 屏幕宽度, 屏幕高度
        """
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        return screen_width, screen_height


# endregion


# region 进程管理器
class ProcessManager(object):
    """
    进程管理器
    """

    @classmethod
    def is_process_running(cls, process_name: str) -> bool:
        """
        检查进程是否正在运行

        Args:
            process_name: 进程名称

        Returns:
            bool: 如果进程正在运行，则返回True，否则返回False
        """
        return bool(cls.get_processes_by_name(process_name))

    @classmethod
    def get_processes_by_name(cls, process_name: str) -> list[psutil.Process]:
        """
        通过进程名称获取所有匹配的进程对象

        Args:
            process_name: 进程名称

        Returns:
            list[psutil.Process]: 匹配的进程对象列表
        """
        matching_processes = []
        for proc in psutil.process_iter(['name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    matching_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return matching_processes

    @classmethod
    def kill_process_by_name(cls, process_name: str, timeout: int = 5) -> None:
        """
        通过进程名称杀死所有匹配的进程

        :param process_name: 进程名称
        :param timeout: 等待进程终止的超时时间（秒）
        """
        processes = cls.get_processes_by_name(process_name)
        if not processes:
            return

        for proc in processes:
            try:
                pid = proc.pid
                proc.terminate()
                logger.info(f"Terminating process {pid} ({proc.name()})...")

                # 等待进程终止
                proc.wait(timeout=timeout)

            except psutil.NoSuchProcess:
                logger.info(f"Process {pid} no longer exists.")
            except psutil.AccessDenied:
                logger.info(f"Access denied to terminate process {pid}.")
            except psutil.TimeoutExpired:
                logger.info(f"Process {pid} did not terminate in time, forcefully killing it.")
                proc.kill()

        # 再次检查进程是否还存在
        remaining = cls.get_processes_by_name(process_name)
        if remaining:
            logger.info(f"Warning: {len(remaining)} processes with name '{process_name}' still running.")
        else:
            logger.info(f"All processes with name '{process_name}' have been terminated.")

    @classmethod
    def kill_process_by_pid(cls, pid: int):
        """
        通过进程ID杀死进程

        :param pid: 进程ID
        """
        try:
            process = psutil.Process(pid)
            process.kill()
        except Exception as e:
            logger.error(f"无法杀死进程: {e}")


# endregion


# region netcat
class Netcat(object):

    @classmethod
    def connect(cls, ip: str, port: int) -> bool:
        """
        连接到目标

        :param ip: 目标IP
        :param port: 目标端口
        :return: 如果连接成功, 则返回True, 否则返回False
        """
        try:
            # 创建一个 socket 对象
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # 设置连接超时时间（可选）
            s.settimeout(5)

            # 记录开始时间
            start_time = time.time()

            # 尝试连接
            logger.info(f"正在连接 {ip} 端口 {port}...")
            s.connect((ip, port))

            # 计算连接时间
            connection_time = time.time() - start_time

            # 获取本地地址和端口
            local_address, local_port = s.getsockname()

            logger.info(f"连接到 {ip} 端口 {port} 成功 从 {local_address}:{local_port}")
            logger.info(f"连接耗时: {connection_time:.6f} 秒")

            # 关闭连接
            s.close()
            return True
        except socket.timeout:
            logger.info(f"连接超时: 无法在指定时间内连接到 {ip}:{port}")
        except ConnectionRefusedError:
            logger.info(f"连接被拒绝: {ip}:{port} 可能没有监听或被防火墙阻止")
        except socket.gaierror:
            logger.info(f"地址解析错误: 无法解析 {ip}")
        except Exception as e:
            logger.info(f"发生错误: {e}")
        return False

    @classmethod
    def get_available_port(cls) -> int:
        """
        获取本机上的一个空闲端口
        :return: 空闲端口
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port


# endregion

def setup_colored_logger(logger: logging.Logger = None):
    """
    设置带颜色的日志记录器
    """
    coloredlogs.install(
        logger=logger,
        level='DEBUG',
        fmt='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level_styles={
            'debug': {'color': 'cyan'},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red', 'bold': True},
            'critical': {'color': 'red', 'bold': True, 'background': 'white'},
        },
        field_styles={
            'asctime': {'color': 'green'},
            'levelname': {'color': 'magenta', 'bold': True},
            'name': {'color': 'blue'},
        }
    )


# region loguru日志
def log_name(name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger_ = logger.bind(name=name)
            return func(logger_, *args, **kwargs)

        return wrapper
    return decorator

logger.remove()
logger.add(sink=sys.stdout,
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan> - <level>{message}</level>")
# endregion