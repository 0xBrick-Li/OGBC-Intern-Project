# Stage 1 快速开始指南

## 1. 安装依赖

```bash
cd stage1
pip install -r requirements.txt
```

## 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env，添加你的 Polygon RPC URL
```

获取免费 RPC URL：
- Alchemy: https://www.alchemy.com/
- Infura: https://www.infura.io/

## 3. 测试基础功能

测试 CTF Token ID 计算（无需 RPC）：
```bash
python -m src.ctf.derive
```

## 4. 运行任务

### 任务 A: 交易解码器

```bash
python -m src.trade_decoder \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --output ./data/trades.json
```

### 任务 B: 市场解码器

```bash
# 使用有效的市场 slug
python -m src.market_decoder \
    --market-slug <市场slug> \
    --output ./data/market.json
```

### 综合演示

```bash
python -m src.demo \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --event-slug <市场slug> \
    --output ./data/demo_output.json
```

## 5. 完整验证

配置好 RPC URL 和有效的 market slug 后：

```bash
./verify.sh
```

## 项目结构

```
stage1/
├── src/
│   ├── trade_decoder.py      # 任务 A
│   ├── market_decoder.py     # 任务 B
│   ├── demo.py               # 综合演示
│   ├── ctf/derive.py         # Token ID 计算
│   └── indexer/gamma.py      # Gamma API
├── data/                     # 输出目录
├── requirements.txt
├── .env
└── verify.sh
```

## 核心功能

### 交易解码器
- 解析 OrderFilled 事件
- 计算交易价格
- 判断买卖方向
- 识别 Token ID

### 市场解码器
- 计算 YES/NO Token ID
- 验证与 Gamma API 数据
- 解析链上创建事件

### Token ID 计算
- 基于 Gnosis CTF 框架
- 支持二元市场
- 精确的哈希计算

## 注意事项

1. **RPC URL**: 交易解码需要有效的 Polygon RPC
2. **Market Slug**: 使用当前有效的市场标识
3. **速率限制**: 注意 API 调用频率

## 帮助

详细说明请查看：
- [README.md](README.md) - 项目说明
- [stage1.md](stage1.md) - 完整任务文档
- [COMPLETED.md](COMPLETED.md) - 完成说明
