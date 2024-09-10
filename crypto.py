import base64
from Cryptodome.Random import get_random_bytes
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
class AESCipher:
    def __init__(self, key):
        self.key = key.encode('utf-8')[:32].ljust(32, b'\0')  # 确保密钥是32字节长

    def encrypt(self, data):
        """
        加密数据
        
        Args:
            data (str): 要加密的数据
        
        Returns:
            str: 加密后的数据，以Base64编码
        """
                # 生成随机的16字节IV
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        
        # 对数据进行填充并加密
        padded_data = pad(data.encode('utf-8'), AES.block_size)
        encrypted_data = cipher.encrypt(padded_data)
        
        # 将IV和加密后的数据组合，并进行Base64编码
        return base64.b64encode(iv + encrypted_data).decode('utf-8')

    def decrypt(self, encrypted_data):
        """
        解密数据
        
        Args:
            encrypted_data (str): 加密后的数据

        Returns:
            str: 解密后的数据
        """
        # 解码Base64
        encrypted_data = base64.b64decode(encrypted_data)
        
        # 提取IV和加密数据
        iv = encrypted_data[:16]
        encrypted_data = encrypted_data[16:]
        
        # 创建解密器并解密
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # 去除填充并返回解密后的数据
        return unpad(decrypted_data, AES.block_size).decode('utf-8')