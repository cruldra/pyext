# 实现一个密钥管理服务用于授权认证
# 有两个部分，一个服务端，一个客户端,服务端用于创建和管理密钥，每个密钥对应一个键是客户端的id,然后客户端获取当前机器码再发送到服务端去获取密钥，如果没获取到就抛出异常
import platform
import uuid
import winreg

import requests
import typer


def get_windows_uuid():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            return winreg.QueryValueEx(key, "MachineGuid")[0]
    except WindowsError:
        return None


def get_machine_code():
    """
    [获取机器码](https://poe.com/s/hSOuw5RNsa4epGXjzCvF)

    Returns:
        str: 机器码
    """
    if platform.system() == 'Windows':
        return get_windows_uuid()
    else:
        return f"{platform.node()}-{uuid.getnode()}"



class KeyClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.client_id = get_machine_code()

    def get_key(self):
        print(f"Getting key for client: {self.client_id}")
        response = requests.post(f"{self.server_url}/get_key", json={
            "client_id": self.client_id
        })

        if response.status_code == 200:
            return response.json()['key']
        else:
            raise Exception("Failed to retrieve key")

typer_app = typer.Typer()

@typer_app.command()
def verify(server_url: str="http://8.130.104.39"):
    client = KeyClient(server_url)
    try:
        key = client.get_key()
        print(f"Retrieved key: {key}")
    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == '__main__':
    typer_app()
# # 使用示例
# if __name__ == "__main__":
#     client = KeyClient("http://localhost:5000")
#     try:
#         key = client.get_key()
#         print(f"Retrieved key: {key}")
#     except Exception as e:
#         print(f"Error: {str(e)}")
#
#     #print(get_windows_uuid())