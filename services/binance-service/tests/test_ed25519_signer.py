"""
测试Ed25519签名工具模块

测试签名工具能够正确对请求payload进行Ed25519签名。
根据币安API要求：
- 签名流程：payload -> Ed25519私钥签名 -> Base64编码 -> URL编码
"""

import pytest
import base64
from unittest.mock import patch, MagicMock


class TestEd25519Signer:
    """Ed25519签名工具测试"""

    def test_sign_returns_base64_encoded_signature(self):
        """测试签名返回Base64编码的结果"""
        from src.utils.ed25519_signer import Ed25519Signer
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        # 生成真实的Ed25519密钥对
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"

        result = signer.sign(payload)

        # 验证结果是Base64编码的字符串
        assert isinstance(result, str)
        # 尝试解码，确保是有效的Base64
        decoded = base64.b64decode(result)
        assert len(decoded) == 64  # Ed25519签名固定64字节

    def test_sign_with_empty_payload(self):
        """测试空payload签名应抛出异常"""
        from src.utils.ed25519_signer import Ed25519Signer
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)

        with pytest.raises(ValueError, match="payload cannot be empty"):
            signer.sign("")

    def test_sign_deterministic(self):
        """测试相同payload产生相同签名"""
        from src.utils.ed25519_signer import Ed25519Signer
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"

        sig1 = signer.sign(payload)
        sig2 = signer.sign(payload)

        # 相同payload应该产生相同签名
        assert sig1 == sig2

    def test_sign_with_special_characters(self):
        """测试包含特殊字符的payload签名"""
        from src.utils.ed25519_signer import Ed25519Signer
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNB/USDT&timestamp=1234567890&extra=data!@#$%"

        result = signer.sign(payload)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_sign_with_invalid_private_key(self):
        """测试使用无效私钥应抛出异常"""
        from src.utils.ed25519_signer import Ed25519Signer

        invalid_key = b"invalid-key-data"

        with pytest.raises(ValueError, match="Invalid Ed25519 private key"):
            Ed25519Signer(invalid_key)

    def test_sign_with_query_string_payload(self):
        """测试使用标准查询字符串payload签名"""
        from src.utils.ed25519_signer import Ed25519Signer
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "timestamp=1699999999999&recvWindow=5000"

        result = signer.sign(payload)

        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert len(decoded) == 64


class TestEd25519SignerIntegration:
    """Ed25519签名集成测试（使用真实的密钥对）"""

    def test_sign_with_real_key_generated(self):
        """测试使用真实生成的密钥对进行签名"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        from src.utils.ed25519_signer import Ed25519Signer

        # 生成真实的Ed25519密钥对
        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"

        result = signer.sign(payload)

        # 验证签名
        assert isinstance(result, str)
        decoded_sig = base64.b64decode(result)
        assert len(decoded_sig) == 64

        # 验证签名可以用公钥验证
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # 使用 cryptography 验证签名
        from cryptography.exceptions import InvalidSignature
        try:
            public_key.verify(decoded_sig, payload.encode('utf-8'))
        except InvalidSignature:
            pytest.fail("Signature verification failed")

    def test_verify_valid_signature(self):
        """测试验证有效签名"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        from src.utils.ed25519_signer import Ed25519Signer

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"
        signature = signer.sign(payload)

        # 验证签名
        is_valid = signer.verify(payload, signature)
        assert is_valid is True

    def test_verify_invalid_signature(self):
        """测试验证无效签名"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        from src.utils.ed25519_signer import Ed25519Signer

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"

        # 使用错误的签名
        invalid_signature = "invalid_signature_base64"
        is_valid = signer.verify(payload, invalid_signature)
        assert is_valid is False

    def test_verify_tampered_payload(self):
        """测试验证被篡改的payload"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        from src.utils.ed25519_signer import Ed25519Signer

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "symbol=BNBUSDT&timestamp=1234567890"
        signature = signer.sign(payload)

        # 修改payload后再验证
        tampered_payload = "symbol=ETHUSDT&timestamp=1234567890"
        is_valid = signer.verify(tampered_payload, signature)
        assert is_valid is False

    def test_generate_keypair(self):
        """测试生成密钥对"""
        from src.utils.ed25519_signer import Ed25519Signer

        private_pem, public_pem = Ed25519Signer.generate_keypair()

        assert private_pem is not None
        assert public_pem is not None
        assert b"PRIVATE KEY" in private_pem
        assert b"PUBLIC KEY" in public_pem

    def test_sign_with_pkcs8_format(self):
        """测试使用PKCS8格式私钥"""
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization
        from src.utils.ed25519_signer import Ed25519Signer

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        signer = Ed25519Signer(private_pem)
        payload = "test=123"

        result = signer.sign(payload)
        assert isinstance(result, str)
