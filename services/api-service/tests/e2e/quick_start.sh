#!/bin/bash

# 端到端测试快速启动脚本（简化版）
# 支持快速WebSocket测试（15秒内完成）
# 作者: Claude Code
# 版本: v2.0.0

echo "================================================================================"
echo "🚀 端到端测试快速启动（简化版）"
echo "================================================================================"

# 检查后端服务是否启动
echo "🔍 检查后端服务状态..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 后端服务正在运行"
else
    echo "⚠️ 后端服务未启动"
    echo "请先启动后端服务:"
    echo "  docker-compose up -d"
    echo ""
    read -p "是否现在启动后端服务? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "启动后端服务..."
        docker-compose up -d
        echo "等待服务启动..."
        sleep 5
    else
        echo "❌ 请先启动后端服务"
        exit 1
    fi
fi

echo ""
echo "📋 可用的测试选项:"
echo "================================================================================"
echo "1. 运行所有WebSocket测试（现货+期货）"
echo "2. 运行现货WebSocket测试"
echo "3. 运行期货WebSocket测试"
echo "4. 超快速测试（10秒）"
echo "5. 运行现货REST API测试"
echo "6. 运行期货REST API测试"
echo "7. 运行演示测试"
echo "0. 退出"
echo "================================================================================"
echo ""

read -p "请选择 (0-7): " choice

case $choice in
    1)
        echo "🚀 运行所有WebSocket测试..."
        uv run python tests/e2e/run_e2e_tests.py
        ;;
    2)
        echo "🚀 运行现货WebSocket测试..."
        uv run python tests/e2e/run_e2e_tests.py --spot-only
        ;;
    3)
        echo "🚀 运行期货WebSocket测试..."
        uv run python tests/e2e/run_e2e_tests.py --futures-only
        ;;
    4)
        echo "⚡ 运行超快速测试..."
        uv run python tests/e2e/quick_test.py
        ;;
    5)
        echo "🚀 运行现货REST API测试..."
        uv run python tests/e2e/test_spot_rest_e2e.py
        ;;
    6)
        echo "🚀 运行期货REST API测试..."
        uv run python tests/e2e/test_futures_rest_e2e.py
        ;;
    7)
        echo "🚀 运行演示测试..."
        uv run python tests/e2e/demo_test.py
        ;;
    0)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "================================================================================"
echo "✅ 测试完成（简化版测试 - 15秒快速验证）"
echo "================================================================================"
