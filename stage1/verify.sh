#!/bin/bash

# 验证脚本 - 用于测试所有功能是否正常工作

set -e  # 遇到错误立即退出

echo "========================================"
echo "Stage 1 验证脚本"
echo "========================================"

# 检查环境变量
if ! grep -q "polygon-mainnet.g.alchemy.com" .env 2>/dev/null || grep -q "YOUR_API_KEY" .env 2>/dev/null; then
    echo ""
    echo "⚠️  警告: 请先配置 .env 文件中的 RPC_URL"
    echo ""
    echo "步骤："
    echo "1. 访问 https://www.alchemy.com/ 或 https://www.infura.io/"
    echo "2. 注册并创建一个 Polygon Mainnet 项目"
    echo "3. 复制 RPC URL"
    echo "4. 编辑 .env 文件，替换 YOUR_API_KEY"
    echo ""
    echo "示例："
    echo "RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/你的API密钥"
    echo ""
    exit 1
fi

echo ""
echo "✓ 环境变量配置检查通过"

# 测试示例交易哈希
TX_HASH="0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946"
# 使用市场 ID 而不是 slug（Gamma API 需要 ID）
MARKET_ID="12"

echo ""
echo "========================================"
echo "测试 1/3: 交易解码器"
echo "========================================"
python -m src.trade_decoder --tx-hash "$TX_HASH" --output ./data/trades_test.json

if [ -f ./data/trades_test.json ]; then
    echo "✓ 交易解码成功，结果已保存到 ./data/trades_test.json"
    echo ""
    echo "结果摘要:"
    python -c "import json; data=json.load(open('./data/trades_test.json')); print(f'  交易数: {len(data)}'); [print(f'  Trade {i+1}: {t[\"side\"]} @ {t[\"price\"]}') for i, t in enumerate(data)]"
else
    echo "✗ 交易解码失败"
    exit 1
fi

echo ""
echo "========================================"
echo "测试 2/3: 市场解码器"
echo "========================================"
python -m src.market_decoder --market-slug "$MARKET_ID" --output ./data/market_test.json

if [ -f ./data/market_test.json ]; then
    echo "✓ 市场解码成功，结果已保存到 ./data/market_test.json"
    echo ""
    echo "结果摘要:"
    python -c "import json; data=json.load(open('./data/market_test.json')); print(f'  Condition ID: {data[\"condition_id\"][:16]}...'); print(f'  Oracle: {data[\"oracle\"]}'); print(f'  YES Token: {data[\"yes_token_id\"][:16]}...'); print(f'  NO Token: {data[\"no_token_id\"][:16]}...')"
else
    echo "✗ 市场解码失败"
    exit 1
fi

echo ""
echo "========================================"
echo "测试 3/3: 综合演示"
echo "========================================"
python -m src.demo \
    --tx-hash "$TX_HASH" \
    --event-slug "$MARKET_ID" \
    --output ./data/demo_test.json

if [ -f ./data/demo_test.json ]; then
    echo "✓ 综合演示成功，结果已保存到 ./data/demo_test.json"
else
    echo "✗ 综合演示失败"
    exit 1
fi

echo ""
echo "========================================"
echo "✓ 所有测试通过！"
echo "========================================"
echo ""
echo "生成的文件:"
echo "  - ./data/trades_test.json"
echo "  - ./data/market_test.json"
echo "  - ./data/demo_test.json"
echo ""
