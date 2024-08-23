import json
import logging
import os.path
import shutil
import textwrap
import threading
import time
from enum import Enum
from pathlib import Path as PathlibPath
from typing import TypeVar, Type, Optional
import http.server
import socketserver

import pysubs2
import yaml
from addict import Dict
from docker import DockerClient
from jsonpath_ng import parse
from langdetect import detect, LangDetectException
from pydantic import BaseModel

from pyext.commons import CommandLine, Text

TF = TypeVar('TF', bound='File')
TPM = TypeVar('TPM', bound=BaseModel)
TAF = TypeVar('TAF', bound='AudioFile')
TSBT = TypeVar('TSBT', bound='SubtitleFile')


# region ffmpeg
class Ffmpeg(object):

    def __init__(self):
        super().__init__()

    def add_subtitle_to_video(self, video_file: 'VideoFile', subtitle_file: 'SubtitleFile',
                              new_name: str, font_directory: str) -> 'VideoFile':
        """
        为视频添加字幕

        Args:
            video_file: 视频文件
            subtitle_file: 字幕文件
            new_name: 新文件名
            font_directory: 字体目录

        Returns:
            新的视频文件
        """
        raise NotImplementedError()

    def video_to_audio(self, video_file: 'VideoFile', audio_type: Type[TAF]) -> TAF:
        """
        将视频文件转换为音频文件

        Args:
            video_file: 视频文件
            audio_type: 音频文件类型

        Returns:
            音频文件
        """
        raise NotImplementedError()

    def srt_to_ass(self, srt_file: 'SrtSubtitleFile') -> 'AssSubtitleFile':
        """
        srt字幕转ass字幕
        """
        raise NotImplementedError()


class DockerFfmpeg(Ffmpeg):
    def __init__(self, docker_client: DockerClient, ffmpeg_image: str = "ffmpeg:1.0"):
        """
        使用Docker运行ffmpeg
        """
        super().__init__()
        self.docker_client = docker_client
        """docker客户端"""
        self.ffmpeg_image = ffmpeg_image
        """使用的docker镜像"""

    def video_to_audio(self, video_file: 'VideoFile', audio_type: Type[TAF]) -> TAF:
        command = (
            f"-y -i /tmp_app/{video_file.path.name} -q:a 0 -map a /tmp_app/{video_file.path.stem}.{audio_type.suffix}"
        )
        full_command = (
            f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logging.info(f"使用以下命令行先将视频文件转换为音频文件: {full_command}")
        logs = (
            self.docker_client.containers.run(
                self.ffmpeg_image,
                command,
                volumes={str(video_file.path.parent.absolute()): {"bind": "/tmp_app", "mode": "rw"}},
                remove=True,
                tty=True,
                stdin_open=True,
            )
            .decode("utf-8")
            .strip()
        )
        logging.info(f"将视频文件转换为音频文件的日志: {logs}")
        if audio_type == Mp3File:
            return Mp3File(str(video_file.path.parent / f"{video_file.path.stem}.{Mp3File.suffix}"))
        else:
            raise ValueError(f"不支持的音频文件类型: {audio_type}")

    def srt_to_ass(self, srt_file: 'SrtSubtitleFile') -> 'AssSubtitleFile':
        command = f'-y -i /tmp_app/{srt_file.path.name} /tmp_app/{srt_file.path.stem}.ass'
        full_command = (
            f"docker run --rm -it -v {str(srt_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logging.info(f"使用以下命令行将srt字幕文件转换为ass字幕文件: {full_command}")
        logs = self.docker_client.containers.run(
            self.ffmpeg_image,
            command,
            volumes={str(srt_file.path.parent.absolute()): {'bind': '/tmp_app', 'mode': 'rw'}},
            remove=True,
            tty=True,
            stdin_open=True
        ).decode('utf-8').strip()
        logging.info(f"将srt字幕文件转换为ass字幕文件的日志: {logs}")
        return AssSubtitleFile(str(srt_file.path.parent / f"{srt_file.path.stem}.ass"))

    def add_subtitle_to_video(self, video_file: 'VideoFile', subtitle_file: 'SubtitleFile',
                              new_name: str, font_directory: str) -> 'VideoFile':
        command = (
            f"-y -i /tmp_app/{video_file.path.name} -vf 'ass=/tmp_app/{subtitle_file.path.name}' -c:a copy /tmp_app/{new_name}"
        )
        full_command = (
            f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logging.info(f"使用以下命令行为视频添加字幕: {full_command}")
        logs = (
            self.docker_client.containers.run(
                self.ffmpeg_image,
                command,
                volumes={str(video_file.path.parent.absolute()): {"bind": "/tmp_app", "mode": "rw"},
                         font_directory: {"bind": "/usr/local/share/fonts/", "mode": "rw"},
                         },
                remove=True,
                tty=True,
                stdin_open=True,
            )
            .decode("utf-8")
            .strip()
        )
        logging.info(f"为视频添加字幕的日志: {logs}")
        return VideoFile(str(video_file.path.parent / new_name))


# endregion

# region aeneas
class LanguageCode(str, Enum):
    """
    aeneas支持的语言代码
    """
    AFR = 'afr'
    AMH = 'amh'
    ARA = 'ara'
    ARG = 'arg'
    ASM = 'asm'
    AZE = 'aze'
    BEN = 'ben'
    BOS = 'bos'
    BUL = 'bul'
    CAT = 'cat'
    CES = 'ces'
    CMN = 'cmn'
    """中文普通话"""
    CYM = 'cym'
    DAN = 'dan'
    DEU = 'deu'
    ELL = 'ell'
    ENG = 'eng'
    EPO = 'epo'
    EST = 'est'
    EUS = 'eus'
    FAS = 'fas'
    FIN = 'fin'
    FRA = 'fra'
    GLA = 'gla'
    GLE = 'gle'
    GLG = 'glg'
    GRC = 'grc'
    GRN = 'grn'
    GUJ = 'guj'
    HEB = 'heb'
    HIN = 'hin'
    HRV = 'hrv'
    HUN = 'hun'
    HYE = 'hye'
    INA = 'ina'
    IND = 'ind'
    ISL = 'isl'
    ITA = 'ita'
    JBO = 'jbo'
    JPN = 'jpn'
    KAL = 'kal'
    KAN = 'kan'
    KAT = 'kat'
    KIR = 'kir'
    KOR = 'kor'
    KUR = 'kur'
    LAT = 'lat'
    LAV = 'lav'
    LFN = 'lfn'
    LIT = 'lit'
    MAL = 'mal'
    MAR = 'mar'
    MKD = 'mkd'
    MLT = 'mlt'
    MSA = 'msa'
    MYA = 'mya'
    NAH = 'nah'
    NEP = 'nep'
    NLD = 'nld'
    NOR = 'nor'
    ORI = 'ori'
    ORM = 'orm'
    PAN = 'pan'
    PAP = 'pap'
    POL = 'pol'
    POR = 'por'
    RON = 'ron'
    RUS = 'rus'
    SIN = 'sin'
    SLK = 'slk'
    SLV = 'slv'
    SPA = 'spa'
    SQI = 'sqi'
    SRP = 'srp'
    SWA = 'swa'
    SWE = 'swe'
    TAM = 'tam'
    TAT = 'tat'
    TEL = 'tel'
    THA = 'tha'
    TSN = 'tsn'
    TUR = 'tur'
    UKR = 'ukr'
    URD = 'urd'
    VIE = 'vie'
    YUE = 'yue'
    ZHO = 'zho'
    """中文"""

    @classmethod
    def from_langdetect(cls, code: str) -> Optional['LanguageCode']:
        mapping = {
            'en': cls.ENG,
            'fr': cls.FRA,
            'zh-cn': cls.CMN,
            'ru': cls.RUS,
            'ja': cls.JPN,
            # 添加更多映射...
        }
        return mapping.get(code)


class Aeneas(object):
    def __init__(self):
        super().__init__()

    @classmethod
    def detect_language(cls, text: str) -> LanguageCode | None:
        """
        检测文本的语言

        Args:
            text: 文本

        Returns:
            语言代码
        """
        try:
            return detect(text)
        except LangDetectException:
            return None

    # region 强制对齐音频和文本
    def force_align(self, audio_file: TAF, text: str, language_code: LanguageCode = None) -> 'SrtSubtitleFile':
        """
        将音频文件与文本强制对齐

        Args:
            audio_file: 音频文件
            text: 文本
            language_code: 语言代码,如果为None,则自动检测

        Returns:
            srt字幕文件
        """
        raise NotImplementedError()

    # endregion


class DockerAeneas(Aeneas):
    def __init__(self, docker_client: DockerClient, aeneas_image: str = "dongjak/aeneas"):
        """
        使用Docker运行aeneas
        """
        super().__init__()
        self.docker_client = docker_client
        """docker客户端"""
        self.aeneas_image = aeneas_image
        """使用的docker镜像"""

    def force_align(self, audio_file: TAF, text: str, language_code: LanguageCode = None) -> 'SrtSubtitleFile':
        language_code = language_code or LanguageCode.from_langdetect(self.detect_language(text))
        content_text_file = File(str(audio_file.path.parent / f"{audio_file.path.stem}-content.txt"))
        content_text_file.write_content(text)
        command = (
            f"bash -c \"source ~/miniconda3/etc/profile.d/conda.sh; "
            f"conda activate aeneas; "
            f"python -m aeneas.tools.execute_task "
            f"/tmp_app/{audio_file.path.name} /tmp_app/{audio_file.path.stem}-content.txt "
            f"'task_language={language_code.value}|os_task_file_format=srt|is_text_type=plain' "
            f"/tmp_app/{audio_file.path.stem}.srt;\""
        )
        local_mapping_dir = str(audio_file.path.parent.absolute())
        full_command = (
            f"docker run --rm -it -v {local_mapping_dir}:/tmp_app {self.aeneas_image} {command}"
        )
        logging.info(f"使用以下命令行先将音频文件与文本强制对齐: {full_command}")
        logs = self.docker_client.containers.run(
            self.aeneas_image,
            command,
            volumes={local_mapping_dir: {'bind': '/tmp_app', 'mode': 'rw'}},
            remove=True,
            tty=True,
            stdin_open=True
        ).decode('utf-8').strip()
        logging.info(f"将音频文件与文本强制对齐的日志: {logs}")
        return SrtSubtitleFile(str(audio_file.path.parent / f"{audio_file.path.stem}.srt"))


# endregion


class File(object):
    def __init__(self, path: str):
        self.path = PathlibPath(path)

    def exists(self):
        return self.path.exists()

    def delete(self):
        self.path.unlink()

    def write_content(self, content: str):
        """
        写入文本内容到该文件中

        Args:
            content: 文本内容
        """
        with self.path.open("w", encoding='utf-8') as f:
            f.write(content)

    def read_content(self):
        """
        读取文件内容

        Returns:
            文件内容
        """
        with self.path.open("r", encoding='utf-8') as f:
            return f.read()

    def move_to(self, target_path: str = None) -> 'File':
        """
        移动文件到新路径

        Args:
            target_path: 目标路径

        Returns:
            新的文件对象
        """
        shutil.move(str(self.path), str(target_path))
        return File(str(target_path))


# region 字幕文件

class SubtitleFile(File):

    def __init__(self, path: str):
        super().__init__(path)


class SrtSubtitleFile(SubtitleFile):
    def __init__(self, path: str):
        super().__init__(path)


class AssSubtitleFile(SubtitleFile):
    def __init__(self, path: str):
        super().__init__(path)
        self.subs = pysubs2.load(path)

    def set_resolution(self, width: int, height: int):
        """
        设置分辨率

        Args:
            width: 宽度
            height: 高度
        """
        self.subs.info["PlayResX"] = str(width)
        self.subs.info["PlayResY"] = str(height)
        self.subs.save(str(self.path))

    def create_style(self, style_name: str, **kwargs):
        """
        创建样式

        Args:
            style_name: 样式名
            **kwargs: 样式参数
        """
        self.subs.styles[style_name] = pysubs2.SSAStyle(**kwargs)
        self.subs.save(str(self.path))

    def apply_style(self, style_name: str, events_filter: callable = lambda event: True):
        """
        应用样式

        Args:
            style_name: 样式名
            events_filter: 仅对符合条件的事件应用样式
        """
        for event in self.subs.events:
            if isinstance(event, pysubs2.SSAEvent) and events_filter(event):
                event.style = style_name
        self.subs.save(str(self.path))

    def set_max_width(self, max_width: int):
        """
        设置最大宽度

        Args:
            max_width: 最大宽度
        """
        new_events = []
        for i, event in enumerate(self.subs.events):
            lines = textwrap.wrap(event.text.strip(), width=max_width)
            new_line = r"\N".join(lines)
            new_events.append(
                pysubs2.SSAEvent(start=event.start, end=event.end, style=event.style, name="", text=new_line))
            # for line in lines:

            # text_width, text_height = Text(line).calculate_text_width( "resources/fonts/华文细黑.ttf", 36)
            # pos_x = (1080 - text_width) // 2
            # new_line = f"{{\\\\an1\\\\pos({pos_x},{line_start_y})}}" + line
            # new_events.append(
            #     pysubs2.SSAEvent(start=event.start, end=event.end, style=event.style, name="", text=new_line))
            # line_start_y += text_height
        self.subs.events = new_events
        self.subs.save(str(self.path))


# endregion

# region 视频文件


class VideoFile(File):

    def __init__(self, path: str):
        super().__init__(path)

    # def extract_audio(self, dest_dir:str, audio_name:str, audio_format:Type[TAF])->TAF:
    #     """
    #     提取音频
    #
    #     Args:
    #         dest_dir: 提取到的音频文件放置的目录
    #         audio_name: 音频文件名
    #         audio_format: 音频文件类型
    #     """
    #     CommandLine.run(f"ffmpeg -i {self.path} -q:a 0 -map a {output_path}")


# endregion


# region 音频文件
class AudioFile(File):
    def __init__(self, path: str):
        super().__init__(path)


class Mp3File(AudioFile):
    suffix = "mp3"

    def __init__(self, path: str):
        super().__init__(path)


# endregion

# region yaml文件
class YamlFile(File):
    def __init__(self, path: str):
        super().__init__(path)

    def read_as_pydantic_model(self, model: Type[TPM]) -> TPM:
        """
        读取文件内容并将其转换为 Pydantic 模型

        :param model: Pydantic 模型
        :return: Pydantic 模型实例
        """
        with open(self.path, 'r', encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)

        # 将 YAML 数据转换为 Pydantic 类实例
        return model(**yaml_data)


# endregion

# region Json文件
class JsonFile(File):

    def __init__(self, path: str):
        super().__init__(path)

    def read_dict(self) -> dict[str, any]:
        """
        读取文件内容并将其转换为字典对象
        """
        with open(self.path, 'r', encoding="utf-8") as file:
            return json.load(file)

    def write_dict(self, dict: dict[str, any]):
        """
        将字典对象转换为json字符串并写入文件
        """
        self.write_content(json.dumps(dict, indent=4, ensure_ascii=False))

    def write_dataclass_json_obj(self, obj):
        """
        对于使用了`@dataclass_json`的数据类对象,将其转换为json字符串并写入文件
        """
        self.write_content(obj.to_json(indent=4, ensure_ascii=False))

    def read_dataclass_json_obj(self, dataclass):
        """
        读取文件内容并将其转换为数据类对象
        """
        with open(self.path, 'r', encoding="utf-8") as file:
            return dataclass.from_json(file.read())

    def write_pydanitc_model(self, model: TPM):
        """
        将 Pydantic 模型写入文件

        :param model: Pydantic 模型
        """
        self.write_content(model.model_dump_json(indent=4, exclude_none=True))

    def get_value_by_jsonpath(self, json_path):
        """
        通过 JSON Path 获取值

        Args:
            json_path: JSON Path

        Returns:
            匹配到的值
        """
        # 读取json为字典
        # region 尝试移除BOM头
        json_str = self.read_content()
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        # endregion
        data = json.loads(json_str)

        # 解析 JSON Path
        jsonpath_expr = parse(json_path)

        # 查找匹配的位置
        matches = jsonpath_expr.find(data)
        # print(len(matches))
        # 返回匹配到的值
        if len(matches) > 0:
            return matches[0].value
        else:
            return None

    def set_value_by_jsonpath(self, json_path, new_value):
        """
        通过 JSON Path 设置值

        Args:
            json_path: JSON Path
            new_value: 新值
        """
        # 读取json为字典
        # region 尝试移除BOM头
        json_str = self.read_content()
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        # endregion
        data = json.loads(json_str)

        # 解析 JSON Path
        jsonpath_expr = parse(json_path)

        # 查找匹配的位置
        new_data = jsonpath_expr.update(data, new_value)
        # print(len(matches))
        # # 修改匹配到的值
        # for match in matches:
        #     match.value = new_value

        # 写入文件
        self.write_content(json.dumps(new_data, indent=4, ensure_ascii=False))

    def read_as_addict(self):
        """
        读取文件内容并将其转换为 Addict 对象
        """
        with open(self.path, 'r', encoding="utf-8") as file:
            return Dict(json.load(file))

    def read_as_pydanitc_model(self, model: Type[TPM]) -> TPM:
        """
        读取文件内容并将其转换为 Pydantic 模型

        :param model: Pydantic 模型
        :return: Pydantic 模型实例
        """
        with open(self.path, 'r', encoding="utf-8") as file:
            return model(**self.read_as_addict())


# endregion


# region 目录
class Directory(object):
    def __init__(self, path: str, auto_create=True):
        """
        创建一个位于指定路径上的目录对象

        :param path: 目录的路径
        """
        self.path = PathlibPath(path)
        if auto_create and not self.path.exists():
            self.path.mkdir(parents=True)
        if not self.path.is_dir():
            raise ValueError(f"路径 {path} 不是一个目录")

    def find_file(self, file_name: str) -> File:
        """
        在目录下查找指定文件

        Args:
            file_name: 文件名

        Returns:
            如果找到,则返回文件对象,否则返回None
        """
        for file in self.list_files():
            if file.name == file_name:
                return File(str(file))

    def new_file(self, file_name: str) -> TF:
        """
        创建一个新文件

        Args:
            file_name: 文件名

        Returns:
            文件对象
        """
        file_path = self.path / file_name
        file_path.touch()
        suffix = file_path.suffix
        if suffix == ".json":
            file = JsonFile(str(file_path))
        else:
            file = File(str(file_path))
        return file

    def new_folders(self, sub_folder_path: str) -> 'Directory':
        """
        在目录下创建子目录

        Args:
            sub_folder_path: 子目录路径

        Returns:
            目录对象
        """
        folder_path = self.path / sub_folder_path
        folder_path.mkdir(parents=True, exist_ok=True)
        return Directory(str(folder_path))

    def get_file(self, file_name: str) -> File:
        """
        获取文件

        :param file_name: 文件名
        :return: 文件对象
        """
        return File(str(self.path / file_name))

    def get_json_file(self, file_name: str) -> JsonFile:
        """
        获取json文件

        :param file_name: 文件名
        :return: json文件对象
        """
        return JsonFile(str(self.path / file_name))

    def list_directories(self):
        """
        列出目录下的所有子目录
        """
        return [Directory(str(f)) for f in self.path.iterdir() if f.is_dir]

    def list_files(self):
        """
        列出目录下的所有文件
        """
        return [f for f in self.path.iterdir() if f.is_file()]

    def list_json_files(self):
        """
        列出目录下的所有json文件
        """
        return [JsonFile(str(f)) for f in self.path.iterdir() if f.is_file() and f.suffix == ".json"]

    def as_static_file_server(self, host: str = "localhost", port: int = 8000):
        """
        将该目录作为静态文件服务器

        静态文件服务会在后台运行,不会阻塞当前线程
        Args:
            host: 主机
            port: 端口

        Returns:
            httpd: http服务器
            server_thread: 服务器线程
        """
        directory = os.path.abspath(self.path)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

        httpd = socketserver.TCPServer((host, port), Handler)
        # with socketserver.TCPServer(("", port), Handler) as httpd:
        #     print(f"Serving at port {port}")
        #     httpd.serve_forever()
        # server_thread = threading.Thread(target=httpd.serve_forever)
        # server_thread.daemon = True
        # server_thread.start()
        # return httpd, server_thread
        httpd.serve_forever()


# endregion


# region git仓库
class GitRepository(Directory):
    def __init__(self, path: str, ignores: list[str] = None):
        """
        创建一个git仓库

        Args:
            path: 仓库路径
            ignores: 忽略的文件,会被添加到.gitignore文件中
        """
        super().__init__(path, auto_create=True)
        self.init(ignores)

    def init(self, ignores: list[str] = None):
        """
        初始化一个git仓库
        """
        # 如果已经是git仓库,则不再初始化
        if self.path.joinpath(".git").exists():
            return
        # 创建.gitignore文件
        if ignores:
            git_ignore_file = self.new_file(".gitignore")
            git_ignore_file.write_content("\n".join(ignores))
        CommandLine.run_and_get("git init", cwd=str(self.path))
        CommandLine.run_and_get("git add .", cwd=str(self.path))

    def commit(self, message: str, files: list[str] = None):
        """
        提交更改

        :param message: 提交信息
        :param files: 仅提交指定文件
        """
        if files:
            CommandLine.run_and_get(f"git add {' '.join(files)}", cwd=str(self.path))
            CommandLine.run_and_get(f"git commit -m '{message}'", cwd=str(self.path))
        else:
            print(CommandLine.run_and_get(f"git commit -am '{message}'", cwd=str(self.path)))

    @classmethod
    def from_remote(cls, url: str, directory: str = None, name: str = None, branch: str = "master",
                    recursive: bool = False):
        """
        从远程仓库克隆

        :param url: 远程仓库地址
        :param directory: 本地目录
        :param name: 本地仓库名
        :param branch: 分支
        :param recursive: 是否递归克隆
        """
        cmd_line = f"git clone {url} -b {branch} {'--recursive' if recursive else ''} {name if name else ''}"
        CommandLine.run(cmd_line, cwd=directory)
        if directory:
            repo_path = PathlibPath(directory) / name
        else:
            repo_path = PathlibPath(CommandLine.run("pwd").output.strip()) / name
        return GitRepository(str(repo_path))


# endregion


if __name__ == '__main__':
    # json_file = JsonFile("../.locator/jianyingpro.cnstore")
    # json_file.set_value_by_jsonpath(
    #     "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.value", 2)

    # httpd.socket = ssl.wrap_socket(httpd.socket,
    #                                keyfile="/path/to/key.pem",
    #                                certfile='/path/to/cert.pem', server_side=True)
    print(Directory("../.data/videos").as_static_file_server())
    time.sleep(1000)
    pass
