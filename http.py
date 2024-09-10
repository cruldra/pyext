from flask import Request


def is_access_from_local_machine(request) -> bool:
    """
    判断请求是否来自本地机器
    
    Args:
        request: 请求对象
    
    Returns:
        bool: 是否来自本地机器
    """
    if isinstance(request, Request):
        return request.host.count("localhost") > 0 or request.host.count("127.0.0.1") > 0
    
    raise Exception("无法判断请求是否来自本地机器")