"""
Ed25519签名工具模块

用于对币安API请求payload进行Ed25519签名。

签名流程：
1. payload (query string) -> Ed25519私钥签名 -> Base64编码 -> URL编码
"""

import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


class Ed25519Signer:
    """Ed25519签名器

    使用Ed25519私钥对请求payload进行签名。

    Args:
        private_key_pem: Ed25519私钥（PEM格式）
    """

    def __init__(self, private_key_pem: bytes) -> None:
        """初始化签名器

        Args:
            private_key_pem: Ed25519私钥的PEM格式字节

        Raises:
            ValueError: 如果私钥无效或格式不正确
        """
        try:
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                private_key_pem
            )
        except Exception as e:
            # 尝试作为PEM格式解析
            try:
                self._private_key = serialization.load_pem_private_key(
                    private_key_pem, password=None
                )
                if not isinstance(self._private_key, ed25519.Ed25519PrivateKey):
                    raise ValueError("Key is not an Ed25519 key")
            except Exception:
                raise ValueError(f"Invalid Ed25519 private key: {e}")

    def sign(self, payload: str) -> str:
        """对payload进行签名

        Args:
            payload: 查询字符串格式的payload（如 "symbol=BNBUSDT&timestamp=1234567890"）

        Returns:
            Base64编码的签名字符串

        Raises:
            ValueError: 如果payload为空
        """
        if not payload:
            raise ValueError("payload cannot be empty")

        # 使用私钥对payload进行签名 - 使用ASCII编码，与币安官方文档一致
        signature = self._private_key.sign(payload.encode("ASCII"))

        # Base64编码
        return base64.b64encode(signature).decode("utf-8")

    def verify(self, payload: str, signature: str) -> bool:
        """验证签名

        Args:
            payload: 原始payload字符串
            signature: Base64编码的签名

        Returns:
            签名是否有效
        """
        try:
            signature_bytes = base64.b64decode(signature)
            public_key = self._private_key.public_key()
            # 使用与sign相同的ASCII编码进行验证
            public_key.verify(signature_bytes, payload.encode("ASCII"))
            return True
        except InvalidSignature:
            return False
        except (ValueError, TypeError):
            return False

    @staticmethod
    def generate_keypair() -> tuple[bytes, bytes]:
        """生成Ed25519密钥对

        Returns:
            (私钥PEM, 公钥PEM)元组
        """
        private_key = ed25519.Ed25519PrivateKey.generate()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_key = private_key.public_key()
        # 使用SubjectPublicKeyInfo格式（X.509），与币安要求兼容
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem, public_pem
