from flask import Request


def is_access_from_local_machine(request_or_host) -> bool:
    """
    判断请求是否来自本地机器

    Args:
        request_or_host: 请求对象或主机地址

    Returns:
        bool: 是否来自本地机器
    """

    def check(host):
        return host.count("localhost") > 0 or host.count("127.0.0.1") > 0

    if isinstance(request_or_host, Request):
        return check(request_or_host.host)
    if isinstance(request_or_host, str):
        return check(request_or_host)

    raise Exception("无法判断请求是否来自本地机器")
