import datetime
import http.server
import json
import os.path
import shutil
import socketserver
import textwrap
import zipfile
from enum import Enum
from pathlib import Path as PathlibPath
from typing import TypeVar, Type, Optional, Union

import docker
import pysubs2
import yaml
from addict import Dict
from docker import DockerClient
from jsonpath_ng import parse
from langdetect import detect, LangDetectException
from loguru import logger
from pydantic import BaseModel
from pysubs2 import SSAEvent

from pyext.commons import CommandLine, Size
from pyext.exceptions import parse_exceptions

TF = TypeVar("TF", bound="File")
TPM = TypeVar("TPM", bound=BaseModel)
TAF = TypeVar("TAF", bound="AudioFile")
TSBT = TypeVar("TSBT", bound="SubtitleFile")


# region aeneas
class LanguageCode(str, Enum):
    """
    aeneas支持的语言代码
    """

    AFR = "afr"
    AMH = "amh"
    ARA = "ara"
    ARG = "arg"
    ASM = "asm"
    AZE = "aze"
    BEN = "ben"
    BOS = "bos"
    BUL = "bul"
    CAT = "cat"
    CES = "ces"
    CMN = "cmn"
    """中文普通话"""
    CYM = "cym"
    DAN = "dan"
    DEU = "deu"
    ELL = "ell"
    ENG = "eng"
    EPO = "epo"
    EST = "est"
    EUS = "eus"
    FAS = "fas"
    FIN = "fin"
    FRA = "fra"
    GLA = "gla"
    GLE = "gle"
    GLG = "glg"
    GRC = "grc"
    GRN = "grn"
    GUJ = "guj"
    HEB = "heb"
    HIN = "hin"
    HRV = "hrv"
    HUN = "hun"
    HYE = "hye"
    INA = "ina"
    IND = "ind"
    ISL = "isl"
    ITA = "ita"
    JBO = "jbo"
    JPN = "jpn"
    KAL = "kal"
    KAN = "kan"
    KAT = "kat"
    KIR = "kir"
    KOR = "kor"
    KUR = "kur"
    LAT = "lat"
    LAV = "lav"
    LFN = "lfn"
    LIT = "lit"
    MAL = "mal"
    MAR = "mar"
    MKD = "mkd"
    MLT = "mlt"
    MSA = "msa"
    MYA = "mya"
    NAH = "nah"
    NEP = "nep"
    NLD = "nld"
    NOR = "nor"
    ORI = "ori"
    ORM = "orm"
    PAN = "pan"
    PAP = "pap"
    POL = "pol"
    POR = "por"
    RON = "ron"
    RUS = "rus"
    SIN = "sin"
    SLK = "slk"
    SLV = "slv"
    SPA = "spa"
    SQI = "sqi"
    SRP = "srp"
    SWA = "swa"
    SWE = "swe"
    TAM = "tam"
    TAT = "tat"
    TEL = "tel"
    THA = "tha"
    TSN = "tsn"
    TUR = "tur"
    UKR = "ukr"
    URD = "urd"
    VIE = "vie"
    YUE = "yue"
    ZHO = "zho"
    """中文"""

    @classmethod
    def from_langdetect(cls, code: str) -> Optional["LanguageCode"]:
        mapping = {
            "en": cls.ENG,
            "fr": cls.FRA,
            "zh-cn": cls.CMN,
            "ru": cls.RUS,
            "ja": cls.JPN,
            # 添加更多映射...
        }
        return mapping.get(code)


class Aeneas(object):
    def __init__(self):
        super().__init__()

    @classmethod
    def from_env(cls):
        """
        自动

        """
        try:
            docker_client = docker.from_env()
            logger.info("使用Docker运行aeneas")
            return DockerAeneas(docker_client)
        except:
            logger.info("使用本地aeneas")
            return LocalAeneas()

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
    def force_align(
            self,
            audio_file: TAF,
            text: str,
            language_code: LanguageCode = None,
            format: str = "srt",
    ) -> Union["SrtSubtitleFile", "JsonFile"]:
        """
        将音频文件与文本强制对齐

        Args:
            audio_file: 音频文件
            text: 文本
            language_code: 语言代码,如果为None,则自动检测
            format: 格式,默认为srt

        Returns:
            srt字幕文件
        """
        raise NotImplementedError()

    # endregion


class LocalAeneas(Aeneas):

    def __init__(self):
        """
        使用本地aeneas
        """
        super().__init__()

    def force_align(
            self,
            audio_file: TAF,
            text: str,
            language_code: LanguageCode = None,
            format: str = "srt",
    ) -> Union["SrtSubtitleFile", "JsonFile"]:
        language_code = language_code or LanguageCode.from_langdetect(
            self.detect_language(text)
        )
        content_text_file_name = f"{audio_file.path.stem}-content.txt"
        content_text_file = File(str(audio_file.path.parent / content_text_file_name))
        content_text_file.write_content(text)
        audio_file_name = audio_file.path.name
        audio_file_dir = str(audio_file.path.parent)
        if format == "srt":
            file_name = f"{audio_file.path.stem}.srt"
        elif format == "json":
            file_name = f"{audio_file.path.stem}.json"
        else:
            raise ValueError(f"不支持的格式: {format}")
        command = [
            "py",
            "-3.9",
            "-m",
            "aeneas.tools.execute_task",
            audio_file_name,
            content_text_file_name,
            f"task_language={language_code.value}|os_task_file_format={format}|is_text_type=plain",
            file_name,
        ]
        logger.info(f"使用以下命令行先将音频文件与文本强制对齐: {command}")
        output = CommandLine.run_and_get(command, audio_file_dir).output
        logger.info(f"将音频文件与文本强制对齐的日志: {output}")
        if format == "srt":
            return SrtSubtitleFile(str(audio_file.path.parent / file_name))
        elif format == "json":
            return JsonFile(str(audio_file.path.parent / file_name))


class DockerAeneas(Aeneas):
    def __init__(
            self, docker_client: DockerClient, aeneas_image: str = "dongjak/aeneas"
    ):
        """
        使用Docker运行aeneas
        """
        super().__init__()
        self.docker_client = docker_client
        """docker客户端"""
        self.aeneas_image = aeneas_image
        """使用的docker镜像"""

    def force_align(
            self,
            audio_file: TAF,
            text: str,
            language_code: LanguageCode = None,
            format: str = "srt",
    ) -> Union["SrtSubtitleFile", "JsonFile"]:
        language_code = language_code or LanguageCode.from_langdetect(
            self.detect_language(text)
        )
        content_text_file = File(
            str(audio_file.path.parent / f"{audio_file.path.stem}-content.txt")
        )
        content_text_file.write_content(text)
        if format == "srt":
            file_name = f"{audio_file.path.stem}.srt"
        elif format == "json":
            file_name = f"{audio_file.path.stem}.json"
        else:
            raise ValueError(f"不支持的格式: {format}")
        command = (
            f'bash -c "source ~/miniconda3/etc/profile.d/conda.sh; '
            f"conda activate aeneas; "
            f"python -m aeneas.tools.execute_task "
            f"/tmp_app/{audio_file.path.name} /tmp_app/{audio_file.path.stem}-content.txt "
            f"'task_language={language_code.value}|os_task_file_format={format}|is_text_type=plain' "
            f'/tmp_app/{file_name};"'
        )
        local_mapping_dir = str(audio_file.path.parent.absolute())
        full_command = f"docker run --rm -it -v {local_mapping_dir}:/tmp_app {self.aeneas_image} {command}"
        logger.info(f"使用以下命令行先将音频文件与文本强制对齐: {full_command}")
        logs = (
            self.docker_client.containers.run(
                self.aeneas_image,
                command,
                volumes={local_mapping_dir: {"bind": "/tmp_app", "mode": "rw"}},
                remove=True,
                tty=True,
                stdin_open=True,
            )
            .decode("utf-8")
            .strip()
        )
        logger.info(f"将音频文件与文本强制对齐的日志: {logs}")
        if format == "srt":
            return SrtSubtitleFile(str(audio_file.path.parent / file_name))
        elif format == "json":
            return JsonFile(str(audio_file.path.parent / file_name))


# endregion


class File(object):
    def __init__(self, path: str, auto_create_parent_dir=False):
        """
        使用指定路径创建一个文件对象

        Args:
            path: 文件路径
            auto_create_parent_dir: 是否自动创建父目录
        """
        if not path:
            raise IOError(f"路径{path}不是一个有效的路径")
        self.path = PathlibPath(path)
        if auto_create_parent_dir:
            # 获取父目录
            parent_dir = self.path.parent
            # 创建父目录（如果不存在）
            parent_dir.mkdir(parents=True, exist_ok=True)

    def exists(self):
        return self.path.exists()

    def raise_for_not_exists(self):
        if not self.exists():
            raise IOError(f"文件{self.path}不存在")

    def delete(self):
        self.path.unlink()

    def write_content(self, content: str):
        """
        写入文本内容到该文件中

        Args:
            content: 文本内容
        """
        with self.path.open("w", encoding="utf-8") as f:
            f.write(content)

    def read_content(self):
        """
        读取文件内容

        Returns:
            文件内容
        """
        with self.path.open("r", encoding="utf-8") as f:
            return f.read()

    def move_to(self, target_path: str) -> "File":
        """
        移动文件到新路径

        Args:
            target_path: 目标路径

        Returns:
            新的文件对象
        """
        shutil.move(str(self.path), str(target_path))
        return File(str(target_path))

    def rename(self, new_name: str) -> "File":
        """
        重命名文件

        Args:
            new_name: 新名称

        Returns:
            File - 新的文件对象
        """
        return File(str(self.path.rename(new_name)))

    # 这里有个前向引用，所以用字符串, 参考https://poe.com/s/kxbWkhgiPORnv2D02LUJ
    def copy_to(self, target: "str | Directory") -> "File":
        """
        复制文件到新路径

        Args:
            target: 如果是字符串,则表示目标路径,如果是Directory对象,则表示目标目录

        Returns:
            新的文件对象
        """

        if isinstance(target, Directory):
            target_path = target.path / self.path.name
        else:
            target_path = PathlibPath(target)

        shutil.copy2(str(self.path), str(target_path))
        return File(str(target_path))

    @property
    def name(self):
        return self.path.name

    @property
    def suffix(self):
        return self.path.suffix

    @property
    def short_name(self):
        return self.path.stem

    @property
    def last_modified(self):
        """
        获取文件的最后修改时间
        """
        # 获取文件的状态信息
        file_stat = os.stat(self.path)
        # 获取最后修改时间
        modification_time = file_stat.st_mtime
        # 将时间戳转换为 datetime 对象
        modification_datetime = datetime.datetime.fromtimestamp(modification_time)
        return modification_datetime

    @property
    def data_size(self):
        return self.path.stat().st_size


# region 字幕文件


class SubtitleFile(File):

    def __init__(self, path: str):
        super().__init__(path)


class SrtSubtitleFile(SubtitleFile):
    def __init__(self, path: str):
        super().__init__(path)


# region ass字幕
class AssSubtitleFile(SubtitleFile):
    def __init__(self, path: str):
        super().__init__(path)
        self.subs = pysubs2.load(path)

    def set_info(self, info: [str, str]):
        self.subs.info = info

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

    def move_to(self, target_path: str) -> "AssSubtitleFile":
        file = super().move_to(target_path)
        return AssSubtitleFile(str(file.path.absolute()))

    def copy_to(self, target: "str | Directory") -> "AssSubtitleFile":
        file = super().copy_to(target)
        return AssSubtitleFile(str(file.path.absolute()))

    @property
    def events(self):
        return self.subs.events

    @events.setter
    def events(self, events: list[SSAEvent]):
        """
        设定事件

        Args:
            events: 事件列表
        """
        self.subs.events = events

    @property
    def styles(self):
        """
        获取样式

        Returns:
            dict[str, pysubs2.SSAStyle]: 样式,键是样式名, 值是SSAStyle
        """
        return self.subs.styles

    @styles.setter
    def styles(self, styles: dict[str, pysubs2.SSAStyle]):
        """
        设定样式

        Args:
            styles: 样式
        """
        self.subs.styles = styles

    @property
    def width(self):
        """
        获取宽度

        Returns:
            int: 宽度
        """
        return int(self.subs.info["PlayResX"])

    @property
    def height(self):
        """
        获取高度

        Returns:
            int: 高度
        """
        return int(self.subs.info["PlayResY"])

    def create_style(self, style_name: str, **kwargs):
        """
        创建样式

        Args:
            style_name: 样式名
            **kwargs: 样式参数
        """
        self.subs.styles[style_name] = pysubs2.SSAStyle(**kwargs)
        self.subs.save(str(self.path))

    def apply_style(
            self, style_name: str, events_filter: callable = lambda event: True
    ):
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

    def apply_style_by_index(self, index: int):
        """
        应用样式

        Args:
            index: 样式索引
        """
        style_name = list(self.subs.styles.keys())[index]
        self.apply_style(style_name)

    def set_max_width(
            self,
            max_width: int,
            font_path: str,
            font_size: int,
            margin_left: int = 20,
            margin_right: int = 20,
    ):
        """
        设置最大宽度

        Args:
            max_width: 最大宽度
            font_path: 字体路径
            font_size: 字号
            margin_left: 左边距
            margin_right: 右边距
        """
        new_events = []
        for i, event in enumerate(self.subs.events):
            lines = textwrap.wrap(event.text.strip(), width=max_width)
            # region 固定位置
            # line_start_y = self.height - (100+len(lines)*10)
            # for line in lines:
            #     # new_events.append(
            #     #     pysubs2.SSAEvent(start=event.start, end=event.end, style=event.style, name="", text=line))
            #     text_width, text_height = Text(line).calculate_text_width(font_path, font_size)
            #     pos_x = (self.width - text_width) // 2
            #     new_line = f"{{\\\\an1\\\\pos({pos_x},{line_start_y})}}" + line
            #     new_events.append(
            #         pysubs2.SSAEvent(start=event.start, end=event.end, style=event.style, name="", text=new_line))
            #     line_start_y += text_height+10
            # endregion

            # region 自动位置
            new_line = r"\N\N".join(lines)
            new_events.append(
                pysubs2.SSAEvent(
                    start=event.start,
                    end=event.end,
                    style=event.style,
                    name="",
                    text=new_line,
                )
            )
            # endregion

            # new_events.append(
            #     pysubs2.SSAEvent(start=event.start, end=event.end, style=event.style, name="", text=new_line))
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


# endregion

# region 视频文件


class VideoFile(File):

    def __init__(self, path: str = None):
        super().__init__(path)

    def extract_audio(self, audio_file_name: str = None) -> "AudioFile":
        """
        提取视频的音频,然后放到视频文件的同级目录下

        Args:
            audio_file_name: 音频文件的名称,带后缀,比如"audio.mp3",如果没有指定,则默认为 "${视频文件名}.mp3"


        Returns:
            AudioFile: 音频文件对象
        """
        video_file_name = self.path.name
        if audio_file_name is None:
            audio_file_name = f"{self.path.stem}.mp3"
        audio_file_path = self.path.parent / audio_file_name
        CommandLine.run(
            f"ffmpeg -i {str(self.path.absolute())} -q:a 0 -map a {str(audio_file_path.absolute())}"
        )
        return AudioFile(str(audio_file_path))

    @property
    def volume(self):
        """
        获取视频音量
        """
        from pyext.ffmpeg import Ffmpeg

        ffmpeg = Ffmpeg.from_env()
        return ffmpeg.get_video_volume(self)

    @property
    def resolution(self):
        """
        获取视频分辨率

        Returns:
            tuple[int, int]: 宽度, 高度
        """
        result = CommandLine.run_and_get(
            f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "{self.path.absolute()}"'
        )
        width, height = result.stdout.strip().split("x")
        return int(width), int(height)

    def resize(self, new_width: int, new_height: int) -> "VideoFile":
        """
        调整视频分辨率

        Args:
            new_width: 新宽度
            new_height: 新高度

        Returns:
            VideoFile: 新的视频文件对象
        """
        new_video_file = self.path.parent / f"{self.path.stem}-resized.mp4"
        output = CommandLine.run_and_get(
            f"""ffmpeg -i "{str(self.path.absolute())}" -vf scale={new_width}:{new_height} -c:a copy  "{str(new_video_file.absolute())}" """
        )
        return VideoFile(str(new_video_file))


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

        Args:
            model: Pydantic 模型类

        Returns:
            TPM: Pydantic 模型实例
        """
        with open(self.path, "r", encoding="utf-8") as file:
            yaml_data = yaml.safe_load(file)

        # 将 YAML 数据转换为 Pydantic 类实例
        return model(**yaml_data)


# endregion


# region Json文件
class JsonFile(File):

    def __init__(self, path: str, auto_create_parent_dir=False):
        super().__init__(path, auto_create_parent_dir)

    def read_dict(self) -> dict[str, any]:
        """
        读取文件内容并将其转换为字典对象
        """
        with open(self.path, "r", encoding="utf-8") as file:
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
        with open(self.path, "r", encoding="utf-8") as file:
            return dataclass.from_json(file.read())

    def write_pydanitc_model(self, model: TPM):
        """
        将 Pydantic 模型写入文件

        Args:
            model: Pydantic 模型

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
        if json_str.startswith("\ufeff"):
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
        if json_str.startswith("\ufeff"):
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
        with open(self.path, "r", encoding="utf-8") as file:
            return Dict(json.load(file))

    def read_as_pydanitc_model(
            self, model: Type[TPM], additional_data: dict[str, any] = None
    ) -> TPM:
        """
        读取文件内容并将其转换为 Pydantic 模型

        Args:
            model: Pydantic 模型
            additional_data: 附加数据
        Returns:
            Pydantic 模型实例

        Raises:
            BusinessException: 读取文件内容失败时抛出异常
        """
        with open(self.path, "r", encoding="utf-8") as file:
            try:
                dict = self.read_as_addict()
                if additional_data:
                    dict.update(additional_data)
                return model(**dict)
            except Exception as e:
                raise parse_exceptions(e)


# endregion


# region 目录
class Directory(object):
    def __init__(self, path: str, auto_create=True):
        """
        创建一个位于指定路径上的目录对象

        Args:
            path: 目录路径
            auto_create: 是否自动创建目录,默认为True
        """
        if not path:
            raise IOError(f"路径{path}不是一个有效的路径")
        self.path = PathlibPath(path)
        if auto_create and not self.path.exists():
            self.path.mkdir(parents=True)
        if not self.path.is_dir():
            raise ValueError(f"路径 {path} 不是一个目录")

    def has_sibling(self, name: str):
        """
        检查这个目录所在的同级目录中是否存在指定名称的目录

        Args:
            name: 要检查的目录名称
        
        Returns:
            bool - 如果存在指定名称的目录，则返回 True，否则返回 False。
        
        Examples:
            假设有如下目录结构：
            ```markdown
                📦resources
                ┣ 📂fonts
                ┣ 📂font_presets
                ┗ 📂prompts
            ```
            >>> dir = Directory("resources")
            >>> dir.has_sibling("prompts")
            True
        """
        return self.path.parent.joinpath(name).exists()

    def copy_to_sibling(self, name: str):
        """
        将这个目录复制为同级目录

        Args:
            name: 新目录的名称

        Returns:
            Directory - 新目录对象
        """
        npath = shutil.copytree(self.path, self.path.parent / name)
        return Directory(str(npath))

    @property
    def absolute_path(self):
        """
        获取这个目录的绝对路径
        """
        return str(self.path.absolute())

    @property
    def last_modified(self):
        """
        获取文件的最后修改时间
        """
        # 获取文件的状态信息
        file_stat = os.stat(self.path)
        # 获取最后修改时间
        modification_time = file_stat.st_mtime
        # 将时间戳转换为 datetime 对象
        modification_datetime = datetime.datetime.fromtimestamp(modification_time)
        return modification_datetime

    @property
    def name(self):
        """
        获取这个目录的名称
        """
        return self.path.name

    # region 删除目录
    def delete(self):
        """
        删除目录
        """
        shutil.rmtree(self.path)

    # endregion

    # region 根据文件名查找文件
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

    # endregion

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

    def new_folders(self, sub_folder_path: str) -> "Directory":
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
        return [Directory(str(f)) for f in self.path.iterdir() if f.is_dir()]

    def list_files(self):
        """
        列出目录下的所有文件
        """
        return [f for f in self.path.iterdir() if f.is_file()]

    def list_json_files(self):
        """
        列出目录下的所有json文件
        """
        return [
            JsonFile(str(f))
            for f in self.path.iterdir()
            if f.is_file() and f.suffix == ".json"
        ]

    def list_ass_files(self):
        """
        列出目录下的所有ass文件
        """

        def parse(f):
            try:
                return AssSubtitleFile(str(f))
            except:
                logger.info(f"无法将文件{f}读取为一个ass文件")
                return None

        ret = [
            parse(f) for f in self.path.iterdir() if f.is_file() and f.suffix == ".ass"
        ]

        return [f for f in ret if f is not None]

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
            print(
                CommandLine.run_and_get(
                    f"git commit -am '{message}'", cwd=str(self.path)
                )
            )

    @classmethod
    def from_remote(
            cls,
            url: str,
            directory: str = None,
            name: str = None,
            branch: str = "master",
            recursive: bool = False,
    ):
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


# region 表示一个图片文件
class ImageFile(File):
    def __init__(self, path: str):
        """
        创建一个图片文件
        """
        super().__init__(path)

    @property
    def size(self):
        """
        获取图片大小
        """
        from PIL import Image

        image = Image.open(self.path)
        width, height = image.size
        return Size(width, height)


# endregion


# region 压缩文件
class CompressedFile(File):
    def __init__(self, path: str):
        """
        表示一个压缩文件
        """
        super().__init__(path)


# region zip文件
class ZipFile(CompressedFile):
    def __init__(self, path: str):
        """
        表示一个zip文件
        """
        super().__init__(path)

    def read_file_content(self, file_name, password=None):
        """
        读取zip压缩包中指定文件的内容

        Args:
            file_name: 文件名
            password: 密码

        Returns:
            str -文件内容
        """
        try:
            with zipfile.ZipFile(self.path, "r") as zf:
                # 获取文件信息
                file_info = zf.getinfo(file_name)

                # 读取文件内容
                with zf.open(
                        file_info, pwd=password.encode() if password else None
                ) as file:
                    content = file.read().decode("utf-8")

                return content
        except zipfile.BadZipFile:
            logger.error(f"Error: {self.path} is not a valid ZIP file.")
        except KeyError:
            logger.error(f"Error: {file_name} not found in the ZIP file.")
        except RuntimeError as e:
            if "Bad password" in str(e):
                logger.error(f"Error: Incorrect password for {self.path}")
            else:
                logger.error(f"Error reading {file_name}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

        return None


# endregion


# endregion


if __name__ == "__main__":
    # json_file = JsonFile("../.locator/jianyingpro.cnstore")
    # json_file.set_value_by_jsonpath(
    #     "locators[6].content.childControls[0].childControls[0].childControls[0].identifier.index.value", 2)

    # httpd.socket = ssl.wrap_socket(httpd.socket,
    #                                keyfile="/path/to/key.pem",
    #                                certfile='/path/to/cert.pem', server_side=True)
    # print(Directory("../.data/videos").as_static_file_server())
    # time.sleep(1000)
    # pass
    video_file = VideoFile(
        r"C:\Users\cruld\Documents\WeChat Files\wxid_gsdq4x6zge5a12\FileStorage\Video\2024-08\output.mp4"
    )
    # print(video_file.resolution)
    new_video_file = video_file.resize(1080, 1920)
    print(new_video_file.exists())
    print(new_video_file.resolution)
