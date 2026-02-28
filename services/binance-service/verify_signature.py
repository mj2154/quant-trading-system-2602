"""验证签名流程 - 按照官方文档"""
import base64
from urllib.parse import urlencode
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# 加载私钥
with open("keys/private_key.pem", "rb") as f:
    private_key_pem = f.read()

# 解析PEM格式私钥
private_key = serialization.load_pem_private_key(private_key_pem, password=None)
public_key = private_key.public_key()

# 构建payload - 使用urlencode (和官方文档一致)
params = {
    "timestamp": "1771795064541",
    "recvWindow": "5000"
}

# 按key排序后urlencode
sorted_params = {k: params[k] for k in sorted(params.keys())}
payload = urlencode(sorted_params, encoding='UTF-8')

print(f"Payload: {payload}")

# 签名 - 使用ASCII编码
signature = private_key.sign(payload.encode('ASCII'))
signature_b64 = base64.b64encode(signature).decode("utf-8")

print(f"Signature (Base64): {signature_b64}")
print(f"Signature length: {len(signature_b64)}")

# 验证：用公钥验证
try:
    public_key.verify(signature, payload.encode('ASCII'))
    print("✅ 签名验证通过")
except Exception as e:
    print(f"❌ 签名验证失败: {e}")
