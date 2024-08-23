import logging
import re
import socket
import time
import uuid
from typing import Tuple, Any
import subprocess
from dataclasses import dataclass
import ctypes

import psutil
from PIL import ImageFont

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

        :return: 一个元组, 第一个元素为屏幕宽度, 第二个元素为屏幕高度
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

        :param process_name: 进程名称
        :return: 如果进程正在运行, 则返回True, 否则返回False
        """
        for proc in psutil.process_iter(['name']):
            if process_name.lower() in proc.info['name'].lower():
                return True
        return False


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
            logging.info(f"正在连接 {ip} 端口 {port}...")
            s.connect((ip, port))

            # 计算连接时间
            connection_time = time.time() - start_time

            # 获取本地地址和端口
            local_address, local_port = s.getsockname()

            logging.info(f"连接到 {ip} 端口 {port} 成功 从 {local_address}:{local_port}")
            logging.info(f"连接耗时: {connection_time:.6f} 秒")

            # 关闭连接
            s.close()
            return True
        except socket.timeout:
            logging.info(f"连接超时: 无法在指定时间内连接到 {ip}:{port}")
        except ConnectionRefusedError:
            logging.info(f"连接被拒绝: {ip}:{port} 可能没有监听或被防火墙阻止")
        except socket.gaierror:
            logging.info(f"地址解析错误: 无法解析 {ip}")
        except Exception as e:
            logging.info(f"发生错误: {e}")
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


if __name__ == '__main__':
    # print(UUID.random(upper=True, formats=[(8, '-'), (12, '-'), (16, '-'), (20, '-')]))
    # CommandLine.run_async("ping 360.com")
    # print(Display.get_screen_resolution())
    # print(ProcessManager.is_process_running("JianyingPro.exe"))
    #print(Netcat.connect("localhost", 9222))
    # 示例使用
    class MyClass:
        def __init__(self):
            self.title1 = "First Title"
            self.title2 = "Second Title"
            self.title10 = "Tenth Title"
            self.other_attr = "Not a title"
            self.title3 = "Third Title"


    obj = MyClass()
    titles = Objects.pick_fields_values(obj, r"title\d+")
    print(titles)