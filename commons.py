import ctypes
import logging
import re
import socket
import subprocess
import textwrap
import time
import uuid
from dataclasses import dataclass
# region 批处理任务的执行结果
from datetime import datetime
from typing import List, Any, Dict, Callable, TypeVar
from typing import Tuple

import coloredlogs
import psutil
import pysubs2
from PIL import ImageFont, Image, ImageDraw
from loguru import logger

T = TypeVar('T')


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

    def complete(self, end_time: datetime = None, fail_threshold: int = None):
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

    def __str__(self):
        return self.value

    @property
    def is_multi_line(self):
        """
        是否是多行文本
        """
        return self.value.count('\n') > 0

    # region 删除所有空格和换行符
    def remove_spaces_and_newlines(self):
        """
        删除所有空格和换行符

        Returns:
            Text: 新的文本对象
        """
        # 删除所有空格
        text = self.value.replace(" ", "")
        # 删除所有换行符（包括 \n 和 \r）
        text = text.replace("\n", "").replace("\r", "")
        return Text(text)

    # endregion

    # region 对文本进行断行
    def break_lines(self, pattern: str):
        """
        对文本进行断行

        Args:
            pattern: 分隔符

        Returns:
            list[Text]: 断行后的文本列表
        """
        return [Text(line) for line in re.split(pattern, self.value) if line]

    # endregion

    # region 计算在图像上渲染此文本所需的宽度和高度
    def calc_size(self, font_path: str, font_size: int, line_spacing: int = 0):
        """
        计算在图像上渲染此文本所需的宽度和高度

        Args:
            font_path: 字体文件路径
            font_size: 字体大小
            line_spacing: 行间距

        Returns:
            tuple[int, int]: 宽度, 高度
        """
        font = ImageFont.truetype(font_path, font_size)
        # 将文本分割成多行
        lines = self.value.split('\n')

        # 计算所有行中最宽的一行
        max_width = max(font.getbbox(line)[2] for line in lines)

        # 计算总高度
        total_height = sum(font.getbbox(line)[3] for line in lines)

        # 如果有多行，在行间添加一些间距
        if len(lines) > 1:
            total_height += line_spacing * (len(lines) - 1)

        return max_width, total_height

    # endregion

    def create_image(self, font_path: str, font_size: int, font_color="white", margin: int = 0, radius: int = 0,
                     background_color="black",
                     line_spacing: int = 0,
                     max_chars_per_line: int = 99999,
                     align: str = "center",
                     ):
        """
        创建图像

        Args:
            font_path: 字体文件路径
            font_size: 字体大小
            font_color: 字体颜色,可以是以下格式 颜色名称|rgb(r,g,b)|rgba(r,g,b,a)|hex(rrggbbaa)
            margin: 边距
            radius: 圆角半径
            background_color: 背景颜色,可以是以下格式 颜色名称|rgb(r,g,b)|rgba(r,g,b,a)|hex(rrggbbaa)
            line_spacing: 行间距
            max_chars_per_line: 每行最大字符数,默认不限制
            align: 对齐方式,可以是以下值 left|center|right
        """
        lines = textwrap.wrap(self.value, width=max_chars_per_line)
        font = ImageFont.truetype(font_path, font_size)
        # 计算所有行中最宽的一行
        max_width = int(max(font.getbbox(line)[2] for line in lines))
        # 计算总高度
        total_height = sum(font.getbbox(line)[3] for line in lines)
        # 如果有多行，在行间添加一些间距
        if len(lines) > 1:
            total_height += line_spacing * (len(lines) - 1)
        max_width += margin * 2
        total_height += margin * 2
        canvas = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([(0, 0), (max_width - 1, total_height - 1)], radius=radius, fill=background_color)
        for i, line in enumerate(lines):
            x = margin
            if align == "center":
                x = (max_width - font.getbbox(line)[2]) // 2
            draw.text((x, margin + i * (font_size + (line_spacing if line_spacing else 0))), line, font=font,
                      fill=font_color)
        return canvas

    def convert_to_pysubs2Color(self):
        """
        把`rgba(r,g,b,a)`格式的字符串转换为`pysubs2.Color`对象

        Returns:
            pysubs2.Color: 颜色对象
        """
        data = tuple(map(lambda v: int(float(v)), self.value.replace("rgba(", "").replace(")", "").split(",")))
        return pysubs2.Color(data[0], data[1], data[2], data[3])


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
    stdout: str
    """标准输出"""
    stderr: str
    """错误输出"""
    status: int
    """状态码"""

    @property
    def output(self):
        return "\n".join([self.stdout, self.stderr])


class CommandLine(object):
    @classmethod
    def run(cls, command: str, cwd: str = None, encoding=None) -> subprocess.Popen:
        """
        运行命令,返回进程对象
        """
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                                encoding=encoding)

    @classmethod
    def run_and_get(cls, command: str | list[str], cwd: str = None, encoding=None) -> CommandLineOutput:
        """
        阻塞方式运行命令,返回命令行输出

        Args:
            command: 命令行命令
            cwd: 工作目录
            encoding: 编码

        Returns:
            CommandLineOutput: 命令行输出
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

    @staticmethod
    def get_all_pids(process_name: str) -> list[int]:
        """
        获取所有匹配的进程ID

        Args:
            process_name: 进程名称

        Returns:
            list[int] - 匹配的进程ID列表
        """
        all_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    all_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return all_pids


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


# region 表示尺寸
class Size(object):
    def __init__(self, width: int, height: int, ratio: str = None):
        self.width = width
        """宽度"""
        self.height = height
        """高度"""
        self.ratio = ratio
        """比例"""


# endregion


# region 异常处理
class Result:
    def __init__(self, value=None, error=None):
        """
        用于表示操作结果的类

        Args:
            value: 操作成功时的返回值
            error: 操作失败时的异常
        """
        self._value = value
        self._error = error

    @property
    def is_success(self):
        """
        检查操作是否成功
        """
        return self._error is None

    @property
    def is_failure(self):
        """
        检查操作是否失败
        """
        return self._error is not None

    def get_or_none(self):
        """
        获取操作结果的值，如果操作失败则返回None
        """
        return self._value

    def get_or_throw(self):
        """
        获取操作结果的值，如果操作失败则抛出异常
        """
        if self.is_failure:
            raise self._error
        return self._value

    def on_success(self, action: Callable[[T], None]):
        """
        如果操作成功，则执行指定的操作
        """
        if self.is_success:
            action(self._value)
        return self

    def on_failure(self, action: Callable[[Exception], None]):
        """
        如果操作失败，则执行指定的操作
        """
        if self.is_failure:
            action(self._error)
        return self


def run_catching(func: Callable[[], T]) -> Result:
    """
    运行指定的函数，并捕获可能的异常

    Args:
        func: 要运行的函数

    Returns:
        Result: 包含操作结果的Result对象
    """
    try:
        return Result(value=func())
    except Exception as e:
        return Result(error=e)
# endregion
