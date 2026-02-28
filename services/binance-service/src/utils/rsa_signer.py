"""
RSA签名器

用于期货API的RSA签名。
"""

import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


class RSASigner:
    """RSA签名器

    使用RSA私钥对payload进行签名（PKCS#8格式）。
    签名算法：RSASSA-PKCS1-v1_5 + SHA-256
    """

    def __init__(self, private_key_pem: bytes) -> None:
        """初始化RSA签名器

        Args:
            private_key_pem: RSA私钥（PEM格式，PKCS#8）

        Raises:
            ValueError: 如果私钥格式无效
        """
        try:
            self._private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
        except Exception as e:
            raise ValueError(f"Invalid RSA private key: {e}") from e

    def sign(self, payload: str) -> str:
        """对payload进行RSA签名

        Args:
            payload: 待签名的字符串

        Returns:
            Base64编码的签名

        Raises:
            RuntimeError: 如果签名失败
        """
        try:
            # 使用SHA-256进行签名
            signature = self._private_key.sign(
                payload.encode('ascii'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Base64编码
            return base64.b64encode(signature).decode('ascii')
        except Exception as e:
            raise RuntimeError(f"Failed to sign payload: {e}") from e
