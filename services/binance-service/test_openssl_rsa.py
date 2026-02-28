"""
使用官方openssl命令测试RSA签名
"""

import subprocess
import base64

# 使用官方示例的测试数据
payload = "timestamp=1671090801999&recvWindow=9999999&symbol=BTCUSDT&side=SELL&type=MARKET&quantity=1.23"

# 使用我们的私钥
key_path = "/app/keys/private_rsa.pem"

# 执行openssl签名命令
cmd = f"echo -n '{payload}' | openssl dgst -keyform PEM -sha256 -sign {key_path}"
result = subprocess.run(cmd, shell=True, capture_output=True)

# Base64编码
signature = base64.b64encode(result.stdout).decode('ascii')

# 移除换行
signature = signature.replace('\n', '')

print(f"Payload: {payload}")
print(f"Signature: {signature}")

# URL编码
from urllib.parse import quote
encoded = quote(signature, safe='')
print(f"URL Encoded: {encoded}")
