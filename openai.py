# 定义泛型类型变量
import json
from typing import TypeVar, Type

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def generate_pydantic_instance(open_client: OpenAI, prompt: str, model: Type[T]) -> T:
    """
    调用 OpenAI API，根据提示词生成符合指定 Pydantic 类型的实例.

    :param open_client: OpenAI 客户端对象
    :param prompt: 提示词
    :param model: Pydantic 泛型类型
    :return: Pydantic 类型的实例
    """
    # 调用 OpenAI API 生成 JSON 数据
    response = open_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"""{prompt},返回的数据需要符合以下 json schema: {json.dumps(model.model_json_schema(), indent=4)}
"""
            }
        ],
        response_format={"type": "json_object"}
    )
    # print(response)
    # 提取生成的 JSON 数据
    result_text = response.choices[0].message.content.strip()

    # 解析 JSON 数据为 Pydantic 实例
    data_dict = json.loads(result_text)
    instance = model(**data_dict)
    return instance
