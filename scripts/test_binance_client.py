"""
币安API客户端测试程序

通过代理访问币安API，测试以下功能：
- 服务器时间获取
- 交易所信息获取
- K线历史数据获取

直接使用httpx，不依赖内部模块
"""

import asyncio
import httpx
import os
from datetime import datetime, timezone


class BinanceAPITester:
    """币安API测试客户端"""

    BASE_URL = "https://api.binance.com"
    API_VERSION = "v3"

    def __init__(self, proxy_url: str | None) -> None:
        """初始化测试客户端

        Args:
            proxy_url: HTTP代理地址
        """
        self.proxy_url = proxy_url

        # 配置传输层
        if proxy_url:
            transport = httpx.AsyncHTTPTransport(proxy=proxy_url)
        else:
            transport = None

        self.client = httpx.AsyncClient(
            timeout=10.0,
            transport=transport,
            # http2=True,  # 需要安装 h2 包
        )
        print(f"初始化完成，代理URL: {proxy_url or '直连'}")

    async def test_server_time(self) -> bool:
        """测试服务器时间接口"""
        print("\n" + "=" * 50)
        print("测试1: 获取服务器时间")
        print("=" * 50)

        try:
            response = await self.client.get(f"{self.BASE_URL}/api/{self.API_VERSION}/time")
            response.raise_for_status()
            data = response.json()
            server_time_ms = data["serverTime"]
            server_time = datetime.fromtimestamp(server_time_ms / 1000)

            print(f"服务器时间戳(毫秒): {server_time_ms}")
            print(f"服务器时间: {server_time.isoformat()}")
            print(f"当前本地时间: {datetime.now(timezone.utc).isoformat()}")

            assert server_time_ms > 0, "服务器时间应为正数"

            print("结果: PASS")
            return True

        except Exception as e:
            print(f"结果: FAIL - {e}")
            return False

    async def test_exchange_info(self) -> bool:
        """测试交易所信息接口"""
        print("\n" + "=" * 50)
        print("测试2: 获取交易所信息")
        print("=" * 50)

        try:
            response = await self.client.get(f"{self.BASE_URL}/api/{self.API_VERSION}/exchangeInfo")
            response.raise_for_status()
            info = response.json()

            symbols = info.get("symbols", [])
            timezone = info.get("timezone", "N/A")
            server_time = info.get("serverTime", 0)

            print(f"交易所时区: {timezone}")
            print(f"服务器时间戳: {server_time}")
            print(f"交易对数量: {len(symbols)}")

            if symbols:
                symbol_list = [s["symbol"] for s in symbols[:10]]
                print(f"前10个交易对: {', '.join(symbol_list)}")
                if len(symbols) > 10:
                    print(f"... 等共 {len(symbols)} 个交易对")

            assert isinstance(symbols, list), "symbols应为列表"
            assert len(symbols) > 0, "应有交易对数据"

            print("结果: PASS")
            return True

        except Exception as e:
            print(f"结果: FAIL - {e}")
            return False

    async def test_klines(self, symbol: str = "BTCUSDT", interval: str = "1h") -> bool:
        """测试K线数据接口"""
        print("\n" + "=" * 50)
        print(f"测试3: 获取K线数据 ({symbol}, {interval})")
        print("=" * 50)

        try:
            params = {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": 5,
            }
            response = await self.client.get(
                f"{self.BASE_URL}/api/{self.API_VERSION}/klines",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            print(f"交易对: {symbol.upper()}")
            print(f"数据条数: {len(data)}")

            if data:
                latest = data[-1]
                first = data[0]

                print(f"\n最新K线:")
                print(f"  时间: {datetime.fromtimestamp(latest[0] / 1000).isoformat()}")
                print(f"  开盘: {latest[1]}")
                print(f"  最高: {latest[2]}")
                print(f"  最低: {latest[3]}")
                print(f"  收盘: {latest[4]}")
                print(f"  成交量: {latest[5]}")

                print(f"\n最老K线:")
                print(f"  时间: {datetime.fromtimestamp(first[0] / 1000).isoformat()}")

                # 验证数据顺序
                for i in range(1, len(data)):
                    assert data[i][0] >= data[i-1][0], "K线应按时间排序"

            print("结果: PASS")
            return True

        except Exception as e:
            print(f"结果: FAIL - {e}")
            return False

    async def run_all(self) -> dict:
        """运行所有测试"""
        print("\n" + "#" * 50)
        print("# 币安API客户端测试程序")
        print("# " + datetime.now().isoformat())
        print("#" * 50)

        results = {
            "server_time": await self.test_server_time(),
            "exchange_info": await self.test_exchange_info(),
            "klines": await self.test_klines(),
        }

        print("\n" + "=" * 50)
        print("测试汇总")
        print("=" * 50)

        passed = sum(results.values())
        total = len(results)

        for test_name, passed_test in results.items():
            status = "PASS" if passed_test else "FAIL"
            print(f"  {test_name}: {status}")

        print(f"\n总计: {passed}/{total} 测试通过")

        await self.client.aclose()

        return results


async def main():
    """主函数"""
    proxy_url = os.getenv("CLASH_PROXY_HTTP_URL")
    if proxy_url:
        print(f"从环境变量读取代理: {proxy_url}")
    else:
        # Docker容器外通过 localhost:7890 访问
        proxy_url = "http://localhost:7890"
        print(f"使用默认代理: {proxy_url}")

    tester = BinanceAPITester(proxy_url=proxy_url)
    results = await tester.run_all()

    if all(results.values()):
        print("\n所有测试通过!")
        return 0
    else:
        print("\n部分测试失败!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
