import platform
import re
from dataclasses import dataclass
from typing import List, Type, TypeVar

import docker
from docker import DockerClient
from loguru import logger

from pyext.commons import CommandLine
from pyext.io import VideoFile, Mp3File, AssSubtitleFile, AudioFile, ImageFile, SubtitleFile, SrtSubtitleFile

TAF = TypeVar('TAF', bound=AudioFile)


@dataclass
class ImageFragment(object):
    """图像片段"""
    image_file: ImageFile
    """图像文件"""
    begin: float
    """开始时间"""
    end: float
    """结束时间"""
    x: float
    """x坐标"""
    y: float
    """y坐标"""


class Ffmpeg(object):

    def __init__(self):
        super().__init__()

    @classmethod
    def from_env(cls):
        """
        自动

        """
        try:
            docker_client = docker.from_env()
            logger.info("使用Docker运行ffmpeg")
            return DockerFfmpeg(docker_client)
        except:
            logger.info("使用本地ffmpeg")
            return LocalFfmpeg()

    def video_denoise(self, video_file: VideoFile, video_filter: str, audio_filter: str) -> VideoFile:
        """
        视频降噪

        Args:
            video_file: 视频文件
            video_filter: 视频降噪滤镜
            audio_filter: 音频降噪滤镜

        Returns:
            VideoFile: 新的视频文件
        """
        raise NotImplementedError()

    def add_background_music(self, video_file: VideoFile, audio_file: AudioFile, volume: int = None) -> VideoFile:
        """
        为视频添加背景音乐

        Args:
            video_file: 视频文件
            audio_file: 音频文件
            volume: 音量,1~100之间的整数

        Returns:
            VideoFile - 新的视频文件
        """
        raise NotImplementedError()

    def change_volume(self, video_file: VideoFile, volume: int) -> VideoFile:
        """
        调整视频音量

        Args:
            video_file: 视频文件
            volume: 音量,1~100之间的整数

        Returns:
            VideoFile: 新的视频文件
        """
        raise NotImplementedError()

    def change_speed(self, video_file: VideoFile, speed: float) -> VideoFile:
        """
        调整视频速度
        Args:
            video_file: 视频文件
            speed: 速度,大于0的浮点数

        Returns:
            VideoFile: 新的视频文件
        """
        raise NotImplementedError()

    def add_subtitle_to_video(self, video_file: VideoFile, subtitle_file: SubtitleFile,
                              new_name: str, font_directory: str) -> VideoFile:
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

    def add_image_fragments_to_video(self, video_file: VideoFile, image_fragments: List[ImageFragment],
                                     new_name: str) -> VideoFile:
        """
        把多个图像片段添加到视频中
        Args:
            video_file: 视频文件
            image_fragments: 图像片段
            new_name: 新文件名

        Returns:
            新的视频文件
        """
        raise NotImplementedError()

    def add_img_subtitle_to_video(self, video_file: VideoFile, img_file: ImageFile, x: int, y: int,
                                  begin_time: float,
                                  end_time: float, new_name: str) -> VideoFile:
        """
        把图片当成字幕添加到视频中

        Args:
            video_file: 视频文件
            img_file: 图片文件
            x: 图片的x坐标
            y: 图片的y坐标
            begin_time: 开始时间
            end_time: 结束时间
            new_name: 新文件名

        Returns:
            新的视频文件
        """
        raise NotImplementedError()

    def video_to_audio(self, video_file: VideoFile, audio_type: Type[TAF]) -> TAF:
        """
        将视频文件转换为音频文件

        Args:
            video_file: 视频文件
            audio_type: 音频文件类型

        Returns:
            AudioFile: 音频文件对象
        """
        raise NotImplementedError()

    def srt_to_ass(self, srt_file: SrtSubtitleFile) -> AssSubtitleFile:
        """
        srt字幕转ass字幕
        """
        raise NotImplementedError()

    def get_video_volume(self, video_file: VideoFile) -> tuple[float, float]:
        """
        获取视频的音量

        Args:
            video_file: 视频文件

        Returns:
            音量
        """
        raise NotImplementedError()


# region 本地安装的ffmpeg
class LocalFfmpeg(Ffmpeg):
    def __init__(self):
        """
        使用本地ffmpeg
        """
        super().__init__()

    def video_denoise(self, video_file: VideoFile, video_filter: str = "atadenoise",
                      audio_filter="afftdn=nf=-25") -> VideoFile:
        output_video_file = video_file.path.parent / f"{video_file.path.stem}_denoise.{video_file.suffix}"
        command = [
            'ffmpeg',
            '-y',
            '-i', video_file.name,
            '-vf', video_filter,
            '-af', audio_filter,
            # '-c:v', 'libx264',  # 使用H.264编码视频
            # '-preset', 'medium',  # 编码速度和质量的平衡
            # '-crf', '23',  # 控制视频质量，范围0-51，越低质量越好
            # '-c:a', 'aac',  # 使用AAC编码音频
            # '-b:a', '192k',  # 设置音频比特率
            output_video_file.name
        ]
        output = CommandLine.run_and_get(command, cwd=str(video_file.path.parent.absolute()), encoding="utf-8")
        logger.info(f"视频降噪: {output.output}")
        return VideoFile(str(output_video_file))

    def add_background_music(self, video_file: VideoFile, audio_file: AudioFile, volume: int = None) -> VideoFile:
        if volume and not 1 <= volume <= 100:
            raise ValueError("音量级别必须在 1 到 100 之间")
        if volume:
            # 将 1-100 映射到 0.01-2.0
            volume_factor = (volume - 1) / 49.5 + 0.01
        output_video_file = video_file.path.parent / f"{video_file.path.stem}_with_music.{video_file.suffix}"
        audio_file.copy_to(str(output_video_file.parent))
        command = [
            "ffmpeg",
            "-y",
            "-i", video_file.name,
            "-stream_loop", "-1",
            "-i", audio_file.name,
            "-filter_complex",
            f"[1:a]aloop=loop=-1:size=2e+09{f",volume={volume_factor}" if volume else ""}[a];[0:a][a]amix=inputs=2:duration=first",
            "-c:v", "copy",
            output_video_file.name
        ]
        output = CommandLine.run_and_get(command, cwd=str(video_file.path.parent.absolute()), encoding="utf-8")
        logger.info(f"添加背景音乐: {output.output}")
        return VideoFile(str(output_video_file))

    def change_speed(self, video_file: VideoFile, speed_factor: float) -> VideoFile:
        if speed_factor <= 0:
            raise ValueError("速度因子必须大于0")
        # 视频速度的改变是通过调整 PTS（Presentation Time Stamp）来实现的 当我们想要加速视频时（speed_factor > 1），我们需要减少 PTS，所以用 1 除以 speed_factor
        video_tempo = 1 / speed_factor
        # 音频速度直接使用 speed_factor，因为 atempo 滤镜期望的值是大于 1 表示加速，小于 1 表示减速
        audio_tempo = speed_factor
        output_video_file = video_file.path.parent / f"{video_file.path.stem}_speed_{speed_factor}.{video_file.suffix}"
        # 对于音频速度的极端变化，我们需要串联多个 atempo 滤镜
        audio_filter = f"atempo={min(2.0, audio_tempo)}"
        while audio_tempo > 2.0:
            audio_filter += f",atempo={min(2.0, audio_tempo / 2.0)}"
            audio_tempo /= 2.0
        command = [
            "ffmpeg",
            "-y",
            "-i", video_file.name,
            "-filter_complex",
            f"[0:v]setpts={video_tempo}*PTS[v];[0:a]{audio_filter}[a]",
            "-map", "[v]",
            "-map", "[a]",
            output_video_file.name
        ]
        output = CommandLine.run_and_get(command, cwd=str(video_file.path.parent.absolute()))
        logger.info(f"改变视频速度:{output.output}")
        return VideoFile(str(output_video_file))

    def video_to_audio(self, video_file: VideoFile, audio_type: Type[TAF]) -> TAF:
        video_dir = str(video_file.path.parent)
        audio_file_path = f"{video_dir}/{video_file.path.stem}.{audio_type.suffix}"
        command = (
            f"ffmpeg -y -i  {str(video_file.path.absolute())} -q:a 0 -map a {audio_file_path}"
        )
        output = CommandLine.run_and_get(command)
        logger.info(f"将视频转换为音频:{output.stdout}")
        if audio_type == Mp3File:
            return Mp3File(audio_file_path)
        else:
            raise ValueError(f"不支持的音频文件类型: {audio_type}")

    def srt_to_ass(self, srt_file: SrtSubtitleFile) -> AssSubtitleFile:
        command = f"ffmpeg -y -i {str(srt_file.path.absolute())} {str(srt_file.path.stem)}.ass"
        output = CommandLine.run_and_get(command)
        logger.info(f"将srt字幕文件转换为ass字幕文件:{output.stdout}")
        return AssSubtitleFile(str(srt_file.path.parent / f"{srt_file.path.stem}.ass"))

    def get_video_volume(self, video_file: VideoFile) -> tuple[float, float]:
        """
        获取视频的音量

        Args:
            video_file: 视频文件

        Returns:
            tuple[float, float] - 平均音量,最大音量
        """
        command = [
            "ffmpeg",
            "-i", video_file.name,
            "-filter:a", "volumedetect",
            "-f", "null",
            "NUL" if platform.system() == "Windows" else "/dev/null"
        ]
        output = CommandLine.run_and_get(command, cwd=str(video_file.path.parent.absolute())).output
        logger.info(f"获取视频音量:{output}")
        mean_volume_match = re.search(r"mean_volume: ([-\d.]+) dB", output)
        max_volume_match = re.search(r"max_volume: ([-\d.]+) dB", output)
        mean_volume = float(mean_volume_match.group(1)) if mean_volume_match else None
        max_volume = float(max_volume_match.group(1)) if max_volume_match else None
        return mean_volume, max_volume

    def change_volume(self, video_file: VideoFile, volume: int) -> VideoFile:
        if not 1 <= volume <= 100:
            raise ValueError("音量级别必须在 1 到 100 之间")
        # 将 1-100 映射到 0.01-2.0
        volume_factor = (volume - 1) / 49.5 + 0.01
        output_video_file = video_file.path.parent / f"{video_file.path.stem}_volume_{volume}.mp4"
        command = [
            "ffmpeg",
            "-y",
            "-i", video_file.name,
            "-filter:a", f"volume={volume_factor}",
            "-c:v", "copy",
            output_video_file.name
        ]
        output = CommandLine.run_and_get(command, cwd=str(video_file.path.parent.absolute()))
        logger.info(f"调整视频音量:{output.output}")
        return VideoFile(str(output_video_file))

    def add_subtitle_to_video(self, video_file: VideoFile, subtitle_file: SubtitleFile, new_name: str,
                              font_directory: str) -> VideoFile:
        command = (
            f"ffmpeg -y -i {str(video_file.path.absolute())} -vf 'ass={str(subtitle_file.path.absolute())}' -c:a copy {str(video_file.path.parent / new_name)}"
        )
        output = CommandLine.run_and_get(command)
        logger.info(f"为视频添加字幕:{output.stdout}")
        return VideoFile(str(video_file.path.parent / new_name))

    def add_image_fragments_to_video(self, video_file: VideoFile, image_fragments: List[ImageFragment],
                                     new_name: str) -> VideoFile:
        sub_cmd1 = " ".join([f"-i {fragment.image_file.path.absolute()}" for fragment in image_fragments])

        # 构建 filter_complex 列表
        filter_complex = []

        for i, fragment in enumerate(image_fragments):
            if i == 0:
                input_label = '0:v'
            else:
                input_label = f'v{i}'

            output_label = f'v{i + 1}'

            filter_complex.append(
                f"[{input_label}][{i + 1}:v]overlay={fragment.x}:{fragment.y}:enable='between(t,{fragment.begin},{fragment.end})'[{output_label}]")

        # 将 filter_complex 列表合并为一个字符串
        filter_complex_str = ';'.join(filter_complex)

        command = f"ffmpeg -y -i {video_file.path.absolute()} {sub_cmd1} -filter_complex \"{filter_complex_str}\" -map \"[v{len(image_fragments)}]\" -map 0:a  -c:a copy {video_file.path.parent.absolute() / new_name}"
        logger.info(f"使用以下命令为视频添加图片片段:\n{command}")
        # 执行命令
        output = CommandLine.run_and_get(command)
        logger.info(f"为视频添加图片片段:{output.output}")

        return VideoFile(str(video_file.path.parent / new_name))


# endregion


# region 基于docker的ffmpeg
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

    def video_to_audio(self, video_file: VideoFile, audio_type: Type[TAF]) -> TAF:
        command = (
            f"-y -i /tmp_app/{video_file.path.name} -q:a 0 -map a /tmp_app/{video_file.path.stem}.{audio_type.suffix}"
        )
        full_command = (
            f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logger.info(f"使用以下命令行先将视频文件转换为音频文件: {full_command}")
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
        logger.info(f"将视频文件转换为音频文件的日志: {logs}")
        if audio_type == Mp3File:
            return Mp3File(str(video_file.path.parent / f"{video_file.path.stem}.{Mp3File.suffix}"))
        else:
            raise ValueError(f"不支持的音频文件类型: {audio_type}")

    def srt_to_ass(self, srt_file: SrtSubtitleFile) -> AssSubtitleFile:
        command = f'-y -i /tmp_app/{srt_file.path.name} /tmp_app/{srt_file.path.stem}.ass'
        full_command = (
            f"docker run --rm -it -v {str(srt_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logger.info(f"使用以下命令行将srt字幕文件转换为ass字幕文件: {full_command}")
        logs = self.docker_client.containers.run(
            self.ffmpeg_image,
            command,
            volumes={str(srt_file.path.parent.absolute()): {'bind': '/tmp_app', 'mode': 'rw'}},
            remove=True,
            tty=True,
            stdin_open=True
        ).decode('utf-8').strip()
        logger.info(f"将srt字幕文件转换为ass字幕文件的日志: {logs}")
        return AssSubtitleFile(str(srt_file.path.parent / f"{srt_file.path.stem}.ass"))

    def add_image_fragments_to_video(self, video_file: VideoFile, image_fragments: List[ImageFragment],
                                     new_name: str) -> VideoFile:
        sub_cmd1 = " ".join([f"-i /tmp_app/images/{fragment.image_file.name}" for fragment in image_fragments])

        # 构建 filter_complex 列表
        filter_complex = []

        for i, fragment in enumerate(image_fragments):
            if i == 0:
                input_label = '0:v'
            else:
                input_label = f'v{i}'

            output_label = f'v{i + 1}'

            filter_complex.append(
                f"[{input_label}][{i + 1}:v]overlay={fragment.x}:{fragment.y}:enable='between(t,{fragment.begin},{fragment.end})'[{output_label}]")

        # 将 filter_complex 列表合并为一个字符串
        filter_complex_str = ';'.join(filter_complex)

        command = f"-y -i /tmp_app/{video_file.path.name} {sub_cmd1} -filter_complex \"{filter_complex_str}\" -map \"[v{len(image_fragments)}]\" -map 0:a  -c:a copy /tmp_app/{new_name}"

        full_command = f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app -v {str(image_fragments[0].image_file.path.parent.absolute())}:/tmp_app/images {self.ffmpeg_image} {command}"
        logger.info(f"使用以下命令行将多张图片添加到视频: {full_command}")

        logs = self.docker_client.containers.run(
            self.ffmpeg_image,
            command,
            volumes={str(video_file.path.parent.absolute()): {'bind': '/tmp_app', 'mode': 'rw'},
                     str(image_fragments[0].image_file.path.parent.absolute()): {"bind": "/tmp_app/images",
                                                                                 "mode": "rw"},
                     },
            remove=True,
            tty=True,
            stdin_open=True
        ).decode('utf-8').strip()

        logger.info(f"将多张图片添加到视频的日志: {logs}")
        return VideoFile(str(video_file.path.parent / new_name))

    def add_img_subtitle_to_video(self, video_file: VideoFile, img_file: ImageFile,
                                  x: int, y: int,
                                  begin_time: float,
                                  end_time: float, new_name: str) -> VideoFile:
        command = f"-y -i /tmp_app/{video_file.path.name} -i /tmp_app/images/{img_file.path.name} -filter_complex \"[0:v][1:v]overlay={x}:{y}:enable='between(t,{begin_time},{end_time})'\" -c:a copy /tmp_app/{new_name}"
        full_command = (
            f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logger.info(f"使用以下命令行为视频添加字幕: {full_command}")
        logs = (
            self.docker_client.containers.run(
                self.ffmpeg_image,
                command,
                volumes={str(video_file.path.parent.absolute()): {"bind": "/tmp_app", "mode": "rw"},
                         str(img_file.path.parent.absolute()): {"bind": "/tmp_app/images", "mode": "rw"},
                         },
                remove=True,
                tty=True,
                stdin_open=True,
            )
            .decode("utf-8")
            .strip()
        )
        logger.info(f"为视频添加字幕的日志: {logs}")
        return VideoFile(str(video_file.path.parent / new_name))

    def add_subtitle_to_video(self, video_file: VideoFile, subtitle_file: SubtitleFile,
                              new_name: str, font_directory: str) -> VideoFile:
        command = (
            f"-y -i /tmp_app/{video_file.path.name} -vf 'ass=/tmp_app/{subtitle_file.path.name}' -c:a copy /tmp_app/{new_name}"
        )
        full_command = (
            f"docker run --rm -it -v {str(video_file.path.parent.absolute())}:/tmp_app {self.ffmpeg_image} {command}"
        )
        logger.info(f"使用以下命令行为视频添加字幕: {full_command}")
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
        logger.info(f"为视频添加字幕的日志: {logs}")
        return VideoFile(str(video_file.path.parent / new_name))

# endregion
