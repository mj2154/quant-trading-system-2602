#!/usr/bin/env python3
"""
代理延迟检测和切换脚本

功能：
1. 检测 Clash 代理延迟
2. 当延迟 > 100ms 时自动切换代理
3. 持续监控并记录延迟变化

使用方式：
- 手动运行：python3 check_proxy_latency.py
- 定时任务：crontab 或 systemd timer

作者: Claude Code
版本: v1.0.0
"""

import asyncio
import logging

import aiohttp

# 配置
CLASH_API_URL = "http://localhost:9090"
CLASH_API_SECRET = "clash-secret-key-2024"
PROXY_THRESHOLD_MS = 100  # 延迟阈值：100ms

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ProxyLatencyChecker:
    """代理延迟检测器"""

    def __init__(self):
        self.clash_api_url = CLASH_API_URL
        self.clash_secret = CLASH_API_SECRET
        self.threshold = PROXY_THRESHOLD_MS

    async def get_proxy_list(self) -> list[dict]:
        """获取 Clash 代理列表"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.clash_api_url}/proxies",
                    headers={"Authorization": f"Bearer {self.clash_secret}"},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("proxies", [])
                    else:
                        logger.error(f"Failed to get proxy list: {resp.status}")
                        return []
        except Exception as e:
            logger.error(f"Error getting proxy list: {e!s}")
            return []

    async def test_proxy_delay(self, proxy_name: str) -> float | None:
        """测试单个代理的延迟"""
        try:
            # 通过 Clash API 测试延迟
            async with aiohttp.ClientSession() as session:
                # 调用延迟测试接口
                async with session.get(
                    f"{self.clash_api_url}/proxies/{proxy_name}/delay",
                    headers={"Authorization": f"Bearer {self.clash_secret}"},
                    params={"url": "http://www.gstatic.com/generate_204", "timeout": 5000},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        delay = data.get("delay")
                        if delay:
                            return float(delay)
                    else:
                        logger.warning(f"Delay test failed for {proxy_name}: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"Error testing proxy {proxy_name}: {e!s}")
            return None

    async def switch_proxy(self, proxy_name: str) -> bool:
        """切换到指定代理"""
        try:
            async with aiohttp.ClientSession() as session:
                # 调用切换接口
                async with session.put(
                    f"{self.clash_api_url}/proxies/自动选择",
                    headers={"Authorization": f"Bearer {self.clash_secret}"},
                    json={"name": proxy_name},
                ) as resp:
                    if resp.status == 204:
                        logger.info(f"Successfully switched to proxy: {proxy_name}")
                        return True
                    else:
                        logger.error(f"Failed to switch proxy: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"Error switching proxy: {e!s}")
            return False

    async def get_current_proxy(self) -> str | None:
        """获取当前选中的代理"""
        proxies = await self.get_proxy_list()
        for proxy in proxies:
            if proxy.get("name") == "自动选择":
                history = proxy.get("history", [])
                if history:
                    return history[-1].get("name")
                break
        return None

    async def check_and_switch(self):
        """检查延迟并在需要时切换代理"""
        proxies = await self.get_proxy_list()
        if not proxies:
            logger.warning("No proxies found")
            return

        current_proxy = await self.get_current_proxy()
        logger.info(f"Current proxy: {current_proxy}")

        # 测试每个代理的延迟
        proxy_delays = []
        for proxy in proxies:
            name = proxy.get("name")
            if name and name not in ["自动选择", "DIRECT", "REJECT"]:
                delay = await self.test_proxy_delay(name)
                if delay is not None:
                    proxy_delays.append({"name": name, "delay": delay})
                    logger.info(f"Proxy {name}: {delay:.0f}ms")

        if not proxy_delays:
            logger.warning("No proxy delay data available")
            return

        # 找到延迟 < 100ms 的代理
        good_proxies = [p for p in proxy_delays if p["delay"] < self.threshold]
        good_proxies.sort(key=lambda x: x["delay"])  # 按延迟排序

        if not good_proxies:
            logger.warning(f"All proxies exceed threshold ({self.threshold}ms)")
            # 如果所有代理都超过阈值，选择延迟最低的
            best_proxy = proxy_delays[0]
            logger.info(
                f"Using lowest latency proxy: {best_proxy['name']} ({best_proxy['delay']:.0f}ms)"
            )
            return

        # 如果当前代理延迟正常，不切换
        if current_proxy in [p["name"] for p in good_proxies]:
            logger.info(f"Current proxy {current_proxy} is within threshold")
            return

        # 切换到最优代理
        best_proxy = good_proxies[0]
        logger.info(
            f"Switching to proxy: {best_proxy['name']} (delay: {best_proxy['delay']:.0f}ms)"
        )
        await self.switch_proxy(best_proxy["name"])


async def main():
    """主函数"""
    checker = ProxyLatencyChecker()

    # 运行一次检查
    await checker.check_and_switch()

    # 如果需要持续监控，可以取消注释下面的循环
    # while True:
    #     await checker.check_and_switch()
    #     await asyncio.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    asyncio.run(main())
