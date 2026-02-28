"""验证当前签名"""
import base64
from urllib.parse import urlencode
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# 加载私钥
with open("keys/private_key.pem", "rb") as f:
    private_key_pem = f.read()

private_key = serialization.load_pem_private_key(private_key_pem, password=None)

# 构建payload - 和代码一致
params = {
    "timestamp": "1771795258481",
    "recvWindow": "5000"
}
sorted_params = {k: params[k] for k in sorted(params.keys())}
payload = urlencode(sorted_params, encoding='UTF-8')

print(f"Payload: {payload}")

# 签名 - ASCII编码
signature = private_key.sign(payload.encode('ASCII'))
signature_b64 = base64.b64encode(signature).decode("utf-8")

print(f"Signature: {signature_b64}")
print(f"URL中显示: {signature_b64.replace('+', '%2B').replace('/', '%2F').replace('=', '%3D')}")
