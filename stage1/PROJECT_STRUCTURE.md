# Stage 1 项目结构

```
stage1/
│
├── 📄 配置文件
│   ├── .env.example              # 环境变量示例
│   ├── .env                      # 环境变量配置（需用户配置 RPC_URL）
│   ├── .gitignore               # Git 忽略规则
│   └── requirements.txt          # Python 依赖
│
├── 📚 文档
│   ├── README.md                 # 项目说明
│   ├── stage1.md                 # 完整任务文档
│   ├── COMPLETED.md              # 完成说明和详细指南
│   └── QUICKSTART.md             # 快速开始指南
│
├── 🔧 脚本
│   └── verify.sh                 # 自动验证脚本
│
├── 💾 数据目录
│   └── data/                     # 输出数据存储
│       └── .gitkeep
│
└── 🐍 源代码
    └── src/
        ├── __init__.py
        │
        ├── 📦 核心模块
        │   ├── trade_decoder.py      # 任务 A: 交易解码器
        │   ├── market_decoder.py     # 任务 B: 市场解码器
        │   └── demo.py               # 综合演示脚本
        │
        ├── 🧮 CTF 工具
        │   └── ctf/
        │       ├── __init__.py
        │       └── derive.py         # Token ID 计算工具
        │
        └── 🌐 API 客户端
            └── indexer/
                ├── __init__.py
                └── gamma.py          # Gamma API 客户端
```

## 文件说明

### 核心实现

#### `src/trade_decoder.py` - 任务 A
- **功能**: 解析 Polymarket 交易日志
- **输入**: 交易哈希 (tx_hash)
- **输出**: 交易详情 JSON（价格、数量、方向等）
- **关键**: 
  - 解析 `OrderFilled` 事件
  - 计算成交价格
  - 判断买卖方向
  - 过滤重复日志

#### `src/market_decoder.py` - 任务 B
- **功能**: 解析市场参数并计算 Token ID
- **输入**: Market slug 或 ConditionPreparation 交易
- **输出**: 市场参数 JSON（Condition ID, Oracle, Token IDs）
- **关键**:
  - 从 Gamma API 获取市场数据
  - 计算 YES/NO Token ID
  - 验证计算结果

#### `src/demo.py` - 综合演示
- **功能**: 整合交易解析和市场解码
- **输入**: 交易哈希 + 市场 slug
- **输出**: 完整分析结果
- **关键**:
  - 匹配交易与市场
  - 识别交易的 YES/NO 方向
  - 生成综合报告

### 工具库

#### `src/ctf/derive.py` - CTF Token ID 计算
- **功能**: 实现 Gnosis Conditional Token Framework 算法
- **核心函数**:
  - `get_condition_id()`: 计算 Condition ID
  - `get_collection_id()`: 计算 Collection ID
  - `get_position_id()`: 计算 Position ID
  - `derive_binary_positions()`: 计算二元市场 YES/NO Token ID
- **特点**: 
  - 纯算法实现，无需链上查询
  - 支持独立测试

#### `src/indexer/gamma.py` - Gamma API 客户端
- **功能**: 与 Polymarket Gamma API 交互
- **核心函数**:
  - `fetch_event_by_slug()`: 获取事件信息
  - `fetch_market_by_slug()`: 获取市场信息
  - `extract_market_params()`: 提取关键参数
- **特点**:
  - 无需 RPC 连接
  - 提供市场元数据

### 配置和脚本

#### `requirements.txt`
```
web3>=6.0.0           # Web3 交互
python-dotenv>=1.0.0  # 环境变量
requests>=2.31.0      # HTTP 请求
eth-abi>=4.0.0        # ABI 编解码
```

#### `.env.example` / `.env`
```env
RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_API_KEY
GAMMA_API_BASE_URL=https://gamma-api.polymarket.com
```

#### `verify.sh`
- 自动化验证脚本
- 依次测试所有功能
- 生成测试报告

## 使用流程

```
1. 安装依赖
   ↓
2. 配置 RPC URL
   ↓
3. 运行 trade_decoder
   ↓
4. 运行 market_decoder
   ↓
5. 运行 demo (综合)
   ↓
6. 验证结果
```

## 数据流

```
交易哈希
   ↓
[trade_decoder]
   ↓
OrderFilled 事件
   ↓
交易详情 (价格、方向、Token ID)

Market Slug
   ↓
[Gamma API]
   ↓
市场元数据 (Condition ID, Question ID)
   ↓
[CTF derive]
   ↓
Token IDs (YES/NO)

交易详情 + 市场参数
   ↓
[demo]
   ↓
完整分析 (匹配交易与市场)
```

## 关键常量

- **USDC 地址**: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
- **CTF Exchange**: `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`
- **NegRisk Exchange**: `0xC5d563A36AE78145C45a50134d48A1215220f80a`
- **ConditionalTokens**: `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`

## 输出示例

### Trade Decoder 输出
```json
{
  "tx_hash": "0x916cad...",
  "log_index": 123,
  "exchange": "0xC5d563A36AE78145C45a50134d48A1215220f80a",
  "maker": "0x...",
  "taker": "0x...",
  "price": "0.52",
  "token_id": "0x1234...",
  "side": "BUY"
}
```

### Market Decoder 输出
```json
{
  "condition_id": "0xabc...",
  "oracle": "0x157Ce...",
  "question_id": "0xdef...",
  "yes_token_id": "0xAAA...",
  "no_token_id": "0xBBB..."
}
```
