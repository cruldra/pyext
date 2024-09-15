import requests
import wrapt


def get_ariel_config(url, env: str, key: str) -> str:
    """
    从ariel配置中心获取配置

    Args:
        url: 配置中心地址
        env: 环境
        key: 配置项

    Returns:
        str: 配置值
    """
    url = f"{url}/{env}/{key}"
    response = requests.request("GET", url)
    response.raise_for_status()
    return response.text


class BaseArielConfig:
    def __init__(self, url: str, env: str, key_prefix: str = None):
        self.url = url
        self.env = env
        self.key_prefix = key_prefix


def ariel_config():
    @wrapt.decorator
    def decorator(wrapped, instance, args, kwargs):
        func_name = wrapped.__name__
        if args[0].key_prefix:
            key = f"{args[0].key_prefix}_{func_name}"
        else:
            key = func_name
        result = get_ariel_config(args[0].url, args[0].env, key)
        return result

    return decorator
