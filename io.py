import json
import os.path
import shutil
import threading
import time
from pathlib import Path as PathlibPath
from typing import TypeVar, Type
import http.server
import socketserver
import yaml
from addict import Dict
from jsonpath_ng import parse
from pydantic import BaseModel

from autoext.commons import CommandLine


class File(object):
    def __init__(self, path: str):
        self.path = PathlibPath(path)

    def write_content(self, content: str):
        """
        写入文本内容到该文件中

        :param content: 文本内容
        """
        with self.path.open("w", encoding='utf-8') as f:
            f.write(content)

    def read_content(self):
        """
        读取文件内容

        :return: 文件内容
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


TF = TypeVar('TF', bound=File)
TPM = TypeVar('TPM', bound=BaseModel)


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

    def write_dataclass_json_obj(self, obj):
        """
        对于使用了`@dataclass_json`的数据类对象,将其转换为json字符串并写入文件
        """
        self.write_content(obj.to_json(indent=4))

    def write_pydanitc_model(self, model: TPM):
        """
        将 Pydantic 模型写入文件

        :param model: Pydantic 模型
        """
        self.write_content(model.model_dump_json(indent=4))

    def set_value_by_jsonpath(self, json_path, new_value):
        """
        通过 JSON Path 设置值

        :param json_path: JSON Path
        :param new_value: 新值
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

    def new_file(self, file_name: str) -> TF:
        """
        创建一个新文件

        :param file_name: 文件名
        :return: 文件对象
        """
        file_path = self.path / file_name
        file_path.touch()
        suffix = file_path.suffix
        if suffix == ".json":
            file = JsonFile(str(file_path))
        else:
            file = File(str(file_path))
        return file

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
        :param host: 主机
        :param port: 端口
        :return: 服务器对象
        """
        directory = os.path.abspath(self.path)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

        httpd = socketserver.TCPServer(("", port), Handler)
        # with socketserver.TCPServer(("", port), Handler) as httpd:
        #     print(f"Serving at port {port}")
        #     httpd.serve_forever()
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return httpd, server_thread


# endregion


# region git仓库
class GitRepository(Directory):
    def __init__(self, path: str):
        """
        创建一个git仓库
        """
        super().__init__(path, auto_create=True)
        self.init()

    def init(self):
        """
        初始化一个git仓库
        """
        # 如果已经是git仓库,则不再初始化
        if self.path.joinpath(".git").exists():
            return
        CommandLine.run("git init", cwd=str(self.path))
        CommandLine.run("git add .", cwd=str(self.path))

    def commit(self, message: str, files: list[str] = None):
        """
        提交更改

        :param message: 提交信息
        :param files: 仅提交指定文件
        """
        if files:
            CommandLine.run(f"git add {' '.join(files)}", cwd=str(self.path))
            CommandLine.run(f"git commit -m '{message}'", cwd=str(self.path))
        else:
            CommandLine.run(f"git commit -am '{message}'", cwd=str(self.path))

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
