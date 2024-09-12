# 定义泛型类型变量
import json
from dataclasses import field
from typing import TypeVar, Type, List, Optional

import requests
from addict import Dict
from pydantic import BaseModel

from pyext.io import AudioFile

T = TypeVar('T', bound=BaseModel)


class ImageData(BaseModel):
    revised_prompt: Optional[str] = None
    """修改后的提示"""

    url: Optional[str] = None
    """URL"""


class ImageGenerationResponse(BaseModel):
    created: Optional[int] = 0
    """创建时间"""

    data: Optional[List[ImageData]] = None
    """数据"""


class ImageGenerationRequest(BaseModel):
    prompt: Optional[str] = None
    """提示"""

    model: str = "dall-e-3"
    """模型"""

    n: int = 1
    """数量"""

    quality: str = "hd"
    """质量"""

    size: str = "1792x1024"
    """尺寸"""

    style: str = "vivid"
    """风格"""


class Message(BaseModel):
    role: str = "user"
    """角色"""

    content: str = ""
    """内容"""

    @classmethod
    def user_say(cls, content: str):
        return cls(role="user", content=content)

    @classmethod
    def assistant_say(cls, content: str):
        return cls(role="assistant", content=content)

    @classmethod
    def system_say(cls, content: str):
        return cls(role="system", content=content)


class Choice(BaseModel):
    index: int = 0
    """索引"""

    message: Message = field(default_factory=Message)
    """消息"""

    logprobs: object = None
    """日志概率"""

    finish_reason: str = "stop"
    """结束原因"""


class Usage(BaseModel):
    prompt_tokens: int = 0
    """提示令牌"""

    completion_tokens: int = 0
    """完成令牌"""

    total_tokens: int = 0
    """总令牌"""


class ChatCompletion(BaseModel):
    id: str = ""
    """ID"""

    object: str = "chat.completion"
    """对象"""

    created: int = 0
    """创建时间"""

    model: str = "gpt-4o-2024-05-13"
    """模型"""

    choices: List[Choice] = field(default_factory=list)
    """选择"""

    usage: Usage = field(default_factory=Usage)
    """使用"""

    system_fingerprint: Optional[str] = None
    """系统指纹"""


class ChatRequest(BaseModel):
    messages: List[Message] = field(default_factory=list)
    """消息"""

    model: str = "gpt-4o"
    """模型"""

    frequency_penalty: float = 0.0
    """频率惩罚"""

    logprobs: bool = False
    """日志概率"""

    presence_penalty: float = 0.0
    """存在惩罚"""

    stream: bool = False
    """流"""

    temperature: float = 1.0
    """温度"""

    top_p: float = 1.0
    """顶级P"""


class OpenAiClient:
    """
    OpenAI 客户端
    """

    def __init__(self, base_url: str, key: str):
        self.base_url = base_url
        self.key = key

    def stt(self,audio_file:AudioFile):
        """
        语音转文字
        Args:
            audio_file (AudioFile): 音频文件

        Returns:
            str: 文字
        """
        url = f"{self.base_url}audio/transcriptions"
        headers = {
            'Authorization': f'Bearer {self.key}'
        }
        payload = {'model': 'whisper-1'}
        files = [
            ('file', (audio_file.name, open(audio_file.path, 'rb'), 'audio/mpeg'))
        ]
        response = requests.request("POST", url, headers=headers, data=payload, files=files)

        return Dict(response.json()).text

    def chat_completion(self, request: ChatRequest) -> ChatCompletion:
        """
        聊天补全

        Args:
            request (ChatRequest): 请求

        Returns:
            ChatCompletion: 完成
        """
        url = f"{self.base_url}chat/completions"
        headers = {
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json; charset=utf-8'
        }

        response = requests.request("POST", url, headers=headers, data=request.model_dump_json(), timeout=(10, 600))
        response.raise_for_status()
        return ChatCompletion(**response.json())


def generate_pydantic_instance(open_client: OpenAiClient, prompt: str, model: Type[T]) -> T:
    """
    调用 OpenAI API，根据提示词生成符合指定 Pydantic 类型的实例.

    Args:
        open_client (OpenAiClient): OpenAI 客户端
        prompt (str): 提示词
        model (Type[T]): 目标 Pydantic 类型

    Returns:
        T: 生成的 Pydantic 实例
    """
    # 调用 OpenAI API 生成 JSON 数据
    response = open_client.chat_completion(ChatRequest(
        model="gpt-4o-mini",
        messages=[Message.user_say(
            f"""{prompt},返回的数据需要符合以下 json schema: {json.dumps(model.model_json_schema(), indent=4)}""")],
        response_format={"type": "json_object"}
    ))
    # print(response)
    # 提取生成的 JSON 数据
    result_text = response.choices[0].message.content.strip()

    # 解析 JSON 数据为 Pydantic 实例
    data_dict = json.loads(result_text)
    instance = model(**data_dict)
    return instance
