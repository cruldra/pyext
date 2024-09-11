from dataclasses import dataclass
from typing import Optional, ClassVar

from pydantic import ValidationError


class BusinessException(Exception):

    def __init__(self, code: int, message: Optional[str] = None, reference_url: Optional[str] = None,
                 cause: Optional[Exception] = None):
        self.code = code
        """错误代码"""
        self.message = message
        """错误信息"""
        self.reference_url = reference_url
        """参考链接"""
        self.cause = cause
        """原因"""

    def __str__(self):
        return f"错误代码: {self.code} \n 详情: {self.message} \n 参考链接: {self.reference_url}"

class NetworkException(BusinessException):
    __网络异常_CODE: ClassVar[int] = 23360
    
    @classmethod
    def generic(cls , msg="网络异常"):
        return cls(code=NetworkException.__网络异常_CODE,
                   message=msg)
    
class AuthorizationException(BusinessException):
    __未授权的用户_CODE: ClassVar[int] = 23361

    @classmethod
    def 未授权的用户(cls):
        return cls(code=AuthorizationException.__未授权的用户_CODE,
                   message="未授权的用户")


class ValidationException(BusinessException):
    # 类变量，相当于 Kotlin 的 companion object 中的静态变量
    PYDANTIC_VALIDATION_ERROR: ClassVar[int] = 19781

    @classmethod
    def parse(cls, exception: Exception) -> Optional['ValidationException']:
        if (isinstance(exception, ValidationError)):
            exception: ValidationError = exception
            return cls(
                code=cls.PYDANTIC_VALIDATION_ERROR,
                message=ValidationException.get_pydantic_detailed_error_info(exception),
                reference_url="https://docs.pydantic.dev/latest/errors/errors/"
            )
        return None

    @staticmethod
    def get_pydantic_detailed_error_info(e: ValidationError) -> str:
        messages = []
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])

            messages.append(
                f"尝试将值{error['input']}设置到Pydantic模型[{e.title}]的[{field_path}]路径时出错: {error['msg']} ,错误类型: {error['type']}")

        return "\n".join(messages)


def parse_exceptions(exception: Exception) -> Optional[BusinessException]:
    """
    解析异常并返回相应的业务异常。
    """
    exception = ValidationException.parse(exception)
    # if  not exception:
    #     exception
    return exception


def _calculate_exception_code(message: str) -> int:
    """
    计算异常代码。
    将消息字符串的每个字符的ASCII码相加，然后取模1000000以确保结果在合理范围内。
    """
    return sum(ord(char) for char in message) % 1000000


if __name__ == '__main__':
    print(_calculate_exception_code("ScriptException"))
