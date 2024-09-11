"""
针对Dash框架的扩展
"""
import threading
from typing import Any
import dongjak_dash_components2 as ddc
import shortuuid
from dash import dash
from dongjak_dash_components2.starter import MantineNotificationOperations
from flask import Flask
from pydantic import BaseModel, Field


class Notificatioins(object):
    def __init__(self):
        self.id = f"notifications-container-{shortuuid.uuid()}"
        self.ops = MantineNotificationOperations(self.id)


class RunParameters(BaseModel):
    """
    运行参数
    """
    host: str = Field(default="localhost")
    """ 服务器主机名 """
    port: int = Field(default=5000)
    """ 服务器端口 """
    debug: bool = Field(default=False)
    """ 是否开启调试模式 """


class DashApp(object):
    """
    表示一个Dash应用程序
    """

    def __init__(self, layout: Any, flask_server: Flask = None):
        self.flask_server = flask_server
        self.app = dash.Dash(server=flask_server) if flask_server is not None else dash.Dash()
        self.app.layout = layout

    def start_server(self, parameters: RunParameters):
        """
        启动服务器

        Args:
            parameters: 运行参数
        """
        self.flask_server.run(port=parameters.port, host=parameters.host, debug=parameters.debug)

    def start_background_server(self, parameters: RunParameters):
        """
        在新的线程中启动服务器

        Args:
            parameters: 运行参数
        """
        parameters.debug = False
        server_thread = threading.Thread(target=lambda: self.start_server(parameters))
        server_thread.daemon = True
        server_thread.start()
