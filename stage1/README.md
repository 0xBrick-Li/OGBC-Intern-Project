# Stage 1: Polymarket 架构与链上数据解码

本项目实现了 Polymarket 链上数据的解析功能，包括交易解码和市场参数解码。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入有效的 Polygon RPC URL
```

### 3. 运行示例

#### 任务 A: 交易解码器

```bash
# 解析指定交易的 OrderFilled 事件
python -m src.trade_decoder --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946

# 输出到文件
python -m src.trade_decoder \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --output ./data/trades.json
```

#### 任务 B: 市场解码器

```bash
# 通过 Gamma API slug 获取市场信息并计算 TokenId
python -m src.market_decoder \
    --market-slug will-there-be-another-us-government-shutdown-by-january-31

# 输出到文件
python -m src.market_decoder \
    --market-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --output ./data/market.json
```

#### 综合演示

```bash
python -m src.demo \
    --tx-hash 0x916cad96dd5c219997638133512fd17fe7c1ce72b830157e4fd5323cf4f19946 \
    --event-slug will-there-be-another-us-government-shutdown-by-january-31 \
    --output ./data/demo_output.json
```

## 项目结构

```
stage1/
├── src/
│   ├── __init__.py
│   ├── trade_decoder.py      # 任务 A: 交易解码器
│   ├── market_decoder.py     # 任务 B: 市场解码器
│   ├── demo.py               # 综合演示
│   ├── ctf/
│   │   ├── __init__.py
│   │   └── derive.py         # CTF Token ID 计算
│   └── indexer/
│       ├── __init__.py
│       └── gamma.py          # Gamma API 客户端
├── data/                     # 输出数据目录
├── requirements.txt
├── .env.example
└── README.md
```

## 核心功能

### 交易解码器 (Trade Decoder)

解析 Polymarket 链上交易日志，还原交易详情：
- 价格、数量、方向
- Maker/Taker 信息
- Token ID 识别
- 买卖方向判定

### 市场解码器 (Market Decoder)

解析市场创建参数，计算链上 Token ID：
- Condition ID 解析
- YES/NO Token ID 计算
- 与 Gamma API 数据验证

## 技术细节

详细的技术说明请参阅 [stage1.md](stage1.md)
