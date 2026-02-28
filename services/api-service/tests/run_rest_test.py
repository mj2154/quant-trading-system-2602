#!/usr/bin/env python3
"""快速测试 REST API"""

import asyncio
import sys
sys.path.insert(0, "/app/tests/e2e")

from test_spot_rest_e2e import TestSpotRestE2E


async def main():
    print("=" * 60)
    print("REST API 测试")
    print("=" * 60)

    t = TestSpotRestE2E()
    await t.setup()

    try:
        print("\n1. 测试 Config...")
        await t.test_config()

        print("\n2. 测试 Search Symbols...")
        await t.test_search_symbols()

        print("\n3. 测试 Klines...")
        await t.test_klines()

        print("\n4. 测试 Quotes...")
        await t.test_quotes()

        print("\n" + "=" * 60)
        print(f"结果: {t.test_results['passed']} 通过, {t.test_results['failed']} 失败")
        print("=" * 60)

    finally:
        await t.teardown()


if __name__ == "__main__":
    asyncio.run(main())
